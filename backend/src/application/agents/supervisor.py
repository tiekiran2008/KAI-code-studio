"""
Supervisor Agent
================
Coordinates flow across the graph, delegates to Planner, collects agent
deliverables, and synthesizes the final answer.

Phase 8 Additions:
- Orchestrates Tool Calling.
- Parses native LLM tool calls and executes them via ToolManager.
- Supports parallel and sequential tool execution.
"""
import time
import json
import asyncio
from typing import Dict, Any, List, Optional
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.domain.models.tools import PermissionLevel
from src.core.logger import logger


class SupervisorAgent:
    def __init__(self, llm_provider: ILLMProvider, tool_manager=None) -> None:
        self.llm = llm_provider
        self.tool_manager = tool_manager

    async def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Return the list of tool schemas for the LLM."""
        if not self.tool_manager:
            return []

        import inspect
        raw = self.tool_manager._registry.list_tools(min_permission=PermissionLevel.ADMIN_ONLY)
        # Guard: AsyncMock returns a coroutine; await it when that happens.
        if inspect.iscoroutine(raw):
            raw = await raw

        llm_tools = []
        for t in raw:
            # Format as native OpenAI/Anthropic tool schema
            llm_tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema
                }
            })
        return llm_tools

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        """
        Supervisor execution step:
        - If no plan exists, route to Planner.
        - If outputs are collected, evaluate if tools are needed to verify or fetch more data.
        - Execute tools if called.
        - Synthesize final answer.
        """
        start = time.perf_counter()
        query = state.get("query", "")
        plan = state.get("plan")
        outputs = state.get("agent_outputs", {})
        tool_results = state.get("tool_results", [])
        
        logger.info("supervisor_execution_start", query=query[:60], has_plan=bool(plan), outputs_count=len(outputs))

        # 1. If no plan, send to planner
        if not plan:
            return {
                "next_agent": AgentType.PLANNER.value,
                "sender": AgentType.SUPERVISOR.value,
                "execution_trace": [{
                    "agent": AgentType.SUPERVISOR.value,
                    "action": "routed_to_planner",
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                }],
            }

        # Fast-path: if only 1 specialized agent output exists and no tool results are pending,
        # directly use the specialized agent's answer to avoid an unnecessary extra LLM synthesis call
        if len(outputs) == 1 and not tool_results:
            single_agent_name, single_out = next(iter(outputs.items()))
            details = single_out.get("details", "")
            if details and len(details.strip()) > 50:
                latency = round((time.perf_counter() - start) * 1000, 2)
                logger.info("supervisor_fastpath_single_output", agent=single_agent_name)
                return {
                    "final_answer": details,
                    "next_agent": "__end__",
                    "sender": AgentType.SUPERVISOR.value,
                    "execution_trace": [{
                        "agent": AgentType.SUPERVISOR.value,
                        "action": f"passthrough_{single_agent_name}_output",
                        "latency_ms": latency,
                    }],
                }

        # 2. Build synthesis prompt
        prompt = f"""You are the Lead Software Architecture Supervisor.
User Question: {query}

Your task is to synthesize the deliverables from our engineering team into a comprehensive response.
If you need more information from the repository or external systems to answer accurately, you may call tools.
DO NOT call tools if the deliverables already contain the full answer.

