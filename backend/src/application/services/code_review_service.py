from typing import List, Optional, Dict, Any
from src.infrastructure.repositories.code_review_repository import CodeReviewRepository
from src.domain.entities.code_review import CodeReviewCreate, ReviewStatusEnum
from src.domain.entities.fix_suggestion import FixSuggestion, FixUserDecision, FixApplicationStatus
from src.domain.entities.verification import StaticVerificationResult
from src.infrastructure.persistence.code_review_models import DBCodeReview

class CodeReviewService:
    def __init__(self, repository: CodeReviewRepository):
        self.repo = repository

    def create_review(self, review_data: CodeReviewCreate, user_id: str, review_id: str) -> DBCodeReview:
        return self.repo.create(review_data, user_id, review_id)

    def get_review(self, review_id: str, user_id: Optional[str] = None) -> Optional[DBCodeReview]:
        return self.repo.get_by_id(review_id, user_id=user_id)

    def get_repository_reviews(self, repository_id: str, user_id: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[DBCodeReview]:
        return self.repo.get_by_repository(repository_id, user_id=user_id, skip=skip, limit=limit)

    def list_user_reviews(
        self,
        user_id: str,
        repository_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[DBCodeReview]:
        return self.repo.list_by_user(
            user_id=user_id,
            repository_id=repository_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    def update_review_status(
        self,
        review_id: str,
        status: ReviewStatusEnum,
        progress_percent: int = None,
        current_stage: str = None,
        progress_message: str = None,
        findings: list = None,
        confidence_score: float = 1.0,
        duration_ms: int = None,
        performance_findings: list = None,
        performance_score: float = None,
        performance_recommendations: list = None,
        estimated_cpu_savings: float = None,
        estimated_memory_savings: float = None,
        estimated_latency_improvement: float = None,
        refactoring_findings: list = None,
        refactoring_priority: str = None,
        estimated_refactoring_effort: float = None,
        estimated_maintainability_improvement: float = None,
        estimated_technical_debt_reduction: float = None,
        estimated_complexity_reduction: float = None,
        architecture_findings: list = None,
        overall_health_score: float = None,
        architecture_score: float = None,
        maintainability_score: float = None,
        technical_debt_score: float = None,
        complexity_score: float = None,
        documentation_score: float = None,
        modularity_score: float = None,
        testability_score: float = None,
        dependency_analysis: dict = None,
    ) -> Optional[DBCodeReview]:
        """Update review status and optional result data."""
        review = self.repo.get_by_id(review_id)
        if not review:
            return None
        # Terminal state protection: CANCELLED reviews must not be overwritten by completed/failed/in_progress
        if review.status == ReviewStatusEnum.CANCELLED.value and status != ReviewStatusEnum.CANCELLED:
            return review
        review.status = status.value
        if progress_percent is not None:
            review.progress_percent = progress_percent
        if current_stage is not None:
            review.current_stage = current_stage
        if progress_message is not None:
            review.progress_message = progress_message
        if findings is not None:

            review.findings_json = findings
        if performance_findings is not None:
            review.performance_findings_json = performance_findings
        if performance_recommendations is not None:
            review.performance_recommendations_json = performance_recommendations
        if estimated_cpu_savings is not None:
            review.estimated_cpu_savings = estimated_cpu_savings
        if estimated_memory_savings is not None:
            review.estimated_memory_savings = estimated_memory_savings
        if estimated_latency_improvement is not None:
            review.estimated_latency_improvement = estimated_latency_improvement
        # Phase 11.4 – Refactoring Analysis
        if refactoring_findings is not None:
            review.refactoring_findings_json = refactoring_findings
        if refactoring_priority is not None:
            review.refactoring_priority = refactoring_priority
        if estimated_refactoring_effort is not None:
            review.estimated_refactoring_effort = estimated_refactoring_effort
        if estimated_maintainability_improvement is not None:
            review.estimated_maintainability_improvement = estimated_maintainability_improvement
        if estimated_technical_debt_reduction is not None:
            review.estimated_technical_debt_reduction = estimated_technical_debt_reduction
        if estimated_complexity_reduction is not None:
            review.estimated_complexity_reduction = estimated_complexity_reduction
        # Phase 11.5 – Architecture & Code Quality Analysis
        if architecture_findings is not None:
            review.architecture_findings_json = architecture_findings
        if overall_health_score is not None:
            review.overall_health_score = overall_health_score
        if architecture_score is not None:
            review.architecture_score = architecture_score
        if maintainability_score is not None:
            review.maintainability_score = maintainability_score
        if technical_debt_score is not None:
            review.technical_debt_score = technical_debt_score
        if complexity_score is not None:
            review.complexity_score = complexity_score
        if documentation_score is not None:
            review.documentation_score = documentation_score
        if modularity_score is not None:
            review.modularity_score = modularity_score
        if testability_score is not None:
            review.testability_score = testability_score
        if dependency_analysis is not None:
            review.dependency_analysis_json = dependency_analysis
        review.confidence_score = confidence_score
        if duration_ms is not None:
            review.duration_ms = duration_ms
        return self.repo.update(review)

    def delete_review(self, review_id: str, user_id: Optional[str] = None) -> bool:
        return self.repo.delete(review_id, user_id=user_id)

    # -------------------------------------------------------------------------
    # Phase 11.2B-3 — Fix Suggestion persistence
    # -------------------------------------------------------------------------

    # Terminal states in which fixes may be generated
    _FIX_ALLOWED_STATUSES = {ReviewStatusEnum.COMPLETED.value}

    def update_finding_fix_suggestion(
        self,
        review_id: str,
        finding_index: int,
        fix_suggestion: FixSuggestion,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Persist a generated FixSuggestion into the correct findings_json slot.

        Returns the serialised fix dict on success, None if review not found.
        Raises ValueError for illegal review status or out-of-range index.
        """
        review = self.repo.get_by_id(review_id, user_id=user_id)
        if not review:
            return None

        if review.status not in self._FIX_ALLOWED_STATUSES:
            raise ValueError(
                f"Fix generation is only allowed on completed reviews (status='{review.status}')"
            )

        findings: list = list(review.findings_json or [])

        if finding_index < 0 or finding_index >= len(findings):
            raise IndexError(
                f"finding_index {finding_index} is out of range (0-{len(findings) - 1})"
            )

        # Idempotency: return existing suggestion without calling LLM again
        existing_fix = findings[finding_index].get("fix_suggestion")
        if existing_fix:
            return existing_fix

        # Build the complete updated finding, preserving all original fields
        updated_finding = dict(findings[finding_index])
        updated_finding["fix_suggestion"] = fix_suggestion.model_dump(mode="json")

        # Replace finding in the list and persist (atomic)
        findings[finding_index] = updated_finding
        review.findings_json = findings
        self.repo.update(review)

        return updated_finding["fix_suggestion"]

    def update_finding_decision(
        self,
        review_id: str,
        finding_index: int,
        decision: FixUserDecision,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update user_decision on a persisted FixSuggestion.

        Returns the updated fix dict on success, None if review not found.
        Raises KeyError when no fix suggestion exists yet.
        Raises IndexError for out-of-range finding index.
        """
        review = self.repo.get_by_id(review_id, user_id=user_id)
        if not review:
            return None

        findings: list = list(review.findings_json or [])

        if finding_index < 0 or finding_index >= len(findings):
            raise IndexError(
                f"finding_index {finding_index} is out of range (0-{len(findings) - 1})"
            )

        existing_fix = findings[finding_index].get("fix_suggestion")
        if not existing_fix:
            raise KeyError("No fix suggestion exists for this finding")

        # Apply decision (idempotent / allows override)
        updated_fix = dict(existing_fix)
        updated_fix["user_decision"] = decision.value

        updated_finding = dict(findings[finding_index])
        updated_finding["fix_suggestion"] = updated_fix
        findings[finding_index] = updated_finding

        review.findings_json = findings
        self.repo.update(review)

        return updated_fix

    def update_finding_application_status(
        self,
        review_id: str,
        finding_index: int,
        application_status: FixApplicationStatus,
        applied_at: Optional[str] = None,
        previous_hash: Optional[str] = None,
        new_hash: Optional[str] = None,
        application_error: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update fix application status and metadata on a persisted FixSuggestion.

        Returns the updated fix dict on success, None if review not found.
        Raises KeyError when no fix suggestion exists yet.
        Raises IndexError for out-of-range finding index.
        """
        review = self.repo.get_by_id(review_id, user_id=user_id)
        if not review:
            return None

        findings: list = list(review.findings_json or [])

        if finding_index < 0 or finding_index >= len(findings):
            raise IndexError(
                f"finding_index {finding_index} is out of range (0-{len(findings) - 1})"
            )

        existing_fix = findings[finding_index].get("fix_suggestion")
        if not existing_fix:
            raise KeyError("No fix suggestion exists for this finding")

        updated_fix = dict(existing_fix)
        updated_fix["application_status"] = (
            application_status.value
            if hasattr(application_status, "value")
            else str(application_status)
        )
        if applied_at is not None:
            updated_fix["applied_at"] = applied_at
        if previous_hash is not None:
            updated_fix["previous_hash"] = previous_hash
        if new_hash is not None:
            updated_fix["new_hash"] = new_hash
        if application_error is not None:
            updated_fix["application_error"] = application_error
        elif application_status == FixApplicationStatus.APPLIED:
            updated_fix["application_error"] = None

        updated_finding = dict(findings[finding_index])
        updated_finding["fix_suggestion"] = updated_fix
        findings[finding_index] = updated_finding

        review.findings_json = findings
        self.repo.update(review)

        return updated_fix

    def update_finding_verification_result(
        self,
        review_id: str,
        finding_index: int,
        verification_result: StaticVerificationResult,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Persist Tier-1 static verification results onto a fix suggestion.

        Returns the updated fix dict on success, None if review not found.
        Raises KeyError when no fix suggestion exists yet.
        Raises IndexError for out-of-range finding index.
        """
        review = self.repo.get_by_id(review_id, user_id=user_id)
        if not review:
            return None

        findings: list = list(review.findings_json or [])

        if finding_index < 0 or finding_index >= len(findings):
            raise IndexError(
                f"finding_index {finding_index} is out of range (0-{len(findings) - 1})"
            )

        existing_fix = findings[finding_index].get("fix_suggestion")
        if not existing_fix:
            raise KeyError("No fix suggestion exists for this finding")

        updated_fix = dict(existing_fix)
        updated_fix["static_verification"] = verification_result.model_dump(mode="json")

        updated_finding = dict(findings[finding_index])
        updated_finding["fix_suggestion"] = updated_fix
        findings[finding_index] = updated_finding

        review.findings_json = findings
        self.repo.update(review)

        return updated_fix

    def update_finding_test_verification_result(
        self,
        review_id: str,
        finding_index: int,
        verification_result: Any,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Persist Tier-2 sandbox test verification results onto a fix suggestion.

        Returns the updated fix dict on success, None if review not found.
        Raises KeyError when no fix suggestion exists yet.
        Raises IndexError for out-of-range finding index.
        """
        review = self.repo.get_by_id(review_id, user_id=user_id)
        if not review:
            return None

        findings: list = list(review.findings_json or [])

        if finding_index < 0 or finding_index >= len(findings):
            raise IndexError(
                f"finding_index {finding_index} is out of range (0-{len(findings) - 1})"
            )

        existing_fix = findings[finding_index].get("fix_suggestion")
        if not existing_fix:
            raise KeyError("No fix suggestion exists for this finding")

        updated_fix = dict(existing_fix)
        if hasattr(verification_result, "model_dump"):
            updated_fix["test_verification"] = verification_result.model_dump(mode="json")
        elif isinstance(verification_result, dict):
            updated_fix["test_verification"] = verification_result
        else:
            updated_fix["test_verification"] = str(verification_result)

        updated_finding = dict(findings[finding_index])
        updated_finding["fix_suggestion"] = updated_fix
        findings[finding_index] = updated_finding

        review.findings_json = findings
        self.repo.update(review)

        return updated_fix

    def update_finding_git_commit_result(
        self,
        review_id: str,
        finding_index: int,
        git_commit_result: Any,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Persist local Git commit results onto a fix suggestion.

        Returns the updated fix dict on success, None if review not found.
        Raises KeyError when no fix suggestion exists yet.
        Raises IndexError for out-of-range finding index.
        """
        review = self.repo.get_by_id(review_id, user_id=user_id)
        if not review:
            return None

        findings: list = list(review.findings_json or [])

        if finding_index < 0 or finding_index >= len(findings):
            raise IndexError(
                f"finding_index {finding_index} is out of range (0-{len(findings) - 1})"
            )

        existing_fix = findings[finding_index].get("fix_suggestion")
        if not existing_fix:
            raise KeyError("No fix suggestion exists for this finding")

        updated_fix = dict(existing_fix)
        if hasattr(git_commit_result, "model_dump"):
            updated_fix["git_commit"] = git_commit_result.model_dump(mode="json")
        elif isinstance(git_commit_result, dict):
            updated_fix["git_commit"] = git_commit_result
        else:
            updated_fix["git_commit"] = str(git_commit_result)

        updated_finding = dict(findings[finding_index])
        updated_finding["fix_suggestion"] = updated_fix
        findings[finding_index] = updated_finding

        review.findings_json = findings
        self.repo.update(review)

        return updated_fix

    def update_finding_git_push_result(
        self,
        review_id: str,
        finding_index: int,
        git_push_result: Any,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Persist remote Git push results onto a fix suggestion.

        Returns the updated fix dict on success, None if review not found.
        Raises KeyError when no fix suggestion exists yet.
        Raises IndexError for out-of-range finding index.
        """
        review = self.repo.get_by_id(review_id, user_id=user_id)
        if not review:
            return None

        findings: list = list(review.findings_json or [])

        if finding_index < 0 or finding_index >= len(findings):
            raise IndexError(
                f"finding_index {finding_index} is out of range (0-{len(findings) - 1})"
            )

        existing_fix = findings[finding_index].get("fix_suggestion")
        if not existing_fix:
            raise KeyError("No fix suggestion exists for this finding")

        updated_fix = dict(existing_fix)
        if hasattr(git_push_result, "model_dump"):
            updated_fix["git_push"] = git_push_result.model_dump(mode="json")
        elif isinstance(git_push_result, dict):
            updated_fix["git_push"] = git_push_result
        else:
            updated_fix["git_push"] = str(git_push_result)

        updated_finding = dict(findings[finding_index])
        updated_finding["fix_suggestion"] = updated_fix
        findings[finding_index] = updated_finding

        review.findings_json = findings
        self.repo.update(review)

        return updated_fix

    def update_finding_git_pull_request_result(
        self,
        review_id: str,
        finding_index: int,
        git_pull_request_result: Any,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Persist GitHub Pull Request creation results onto a fix suggestion.

        Returns the updated fix dict on success, None if review not found.
        Raises KeyError when no fix suggestion exists yet.
        Raises IndexError for out-of-range finding index.
        """
        review = self.repo.get_by_id(review_id, user_id=user_id)
        if not review:
            return None

        findings: list = list(review.findings_json or [])

        if finding_index < 0 or finding_index >= len(findings):
            raise IndexError(
                f"finding_index {finding_index} is out of range (0-{len(findings) - 1})"
            )

        existing_fix = findings[finding_index].get("fix_suggestion")
        if not existing_fix:
            raise KeyError("No fix suggestion exists for this finding")

        updated_fix = dict(existing_fix)
        if hasattr(git_pull_request_result, "model_dump"):
            updated_fix["git_pull_request"] = git_pull_request_result.model_dump(mode="json")
        elif isinstance(git_pull_request_result, dict):
            updated_fix["git_pull_request"] = git_pull_request_result
        else:
            updated_fix["git_pull_request"] = str(git_pull_request_result)

        updated_finding = dict(findings[finding_index])
        updated_finding["fix_suggestion"] = updated_fix
        findings[finding_index] = updated_finding

        review.findings_json = findings
        self.repo.update(review)

        return updated_fix







