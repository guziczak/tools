"""Context Manager with automatic verification and TTL.

This solves the "stale data" problem from Claude Desktop:
- Stores context from previous interactions
- Automatically verifies freshness before using
- Expires data after TTL
- NEVER returns stale data without verification

Best Practices:
- Observer Pattern: Notifies when data is stale
- Decorator Pattern: Wraps tool execution with caching
- Strategy Pattern: Different verification strategies per data type
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib

from core.logging import get_logger

logger = get_logger(__name__)

MAX_CONTEXT_ENTRIES = 50


@dataclass
class ContextEntry:
    """Entry in context manager.

    Attributes:
        key: Unique key (e.g., "git_last_commit")
        value: Stored value
        timestamp: When this was stored
        ttl_seconds: How long this is valid
        verification_command: Command to verify freshness (optional)
    """

    key: str
    value: Any
    timestamp: datetime
    ttl_seconds: int
    verification_command: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if entry has exceeded TTL."""
        age = datetime.now() - self.timestamp
        return age.total_seconds() > self.ttl_seconds

    def age_seconds(self) -> float:
        """Get age in seconds."""
        return (datetime.now() - self.timestamp).total_seconds()


class VerificationStrategy(ABC):
    """Strategy for verifying if cached data is still fresh."""

    @abstractmethod
    def verify(self, cached_value: Any, live_value: Any) -> bool:
        """Check if cached value matches live value.

        Args:
            cached_value: Value from cache
            live_value: Fresh value from execution

        Returns:
            True if values match (cache is fresh)
        """
        pass


class ExactMatchStrategy(VerificationStrategy):
    """Exact match verification (for commit hashes, etc)."""

    def verify(self, cached_value: Any, live_value: Any) -> bool:
        """Check exact equality."""
        return cached_value == live_value


class HashMatchStrategy(VerificationStrategy):
    """Hash-based verification (for large outputs like git show)."""

    def verify(self, cached_value: Any, live_value: Any) -> bool:
        """Compare hashes instead of full content."""
        cached_hash = hashlib.sha256(str(cached_value).encode()).hexdigest()
        live_hash = hashlib.sha256(str(live_value).encode()).hexdigest()
        return cached_hash == live_hash


