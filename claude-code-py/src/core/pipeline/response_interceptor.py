"""Response interceptor for auto-execution after LLM response.

This is a thin wrapper around ResponseAnalyzer + AutoExecutor,
kept as a separate module for clarity.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from core.logging import get_logger

if TYPE_CHECKING:
    from core.response_analyzer import ResponseAnalyzer
    from core.auto_executor import AutoExecutor

logger = get_logger(__name__)


class ResponseInterceptor:
    """Detects paste-request patterns and auto-executes safe commands."""

    def __init__(
        self,
        response_analyzer: Optional["ResponseAnalyzer"] = None,
        auto_executor: Optional["AutoExecutor"] = None,
    ) -> None:
        self._analyzer = response_analyzer
        self._executor = auto_executor

    @property
    def available(self) -> bool:
        return self._analyzer is not None and self._executor is not None

    def try_auto_execute(self, response_text: str) -> Optional[str]:
        """Check response for paste requests and auto-execute if safe.

        Returns:
            Follow-up message to inject, or None if nothing to do.
        """
        if not self.available:
            return None

        paste_request = self._analyzer.analyze(response_text)
        if not paste_request.detected or not paste_request.command:
            return None

        if not self._executor.should_auto_execute(paste_request.command):
            logger.warning("Blocked dangerous command: %s", paste_request.command)
            return None

        exec_result = self._executor.execute(paste_request.command)
        return self._executor.create_followup_message(
            paste_request.command, exec_result
        )
