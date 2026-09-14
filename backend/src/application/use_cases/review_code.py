import time
import uuid
from datetime import datetime, timezone
from src.domain.models.agents import AgentType

from src.application.services.code_review_service import CodeReviewService
from src.application.use_cases.agent_execution import ExecuteAgentWorkflowUseCase
from src.domain.entities.code_review import CodeReviewCreate, ReviewStatusEnum
from src.core.errors import LLMQuotaExceededError, WorkflowExecutionError
from src.core.logger import logger
from typing import Dict, Any, Optional
import asyncio

class ReviewCodeUseCase:
    def __init__(
        self,
        code_review_service: CodeReviewService,
        agent_executor: ExecuteAgentWorkflowUseCase,
    ):
        self.review_service = code_review_service
        self.agent_executor = agent_executor

    async def execute(
        self,
        repository_id: str,
        user_id: str,
        files_to_review: Optional[list[str]] = None,
        review_id: Optional[str] = None,
        review_config: Optional[Any] = None,
    ) -> Dict[str, Any]:
        
        if review_id is None:
            review_id = str(uuid.uuid4())
            review_data = CodeReviewCreate(repository_id=repository_id)
            self.review_service.create_review(review_data, user_id, review_id)
        
        # Update status to IN_PROGRESS (Preparing stage - 10%)
        self.review_service.update_review_status(
            review_id,
            ReviewStatusEnum.IN_PROGRESS,
            progress_percent=10,
            current_stage="preparing",
            progress_message="Initializing review pipeline…",
        )

        # Parse review configuration
        config_dict = (
            review_config.model_dump()
            if hasattr(review_config, "model_dump")
            else (review_config or {})
        )
        strictness = config_dict.get("strictness", "medium")
        code_quality_enabled = config_dict.get("code_quality", config_dict.get("codeQuality", True))
        documentation_enabled = config_dict.get("documentation", True)
        architecture_enabled = config_dict.get("architecture", False)
        security_enabled = config_dict.get("security", True)
        performance_enabled = config_dict.get("performance", True)

        query = f"Perform a structured code review of the repository with strictness level '{strictness}'."
        checks = []
        if security_enabled: checks.append("security vulnerabilities")
        if performance_enabled: checks.append("performance optimization")
        if architecture_enabled: checks.append("architecture design")
        if code_quality_enabled: checks.append("code quality and readability")
        if documentation_enabled: checks.append("documentation completeness")
        if checks:
            query += f" Evaluate the following requested check categories: {', '.join(checks)}."
        if files_to_review:
            query += f" Focus specifically on these files: {', '.join(files_to_review)}."

        import asyncio

        start_time = time.perf_counter()
        
        last_progress_percent = 10
        last_stage = "preparing"

        async def on_progress(stage: str, percent: int, msg: str):
            nonlocal last_progress_percent, last_stage
            # Guard: check if review was cancelled
            rev = self.review_service.get_review(review_id)
            if rev and rev.status == ReviewStatusEnum.CANCELLED.value:
                raise asyncio.CancelledError("Review cancelled by user")
            last_progress_percent = max(last_progress_percent, min(99, percent))
            last_stage = stage
            self.review_service.update_review_status(
                review_id,
                ReviewStatusEnum.IN_PROGRESS,
                progress_percent=percent,
                current_stage=stage,
                progress_message=msg,
            )

        try:
            result = await self.agent_executor.execute(
                query=query,
                repo_id=repository_id,
                user_id=user_id,
                review_config=config_dict,
                on_progress=on_progress,
            )
            
            if result.get("error"):
                raise RuntimeError(f"Agent workflow execution failed: {result['error']}")

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Race condition protection: verify review has not been cancelled before persistence
            rev_check = self.review_service.get_review(review_id)
            if rev_check and rev_check.status == ReviewStatusEnum.CANCELLED.value:
                logger.info("code_review_cancelled_before_persistence", review_id=review_id)
                return {
                    "review_id": review_id,
                    "status": "cancelled",
                    "findings": [],
                    "duration_ms": duration_ms,
                }
            
            await on_progress("persisting", 90, "Saving structured review report…")

            agent_outputs = result.get("agent_outputs", {})
            confidence = result.get("confidence_score", 1.0)

            # Code review findings
            code_review_output = agent_outputs.get(AgentType.CODE_REVIEW.value, {})
            code_review_findings = code_review_output.get("structured_findings", [])

            # Security review findings
            if security_enabled:
                security_output = agent_outputs.get(AgentType.SECURITY_REVIEW.value, {})
                security_findings = security_output.get("structured_findings", [])
                # Normalize security findings to have compatible schema
                for sf in security_findings:
                    if "issue" not in sf and "vulnerability" in sf:
                        sf["issue"] = sf["vulnerability"]
                    if "confidence_score" not in sf and "confidence" in sf:
                        sf["confidence_score"] = sf["confidence"]
            else:
                security_findings = []

            # Combined findings for review.findings_json (code quality + security)
            findings = list(code_review_findings) + list(security_findings)

            # Performance findings & scores
            if performance_enabled:
                performance_output = agent_outputs.get(AgentType.PERFORMANCE.value, {})
                performance_findings = performance_output.get("structured_findings", [])
                
                def calculate_performance_score(findings: list) -> float:
                    if not findings:
                        return 100.0
                    severity_weights = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
                    total_weight = sum(severity_weights.get(f.get("severity", "info").lower(), 1) for f in findings)
                    max_possible = len(findings) * 5
                    score = (1.0 - (total_weight / max_possible)) * 100 if max_possible else 100.0
                    return round(max(0.0, score), 2)

                if performance_output:
                    performance_score = calculate_performance_score(performance_findings)
                else:
                    performance_score = None

                performance_recommendations = []
                estimated_cpu_savings = 0.0
                estimated_memory_savings = 0.0
                estimated_latency_improvement = 0.0
                for f in performance_findings:
                    gain = f.get("expected_performance_gain")
                    try:
                        gain_val = float(str(gain).replace('%', '').strip())
                    except Exception:
                        gain_val = 0.0
                    estimated_cpu_savings += gain_val
                    estimated_memory_savings += gain_val * 0.5
                    estimated_latency_improvement += gain_val * 0.3
                    if f.get("suggested_optimization"):
                        performance_recommendations.append({
                            "title": f["suggested_optimization"],
                            "description": f.get("root_cause", ""),
                            "impact_estimate": f.get("expected_performance_gain", "")
                        })
            else:
                performance_findings = []
                performance_score = None
                performance_recommendations = []
                estimated_cpu_savings = 0.0
                estimated_memory_savings = 0.0
                estimated_latency_improvement = 0.0

            # Refactoring analysis output
            refactoring_output = agent_outputs.get(AgentType.REFACTORING_ANALYSIS.value, {})
            refactoring_findings = refactoring_output.get("structured_findings", [])
            refactoring_priority = refactoring_output.get("overall_priority", "medium") if refactoring_output else None
            estimated_refactoring_effort = refactoring_output.get("estimated_total_effort_hours", 0.0)
            estimated_maintainability_improvement = refactoring_output.get("estimated_maintainability_improvement", 0.0)
            estimated_technical_debt_reduction = refactoring_output.get("estimated_technical_debt_reduction", 0.0)
            estimated_complexity_reduction = refactoring_output.get("estimated_complexity_reduction", 0.0)

            # Architecture & Code Quality output
            if architecture_enabled or code_quality_enabled:
                code_quality_output = agent_outputs.get(AgentType.CODE_QUALITY.value, {})
                architecture_findings = code_quality_output.get("structured_findings", [])
                quality_metrics = code_quality_output.get("metrics", {})
                dependency_analysis = code_quality_output.get("dependency_analysis", {})

                if quality_metrics:
                    overall_health_score = quality_metrics.get("overall_health_score")
                    architecture_score = quality_metrics.get("architecture_score")
                    maintainability_score = quality_metrics.get("maintainability_score")
                    technical_debt_score = quality_metrics.get("technical_debt_score")
                    complexity_score = quality_metrics.get("complexity_score")
                    documentation_score = quality_metrics.get("documentation_score")
                    modularity_score = quality_metrics.get("modularity_score")
                    testability_score = quality_metrics.get("testability_score")
                elif code_quality_output:
                    # Agent ran but metrics dict was omitted
                    if architecture_findings:
                        overall_health_score = max(30.0, round(100.0 - (len(architecture_findings) * 6.5), 1))
                        architecture_score = max(40.0, round(100.0 - (len(architecture_findings) * 5.0), 1))
                        maintainability_score = max(35.0, round(100.0 - (len(architecture_findings) * 6.0), 1))
                        technical_debt_score = max(25.0, round(100.0 - (len(architecture_findings) * 7.0), 1))
                        complexity_score = 75.0
                        documentation_score = 80.0
                        modularity_score = 75.0
                        testability_score = 75.0
                    else:
                        overall_health_score = 100.0
                        architecture_score = 100.0
                        maintainability_score = 100.0
                        technical_debt_score = 100.0
                        complexity_score = 100.0
                        documentation_score = 100.0
                        modularity_score = 100.0
                        testability_score = 100.0
                else:
                    # Code quality / architecture agent was not executed
                    overall_health_score = None
                    architecture_score = None
                    maintainability_score = None
                    technical_debt_score = None
                    complexity_score = None
                    documentation_score = None
                    modularity_score = None
                    testability_score = None
            else:
                architecture_findings = []
                dependency_analysis = {}
                overall_health_score = None
                architecture_score = None
                maintainability_score = None
                technical_debt_score = None
                complexity_score = None
                documentation_score = None
                modularity_score = None
                testability_score = None

            # Safe structured logging of counts
            logger.info(
                "review_findings_summary",
                review_id=review_id,
                raw_findings_count=len(code_review_findings) + len(security_findings) + len(performance_findings) + len(architecture_findings),
                parsed_findings_count=len(findings) + len(performance_findings) + len(architecture_findings),
                code_quality_count=len(code_review_findings),
                security_count=len(security_findings),
                performance_count=len(performance_findings),
                architecture_count=len(architecture_findings),
                overall_health_score=overall_health_score,
                performance_score=performance_score,
            )

            # Build per-category execution metadata (real data only – no fabrication)
            now_iso = datetime.now(timezone.utc).isoformat()
            category_metadata: dict = {}

            if code_quality_enabled:
                # The "Code Quality" UI tab shows findings from the code_review agent
                # (stored in findings_json). Use code_review agent output to determine
                # whether this category was actually evaluated.
                cr_output = agent_outputs.get(AgentType.CODE_REVIEW.value, {})
                category_metadata["code_quality"] = {
                    "status": "completed" if cr_output else "not_evaluated",
                    "findings_count": len(code_review_findings),
                    "evaluated_at": now_iso if cr_output else None,
                }
            else:
                category_metadata["code_quality"] = {"status": "not_evaluated", "findings_count": 0}

            if security_enabled:
                sec_output = agent_outputs.get(AgentType.SECURITY_REVIEW.value, {})
                category_metadata["security"] = {
                    "status": "completed" if sec_output else "not_evaluated",
                    "findings_count": len(security_findings),
                    "evaluated_at": now_iso if sec_output else None,
                }
            else:
                category_metadata["security"] = {"status": "not_evaluated", "findings_count": 0}

            if performance_enabled:
                perf_output = agent_outputs.get(AgentType.PERFORMANCE.value, {})
                category_metadata["performance"] = {
                    "status": "completed" if perf_output else "not_evaluated",
                    "findings_count": len(performance_findings),
                    "evaluated_at": now_iso if perf_output else None,
                }
            else:
                category_metadata["performance"] = {"status": "not_evaluated", "findings_count": 0}

            if code_quality_enabled:
                # Refactoring is scheduled by the planner only when code_quality is enabled
                refact_output = agent_outputs.get(AgentType.REFACTORING_ANALYSIS.value, {})
                category_metadata["refactoring"] = {
                    "status": "completed" if refact_output else "not_evaluated",
                    "findings_count": len(refactoring_findings),
                    "evaluated_at": now_iso if refact_output else None,
                }
            else:
                category_metadata["refactoring"] = {"status": "not_evaluated", "findings_count": 0}

            if architecture_enabled or code_quality_enabled:
                # Architecture metrics come from the code_quality architectural agent
                arch_agent_output = agent_outputs.get(AgentType.CODE_QUALITY.value, {})
                category_metadata["architecture"] = {
                    "status": "completed" if arch_agent_output else "not_evaluated",
                    "findings_count": len(architecture_findings),
                    "evaluated_at": now_iso if arch_agent_output else None,
                }
            else:
                category_metadata["architecture"] = {"status": "not_evaluated", "findings_count": 0}

            # Final check before updating DB to COMPLETED
            rev_final = self.review_service.get_review(review_id)
            if rev_final and rev_final.status == ReviewStatusEnum.CANCELLED.value:
                logger.info("code_review_cancelled_before_completion", review_id=review_id)
                return {
                    "review_id": review_id,
                    "status": "cancelled",
                    "findings": [],
                    "duration_ms": duration_ms,
                }

            # 5. Update DB record to COMPLETED (100%)
            updated_review = self.review_service.update_review_status(
                review_id,
                ReviewStatusEnum.COMPLETED,
                progress_percent=100,
                current_stage="completed",
                progress_message="Review completed successfully",
                findings=findings,
                confidence_score=confidence,
                duration_ms=duration_ms,
                performance_findings=performance_findings,
                performance_score=performance_score,
                performance_recommendations=performance_recommendations,
                estimated_cpu_savings=estimated_cpu_savings,
                estimated_memory_savings=estimated_memory_savings,
                estimated_latency_improvement=estimated_latency_improvement,
                refactoring_findings=refactoring_findings,
                refactoring_priority=refactoring_priority,
                estimated_refactoring_effort=estimated_refactoring_effort,
                estimated_maintainability_improvement=estimated_maintainability_improvement,
                estimated_technical_debt_reduction=estimated_technical_debt_reduction,
                estimated_complexity_reduction=estimated_complexity_reduction,
                architecture_findings=architecture_findings,
                overall_health_score=overall_health_score,
                architecture_score=architecture_score,
                maintainability_score=maintainability_score,
                technical_debt_score=technical_debt_score,
                complexity_score=complexity_score,
                documentation_score=documentation_score,
                modularity_score=modularity_score,
                testability_score=testability_score,
                dependency_analysis=dependency_analysis,
                category_metadata=category_metadata,
            )
            
            return {
                "review_id": review_id,
                "status": "completed",
                "findings": findings,
                "duration_ms": duration_ms
            }

        except asyncio.CancelledError:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info("code_review_cancelled_exception", review_id=review_id, duration_ms=duration_ms)
            rev_cancel = self.review_service.get_review(review_id)
            if not rev_cancel or rev_cancel.status != ReviewStatusEnum.CANCELLED.value:
                self.review_service.update_review_status(
                    review_id,
                    ReviewStatusEnum.CANCELLED,
                    progress_percent=min(last_progress_percent, 99),
                    current_stage="cancelled",
                    progress_message="Review cancelled by user",
                    duration_ms=duration_ms,
                )
            return {
                "review_id": review_id,
                "status": "cancelled",
                "findings": [],
                "duration_ms": duration_ms,
            }

        except LLMQuotaExceededError as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            rev_quota = self.review_service.get_review(review_id)
            if rev_quota and rev_quota.status == ReviewStatusEnum.CANCELLED.value:
                return {
                    "review_id": review_id,
                    "status": "cancelled",
                    "findings": [],
                    "duration_ms": duration_ms,
                }
            logger.error(
                "code_review_quota_exceeded",
                review_id=review_id,
                error=str(exc)[:200],
                duration_ms=duration_ms,
            )
            self.review_service.update_review_status(
                review_id,
                ReviewStatusEnum.FAILED,
                progress_percent=min(last_progress_percent, 99),
                current_stage="failed",
                progress_message=f"LLM quota exceeded: {str(exc)[:150]}",
                duration_ms=duration_ms,
            )
            raise

        except WorkflowExecutionError as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            rev_wf = self.review_service.get_review(review_id)
            if rev_wf and rev_wf.status == ReviewStatusEnum.CANCELLED.value:
                return {
                    "review_id": review_id,
                    "status": "cancelled",
                    "findings": [],
                    "duration_ms": duration_ms,
                }
            sanitized = str(exc)[:300]
            logger.error(
                "code_review_workflow_failed",
                review_id=review_id,
                error=sanitized,
                duration_ms=duration_ms,
            )
            self.review_service.update_review_status(
                review_id,
                ReviewStatusEnum.FAILED,
                progress_percent=min(last_progress_percent, 99),
                current_stage="failed",
                progress_message=f"Workflow execution failed: {sanitized[:150]}",
                duration_ms=duration_ms,
            )
            raise

        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            rev_exc = self.review_service.get_review(review_id)
            if rev_exc and rev_exc.status == ReviewStatusEnum.CANCELLED.value:
                return {
                    "review_id": review_id,
                    "status": "cancelled",
                    "findings": [],
                    "duration_ms": duration_ms,
                }
            sanitized = str(exc)[:300]
            logger.error(
                "code_review_failed",
                review_id=review_id,
                error=sanitized,
                duration_ms=duration_ms,
            )
            self.review_service.update_review_status(
                review_id,
                ReviewStatusEnum.FAILED,
                progress_percent=min(last_progress_percent, 99),
                current_stage="failed",
                progress_message=f"Review failed: {sanitized[:150]}",
                duration_ms=duration_ms,
            )
            raise

