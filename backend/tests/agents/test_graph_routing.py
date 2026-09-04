"""Routing & Workflow graph compilation tests for the LangGraph state machine."""
import pytest
from unittest.mock import MagicMock
from src.application.agents.graph import build_agent_graph
from src.domain.interfaces.llm import ILLMProvider
from src.application.rag.query_processor import QueryProcessor

def test_build_agent_graph_compilation():
    mock_llm = MagicMock(spec=ILLMProvider)
    mock_qp = MagicMock(spec=QueryProcessor)

    # Compile state graph
    graph = build_agent_graph(mock_llm, mock_qp)
    
    assert graph is not None
    # Check that compiled graph object is ready for invocation
    assert hasattr(graph, "ainvoke")
