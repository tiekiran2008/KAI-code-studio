"""
Database Schema Migrator & Repair Engine
=========================================
Automatically detects schema drift between SQLAlchemy model definitions
and the physical database tables (PostgreSQL / SQLite).
Safely and idempotently adds missing columns and repairs legacy null/empty fields
without dropping tables or losing existing data.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Set
from sqlalchemy import inspect, text, Table, Column, Integer, Float, String, Text as SQLText, Boolean, DateTime as SQLDateTime, JSON
from sqlalchemy.engine import Engine

from src.core.logger import logger
from src.infrastructure.persistence.models import Base


def _get_column_sql_def(col: Column, dialect_name: str) -> str:
    """Generate safe ALTER TABLE ADD COLUMN SQL clause for a given column."""
    col_type = col.type
    type_str = str(col_type.compile())

    # Build dialect-aware default value clause if column has defaults
    default_clause = ""
    
    if isinstance(col_type, Integer):
        if col.default is not None and col.default.arg is not None:
            default_clause = f" DEFAULT {int(col.default.arg)}"
        else:
            default_clause = " DEFAULT 0"
    elif isinstance(col_type, Float):
        if col.default is not None and col.default.arg is not None:
            default_clause = f" DEFAULT {float(col.default.arg)}"
        else:
            default_clause = " DEFAULT 0.0"
    elif isinstance(col_type, Boolean):
        if col.default is not None and col.default.arg is not None:
            val = "TRUE" if col.default.arg else "FALSE"
            default_clause = f" DEFAULT {val}"
        else:
            default_clause = " DEFAULT FALSE"
    elif isinstance(col_type, JSON):
        is_list = False
        if col.default is not None:
            arg = col.default.arg
            if arg is list or arg == list or arg == "[]" or getattr(arg, "__name__", "") == "list":
                is_list = True
        if not is_list and (
            col.name.endswith("findings_json")
            or col.name.endswith("recommendations_json")
            or col.name.endswith("stats_json")
            or col.name.endswith("formats_json")
            or col.name in ("branches_json", "tags_json")
        ):
            is_list = True

        if dialect_name == "postgresql":
            default_clause = " DEFAULT '[]'::json" if is_list else " DEFAULT '{}'::json"
        else:
            default_clause = " DEFAULT '[]'" if is_list else " DEFAULT '{}'"
    elif isinstance(col_type, SQLDateTime):
        if dialect_name == "postgresql":
            type_str = "TIMESTAMP WITH TIME ZONE"
            default_clause = " DEFAULT CURRENT_TIMESTAMP"
        else:
            type_str = "DATETIME"
            default_clause = ""
    elif isinstance(col_type, (String, SQLText)):
        if col.default is not None and isinstance(col.default.arg, str):
            default_clause = f" DEFAULT '{col.default.arg}'"

    return f"{type_str}{default_clause}"


def sync_schema(engine: Engine) -> Dict[str, List[str]]:
    """
    Inspect all tables in Base.metadata and add any missing columns.
    Returns a dict mapping table_name -> list of newly added column names.
    """
    added_columns: Dict[str, List[str]] = {}
    dialect_name = engine.dialect.name.lower()

    # Step 1: Create any completely missing tables first
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in Base.metadata.tables.values():
            if table.name not in existing_tables:
                continue

            existing_cols = {col["name"].lower() for col in inspector.get_columns(table.name)}
            table_added = []

            for col in table.columns:
                col_name = col.name
                if col_name.lower() not in existing_cols:
                    col_sql_def = _get_column_sql_def(col, dialect_name)
                    alter_query = f"ALTER TABLE {table.name} ADD COLUMN {col_name} {col_sql_def}"
                    try:
                        conn.execute(text(alter_query))
                        table_added.append(col_name)
                        logger.info("schema_migrator_column_added", table=table.name, column=col_name)
                    except Exception as exc:
                        logger.warning("schema_migrator_alter_failed", table=table.name, column=col_name, error=str(exc))

            if table_added:
                added_columns[table.name] = table_added

        # Step 2: Data backfill & repair queries
        _repair_data(conn, dialect_name)

    return added_columns


def _repair_data(conn: Any, dialect_name: str) -> None:
    """Run idempotent data repair and normalization queries."""
    now_func = "CURRENT_TIMESTAMP"

    repair_statements = [
        # code_reviews
        "UPDATE code_reviews SET status = 'pending' WHERE status IS NULL OR status = ''",
        "UPDATE code_reviews SET progress_percent = 0 WHERE progress_percent IS NULL",
        "UPDATE code_reviews SET current_stage = 'queued' WHERE current_stage IS NULL OR current_stage = ''",
        "UPDATE code_reviews SET findings_json = '[]' WHERE findings_json IS NULL",
        "UPDATE code_reviews SET performance_findings_json = '[]' WHERE performance_findings_json IS NULL",
        "UPDATE code_reviews SET performance_recommendations_json = '[]' WHERE performance_recommendations_json IS NULL",
        "UPDATE code_reviews SET refactoring_findings_json = '[]' WHERE refactoring_findings_json IS NULL",
        "UPDATE code_reviews SET architecture_findings_json = '[]' WHERE architecture_findings_json IS NULL",
        "UPDATE code_reviews SET dependency_analysis_json = '{}' WHERE dependency_analysis_json IS NULL",
        "UPDATE code_reviews SET confidence_score = 1.0 WHERE confidence_score IS NULL",
        "UPDATE code_reviews SET performance_score = 0.0 WHERE performance_score IS NULL",
        f"UPDATE code_reviews SET created_at = {now_func} WHERE created_at IS NULL",
        "UPDATE code_reviews SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL",
        f"UPDATE code_reviews SET updated_at = {now_func} WHERE updated_at IS NULL",

        # repositories
        "UPDATE repositories SET provider = 'github' WHERE provider IS NULL OR provider = ''",
        "UPDATE repositories SET indexing_status = 'pending' WHERE indexing_status IS NULL OR indexing_status = ''",
        "UPDATE repositories SET branches_json = '[]' WHERE branches_json IS NULL",
        "UPDATE repositories SET language_stats_json = '[]' WHERE language_stats_json IS NULL",
        "UPDATE repositories SET detected_stack_json = '{}' WHERE detected_stack_json IS NULL",
        "UPDATE repositories SET chunks_count = 0 WHERE chunks_count IS NULL",
        f"UPDATE repositories SET created_at = {now_func} WHERE created_at IS NULL",
        "UPDATE repositories SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL",
        f"UPDATE repositories SET updated_at = {now_func} WHERE updated_at IS NULL",

        # projects
        "UPDATE projects SET status = 'active' WHERE status IS NULL OR status = ''",
        "UPDATE projects SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL",
        f"UPDATE projects SET created_at = {now_func} WHERE created_at IS NULL",
        f"UPDATE projects SET updated_at = {now_func} WHERE updated_at IS NULL",

        # workspaces
        "UPDATE workspaces SET default_ai_model = 'gpt-4o' WHERE default_ai_model IS NULL OR default_ai_model = ''",
        "UPDATE workspaces SET default_ai_model = 'gemini-3.6-flash' WHERE default_ai_model IN ('gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-3.1-pro')",
        "UPDATE user_profiles SET default_ai_model = 'gemini-3.6-flash' WHERE default_ai_model IN ('gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-3.1-pro')",
        "UPDATE workspaces SET vector_db_config = '{}' WHERE vector_db_config IS NULL",
        "UPDATE workspaces SET tool_config = '{}' WHERE tool_config IS NULL",
        f"UPDATE workspaces SET created_at = {now_func} WHERE created_at IS NULL",
        "UPDATE workspaces SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL",
        f"UPDATE workspaces SET updated_at = {now_func} WHERE updated_at IS NULL",

        # engineering_reports
        "UPDATE engineering_reports SET report_content_json = '{}' WHERE report_content_json IS NULL",
        "UPDATE engineering_reports SET repository_snapshot_json = '{}' WHERE repository_snapshot_json IS NULL",
        "UPDATE engineering_reports SET export_formats_json = '[]' WHERE export_formats_json IS NULL",
        f"UPDATE engineering_reports SET created_at = {now_func} WHERE created_at IS NULL",
        "UPDATE engineering_reports SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL",
        f"UPDATE engineering_reports SET updated_at = {now_func} WHERE updated_at IS NULL",
    ]

    for stmt in repair_statements:
        try:
            conn.execute(text(stmt))
        except Exception as exc:
            logger.debug("schema_migrator_repair_stmt_skip", stmt=stmt, error=str(exc))
