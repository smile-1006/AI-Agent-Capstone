"""
Memory subsystem package.

This repository currently uses `agents/memory_agent.py` for deterministic
conversation history in-process, but Dockerfile expects a production-ready
`memory/` package to exist.

The modules here implement:
- Conversation history helpers (optional external persistence)
- Local embedding wrapper and retrieval logic (keyword fallback included)
- A small, filesystem-backed vector store safe for Kaggle-style deployments
"""

from .history import ConversationHistory
from .retrieval import Retriever
from .vector_store import VectorStore

__all__ = ["ConversationHistory", "Retriever", "VectorStore"]
