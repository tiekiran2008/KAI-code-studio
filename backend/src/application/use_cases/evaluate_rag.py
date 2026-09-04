"""
Evaluate RAG Use Case
=====================
Runs the evaluation framework over a set of test (question, expected_chunk_ids)
pairs and returns a list of EvaluationMetrics.

Intended for:
- CI quality gates (fail if avg precision < threshold)
- Offline regression testing after retrieval changes
- Manual evaluation via the /api/v1/rag/evaluate endpoint
"""
import logging
import time
from typing import List, Optional

from src.application.rag.evaluator import RAGEvaluator
from src.application.rag.query_processor import QueryProcessor
from src.domain.models.rag import EvaluationMetrics
from src.core.logger import logger


class EvaluationDataPoint:
    """A single labelled evaluation example."""
    def __init__(
        self,
        question: str,
        repo_id: str,
        expected_chunk_ids: Optional[List[str]] = None,
    ) -> None:
        self.question = question
        self.repo_id = repo_id
        self.expected_chunk_ids = expected_chunk_ids or []


class EvaluateRAGUseCase:
    """Runs the RAG pipeline over a dataset and computes quality metrics."""

    def __init__(self, processor: QueryProcessor) -> None:
        self._processor = processor
        self._evaluator = RAGEvaluator()

    async def execute(
        self,
        dataset: List[EvaluationDataPoint],
    ) -> List[EvaluationMetrics]:
        """
        Evaluate each data point in the dataset.

        Args:
            dataset: List of labelled question/answer pairs.

        Returns:
            List of EvaluationMetrics, one per data point.
        """
        all_metrics: List[EvaluationMetrics] = []

        for i, dp in enumerate(dataset):
            logger.info("evaluating_datapoint", index=i + 1, total=len(dataset))
            start = time.perf_counter()
            try:
                response = await self._processor.process(
                    question=dp.question,
                    repo_id=dp.repo_id,
                )
                latency_ms = (time.perf_counter() - start) * 1000

                # Gather chunk IDs from the response citations
                retrieved_ids = [c.chunk_id for c in response.citations if c.chunk_id]

                metrics = self._evaluator.compute_metrics(
                    question=dp.question,
                    answer=response.answer,
                    chunks=[],  # No RerankedChunk available post-pipeline here
                    relevant_chunk_ids=dp.expected_chunk_ids,
                    intent=response.intent,
                    latency_ms=latency_ms,
                    session_id=response.session_id,
                )
                all_metrics.append(metrics)

            except Exception as exc:
                logger.error("evaluation_datapoint_failed", index=i, error=str(exc))
                from src.domain.models.rag import QueryIntent
                all_metrics.append(EvaluationMetrics(
                    query=dp.question,
                    retrieval_precision=0.0,
                    retrieval_recall=0.0,
                    answer_relevance=0.0,
                    groundedness=0.0,
                    latency_ms=-1.0,
                    num_retrieved=0,
                    intent=QueryIntent.GENERAL_SEARCH,
                    notes=f"Error: {str(exc)[:200]}",
                ))

        # Log aggregate statistics
        if all_metrics:
            avg_precision = sum(m.retrieval_precision for m in all_metrics) / len(all_metrics)
            avg_recall = sum(m.retrieval_recall for m in all_metrics) / len(all_metrics)
            avg_relevance = sum(m.answer_relevance for m in all_metrics) / len(all_metrics)
            avg_groundedness = sum(m.groundedness for m in all_metrics) / len(all_metrics)
            avg_latency = sum(m.latency_ms for m in all_metrics if m.latency_ms > 0) / len(all_metrics)

            logger.info(
                "evaluation_complete",
                num_datapoints=len(all_metrics),
                avg_precision=round(avg_precision, 4),
                avg_recall=round(avg_recall, 4),
                avg_relevance=round(avg_relevance, 4),
                avg_groundedness=round(avg_groundedness, 4),
                avg_latency_ms=round(avg_latency, 1),
            )

        return all_metrics