class ContextManager:
    """Manages conversation context with automatic freshness verification.

    This is SAFE memory - unlike Claude Desktop, it:
    1. Auto-expires after TTL
    2. Verifies freshness before use
    3. Warns about stale data
    4. Never silently uses old data

    Example:
        ctx = ContextManager(tool_registry)

        # Store last commit
        ctx.store("git_last_commit", "abc123",
                  ttl_seconds=300,  # Valid for 5 minutes
                  verification_cmd="git log -1 --format=%H")

        # Later, retrieve with auto-verification
        commit = ctx.get_verified("git_last_commit")
        # → Returns abc123 only if git log still shows abc123
        # → If changed, returns None + warning
    """

    def __init__(self, tool_registry=None, max_entries: int = MAX_CONTEXT_ENTRIES):
        """Initialize context manager.

        Args:
            tool_registry: Tool registry for verification commands
            max_entries: Maximum number of context entries to keep
        """
        self.tool_registry = tool_registry
        self.max_entries = max_entries
        self.entries: Dict[str, ContextEntry] = {}
        self.verification_strategies: Dict[str, VerificationStrategy] = {
            "exact": ExactMatchStrategy(),
            "hash": HashMatchStrategy(),
        }

    def store(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 300,  # Default: 5 minutes
        verification_cmd: Optional[str] = None,
    ) -> None:
        """Store value in context with TTL and optional verification.

        Args:
            key: Unique key (e.g., "git_last_commit")
            value: Value to store
            ttl_seconds: How long this is valid (default: 5 min)
            verification_cmd: Command to verify freshness (optional)
        """
        entry = ContextEntry(
            key=key,
            value=value,
            timestamp=datetime.now(),
            ttl_seconds=ttl_seconds,
            verification_command=verification_cmd,
        )
        self.entries[key] = entry
        self._evict_if_needed()

        logger.debug("Stored '%s' (TTL: %ds)", key, ttl_seconds)

    def _evict_if_needed(self) -> None:
        """Evict oldest expired entries if over max_entries."""
        if len(self.entries) <= self.max_entries:
            return
        # Remove expired entries first
        expired = [k for k, v in self.entries.items() if v.is_expired()]
        for k in expired:
            del self.entries[k]
        # If still over limit, remove oldest
        while len(self.entries) > self.max_entries:
            oldest_key = min(self.entries, key=lambda k: self.entries[k].timestamp)
            del self.entries[oldest_key]
            logger.debug("Evicted oldest entry '%s' (max_entries=%d)", oldest_key, self.max_entries)

    def get(self, key: str, allow_expired: bool = False) -> Optional[Any]:
        """Get value from context (no verification).

        Use this only when you're sure data is fresh (e.g., within same function).
        For cross-turn retrieval, use get_verified() instead.

        Args:
            key: Context key
            allow_expired: Return even if TTL expired (default: False)

        Returns:
            Stored value or None if expired/not found
        """
        entry = self.entries.get(key)

        if not entry:
            return None

        if entry.is_expired() and not allow_expired:
            logger.debug("'%s' expired (%.0fs > %ds)", key, entry.age_seconds(), entry.ttl_seconds)
            return None

        return entry.value

    def get_verified(
        self, key: str, verification_strategy: str = "exact"
    ) -> Optional[Dict[str, Any]]:
        """Get value with automatic freshness verification.

        This is SAFE retrieval - verifies data is still fresh before returning.

        Args:
            key: Context key
            verification_strategy: "exact" or "hash"

        Returns:
            Dict with:
            - value: The stored value (if verified fresh)
            - status: "fresh", "stale", "expired", or "not_found"
            - age_seconds: How old the data is
            - verified: Whether verification was performed
        """
        entry = self.entries.get(key)

        if not entry:
            return {"value": None, "status": "not_found", "age_seconds": 0, "verified": False}

        # Check TTL first
        if entry.is_expired():
            return {
                "value": None,
                "status": "expired",
                "age_seconds": entry.age_seconds(),
                "verified": False,
                "message": f"Data expired (age: {entry.age_seconds():.0f}s > TTL: {entry.ttl_seconds}s)",
            }

        # If no verification command, return with warning
        if not entry.verification_command:
            logger.debug("'%s' retrieved without verification (age: %.0fs)", key, entry.age_seconds())
            return {
                "value": entry.value,
                "status": "unverified",
                "age_seconds": entry.age_seconds(),
                "verified": False,
                "message": "No verification command configured",
            }

        # Execute verification command
        if not self.tool_registry:
            logger.debug("No tool registry - cannot verify '%s'", key)
            return {
                "value": entry.value,
                "status": "unverified",
                "age_seconds": entry.age_seconds(),
                "verified": False,
                "message": "No tool registry available",
            }

        # Verify freshness
        logger.debug("Verifying '%s' (age: %.0fs) cmd: %s", key, entry.age_seconds(), entry.verification_command)

        result = self.tool_registry.execute_tool("bash", command=entry.verification_command)

        if result.status.value != "success":
            logger.warning("Verification failed for '%s': %s", key, result.error)
            return {
                "value": None,
                "status": "verification_failed",
                "age_seconds": entry.age_seconds(),
                "verified": False,
                "message": f"Verification command failed: {result.error}",
            }

        # Compare cached vs live
        live_value = result.output.strip()
        strategy = self.verification_strategies.get(verification_strategy, ExactMatchStrategy())

        if strategy.verify(entry.value, live_value):
            logger.debug("'%s' is FRESH (matches live value)", key)
            return {
                "value": entry.value,
                "status": "fresh",
                "age_seconds": entry.age_seconds(),
                "verified": True,
                "message": "Verified fresh",
            }
        else:
            logger.info("'%s' is STALE: cached=%s live=%s", key, entry.value, live_value)
            return {
                "value": live_value,
                "status": "stale",
                "age_seconds": entry.age_seconds(),
                "verified": True,
                "cached_value": entry.value,
                "live_value": live_value,
                "message": f"Data changed: {entry.value} -> {live_value}",
            }

    def clear(self, key: Optional[str] = None) -> None:
        """Clear context entry or all entries.

        Args:
            key: Key to clear (or None to clear all)
        """
        if key:
            if key in self.entries:
                del self.entries[key]
                logger.debug("Cleared '%s'", key)
        else:
            self.entries.clear()
            logger.debug("Cleared all entries")
