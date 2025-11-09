"""Response analysis for detecting when Claude asks user to paste command output.

This module implements the Strategy Pattern for analyzing Claude's responses
and detecting anti-patterns (like asking user to run commands instead of using tools).

Best Practices:
- Strategy Pattern: Different analyzers for different detection strategies
- Single Responsibility: Each analyzer detects ONE pattern
- Immutable results: Analysis returns dataclasses, doesn't modify state
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass
import re


@dataclass
class PasteRequest:
    """Represents a detected request for user to paste command output.

    Attributes:
        detected: Whether a paste request was detected
        command: The command Claude wants user to run (if extracted)
        original_text: Original text that triggered detection
        confidence: Confidence score (0-1) that this is a paste request
    """

    detected: bool
    command: Optional[str] = None
    original_text: Optional[str] = None
    confidence: float = 0.0


class PasteRequestDetector(ABC):
    """Abstract base class for paste request detectors (Strategy Pattern)."""

    @abstractmethod
    def detect(self, response_text: str) -> PasteRequest:
        """Detect if response contains a paste request.

        Args:
            response_text: Claude's response text

        Returns:
            PasteRequest with detection results
        """
        pass


class RegexPasteDetector(PasteRequestDetector):
    """Detects paste requests using regex patterns.

    Patterns:
    - "Wklej mi output z [command]"
    - "Please paste the output of [command]"
    - "Run [command] and paste the result"
    - "Can you paste: [command]"
    """

    # Regex patterns for different languages
    PATTERNS = [
        # Polish
        r'wklej\s+(?:mi\s+)?(?:output\s+z|wynik\s+z?|rezultat)\s+[`"]?([^`"\n]+)[`"]?',
        r'(?:możesz|proszę)\s+wkleić\s+[`"]?([^`"\n]+)[`"]?',
        # English
        r'paste\s+(?:the\s+)?(?:output\s+(?:of|from)|result\s+of)\s+[`"]?([^`"\n]+)[`"]?',
        r'please\s+paste\s+[`"]?([^`"\n]+)[`"]?',
        r'can\s+you\s+paste\s+[`"]?([^`"\n]+)[`"]?',
        # Command in code block followed by "paste"
        r"```(?:bash|sh)?\n([^`]+)\n```\s*(?:.*)?(?:wklej|paste)",
    ]

    def detect(self, response_text: str) -> PasteRequest:
        """Detect paste requests using regex patterns.

        Args:
            response_text: Claude's response text

        Returns:
            PasteRequest with detected command if found
        """
        text_lower = response_text.lower()

        # Quick check: does it contain paste-related keywords?
        if "wklej" not in text_lower and "paste" not in text_lower:
            return PasteRequest(detected=False)

        # Try each pattern
        for pattern in self.PATTERNS:
            match = re.search(pattern, response_text, re.IGNORECASE | re.MULTILINE)
            if match:
                command = match.group(1).strip()
                # Clean up command (remove trailing punctuation)
                command = command.rstrip(".,;:!?")

                return PasteRequest(
                    detected=True, command=command, original_text=match.group(0), confidence=0.9
                )

        # Pattern not matched, but contains paste keywords - low confidence
        return PasteRequest(detected=True, command=None, original_text=None, confidence=0.3)


class CodeBlockDetector(PasteRequestDetector):
    """Detects when Claude suggests commands in code blocks without executing.

    Pattern:
    ```bash
    git show abc123
    ```

    Followed by text like "run this" or question marks suggesting user should execute.
    """

    def detect(self, response_text: str) -> PasteRequest:
        """Detect command suggestions in code blocks.

        Args:
            response_text: Claude's response text

        Returns:
            PasteRequest if code block suggests user should run command
        """
        # Find code blocks with bash/sh
        pattern = r"```(?:bash|sh|shell)?\n([^`]+)\n```"
        matches = re.findall(pattern, response_text, re.MULTILINE)

        if not matches:
            return PasteRequest(detected=False)

        # Check if there's text after code block suggesting user should run it
        suggestion_keywords = [
            "możesz uruchomić",
            "możesz wykonać",
            "uruchom",
            "wykonaj",
            "you can run",
            "run this",
            "execute this",
            "try running",
        ]

        text_lower = response_text.lower()
        has_suggestion = any(keyword in text_lower for keyword in suggestion_keywords)

        if has_suggestion and matches:
            # Return first command found
            command = matches[0].strip()
            return PasteRequest(
                detected=True, command=command, original_text=f"```\n{command}\n```", confidence=0.7
            )

        return PasteRequest(detected=False)


class ResponseAnalyzer:
    """Analyzes Claude's responses for anti-patterns (Chain of Responsibility).

    This combines multiple detection strategies to identify when Claude
    asks user to paste command output instead of using tools.
    """

    def __init__(self, detectors: Optional[List[PasteRequestDetector]] = None):
        """Initialize analyzer with detectors.

        Args:
            detectors: List of PasteRequestDetector instances
        """
        if detectors is None:
            # Default detectors
            self.detectors = [
                RegexPasteDetector(),
                CodeBlockDetector(),
            ]
        else:
            self.detectors = detectors

    def analyze(self, response_text: str) -> PasteRequest:
        """Analyze response for paste requests.

        Uses multiple detectors and returns result with highest confidence.

        Args:
            response_text: Claude's response text

        Returns:
            PasteRequest with highest confidence detection
        """
        results = []

        # Run all detectors
        for detector in self.detectors:
            result = detector.detect(response_text)
            if result.detected:
                results.append(result)

        if not results:
            return PasteRequest(detected=False)

        # Return result with highest confidence
        best_result = max(results, key=lambda r: r.confidence)
        return best_result

    def add_detector(self, detector: PasteRequestDetector):
        """Add a custom detector to the chain.

        This makes the system Open/Closed:
        - Open for extension (add new detectors)
        - Closed for modification (no need to change existing code)

        Args:
            detector: Custom PasteRequestDetector
        """
        self.detectors.append(detector)
