import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from src.infrastructure.embeddings.sentence_transformer_service import (
    SentenceTransformerService,
    OnnxEmbeddingService,
    _OnnxEmbeddingWrapper,
)
from src.application.services.index_manager import IndexManager
from src.domain.models.chunk import SemanticChunk


def test_onnx_embedding_service_lazy_loading():
    """Verify embedding service does NOT load any ONNX session or tokenizer in __init__."""
    with patch.object(SentenceTransformerService, "_ensure_model_loaded") as mock_ensure:
        svc = SentenceTransformerService()
        assert svc.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        mock_ensure.assert_not_called()


def test_onnx_embedding_service_alias():
    """Verify OnnxEmbeddingService is an alias to SentenceTransformerService."""
    assert OnnxEmbeddingService is SentenceTransformerService


def test_onnx_embedding_wrapper_encode():
    """Test _OnnxEmbeddingWrapper produces 384-dimensional normalized embeddings."""
    mock_session = MagicMock()
    # Simulate ONNX session returning last_hidden_state of shape (batch, seq_len, 384)
    batch_size = 2
    seq_len = 8
    dim = 384
    mock_hidden_state = np.ones((batch_size, seq_len, dim), dtype=np.float32)
    mock_session.run.return_value = [mock_hidden_state]
    mock_session.get_inputs.return_value = [MagicMock(name="input_ids"), MagicMock(name="attention_mask")]

    mock_tokenizer = MagicMock()
    mock_encoded_item = MagicMock()
    mock_encoded_item.ids = [101] + [1000] * (seq_len - 2) + [102]
    mock_encoded_item.attention_mask = [1] * seq_len
    mock_encoded_item.type_ids = [0] * seq_len
    mock_tokenizer.encode_batch.return_value = [mock_encoded_item, mock_encoded_item]

    wrapper = _OnnxEmbeddingWrapper(mock_session, mock_tokenizer, max_length=256)
    assert wrapper.get_embedding_dimension() == 384

    # Single text encode
    single_res = wrapper.encode("hello world")
    assert isinstance(single_res, np.ndarray)
    assert single_res.shape == (384,)
    # Norm must be ~1.0
    assert abs(np.linalg.norm(single_res) - 1.0) < 1e-4

    # Batch encode
    batch_res = wrapper.encode(["hello", "world"])
    assert isinstance(batch_res, np.ndarray)
    assert batch_res.shape == (2, 384)
    for row in batch_res:
        assert abs(np.linalg.norm(row) - 1.0) < 1e-4


def test_index_manager_incremental_batching():
    """Test IndexManager's prepare_repository_indexing and index_chunk_batch methods."""
    mock_emb = MagicMock()
    mock_emb.dimension = 384
    mock_emb.generate_embeddings.return_value = [[0.1] * 384, [0.2] * 384]

    mock_vdb = MagicMock()
    mock_session = MagicMock()

    mgr = IndexManager(mock_emb, mock_vdb, mock_session)
    mgr.prepare_repository_indexing("repo-123")

    mock_vdb.ensure_collection.assert_called_with("codebase_chunks", 384)
    mock_vdb.delete_by_repo.assert_called_with("codebase_chunks", "repo-123")

    chunks = [
        SemanticChunk(
            id="c1",
            repo_id="repo-123",
            file_path="main.py",
            content="def main(): pass",
            language="python",
            commit_hash="HEAD",
            start_line=1,
            end_line=2,
        ),
        SemanticChunk(
            id="c2",
            repo_id="repo-123",
            file_path="main.py",
            content="def helper(): pass",
            language="python",
            commit_hash="HEAD",
            start_line=3,
            end_line=4,
        ),
    ]

    latency = mgr.index_chunk_batch(chunks)
    assert latency >= 0.0
    mock_emb.generate_embeddings.assert_called_once_with(["def main(): pass", "def helper(): pass"])
    mock_vdb.upsert_chunks.assert_called_once()
