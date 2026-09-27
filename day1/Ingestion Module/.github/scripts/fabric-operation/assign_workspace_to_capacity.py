"""Assign a Microsoft Fabric workspace to a capacity."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"


def assign_workspace_to_capacity(
    token: str, workspace_id: str, capacity_id: str
) -> dict:
    """Start assigning a workspace to a Fabric capacity."""
    endpoint = f"{FABRIC_RESOURCE}/v1/workspaces/{workspace_id}/assignToCapacity"
    payload = json.dumps({"capacityId": capacity_id}).encode("utf-8")
    request = Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request) as response:
            result = {
                "status": response.status,
                "message": "Capacity assignment accepted and is in progress.",
            }
            location = response.headers.get("Location")
            if location:
                result["location"] = location
            return result
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Fabric capacity assignment failed with HTTP {error.code}: {error_body}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    parser.add_argument("--workspace-id", required=True, help="Workspace GUID")
    parser.add_argument("--capacity-id", required=True, help="Capacity GUID")
    args = parser.parse_args()

    try:
        result = assign_workspace_to_capacity(
            args.token,
            args.workspace_id,
            args.capacity_id,
        )
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
