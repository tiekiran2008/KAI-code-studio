"""
Prompt Builder
==============
Constructs structured system + user prompts for the LLM, selecting
a template appropriate for the detected query intent.

Each template:
- Sets the LLM role and output format expectations.
- Injects the formatted code context window.
- Appends recent conversation history (if present).
- Ends with the user's question.

Design decisions:
- No external templating library (Jinja2) to avoid a dependency;
  f-strings and str.format() are sufficient for these fixed templates.
- System prompt is kept under 200 tokens to reserve budget for context.
- Citation format is instructed explicitly so ResponseValidator can parse it.
"""
from typing import Optional, Tuple

from src.domain.interfaces.rag import IPromptBuilder
from src.domain.models.rag import ParsedQuery, ContextWindow, ConversationHistory, QueryIntent

# ---------------------------------------------------------------------------
# Citation instructions — included in every system prompt
# ---------------------------------------------------------------------------

_CITATION_INSTRUCTIONS = """
When you reference code from the provided context, cite the source using this
exact format on the same line: [FILE: path/to/file.py, LINES: 10-45, SYMBOL: ClassName].
If you are unsure about a claim and cannot find supporting evidence in the context,
explicitly state "I don't have enough context to confirm this."
Do NOT invent code, function names, or file paths not present in the context.
""".strip()

# ---------------------------------------------------------------------------
# Per-intent system prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPTS = {
    QueryIntent.EXPLAIN_CODE: (
        "You are an expert software engineer specialising in code comprehension. "
        "Explain the provided code clearly and accurately, covering: purpose, "
        "inputs/outputs, key logic, and any notable patterns or trade-offs. "
        "Structure your answer with headers where helpful."
    ),
    QueryIntent.FIND_IMPLEMENTATION: (
        "You are an expert software engineer performing a code search. "
        "Identify and describe exactly where the requested feature or function is "
        "implemented in the codebase. Point to specific files, classes, and functions. "
        "If multiple implementations exist, list all of them."
    ),
    QueryIntent.DEBUG_ISSUE: (
        "You are a senior software engineer debugging a codebase. "
        "Analyse the provided code context to identify the root cause of the issue. "
        "Explain the bug, why it occurs, and recommend a concrete fix with example code."
    ),
    QueryIntent.ARCHITECTURE: (
        "You are a software architect. Provide a high-level explanation of the repository's "
        "architecture, module structure, key design patterns, and data flow. "
        "Describe how the components interact with each other."
    ),
    QueryIntent.DEPENDENCY_ANALYSIS: (
        "You are a dependency analysis expert. Trace and explain the dependency "
        "relationships in the provided code context: what imports what, which "
        "modules are tightly coupled, and what the dependency graph looks like."
    ),
    QueryIntent.API_EXPLANATION: (
        "You are an API documentation specialist. Explain the API endpoints, "
        "their HTTP methods, request/response schemas, authentication requirements, "
        "and expected behaviours based on the provided code context."
    ),
    QueryIntent.SECURITY_REVIEW: (
        "You are a security engineer conducting a code security review. "
        "Identify security vulnerabilities, anti-patterns, or risks in the "
        "provided code context. Classify each issue by severity and suggest remediation."
    ),
    QueryIntent.PERFORMANCE_REVIEW: (
        "You are a performance engineering expert. Identify performance bottlenecks, "
        "inefficiencies, or anti-patterns in the provided code. Suggest specific "
        "optimisations with reasoning and estimated impact."
    ),
    QueryIntent.DOCUMENTATION: (
        "You are a technical writer generating documentation from source code. "
        "Produce clear, accurate documentation for the provided code including: "
        "purpose, parameters, return values, exceptions, and usage examples."
    ),
    QueryIntent.GENERAL_SEARCH: (
        "You are an expert software engineer with deep knowledge of this codebase. "
        "Answer the user's question accurately based solely on the provided code context. "
        "Be specific and reference concrete code elements."
    ),
}

# ---------------------------------------------------------------------------
# Conversation history formatter
# ---------------------------------------------------------------------------

def _format_history(history: Optional[ConversationHistory], max_turns: int = 6) -> str:
    if not history or not history.turns:
        return ""
    recent_turns = history.turns[-max_turns:]
    lines = ["## Conversation History"]
    for turn in recent_turns:
        role_label = "User" if turn.role.value == "user" else "Assistant"
        lines.append(f"**{role_label}:** {turn.content[:500]}")  # Truncate old turns
    return "\n".join(lines)


class PromptBuilder(IPromptBuilder):
    """Builds (system_prompt, user_prompt) pairs for each query intent."""

    def build_prompt(
        self,
        parsed_query: ParsedQuery,
        context: ContextWindow,
        history: Optional[ConversationHistory] = None,
    ) -> Tuple[str, str]:
        """
        Returns (system_prompt, user_prompt).

        The user_prompt contains: context window, optional history, and the question.
        The system_prompt contains: role definition and citation instructions.
        """
        intent = parsed_query.intent
        system_base = _SYSTEM_PROMPTS.get(intent, _SYSTEM_PROMPTS[QueryIntent.GENERAL_SEARCH])
        system_prompt = f"{system_base}\n\n{_CITATION_INSTRUCTIONS}"

        user_parts = []

        # Context window
        if context.formatted_context:
            user_parts.append("## Code Context\n\n" + context.formatted_context)
            if context.truncated:
                user_parts.append(
                    "_Note: The context was truncated to fit within the token budget. "
                    "Some relevant code may not be shown._"
                )

        # Conversation history
        history_str = _format_history(history)
        if history_str:
            user_parts.append(history_str)

        # The actual question
        user_parts.append(f"## Question\n\n{parsed_query.original_query}")

        user_prompt = "\n\n".join(user_parts)
        return system_prompt, user_prompt