Deliverables:
"""
        for agent_name, out in outputs.items():
            prompt += f"\n--- Output from [{agent_name.upper()}] ---\n"
            prompt += f"Summary: {out.get('summary', '')}\n"
            prompt += f"Details: {out.get('details', '')}\n"

        if tool_results:
            prompt += "\n\n--- Tool Results ---\n"
            for tr in tool_results:
                prompt += f"Tool: {tr['tool_name']}\nSuccess: {tr['success']}\nData: {json.dumps(tr.get('data', tr.get('error', '')))}\n\n"

        prompt += "\nFormat the response using clean Markdown with appropriate headings and code blocks."

        supervisor_system_prompt = (
            "You are an expert Principal AI Software Architect consolidating multi-agent engineering deliverables.\n\n"
            "STRICT GROUNDING & CITATION RULES:\n"
            "1. Every technical claim must come directly from the agent deliverables and retrieved code evidence.\n"
            "2. NEVER invent files, functions, line numbers, or metrics (do not produce fake scores like 52/100 or 12.5h).\n"
            "3. PRESERVE EXACT CITATIONS: Keep all file and line citations in the format: Evidence: `path/to/file.ext#Lx-Ly` — `function_or_symbol_name()`\n"
            "4. STRUCTURED FINDING FORMAT: When listing weaknesses, bugs, or architectural issues, format each as:\n"
            "   ### Weakness <N> — <Title>\n"
            "   Evidence: `file.py#Lx-Ly` — `function_name()`\n\n"
            "   Observed code:\n"
            "   <Brief factual description directly from cited lines>\n\n"
            "   Why it matters:\n"
            "   <Architectural impact>\n\n"
            "   Recommended improvement:\n"
            "   <Concrete fix based on existing architecture>\n"
        )
        available_tools = await self._get_available_tools()

        try:
            llm_resp = await self.llm.complete(
                prompt=prompt,
                system=supervisor_system_prompt,
                max_tokens=2048,
                temperature=0.2,
                tools=available_tools if available_tools else None
            )
        except TypeError:
            # Fallback if complete() doesn't accept tools
            llm_resp = await self.llm.complete(
                prompt=prompt,
                system=supervisor_system_prompt,
                max_tokens=2048,
                temperature=0.2,
            )

        # 4. Check for tool calls (assuming LLM returns a structured tool_calls list on the response object)
        tool_calls = getattr(llm_resp, 'tool_calls', [])
        
        if tool_calls and self.tool_manager:
            logger.info("supervisor_tool_calls_detected", count=len(tool_calls))
            
            # Execute tools in parallel
            tasks = []
            for tc in tool_calls:
                # tc structure assumed: {"name": "...", "arguments": {...}}
                name = tc.get("name")
                args = tc.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                        
                tasks.append(
                    self.tool_manager.execute_tool(
                        tool_name=name,
                        arguments=args,
                        caller_permission=PermissionLevel.ADMIN_ONLY,
                        agent_name="SupervisorAgent"
                    )
                )
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            new_tool_results = []
            for tc, result in zip(tool_calls, results):
                if isinstance(result, Exception):
                    new_tool_results.append({
                        "tool_name": tc.get("name"),
                        "success": False,
                        "error": str(result)
                    })
                else:
                    new_tool_results.append({
                        "tool_name": tc.get("name"),
                        "success": result.success,
                        "data": result.data,
                        "error": result.error,
                        "latency_ms": result.latency_ms
                    })
                    
            state_tool_results = tool_results + new_tool_results
            
            # Since tools were called, we don't end the graph. We route back to Supervisor 
            # to evaluate the tool results (simulated by returning next_agent = Supervisor)
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "tool_results": state_tool_results,
                "next_agent": AgentType.SUPERVISOR.value, # Re-run supervisor to synthesize
                "sender": AgentType.SUPERVISOR.value,
                "execution_trace": [{
                    "agent": AgentType.SUPERVISOR.value,
                    "action": "executed_tools",
                    "tool_calls": [t.get("name") for t in tool_calls],
                    "latency_ms": latency,
                }],
            }

        # 5. Synthesize final answer
        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info("supervisor_synthesis_complete", latency_ms=latency)

        return {
            "final_answer": llm_resp.content,
            "next_agent": "__end__",
            "sender": AgentType.SUPERVISOR.value,
            "execution_trace": [{
                "agent": AgentType.SUPERVISOR.value,
                "action": "synthesized_final_answer",
                "latency_ms": latency,
            }],
        }
