import networkx as nx
from typing import Dict, Any
from src.domain.models.repository import Repository

class GraphBuilder:
    def build_dependency_graph(self, repo: Repository) -> nx.DiGraph:
        """Builds a directed graph representing file-level dependencies based on imports."""
        G = nx.DiGraph()
        
        for file in repo.files:
            G.add_node(file.path, type="file", language=file.language)
            for imp in file.imports:
                # In a real scenario, we'd map the import string to an actual file path in the repo.
                # For simplicity, we just add the import module as a node.
                G.add_node(imp, type="module")
                G.add_edge(file.path, imp, relationship="imports")
                
        return G

    def build_symbol_graph(self, repo: Repository) -> nx.DiGraph:
        """Builds a directed graph for classes, functions, and methods."""
        G = nx.DiGraph()
        
        for file in repo.files:
            for symbol in file.symbols:
                node_id = f"{file.path}::{symbol.name}"
                G.add_node(node_id, type=symbol.symbol_type, file=file.path)
                
                # If it's a method or nested class, we could infer parents and add edges
                # based on indentation/start-end lines in a real implementation.
                
        return G
