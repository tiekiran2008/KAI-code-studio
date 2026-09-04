"""
RAG Evaluator
=============
Offline evaluation framework for measuring RAG pipeline quality.
Computes standard IR and NLP metrics without requiring an external service.

Metrics computed:
- Retrieval Precision  = |relevant ∩ retrieved| / |retrieved|
- Retrieval Recall     = |relevant ∩ retrieved| / |relevant|
- Answer Relevance     = heuristic: query keyword overlap with the answer
- Groundedness         = from ResponseValidator confidence score
- Latency              = end-to-end wall-clock time from pipeline logs
"""
import re
from typing import List, Set
from src.domain.models.rag import EvaluationMetrics, RerankedChunk, QueryIntent
from src.core.logger import logger

_MIN_KEYWORD_LEN = 3


def _extract_keywords(text: str) -> Set[str]:
    """Extract meaningful lowercase keywords from text."""
    stopwords = {
        "the", "a", "an", "is", "are", "was", "in", "of", "to", "and",
        "for", "with", "how", "what", "where", "this", "that", "it",
        "be", "do", "does", "from", "by", "on", "at", "can", "has",
    }
    tokens = re.findall(r"\b[a-z][a-z0-9_]{2,}\b", text.lower())
    return {t for t in tokens if t not in stopwords}


class RAGEvaluator:
    """Computes retrieval and generation quality metrics."""

    def evaluate_retrieval(
        self,
        relevant_chunk_ids: List[str],
        retrieved_chunk_ids: List[str],
    ) -> tuple[float, float]:
        """
        Compute precision and recall for a retrieval result.

        Returns:
            (precision, recall) — both in [0, 1]
        """
        if not retrieved_chunk_ids:
            return 0.0, 0.0
        if not relevant_chunk_ids:
            return 0.0, 0.0

        relevant_set = set(relevant_chunk_ids)
        retrieved_set = set(retrieved_chunk_ids)
        true_positives = relevant_set & retrieved_set

        precision = len(true_positives) / len(retrieved_set)
        recall = len(true_positives) / len(relevant_set)
        return precision, recall

    def evaluate_answer_relevance(
        self,
        question: str,
        answer: str,
    ) -> float:
        """
        Heuristic relevance score: how many question keywords appear in the answer?

        Returns a score in [0, 1].
        """
        q_keywords = _extract_keywords(question)
        a_keywords = _extract_keywords(answer)

        if not q_keywords:
            return 1.0   # Can't evaluate; assume relevant

        overlap = q_keywords & a_keywords
        return len(overlap) / len(q_keywords)

    def evaluate_groundedness(
        self,
        answer: str,
        chunks: List[RerankedChunk],
    ) -> float:
        """
        Heuristic groundedness: how much of the answer's vocabulary
        appears in the retrieved context?
        """
        if not chunks:
            return 0.0

        context_text = " ".join(c.content for c in chunks)
        context_keywords = _extract_keywords(context_text)
        answer_keywords = _extract_keywords(answer)

        if not answer_keywords:
            return 1.0

        overlap = answer_keywords & context_keywords
        return len(overlap) / len(answer_keywords)

    def compute_metrics(
        self,
        question: str,
        answer: str,
        chunks: List[RerankedChunk],
        relevant_chunk_ids: List[str],
        intent: QueryIntent,
        latency_ms: float,
        session_id: str = "",
    ) -> EvaluationMetrics:
        """Compute all metrics for a single RAG query."""
        retrieved_ids = [c.chunk_id for c in chunks]
        precision, recall = self.evaluate_retrieval(relevant_chunk_ids, retrieved_ids)
        relevance = self.evaluate_answer_relevance(question, answer)
        groundedness = self.evaluate_groundedness(answer, chunks)

        metrics = EvaluationMetrics(
            query=question,
            retrieval_precision=round(precision, 4),
            retrieval_recall=round(recall, 4),
            answer_relevance=round(relevance, 4),
            groundedness=round(groundedness, 4),
            latency_ms=latency_ms,
            num_retrieved=len(chunks),
            intent=intent,
            session_id=session_id,
        )

        logger.info(
            "rag_evaluation",
            precision=metrics.retrieval_precision,
            recall=metrics.retrieval_recall,
            relevance=metrics.answer_relevance,
            groundedness=metrics.groundedness,
            latency_ms=metrics.latency_ms,
        )
        return metrics
