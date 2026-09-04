"""
Response Validator
==================
Guards the final LLM answer against hallucinations by measuring how well
each factual sentence is grounded in the retrieved code context.

Algorithm:
1. Split the answer into sentences.
2. For each sentence, check if it contains at least one token (≥4 chars)
   that appears verbatim in one of the retrieved code chunks.
3. A sentence is "grounded" if it passes the token overlap check OR
   if it contains a recognised hedging phrase ("I don't know", "unclear").
4. Confidence = grounded_sentences / total_sentences.
5. If confidence < settings.MIN_CONFIDENCE_THRESHOLD → reject the answer.

Limitations acknowledged:
- This is a heuristic validator; a production system would use an LLM
  cross-check, but that doubles latency and cost. The heuristic is
  sufficient to catch obvious hallucinations (invented file names,
  non-existent function names).
"""
import re
from typing import List, Optional, Set

from src.core.logger import logger
from src.domain.interfaces.rag import IResponseValidator
from src.domain.models.rag import ValidationResult, RerankedChunk
from src.core.config import settings

# Sentence splitter — split on period/question mark/exclamation not inside backticks
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z`])")

# Hedging phrases that indicate the LLM is acknowledging uncertainty
_HEDGE_PHRASES = {
    "i don't have",
    "i do not have",
    "i'm not sure",
    "i am not sure",
    "cannot confirm",
    "not enough context",
    "unclear from the context",
    "not visible in",
    "not present in",
    "i cannot find",
    "based on the provided context",
}

# Minimum token length to count as "meaningful" for overlap check
_MIN_TOKEN_LEN = 4


def _extract_meaningful_tokens(text: str) -> Set[str]:
    """Extract lowercase tokens ≥ _MIN_TOKEN_LEN chars from text."""
    return {
        t.lower()
        for t in re.findall(r"\b\w+\b", text)
        if len(t) >= _MIN_TOKEN_LEN
    }


def _build_context_token_set(chunks: List[RerankedChunk]) -> Set[str]:
    """Build a union of all meaningful tokens across retrieved chunks."""
    tokens: Set[str] = set()
    for chunk in chunks:
        tokens.update(_extract_meaningful_tokens(chunk.content))
        if chunk.symbol_name:
            tokens.add(chunk.symbol_name.lower())
        if chunk.file_path:
            # Include filename components
            for part in re.split(r"[/\\.]", chunk.file_path):
                if len(part) >= _MIN_TOKEN_LEN:
                    tokens.add(part.lower())
    return tokens


def _is_hedged(sentence: str) -> bool:
    s = sentence.lower()
    return any(phrase in s for phrase in _HEDGE_PHRASES)


class ResponseValidator(IResponseValidator):
    """
    Heuristic groundedness validator.
    Rejects answers where fewer than `settings.MIN_CONFIDENCE_THRESHOLD`
    of sentences can be traced back to retrieved evidence.
    """

    def validate(
        self,
        answer: str,
        chunks: List[RerankedChunk],
    ) -> ValidationResult:
        if not answer.strip():
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                grounded_claims=0,
                total_claims=0,
                rejection_reason="Empty answer received from LLM",
            )

        if not chunks:
            # No context was provided — can't validate; let it through with low confidence
            return ValidationResult(
                is_valid=True,
                confidence=0.5,
                grounded_claims=0,
                total_claims=0,
                rejection_reason=None,
            )

        # Build evidence token set from all retrieved chunks
        context_tokens = _build_context_token_set(chunks)

        # Split answer into sentences
        sentences = [s.strip() for s in _SENTENCE_RE.split(answer) if s.strip()]
        if not sentences:
            sentences = [answer.strip()]

        grounded = 0
        ungrounded: List[str] = []

        for sentence in sentences:
            # Skip very short sentences (e.g. "Yes." "Okay.")
            if len(sentence) < 20:
                grounded += 1
                continue

            if _is_hedged(sentence):
                grounded += 1
                continue

            # Check token overlap with context
            sentence_tokens = _extract_meaningful_tokens(sentence)
            overlap = sentence_tokens & context_tokens
            # Require at least 2 overlapping meaningful tokens or >30% overlap
            overlap_ratio = len(overlap) / max(len(sentence_tokens), 1)
            if len(overlap) >= 2 or overlap_ratio >= 0.30:
                grounded += 1
            else:
                ungrounded.append(sentence[:120])

        total = len(sentences)
        confidence = grounded / total if total > 0 else 0.0
        is_valid = confidence >= settings.MIN_CONFIDENCE_THRESHOLD

        if not is_valid:
            logger.warning(
                "response_validation_failed",
                confidence=round(confidence, 3),
                threshold=settings.MIN_CONFIDENCE_THRESHOLD,
                ungrounded_count=len(ungrounded),
            )

        logger.info(
            "response_validated",
            confidence=round(confidence, 3),
            grounded=grounded,
            total=total,
            is_valid=is_valid,
        )

        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            grounded_claims=grounded,
            total_claims=total,
            ungrounded_claims=ungrounded[:5],  # Return first 5 for diagnosis
            rejection_reason=None if is_valid else f"Low groundedness: {confidence:.1%}",
        )
