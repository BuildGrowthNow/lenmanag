#!/usr/bin/env python3
"""Get JWT token for AI agent testing.

Quick script for AI agents to authenticate and get a JWT token.
"""

import json
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def get_token(base_url="http://localhost:8000"):
    """Get JWT token for AI agent."""
    url = f"{base_url}/api/v1/users/login"

    payload = {
        "email": "ai-agent@lenquant.internal",
        "password": "LQ$aiAgent2026!Secure#TestOnly",
    }

    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            token = data["data"]["access_token"]
            user_id = data["data"]["user"]["id"]
            email = data["data"]["user"]["email"]

            print("[OK] Authentication successful")
            print(f"Email: {email}")
            print(f"User ID: {user_id}")
            print("\nAccess Token:")
            print(token)
            print("\nUsage:")
            print(f'export TOKEN="{token}"')
            print(f'curl -H "Authorization: Bearer $TOKEN" {base_url}/api/v1/users/me')

            return token

    except HTTPError as e:
        print(f"[ERROR] Authentication failed: {e.code} {e.reason}", file=sys.stderr)
        print(e.read().decode("utf-8"), file=sys.stderr)
        return None


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    token = get_token(base_url)
    sys.exit(0 if token else 1)
