"""Proxy server lifecycle management.

Extracted from ``main.py`` to follow Single Responsibility.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Optional, Tuple

from core.logging import get_logger

logger = get_logger(__name__)


def ensure_proxy_dependencies() -> bool:
    """Install Flask and cloudscraper if missing. Returns True if ready."""
    missing = []
    try:
        import flask  # noqa: F401
    except ImportError:
        missing.append("flask")
    try:
        import cloudscraper  # noqa: F401
    except ImportError:
        missing.append("cloudscraper")

    if not missing:
        return True

    import subprocess

    logger.info("Installing missing proxy dependencies: %s", ", ".join(missing))
    for flags in [["--user"], []]:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", *flags, *missing],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Successfully installed: %s", ", ".join(missing))
            return True
        except subprocess.CalledProcessError:
            continue

    logger.error("Failed to install: %s. Run: pip install %s", ", ".join(missing), " ".join(missing))
    return False


def start_proxy_if_needed(api_key: str) -> Optional[str]:
    """Start proxy for OAuth/session tokens. Returns proxy base URL or None.

    Modifies ``ANTHROPIC_BASE_URL`` in the environment if proxy starts.
    """
    if not (api_key.startswith("sk-ant-oat") or api_key.startswith("sk-ant-sid01-")):
        return None

    if not ensure_proxy_dependencies():
        return None

    try:
        from proxy import start_proxy_server, get_proxy_base_url

        proxy_started, proxy_port = start_proxy_server(api_key, port=8765)
        if proxy_started:
            proxy_url = get_proxy_base_url(proxy_port)
            os.environ["ANTHROPIC_BASE_URL"] = proxy_url
            logger.info("Proxy started at %s", proxy_url)
            time.sleep(1)
            return proxy_url
        else:
            logger.error("Failed to start proxy")
            return None
    except Exception as exc:
        logger.error("Proxy error: %s", exc)
        return None
