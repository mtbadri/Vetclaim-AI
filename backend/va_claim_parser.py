"""
Backward compatibility re-export.
The canonical VAClaimParser is now in backend/agents/parser_agent.py
"""

from agents.parser_agent import VAClaimParser  # noqa: F401

__all__ = ["VAClaimParser"]
