"""
Query Rewriter
==============
Expands ambiguous user queries into a set of focused retrieval sub-queries
that maximise recall from the vector store. Each intent has a tailored
expansion template.

Example:
  Input:  "Where is login?"
  Intent: FIND_IMPLEMENTATION
  Output: [
    "authentication implementation login handler",
    "JWT middleware token validation session",
    "login API endpoint user credentials",
    "authentication service class login method",
  ]

Design decisions:
- Template-based (no LLM) for determinism and sub-10ms latency.
- Symbols detected by QueryUnderstanding are injected into every sub-query.
- 3–4 sub-queries generated per intent to balance recall vs. retrieval cost.
"""
from typing import List, Dict
from src.domain.interfaces.rag import IQueryRewriter
from src.domain.models.rag import ParsedQuery, QueryIntent


# Per-intent expansion templates.
# {query} = original query, {symbols} = detected symbol string
_TEMPLATES: Dict[QueryIntent, List[str]] = {
    QueryIntent.EXPLAIN_CODE: [
        "{query}",
        "code explanation {symbols} implementation details",
        "{symbols} function class definition usage",
        "{symbols} purpose behaviour description",
    ],
    QueryIntent.FIND_IMPLEMENTATION: [
        "{query}",
        "{symbols} implementation function class definition",
        "{symbols} method handler service repository",
        "{symbols} API route controller",
    ],
    QueryIntent.DEBUG_ISSUE: [
        "{query}",
        "{symbols} error exception handling stacktrace",
        "{symbols} bug cause root analysis fix",
        "{symbols} validation error condition guard",
    ],
    QueryIntent.ARCHITECTURE: [
        "{query}",
        "project architecture module layer structure",
        "component design pattern service repository",
        "dependency injection configuration startup",
    ],
    QueryIntent.DEPENDENCY_ANALYSIS: [
        "{query}",
        "{symbols} imports dependencies uses calls",
        "{symbols} dependency graph external libraries",
        "module imports require dependencies {symbols}",
    ],
    QueryIntent.API_EXPLANATION: [
        "{query}",
        "{symbols} REST API endpoint route handler",
        "{symbols} request response schema validation",
        "{symbols} HTTP method controller service",
    ],
    QueryIntent.SECURITY_REVIEW: [
        "{query}",
        "authentication authorization token validation",
        "input sanitization SQL injection XSS protection",
        "secret management environment variable exposure",
    ],
    QueryIntent.PERFORMANCE_REVIEW: [
        "{query}",
        "{symbols} performance bottleneck optimization cache",
        "query optimization database indexing N+1",
        "async concurrency thread pool memory allocation",
    ],
    QueryIntent.DOCUMENTATION: [
        "{query}",
        "{symbols} docstring documentation comment",
        "{symbols} API contract interface specification",
        "{symbols} usage example parameters returns",
    ],
    QueryIntent.GENERAL_SEARCH: [
        "{query}",
        "{symbols} implementation usage",
        "{query} code function class",
    ],
}


class QueryRewriter(IQueryRewriter):
    """Template-based query expansion — deterministic, sub-millisecond."""

    def rewrite(self, parsed_query: ParsedQuery) -> ParsedQuery:
        """
        Populates `parsed_query.rewritten_queries` using per-intent templates.
        The original query is always the first entry.
        """
        symbol_str = " ".join(parsed_query.detected_symbols) if parsed_query.detected_symbols else ""
        templates = _TEMPLATES.get(parsed_query.intent, _TEMPLATES[QueryIntent.GENERAL_SEARCH])

        rewritten: List[str] = []
        seen: set = set()

        for tmpl in templates:
            expanded = tmpl.format(
                query=parsed_query.original_query,
                symbols=symbol_str,
            ).strip()
            # Deduplicate identical expansions
            key = expanded.lower()
            if key not in seen:
                seen.add(key)
                rewritten.append(expanded)

        # Inject detected file names as a dedicated sub-query if present
        if parsed_query.detected_files:
            file_query = "file " + " ".join(parsed_query.detected_files) + " " + symbol_str
            file_query = file_query.strip()
            if file_query.lower() not in seen:
                rewritten.append(file_query)

        parsed_query.rewritten_queries = rewritten
        return parsed_query
