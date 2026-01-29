"""Tests for AppConfig."""

import os
import pytest


def test_from_env_defaults(monkeypatch):
    """from_env() returns sensible defaults when env vars are empty."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("CLAUDE_MODEL", raising=False)
    monkeypatch.delenv("CLAUDE_MAX_TOKENS", raising=False)
    monkeypatch.delenv("CLAUDE_TEMPERATURE", raising=False)
    monkeypatch.delenv("CLAUDE_THINKING_ENABLED", raising=False)
    monkeypatch.delenv("CLAUDE_THINKING_BUDGET", raising=False)
    monkeypatch.delenv("CLAUDE_USE_OAUTH", raising=False)
    monkeypatch.delenv("CLAUDE_TOOLS_ENABLED", raising=False)
    monkeypatch.delenv("CLAUDE_AGENTS_ENABLED", raising=False)

    from config.app_config import AppConfig

    cfg = AppConfig.from_env()
    assert cfg.api_key == ""
    assert cfg.model == "claude-sonnet-4-20250514"
    assert cfg.max_tokens == 8000
    assert cfg.temperature == 1.0
    assert cfg.thinking_enabled is True
    assert cfg.thinking_budget == 10000
    assert cfg.use_oauth is False
    assert cfg.tools_enabled is True
    assert cfg.agents_enabled is True


def test_from_env_custom(monkeypatch):
    """from_env() reads custom values from environment."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    monkeypatch.setenv("CLAUDE_MODEL", "claude-opus-4-20250514")
    monkeypatch.setenv("CLAUDE_MAX_TOKENS", "16000")
    monkeypatch.setenv("CLAUDE_TEMPERATURE", "0.5")
    monkeypatch.setenv("CLAUDE_THINKING_ENABLED", "false")
    monkeypatch.setenv("CLAUDE_THINKING_BUDGET", "5000")
    monkeypatch.setenv("CLAUDE_USE_OAUTH", "true")
    monkeypatch.setenv("CLAUDE_TOOLS_ENABLED", "false")
    monkeypatch.setenv("CLAUDE_AGENTS_ENABLED", "false")

    from config.app_config import AppConfig

    cfg = AppConfig.from_env()
    assert cfg.api_key == "sk-test-key"
    assert cfg.model == "claude-opus-4-20250514"
    assert cfg.max_tokens == 16000
    assert cfg.temperature == 0.5
    assert cfg.thinking_enabled is False
    assert cfg.thinking_budget == 5000
    assert cfg.use_oauth is True
    assert cfg.tools_enabled is False
    assert cfg.agents_enabled is False


def test_from_env_oauth_token_fallback(monkeypatch):
    """from_env() falls back to CLAUDE_CODE_OAUTH_TOKEN if no API key."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat-test")

    from config.app_config import AppConfig

    cfg = AppConfig.from_env()
    assert cfg.api_key == "sk-ant-oat-test"


def test_frozen(monkeypatch):
    """AppConfig is frozen (immutable)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    from config.app_config import AppConfig

    cfg = AppConfig.from_env()
    with pytest.raises(AttributeError):
        cfg.model = "other"  # type: ignore[misc]
