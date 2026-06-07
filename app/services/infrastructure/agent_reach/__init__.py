"""Agent-Reach integration — CLI tool wrappers for multi-platform discovery.

Provides subprocess-based adapters for rdt-cli (Reddit) and twitter-cli,
with graceful degradation when tools are not installed or authenticated.
"""

from app.services.infrastructure.agent_reach.client import AgentReachClient

__all__ = ["AgentReachClient"]
