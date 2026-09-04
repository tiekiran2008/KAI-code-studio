"""
Evaluation Agent
================
Evaluates outputs from all specialized agents for correctness, consistency,
groundedness, and hallucination risks. Assigns confidence score and controls
the evaluation feedback loop.
"""
import json
import time
from typing import Dict, Any
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.config import settings
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Quality Assurance & Validation Agent.
Review the collective outputs from all specialized engineering agents and evaluate:
1. Groundedness: Are claims backed by retrieved codebase context?
2. Consistency: Do agent outputs agree with each other?
3. Completeness: Did agents address the user's core query?

Return ONLY a JSON object in this exact format:
{
  "confidence_score": 0.85,
  "groundedness_ratio": 0.90,
  "is_passed": true,
  "notes": "Outputs are well-grounded in code context and consistent."
}
"""


class EvaluationAgent:
    def __init__(self, llm_provider: ILLMProvider) -> None:
        self.llm = llm_provider

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        start = time.perf_counter()
        query = state.get("query", "")
        context = state.get("retrieved_context", "")
        outputs = state.get("agent_outputs", {})
        retry_count = state.get("retry_count", 0)

        logger.info("evaluation_agent_start", outputs_count=len(outputs), retry_count=retry_count)

        prompt = f"User Request: {query}\n\nRetrieved Code Context:\n{context[:2000]}\n\nAgent Outputs:\n"
        for agent_name, out in outputs.items():
            prompt += f"\n[{agent_name}]: {out.get('summary', '')}\n{out.get('details', '')[:500]}\n"

        llm_resp = await self.llm.complete(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            max_tokens=512,
            temperature=0.0,
        )

        eval_result = self._parse_evaluation(llm_resp.content)
        confidence = eval_result.get("confidence_score", 0.80)
        is_passed = eval_result.get("is_passed", True)

        # Enforce confidence threshold check
        threshold = settings.AGENT_CONFIDENCE_THRESHOLD
        if confidence < threshold:
            is_passed = False

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "evaluation_agent_complete",
            confidence=confidence,
            is_passed=is_passed,
            latency_ms=latency,
        )

        # Routing decision
        next_agent = AgentType.SUPERVISOR.value
        new_retry_count = retry_count

        if not is_passed and retry_count < settings.AGENT_EVALUATION_RETRIES_MAX:
            logger.warning("evaluation_failed_triggering_retry", retry_count=retry_count)
            new_retry_count += 1
            # Route back to Context agent if context was thin, or Planner to adjust
            next_agent = AgentType.CONTEXT.value

        return {
            "confidence_score": confidence,
            "groundedness_ratio": eval_result.get("groundedness_ratio", confidence),
            "is_eval_passed": is_passed,
            "evaluation_notes": eval_result.get("notes", ""),
            "retry_count": new_retry_count,
            "next_agent": next_agent,
            "sender": AgentType.EVALUATION.value,
            "execution_trace": [{
                "agent": AgentType.EVALUATION.value,
                "action": "evaluated_multi_agent_outputs",
                "confidence": confidence,
                "is_passed": is_passed,
                "latency_ms": latency,
            }],
        }

    def _parse_evaluation(self, content: str) -> Dict[str, Any]:
        try:
            cleaned = content.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
            return json.loads(cleaned)
        except Exception:
            return {
                "confidence_score": 0.80,
                "groundedness_ratio": 0.85,
                "is_passed": True,
                "notes": "Default evaluation fallback",
            }
