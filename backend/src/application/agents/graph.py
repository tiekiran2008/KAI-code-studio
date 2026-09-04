"""
LangGraph Multi-Agent StateGraph
================================
Assembles the complete state graph for the multi-agent system using LangGraph.
Implements dynamic routing, specialized execution nodes, and evaluation loops.
"""
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END

from src.domain.interfaces.llm import ILLMProvider
from src.application.rag.query_processor import QueryProcessor
from src.domain.models.agents import AgentState, AgentType

from src.application.agents.supervisor import SupervisorAgent
from src.application.agents.planner import PlannerAgent
from src.application.agents.context import ContextAgent
from src.application.agents.code_analysis import CodeAnalysisAgent
from src.application.agents.bug_detection import BugDetectionAgent
from src.application.agents.security_review import SecurityReviewAgent
from src.application.agents.performance import PerformanceAgent
from src.application.agents.documentation import DocumentationAgent
from src.application.agents.test_generation import TestGenerationAgent
from src.application.agents.code_review import CodeReviewAgent
from src.application.agents.refactoring import RefactoringAnalysisAgent
from src.application.agents.code_quality import CodeQualityAgent
from src.application.agents.report_generator import ReportGeneratorAgent
from src.application.agents.evaluation import EvaluationAgent


def build_agent_graph(
    llm_provider: ILLMProvider,
    query_processor: QueryProcessor,
    tool_manager=None,
) -> StateGraph:
    """
    Constructs and compiles the LangGraph StateGraph for multi-agent software engineering.
    """
    # 1. Instantiate Agent instances
    supervisor = SupervisorAgent(llm_provider, tool_manager)
    planner = PlannerAgent(llm_provider)
    context_agent = ContextAgent(query_processor)
    code_analysis = CodeAnalysisAgent(llm_provider)
    bug_detection = BugDetectionAgent(llm_provider)
    security_review = SecurityReviewAgent(llm_provider)
    performance = PerformanceAgent(llm_provider)
    documentation = DocumentationAgent(llm_provider)
    test_generation = TestGenerationAgent(llm_provider)
    code_review = CodeReviewAgent(llm_provider)
    refactoring_analysis = RefactoringAnalysisAgent(llm_provider)
    code_quality = CodeQualityAgent(llm_provider)
    report_generator = ReportGeneratorAgent(llm_provider)
    evaluation = EvaluationAgent(llm_provider)

    # 2. Define StateGraph
    builder = StateGraph(AgentState)

    # 3. Add Agent Nodes
    builder.add_node(AgentType.SUPERVISOR.value, supervisor.execute)
    builder.add_node(AgentType.PLANNER.value, planner.execute)
    builder.add_node(AgentType.CONTEXT.value, context_agent.execute)
    builder.add_node(AgentType.CODE_ANALYSIS.value, code_analysis.execute)
    builder.add_node(AgentType.BUG_DETECTION.value, bug_detection.execute)
    builder.add_node(AgentType.SECURITY_REVIEW.value, security_review.execute)
    builder.add_node(AgentType.PERFORMANCE.value, performance.execute)
    builder.add_node(AgentType.DOCUMENTATION.value, documentation.execute)
    builder.add_node(AgentType.TEST_GENERATION.value, test_generation.execute)
    builder.add_node(AgentType.CODE_REVIEW.value, code_review.execute)
    builder.add_node(AgentType.REFACTORING_ANALYSIS.value, refactoring_analysis.execute)
    builder.add_node(AgentType.CODE_QUALITY.value, code_quality.execute)
    builder.add_node(AgentType.REPORT_GENERATION.value, report_generator.execute)
    builder.add_node(AgentType.EVALUATION.value, evaluation.execute)

    # 4. Define Entry Point
    builder.add_edge(START, AgentType.SUPERVISOR.value)

    # 5. Routing Decision Functions
    def route_from_supervisor(state: AgentState) -> str:
        next_agent = state.get("next_agent", AgentType.PLANNER.value)
        if next_agent == "__end__":
            return END
        return next_agent

    def route_from_planner(state: AgentState) -> str:
        pending = state.get("pending_tasks", [])
        if pending:
            return pending[0]
        return AgentType.EVALUATION.value

    def route_after_agent_execution(state: AgentState) -> str:
        pending = state.get("pending_tasks", [])
        if pending:
            # Route to next pending specialized agent
            return pending[0]
        # Once all planned agents have executed, route to Evaluation Agent
        return AgentType.EVALUATION.value

    def route_from_evaluation(state: AgentState) -> str:
        next_agent = state.get("next_agent", AgentType.SUPERVISOR.value)
        return next_agent

    # 6. Add Conditional Edges
    builder.add_conditional_edges(
        AgentType.SUPERVISOR.value,
        route_from_supervisor,
        {
            AgentType.PLANNER.value: AgentType.PLANNER.value,
            END: END,
        },
    )

    builder.add_conditional_edges(
        AgentType.PLANNER.value,
        route_from_planner,
        {
            AgentType.CONTEXT.value: AgentType.CONTEXT.value,
            AgentType.CODE_ANALYSIS.value: AgentType.CODE_ANALYSIS.value,
            AgentType.BUG_DETECTION.value: AgentType.BUG_DETECTION.value,
            AgentType.SECURITY_REVIEW.value: AgentType.SECURITY_REVIEW.value,
            AgentType.PERFORMANCE.value: AgentType.PERFORMANCE.value,
            AgentType.DOCUMENTATION.value: AgentType.DOCUMENTATION.value,
            AgentType.TEST_GENERATION.value: AgentType.TEST_GENERATION.value,
            AgentType.CODE_REVIEW.value: AgentType.CODE_REVIEW.value,
            AgentType.REFACTORING_ANALYSIS.value: AgentType.REFACTORING_ANALYSIS.value,
            AgentType.CODE_QUALITY.value: AgentType.CODE_QUALITY.value,
            AgentType.REPORT_GENERATION.value: AgentType.REPORT_GENERATION.value,
            AgentType.EVALUATION.value: AgentType.EVALUATION.value,
        },
    )

    # All specialized agents route to next pending or Evaluation
    specialized_agents = [
        AgentType.CONTEXT.value,
        AgentType.CODE_ANALYSIS.value,
        AgentType.BUG_DETECTION.value,
        AgentType.SECURITY_REVIEW.value,
        AgentType.PERFORMANCE.value,
        AgentType.DOCUMENTATION.value,
        AgentType.TEST_GENERATION.value,
        AgentType.CODE_REVIEW.value,
        AgentType.REFACTORING_ANALYSIS.value,
        AgentType.CODE_QUALITY.value,
        AgentType.REPORT_GENERATION.value,
    ]

    agent_routing_map = {
        AgentType.CONTEXT.value: AgentType.CONTEXT.value,
        AgentType.CODE_ANALYSIS.value: AgentType.CODE_ANALYSIS.value,
        AgentType.BUG_DETECTION.value: AgentType.BUG_DETECTION.value,
        AgentType.SECURITY_REVIEW.value: AgentType.SECURITY_REVIEW.value,
        AgentType.PERFORMANCE.value: AgentType.PERFORMANCE.value,
        AgentType.DOCUMENTATION.value: AgentType.DOCUMENTATION.value,
        AgentType.TEST_GENERATION.value: AgentType.TEST_GENERATION.value,
        AgentType.CODE_REVIEW.value: AgentType.CODE_REVIEW.value,
        AgentType.REFACTORING_ANALYSIS.value: AgentType.REFACTORING_ANALYSIS.value,
        AgentType.CODE_QUALITY.value: AgentType.CODE_QUALITY.value,
        AgentType.REPORT_GENERATION.value: AgentType.REPORT_GENERATION.value,
        AgentType.EVALUATION.value: AgentType.EVALUATION.value,
    }

    for agent_name in specialized_agents:
        builder.add_conditional_edges(
            agent_name,
            route_after_agent_execution,
            agent_routing_map,
        )

    # Evaluation Agent routes to Supervisor or back to Context
    builder.add_conditional_edges(
        AgentType.EVALUATION.value,
        route_from_evaluation,
        {
            AgentType.SUPERVISOR.value: AgentType.SUPERVISOR.value,
            AgentType.CONTEXT.value: AgentType.CONTEXT.value,
        },
    )

    return builder.compile()
