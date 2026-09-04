"""
Query Understanding
===================
Rule-based intent classifier and entity extractor. Operates without an
LLM call on the hot path — uses keyword signals, regex patterns, and
symbol-name heuristics to classify the user's intent and extract
relevant code entities (symbols, filenames, language hints).

Design decisions:
- No LLM on this stage to keep retrieval latency low (<50ms).
- Intent classification is keyword-weighted: each intent has a bag of
  trigger phrases; the intent with the most signal wins.
- Symbol detection uses Python/Java/TS naming conventions (CamelCase,
  snake_case) to identify likely identifiers in the query.
"""
import re
from typing import List, Dict

from src.domain.interfaces.rag import IQueryUnderstanding
from src.domain.models.rag import ParsedQuery, QueryIntent

# ---------------------------------------------------------------------------
# Intent keyword maps — weights let us resolve close calls
# ---------------------------------------------------------------------------

_INTENT_KEYWORDS: Dict[QueryIntent, List[str]] = {
    QueryIntent.EXPLAIN_CODE: [
        "explain", "what does", "how does", "describe", "tell me about",
        "what is", "purpose of", "walk me through", "overview of",
    ],
    QueryIntent.FIND_IMPLEMENTATION: [
        "where is", "find", "locate", "show me", "implementation of",
        "where can i find", "which file", "where does", "how is",
        "show the code", "give me the code",
    ],
    QueryIntent.DEBUG_ISSUE: [
        "bug", "error", "exception", "crash", "fail", "not working",
        "why is", "broken", "issue", "problem", "traceback", "stacktrace",
        "fix", "debug", "wrong", "unexpected",
    ],
    QueryIntent.ARCHITECTURE: [
        "architecture", "design", "structure", "overview", "high level",
        "components", "modules", "system", "how is the project", "layers",
        "pattern", "organisation", "organization",
    ],
    QueryIntent.DEPENDENCY_ANALYSIS: [
        "depends on", "imports", "dependency", "dependencies", "uses",
        "relies on", "what calls", "who calls", "callers", "callees",
        "import graph",
    ],
    QueryIntent.API_EXPLANATION: [
        "api", "endpoint", "route", "rest", "graphql", "request", "response",
        "http", "post", "get", "delete", "put", "patch", "interface",
        "contract",
    ],
    QueryIntent.SECURITY_REVIEW: [
        "security", "vulnerability", "xss", "sql injection", "auth",
        "authentication", "authorization", "permission", "token", "jwt",
        "secret", "exposure", "sanitize", "validate input",
    ],
    QueryIntent.PERFORMANCE_REVIEW: [
        "performance", "slow", "latency", "bottleneck", "optimise",
        "optimize", "speed", "memory", "cpu", "profil", "cache",
        "throughput", "efficiency",
    ],
    QueryIntent.DOCUMENTATION: [
        "document", "docstring", "readme", "comment", "generate docs",
        "write documentation", "jsdoc", "swagger", "openapi",
    ],
    QueryIntent.GENERAL_SEARCH: [],  # fallback — always scores 0
}

# Regex patterns for entity detection
_CAMEL_CASE_RE = re.compile(r"\b[A-Z][a-zA-Z0-9]{2,}\b")
_SNAKE_CASE_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b")
_FILE_EXT_RE = re.compile(r"\b\w+\.(?:py|ts|js|java|go|rs|rb|kt|cs|cpp|h)\b")
_LANG_KEYWORDS: Dict[str, List[str]] = {
    "python": ["python", ".py", "django", "flask", "fastapi"],
    "typescript": ["typescript", ".ts", "angular", "nextjs"],
    "javascript": ["javascript", ".js", "node", "react", "vue"],
    "java": ["java", ".java", "spring", "gradle", "maven"],
    "go": ["golang", ".go", "goroutine"],
}


class QueryUnderstanding(IQueryUnderstanding):
    """Keyword-weighted intent classifier with regex entity extraction."""

    def classify_intent(self, query: str) -> ParsedQuery:
        """
        Classify the query intent and extract entities.
        Returns a ParsedQuery with all detected metadata populated.
        """
        query_lower = query.lower()

        # Score each intent
        scores: Dict[QueryIntent, int] = {intent: 0 for intent in QueryIntent}
        for intent, keywords in _INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in query_lower:
                    scores[intent] += 1

        # Pick the highest-scoring intent; fall back to GENERAL_SEARCH
        best_intent = max(scores, key=lambda i: scores[i])
        if scores[best_intent] == 0:
            best_intent = QueryIntent.GENERAL_SEARCH

        symbols = self.extract_symbols(query)
        files = _FILE_EXT_RE.findall(query)
        languages = self._detect_languages(query_lower)

        return ParsedQuery(
            original_query=query,
            rewritten_queries=[query],   # Rewriter will expand this
            intent=best_intent,
            detected_symbols=symbols,
            detected_files=files,
            language_hints=languages,
        )

    def extract_symbols(self, query: str) -> List[str]:
        """
        Detect likely code symbol names (CamelCase class names,
        snake_case function/variable names) mentioned in the query.
        """
        camel = _CAMEL_CASE_RE.findall(query)
        snake = _SNAKE_CASE_RE.findall(query)
        # Filter out common English words that happen to be CamelCase
        english_stopwords = {"This", "That", "What", "Where", "Which", "When", "How"}
        camel = [s for s in camel if s not in english_stopwords]
        return list(set(camel + snake))

    def _detect_languages(self, query_lower: str) -> List[str]:
        detected = []
        for lang, keywords in _LANG_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                detected.append(lang)
        return detected
