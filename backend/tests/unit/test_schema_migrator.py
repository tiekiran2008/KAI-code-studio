"""
Unit Tests for Database Schema Migrator & Repair Engine
========================================================
Verifies that legacy tables missing columns are safely upgraded with appropriate
types and sensible defaults, and existing rows are preserved and normalized.
"""
import pytest
from sqlalchemy import create_engine, text, inspect
from src.infrastructure.persistence.schema_migrator import sync_schema
from src.infrastructure.persistence.models import Base


def test_schema_migrator_upgrades_legacy_code_reviews_table():
    """Prove that a legacy code_reviews table missing newer columns is upgraded successfully."""
    engine = create_engine("sqlite:///:memory:")

    # 1. Create a legacy code_reviews table missing progress_percent and all Phase 11 columns
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE code_reviews (
                    id VARCHAR PRIMARY KEY,
                    repository_id VARCHAR NOT NULL,
                    user_id VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    created_at DATETIME
                )
                """
            )
        )
        # Insert a legacy review row
        conn.execute(
            text(
                """
                INSERT INTO code_reviews (id, repository_id, user_id, status, created_at)
                VALUES ('rev_legacy_001', 'repo_001', 'user_001', 'pending', '2026-01-01 00:00:00')
                """
            )
        )

    # 2. Run sync_schema
    added = sync_schema(engine)

    # 3. Inspect columns on upgraded table
    inspector = inspect(engine)
    columns = {col["name"].lower() for col in inspector.get_columns("code_reviews")}

    # Assert critical columns were added
    assert "progress_percent" in columns
    assert "current_stage" in columns
    assert "findings_json" in columns
    assert "performance_score" in columns
    assert "architecture_score" in columns
    assert "updated_at" in columns
    assert "code_reviews" in added
    assert "progress_percent" in added["code_reviews"]

    # 4. Verify existing legacy row preserved and data repaired
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, status, progress_percent, current_stage, findings_json FROM code_reviews WHERE id = 'rev_legacy_001'")
        ).fetchone()

        assert row is not None
        assert row[0] == "rev_legacy_001"
        assert row[1] == "pending"
        assert row[2] == 0  # Default progress_percent
        assert row[3] == "queued"  # Default current_stage
        assert row[4] == "[]"  # Default findings_json


def test_schema_migrator_idempotent_on_full_schema():
    """Verify sync_schema is idempotent and performs zero unwanted changes on up-to-date schema."""
    engine = create_engine("sqlite:///:memory:")

    # Create all tables from scratch
    Base.metadata.create_all(bind=engine)

    # Run sync_schema twice
    added_first = sync_schema(engine)
    added_second = sync_schema(engine)

    assert added_second == {}
