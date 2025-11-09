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

    def __init__(self, tool_registry=None):
        """Initialize context manager.

        Args:
            tool_registry: Tool registry for verification commands
        """
        self.tool_registry = tool_registry
        self.entries: Dict[str, ContextEntry] = {}
        self.verification_strategies: Dict[str, VerificationStrategy] = {
            "exact": ExactMatchStrategy(),
            "hash": HashMatchStrategy()
        }

    def store(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 300,  # Default: 5 minutes
        verification_cmd: Optional[str] = None
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
            verification_command=verification_cmd
        )
        self.entries[key] = entry

        print(f"📝 [ContextManager] Stored '{key}' (TTL: {ttl_seconds}s)")

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
            print(f"⚠️  [ContextManager] '{key}' expired ({entry.age_seconds():.0f}s > {entry.ttl_seconds}s)")
            return None

        return entry.value

    def get_verified(
        self,
        key: str,
        verification_strategy: str = "exact"
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
            return {
                "value": None,
                "status": "not_found",
                "age_seconds": 0,
                "verified": False
            }

        # Check TTL first
        if entry.is_expired():
            return {
                "value": None,
                "status": "expired",
                "age_seconds": entry.age_seconds(),
                "verified": False,
                "message": f"Data expired (age: {entry.age_seconds():.0f}s > TTL: {entry.ttl_seconds}s)"
            }

        # If no verification command, return with warning
        if not entry.verification_command:
            print(f"⚠️  [ContextManager] '{key}' retrieved without verification (age: {entry.age_seconds():.0f}s)")
            return {
                "value": entry.value,
                "status": "unverified",
                "age_seconds": entry.age_seconds(),
                "verified": False,
                "message": "No verification command configured"
            }

        # Execute verification command
        if not self.tool_registry:
            print(f"⚠️  [ContextManager] No tool registry - cannot verify '{key}'")
            return {
                "value": entry.value,
                "status": "unverified",
                "age_seconds": entry.age_seconds(),
                "verified": False,
                "message": "No tool registry available"
            }

        # Verify freshness
        print(f"🔍 [ContextManager] Verifying '{key}' (age: {entry.age_seconds():.0f}s)...")
        print(f"   Command: {entry.verification_command}")

        result = self.tool_registry.execute_tool("bash", command=entry.verification_command)

        if result.status.value != "success":
            print(f"   ❌ Verification failed: {result.error}")
            return {
                "value": None,
                "status": "verification_failed",
                "age_seconds": entry.age_seconds(),
                "verified": False,
                "message": f"Verification command failed: {result.error}"
            }

        # Compare cached vs live
        live_value = result.output.strip()
        strategy = self.verification_strategies.get(verification_strategy, ExactMatchStrategy())

        if strategy.verify(entry.value, live_value):
            print(f"   ✅ Data is FRESH (matches live value)")
            return {
                "value": entry.value,
                "status": "fresh",
                "age_seconds": entry.age_seconds(),
                "verified": True,
                "message": "Verified fresh"
            }
        else:
            print(f"   ⚠️  Data is STALE!")
            print(f"      Cached: {entry.value}")
            print(f"      Live:   {live_value}")
            return {
                "value": live_value,  # Return LIVE value (auto-update!)
                "status": "stale",
                "age_seconds": entry.age_seconds(),
                "verified": True,
                "cached_value": entry.value,
                "live_value": live_value,
                "message": f"Data changed: {entry.value} → {live_value}"
            }

    def clear(self, key: Optional[str] = None) -> None:
        """Clear context entry or all entries.

        Args:
            key: Key to clear (or None to clear all)
        """
        if key:
            if key in self.entries:
                del self.entries[key]
                print(f"🗑️  [ContextManager] Cleared '{key}'")
        else:
            self.entries.clear()
            print(f"🗑️  [ContextManager] Cleared all entries")
