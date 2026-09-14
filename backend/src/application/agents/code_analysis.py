"""
Code Analysis Agent
===================
Analyzes functions, classes, APIs, architecture layers, design patterns,
and module dependencies.
"""
import time
from typing import Dict, Any
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Senior Software Architect and Code Analysis Specialist.
Examine the retrieved codebase context and provide a rigorous technical analysis strictly grounded in the code evidence.

STRICT GROUNDING & CITATION RULES:
1. Every claim must be directly supported by retrieved code chunks. Never invent files, functions, dependencies, or line numbers.
2. If evidence is insufficient, state: "I don't have enough context in the retrieved repository files to confirm this."
3. NO FAKE METRICS: Do not invent numerical scores (e.g., 52/100, 12.5h). Describe impact qualitatively.
4. EXACT CITATIONS: For every finding or issue, include:
   Evidence: `path/to/file.ext#Lx-Ly` — `function_or_symbol_name()`
5. STRUCTURED FINDING FORMAT: When describing architectural weaknesses, anti-patterns, or design issues, format each as:
   ### Weakness <N> — <Title>
   Evidence: `file.py#Lx-Ly` — `function_name()`

   Observed code:
   <Brief factual description directly from the cited lines>

   Why it matters:
   <Architectural impact>

   Recommended improvement:
   <Concrete fix based on the existing architecture>
"""


class CodeAnalysisAgent:
    def __init__(self, llm_provider: ILLMProvider) -> None:
        self.llm = llm_provider

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        start = time.perf_counter()
        query = state.get("query", "")
        context = state.get("retrieved_context", "No context retrieved.")

        prompt = f"User Request: {query}\n\nCodebase Context:\n{context}"

        llm_resp = await self.llm.complete(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            max_tokens=1500,
            temperature=0.2,
        )

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info("code_analysis_agent_complete", latency_ms=latency)

        pending = [t for t in state.get("pending_tasks", []) if t != AgentType.CODE_ANALYSIS.value]
        completed = state.get("completed_tasks", []) + [AgentType.CODE_ANALYSIS.value]

        output = {
            "summary": "Completed architectural and code pattern analysis.",
            "details": llm_resp.content,
        }

        return {
            "agent_outputs": {AgentType.CODE_ANALYSIS.value: output},
            "pending_tasks": pending,
            "completed_tasks": completed,
            "sender": AgentType.CODE_ANALYSIS.value,
            "execution_trace": [{
                "agent": AgentType.CODE_ANALYSIS.value,
                "action": "analyzed_code_architecture",
                "latency_ms": latency,
            }],
        }
