"""
Memory Service
==============
Application-layer façade that exposes a simplified, high-level memory API
to agents and use-cases without them needing to know about the
MemoryManager's internal storage details.

Responsibilities
----------------
- Persist episodic memories after every agent session.
- Update user long-term preferences from inferred signals.
- Provide a single ``enrich_agent_context`` method for the
  ExecuteAgentWorkflowUseCase pre-execution hook.
- Expose GDPR operations (forget_memory, forget_user).

Design: thin facade — delegates directly to IMemoryManager.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.domain.memory.entities import (
    EpisodeType,
    EpisodicMemory,
    LongTermMemory,
    MemoryScore,
    MemorySearchQuery,
    MemorySearchResult,
    MemoryType,
    ShortTermMemory,
    UserPreferences,
)
from src.domain.memory.ports import IMemoryManager
from src.core.logger import logger


class MemoryService:
    """
    Application-level memory façade.
    Inject this into use-cases and agents; never inject MemoryManager directly.
    """

    def __init__(self, memory_manager: IMemoryManager) -> None:
        self._mgr = memory_manager

    # ------------------------------------------------------------------
    # Context enrichment (called before every agent execution)
    # ------------------------------------------------------------------

    async def enrich_agent_context(
        self,
        query: str,
        user_id: str,
        session_id: Optional[str],
        repository_id: Optional[str],
        existing_rag_context: str,
        token_budget: int = 2000,
    ) -> str:
        """
        Returns a memory-enriched context string to be prepended to the
        RAG context before the LangGraph graph executes.
        """
        return await self._mgr.enrich_context(
            query_text=query,
            user_id=user_id,
            session_id=session_id,
            repository_id=repository_id,
            existing_rag_context=existing_rag_context,
            token_budget=token_budget,
        )

    # ------------------------------------------------------------------
    # Session memory management
    # ------------------------------------------------------------------

    async def init_session(
        self,
        user_id: str,
        session_id: str,
        query: str,
        repository_id: Optional[str] = None,
    ) -> ShortTermMemory:
        """Create or refresh the short-term session memory for a new execution."""
        memory = ShortTermMemory(
            user_id=user_id,
            session_id=session_id,
            repository_id=repository_id,
            memory_type=MemoryType.SHORT_TERM,
            content=query,
            summary=f"Session for: {query[:100]}",
            conversation_turns=[{"role": "user", "content": query}],
            current_task=query,
            score=MemoryScore(source="agent_execution"),
        )
        return await self._mgr.create_short_term(user_id, session_id, memory)

    async def append_conversation_turn(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Append a new turn to the active session conversation history."""
        session = await self._mgr.get_session_memory(session_id, user_id)
        if session is None:
            return
        session.conversation_turns.append({"role": role, "content": content})
        await self._mgr.create_short_term(user_id, session_id, session)

    # ------------------------------------------------------------------
    # Episodic memory (called after agent execution completes)
    # ------------------------------------------------------------------

    async def save_episode(
        self,
        user_id: str,
        session_id: str,
        query: str,
        repository_id: Optional[str],
        agent_outputs: Dict[str, Any],
        final_answer: str,
        confidence_score: float,
        citations: List[Dict[str, Any]],
        execution_trace: List[Dict[str, Any]],
        episode_type: EpisodeType = EpisodeType.GENERAL,
    ) -> EpisodicMemory:
        """
        Persist the completed agent session as an episodic memory so future
        sessions can reference previous reasoning and conclusions.
        """
        # Infer episode type from agent outputs if not specified
        if episode_type == EpisodeType.GENERAL:
            if "bug_detection" in agent_outputs:
                episode_type = EpisodeType.DEBUGGING
            elif "security_review" in agent_outputs:
                episode_type = EpisodeType.SECURITY_REVIEW
            elif "test_generation" in agent_outputs:
                episode_type = EpisodeType.TEST_GENERATION
            elif "documentation" in agent_outputs:
                episode_type = EpisodeType.DOCUMENTATION
            elif "code_review" in agent_outputs:
                episode_type = EpisodeType.CODE_REVIEW

        # Distil a lessons-learned sentence
        lessons = self._distil_lessons(agent_outputs, final_answer)

        memory = EpisodicMemory(
            user_id=user_id,
            session_id=session_id,
            repository_id=repository_id,
            memory_type=MemoryType.EPISODIC,
            content=final_answer[:2048],
            summary=f"{episode_type.value}: {query[:100]}",
            episode_type=episode_type,
            query=query,
            agent_outputs=agent_outputs,
            final_answer=final_answer,
            confidence_score=confidence_score,
            citations=citations,
            execution_trace=execution_trace,
            lessons_learned=lessons,
            score=MemoryScore(
                importance=min(1.0, confidence_score + 0.1),
                confidence=confidence_score,
                source="agent_execution",
            ),
        )
        saved = await self._mgr.create_episodic(user_id, memory)
        logger.info(
            "episodic_memory_saved",
            user_id=user_id,
            episode_type=episode_type.value,
            session_id=session_id,
        )
        return saved

    # ------------------------------------------------------------------
    # User preference learning
    # ------------------------------------------------------------------

    async def update_user_preferences(
        self,
        user_id: str,
        preferences_update: Dict[str, Any],
    ) -> LongTermMemory:
        """
        Upsert a long-term preference memory for a user.
        If a preference memory already exists, it is updated; otherwise created.
        """
        existing_results = await self._mgr.search(
            MemorySearchQuery(
                query_text="user preferences coding style",
                user_id=user_id,
                memory_types=[MemoryType.LONG_TERM],
                top_k=1,
            )
        )

        if existing_results and isinstance(existing_results[0].memory, LongTermMemory):
            existing: LongTermMemory = existing_results[0].memory  # type: ignore
            # Merge preferences
            for key, value in preferences_update.items():
                if hasattr(existing.preferences, key):
                    setattr(existing.preferences, key, value)
            existing.increment_version()
            await self._mgr.update_memory(
                existing.id,
                user_id,
                {"preferences": existing.preferences},
            )
            return existing
        else:
            prefs = UserPreferences(**{
                k: v for k, v in preferences_update.items()
                if hasattr(UserPreferences(), k)
            })
            memory = LongTermMemory(
                user_id=user_id,
                memory_type=MemoryType.LONG_TERM,
                content=f"User preferences: {preferences_update}",
                summary="User coding preferences and style settings",
                preferences=prefs,
                topic="user_preferences",
                score=MemoryScore(importance=0.9, source="user_explicit"),
            )
            return await self._mgr.create_long_term(user_id, memory)

    # ------------------------------------------------------------------
    # GDPR
    # ------------------------------------------------------------------

    async def forget_memory(
        self, memory_id: str, user_id: str, hard: bool = False
    ) -> None:
        """Delete a specific memory (soft by default, hard for GDPR erasure)."""
        await self._mgr.forget(memory_id, user_id, hard=hard)

    async def forget_user(self, user_id: str) -> int:
        """GDPR right-to-erasure: delete ALL memories for a user."""
        return await self._mgr.forget_user(user_id)

    # ------------------------------------------------------------------
    # Search (passthrough)
    # ------------------------------------------------------------------

    async def search(self, query: MemorySearchQuery) -> List[MemorySearchResult]:
        return await self._mgr.search(query)

    async def list_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        repository_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ):
        return await self._mgr.list_memories(
            user_id=user_id,
            memory_type=memory_type,
            repository_id=repository_id,
            limit=limit,
            offset=offset,
        )

    async def get_memory(self, memory_id: str, user_id: str):
        return await self._mgr.get_by_id(memory_id, user_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _distil_lessons(
        agent_outputs: Dict[str, Any],
        final_answer: str,
    ) -> str:
        """
        Build a compact 'lessons learned' note from agent outputs.
        This avoids an LLM call for low-priority distillation; a richer
        version could call the LLM to summarise.
        """
        agents_used = list(agent_outputs.keys())
        count = len(agents_used)
        excerpt = final_answer[:200].replace("\n", " ")
        return (
            f"Session used {count} agent(s): {', '.join(agents_used)}. "
            f"Excerpt: {excerpt}..."
        )
