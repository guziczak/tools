"""Memory system with automatic verification.

Safe alternative to Claude Desktop's conversation memory:
- Auto-expires after TTL
- Verifies freshness before use
- Never returns stale data silently

Example:
    from core.memory import ContextManager

    ctx = ContextManager(tool_registry)

    # Store commit hash (expires after 5 min)
    ctx.store("last_commit", "abc123",
              ttl_seconds=300,
              verification_cmd="git log -1 --format=%H")

    # Later, retrieve with verification
    result = ctx.get_verified("last_commit")

    if result["status"] == "fresh":
        print(f"Still abc123: {result['value']}")
    elif result["status"] == "stale":
        print(f"Changed! Was {result['cached_value']}, now {result['live_value']}")
"""

from .context_manager import ContextManager, ContextEntry, VerificationStrategy

__all__ = ["ContextManager", "ContextEntry", "VerificationStrategy"]
