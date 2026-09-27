"""Create a Microsoft Fabric workspace."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
WORKSPACES_ENDPOINT = f"{FABRIC_RESOURCE}/v1/workspaces"


def create_workspace(workspace_name: str, token: str) -> dict:
    """Create a Fabric workspace and return its API response."""
    payload = json.dumps({"displayName": workspace_name}).encode("utf-8")
    request = Request(
        WORKSPACES_ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request) as response:
            return json.load(response)
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Fabric workspace creation failed with HTTP {error.code}: {error_body}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_name", help="Display name for the new Fabric workspace")
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    args = parser.parse_args()

    try:
        workspace = create_workspace(args.workspace_name, args.token)
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(workspace, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
