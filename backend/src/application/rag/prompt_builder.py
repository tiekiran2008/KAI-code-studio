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
STRICT REPOSITORY GROUNDING RULES:
1. Every technical claim must come directly from retrieved repository code context.
2. NEVER invent files, functions, dependencies, bugs, metrics, scores, or line numbers.
3. If evidence in the retrieved context is insufficient, explicitly state: "I don't have enough context in the retrieved repository files to confirm this."
4. NO FAKE METRICS: Do NOT generate arbitrary numerical values (such as "Architecture Health 52/100" or "Technical Debt 12.5 hours"). Describe impact and severity qualitatively (High / Medium / Low).
5. EXACT CITATIONS: For every issue, weakness, or technical finding, include exact citations in this format:
   Evidence: `path/to/file.ext#Lx-Ly` — `function_or_symbol_name()`
   Also support inline tag: [FILE: path/to/file.ext, LINES: x-y, SYMBOL: symbol_name]
6. STRUCTURED FINDING FORMAT: When listing weaknesses, bugs, or architectural issues, format each as:
   ### Weakness <N> — <Title>
   Evidence: `file.py#Lx-Ly` — `function_name()`

   Observed code:
   <Brief factual description directly from the cited lines>

   Why it matters:
   <Architectural impact>

   Recommended improvement:
   <Concrete fix based on the existing architecture>
""".strip()

# ---------------------------------------------------------------------------
# Per-intent system prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPTS = {
    QueryIntent.EXPLAIN_CODE: (
        "You are an expert software engineer specialising in code comprehension. "
        "Explain the provided code clearly and factually based solely on the retrieved code context. "
        "Cover purpose, inputs/outputs, key logic, and patterns. "
        "Every claim must cite exact files and line numbers from the context."
    ),
    QueryIntent.FIND_IMPLEMENTATION: (
        "You are an expert software engineer performing a code search. "
        "Identify and describe exactly where the requested feature or function is "
        "implemented in the codebase. Point to specific files, classes, and functions with exact line numbers. "
        "If multiple implementations exist, list all of them."
    ),
    QueryIntent.DEBUG_ISSUE: (
        "You are a senior software engineer debugging a codebase. "
        "Analyse the provided code context to identify the root cause of the issue from verifiable code evidence. "
        "Explain the bug, cite exact lines (Evidence: `file.py#Lx-Ly` — `symbol()`), why it occurs, and recommend a concrete fix."
    ),
    QueryIntent.ARCHITECTURE: (
        "You are a software architect conducting a rigorous codebase analysis. "
        "Explain the repository's architecture, module structure, and data flow strictly based on retrieved files. "
        "When identifying architectural weaknesses or anti-patterns, provide exact line citations (Evidence: `file.py#Lx-Ly` — `symbol()`), "
        "factual observed code, architectural impact, and concrete recommendations. Never invent scores or metrics."
    ),
    QueryIntent.DEPENDENCY_ANALYSIS: (
        "You are a dependency analysis expert. Trace and explain the dependency "
        "relationships in the provided code context: what imports what, which "
        "modules are coupled, and what the dependency graph looks like, citing exact import lines."
    ),
    QueryIntent.API_EXPLANATION: (
        "You are an API documentation specialist. Explain the API endpoints, "
        "their HTTP methods, schemas, and behaviours based strictly on the provided route definitions and code."
    ),
    QueryIntent.SECURITY_REVIEW: (
        "You are a security engineer conducting a code security review. "
        "Identify security vulnerabilities strictly present in the retrieved code context. "
        "Cite exact files and lines (Evidence: `file.py#Lx-Ly` — `symbol()`), classify severity qualitatively, and suggest remediation."
    ),
    QueryIntent.PERFORMANCE_REVIEW: (
        "You are a performance engineering expert. Identify performance bottlenecks "
        "directly observable in the provided code. Cite exact line ranges and suggest concrete optimisations."
    ),
    QueryIntent.DOCUMENTATION: (
        "You are a technical writer generating documentation from source code. "
        "Produce clear, accurate documentation for the provided code based on factual signatures and docstrings."
    ),
    QueryIntent.GENERAL_SEARCH: (
        "You are an expert software engineer with deep knowledge of this codebase. "
        "Answer the user's question accurately based solely on the provided code context. "
        "Be specific, cite concrete code elements with exact file and line numbers, and never make assumptions."
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
