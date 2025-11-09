"""Automatic API key generation from OAuth token.

This module implements a hybrid authentication system:
1. User goes through OAuth flow (like official Claude Code)
2. OAuth token is used to automatically generate an API key
3. API key is saved and used for all subsequent requests

This gives the best of both worlds:
- Seamless OAuth experience (no manual key copying)
- Full API functionality (tools, agents, thinking)
- Works with Claude Max/Pro subscriptions
"""

import httpx
import json
from typing import Optional
from pathlib import Path


def generate_api_key_from_oauth(
    oauth_token: str, key_name: str = "claude-code-python-auto"
) -> Optional[str]:
    """Generate API key from OAuth token automatically.

    Args:
        oauth_token: OAuth token from claude setup-token
        key_name: Name for the generated API key

    Returns:
        API key string if successful, None otherwise
    """
    print("\n🔄 Converting OAuth token to API key...")

    client = httpx.Client(
        base_url="https://api.anthropic.com",
        headers={
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )

    try:
        # Try to generate API key using OAuth token
        response = client.post("/api/oauth/claude_cli/create_api_key", json={"name": key_name})

        if response.status_code == 200:
            data = response.json()
            api_key = data.get("key") or data.get("api_key")

            if api_key:
                print("✅ API key generated successfully!")
                return api_key

        # If permission error, user needs different scope
        if response.status_code == 403:
            error_data = response.json()
            if "scope" in error_data.get("error", {}).get("message", ""):
                print("⚠️  OAuth token doesn't have permission to create API keys")
                print("   This is a limitation of the current OAuth token scope")
                return None

        print(f"❌ Failed to generate API key: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return None

    except Exception as e:
        print(f"❌ Error generating API key: {e}")
        return None
    finally:
        client.close()


def save_oauth_token(oauth_token: str) -> bool:
    """Save OAuth token to local credentials file.

    Args:
        oauth_token: OAuth token to save

    Returns:
        True if successful
    """
    try:
        creds_dir = Path(".claude")
        creds_dir.mkdir(exist_ok=True)

        creds_file = creds_dir / "oauth_token.json"

        data = {"accessToken": oauth_token, "source": "claude-code-python-auto-setup"}

        with open(creds_file, "w") as f:
            json.dump(data, f, indent=2)

        return True
    except Exception as e:
        print(f"⚠️  Could not save OAuth token: {e}")
        return False
