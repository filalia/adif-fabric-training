"""Verify that a workspace exists in Microsoft Fabric."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
WORKSPACES_ENDPOINT = f"{FABRIC_RESOURCE}/v1/workspaces"


def verify_workspace(workspace_name: str, token: str) -> dict:
    """Return workspace name, ID, and existence for an accessible workspace."""
    continuation_token = None

    while True:
        url = WORKSPACES_ENDPOINT
        if continuation_token:
            url = f"{url}?{urlencode({'continuationToken': continuation_token})}"

        request = Request(
            url,
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        try:
            with urlopen(request) as response:
                payload = json.load(response)
        except HTTPError as error:
            raise RuntimeError(f"Fabric workspace request failed with HTTP {error.code}.") from error
        except URLError as error:
            raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error

        for workspace in payload.get("value", []):
            if workspace.get("displayName", "").casefold() == workspace_name.casefold():
                return {
                    "workspaceName": workspace.get("displayName", workspace_name),
                    "workspaceId": workspace.get("id"),
                    "exists": True,
                }

        continuation_token = payload.get("continuationToken")
        if not continuation_token:
            return {
                "workspaceName": workspace_name,
                "workspaceId": None,
                "exists": False,
            }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_name", help="Fabric workspace display name to verify")
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    args = parser.parse_args()

    try:
        result = verify_workspace(args.workspace_name, args.token)
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0 if result["exists"] else 1


if __name__ == "__main__":
    raise SystemExit(main())