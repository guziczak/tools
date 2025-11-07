"""OAuth device flow authentication for Anthropic API."""

import time
import json
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import requests


class AuthenticationError(Exception):
    """Authentication error."""
    pass


class TokenStorage:
    """Secure token storage manager."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize token storage.

        Args:
            config_dir: Directory to store tokens (default: ~/.claude-code-py)
        """
        if config_dir is None:
            config_dir = Path.home() / ".claude-code-py"

        self.config_dir = config_dir
        self.token_file = config_dir / "auth.json"

        # Ensure directory exists with proper permissions
        self.config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    def save_token(self, token_data: Dict[str, Any]) -> None:
        """Save token data securely.

        Args:
            token_data: Token data from OAuth flow
        """
        # Add expiry timestamp
        if "expires_in" in token_data:
            expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
            token_data["expires_at"] = expires_at.isoformat()

        # Write with restricted permissions
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f, indent=2)

        # Ensure file is only readable by owner
        self.token_file.chmod(0o600)

    def load_token(self) -> Optional[Dict[str, Any]]:
        """Load token data.

        Returns:
            Token data or None if not found/expired
        """
        if not self.token_file.exists():
            return None

        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)

            # Check if token is expired
            if "expires_at" in token_data:
                expires_at = datetime.fromisoformat(token_data["expires_at"])
                if datetime.now() >= expires_at:
                    # Token expired
                    self.clear_token()
                    return None

            return token_data
        except Exception:
            return None

    def clear_token(self) -> None:
        """Clear stored token."""
        if self.token_file.exists():
            self.token_file.unlink()

    def get_access_token(self) -> Optional[str]:
        """Get valid access token.

        Returns:
            Access token or None if not available
        """
        token_data = self.load_token()
        if token_data:
            return token_data.get("access_token")
        return None


class DeviceFlowAuth:
    """OAuth device flow authentication."""

    # Anthropic OAuth endpoints
    DEVICE_AUTH_URL = "https://api.anthropic.com/v1/oauth/device"
    TOKEN_URL = "https://api.anthropic.com/v1/oauth/token"
    VERIFICATION_URL = "https://console.anthropic.com/device"

    # Client ID for Claude Code (this would need to be registered with Anthropic)
    # Note: This is a placeholder - you'd need the actual client_id from Anthropic
    CLIENT_ID = "claude-code-python"

    def __init__(self, token_storage: TokenStorage):
        """Initialize device flow authenticator.

        Args:
            token_storage: Token storage manager
        """
        self.token_storage = token_storage

    def start_device_flow(self) -> Dict[str, str]:
        """Start device authorization flow.

        Returns:
            Dict with device_code, user_code, verification_uri

        Raises:
            AuthenticationError: If request fails
        """
        try:
            response = requests.post(
                self.DEVICE_AUTH_URL,
                json={
                    "client_id": self.CLIENT_ID,
                    "scope": "api"
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise AuthenticationError(
                    "OAuth device flow not available. "
                    "Please use manual API key instead (set ANTHROPIC_API_KEY in .env)"
                )
            raise AuthenticationError(f"Failed to start device flow: {e}")
        except requests.RequestException as e:
            raise AuthenticationError(
                f"Failed to start device flow: {e}\n"
                "OAuth may not be available. Try using manual API key instead."
            )

    def poll_for_token(
        self,
        device_code: str,
        interval: int = 5,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Poll for access token.

        Args:
            device_code: Device code from start_device_flow
            interval: Polling interval in seconds
            timeout: Total timeout in seconds

        Returns:
            Token data

        Raises:
            AuthenticationError: If polling fails or times out
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.post(
                    self.TOKEN_URL,
                    json={
                        "client_id": self.CLIENT_ID,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    # Success!
                    token_data = response.json()
                    self.token_storage.save_token(token_data)
                    return token_data

                elif response.status_code == 400:
                    error = response.json().get("error")

                    if error == "authorization_pending":
                        # Still waiting for user authorization
                        time.sleep(interval)
                        continue
                    elif error == "slow_down":
                        # Increase polling interval
                        interval += 5
                        time.sleep(interval)
                        continue
                    elif error == "expired_token":
                        raise AuthenticationError("Device code expired. Please try again.")
                    elif error == "access_denied":
                        raise AuthenticationError("Authorization denied by user.")
                    else:
                        raise AuthenticationError(f"Authentication error: {error}")
                else:
                    raise AuthenticationError(f"Unexpected response: {response.status_code}")

            except requests.RequestException as e:
                raise AuthenticationError(f"Network error during polling: {e}")

        raise AuthenticationError("Authentication timed out. Please try again.")

    def authenticate(self, open_browser: bool = True) -> str:
        """Complete device flow authentication.

        Args:
            open_browser: Whether to automatically open browser

        Returns:
            Access token

        Raises:
            AuthenticationError: If authentication fails
        """
        # Start device flow
        flow_data = self.start_device_flow()

        user_code = flow_data["user_code"]
        device_code = flow_data["device_code"]
        verification_uri = flow_data.get("verification_uri_complete") or self.VERIFICATION_URL
        interval = flow_data.get("interval", 5)

        # Show user the verification URL and code
        print(f"\n{'='*60}")
        print(f"  Please authenticate in your browser")
        print(f"{'='*60}\n")
        print(f"  1. Visit: {verification_uri}")
        print(f"  2. Enter code: {user_code}\n")

        if open_browser:
            print("  Opening browser...")
            try:
                webbrowser.open(verification_uri)
            except Exception:
                print("  (Could not open browser automatically)")

        print(f"\n{'='*60}")
        print("  Waiting for authorization...")
        print(f"{'='*60}\n")

        # Poll for token
        token_data = self.poll_for_token(device_code, interval)

        return token_data["access_token"]


class AuthManager:
    """High-level authentication manager."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize auth manager.

        Args:
            config_dir: Directory to store tokens
        """
        self.token_storage = TokenStorage(config_dir)
        self.device_flow = DeviceFlowAuth(self.token_storage)

    def get_access_token(self, force_reauth: bool = False) -> str:
        """Get valid access token, authenticating if needed.

        Args:
            force_reauth: Force re-authentication even if token exists

        Returns:
            Valid access token

        Raises:
            AuthenticationError: If authentication fails
        """
        # Check for existing token
        if not force_reauth:
            token = self.token_storage.get_access_token()
            if token:
                return token

        # Need to authenticate
        return self.device_flow.authenticate()

    def logout(self) -> None:
        """Clear stored credentials."""
        self.token_storage.clear_token()

    def is_authenticated(self) -> bool:
        """Check if user is authenticated.

        Returns:
            True if valid token exists
        """
        return self.token_storage.get_access_token() is not None
