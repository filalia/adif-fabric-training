"""Provision a Microsoft Fabric workspace identity."""

import argparse
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
WORKSPACES_ENDPOINT = f"{FABRIC_RESOURCE}/v1/workspaces"


def get_workspace(token: str, workspace_id: str) -> dict:
    """Return workspace details from the Fabric API."""
    request = Request(
        f"{WORKSPACES_ENDPOINT}/{workspace_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request) as response:
            return json.load(response)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Workspace lookup failed with HTTP {error.code}: {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error


def provision_workspace_identity(
    token: str,
    workspace_id: str,
    *,
    timeout_seconds: int = 300,
    poll_interval_seconds: int = 5,
) -> dict:
    """Provision a workspace identity and return its GUID when available."""
    endpoint = f"{WORKSPACES_ENDPOINT}/{workspace_id}/provisionIdentity"
    request = Request(
        endpoint,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request) as response:
            result = {
                "status": response.status,
                "message": "Workspace identity provisioned.",
            }
            if response.status == 200:
                result["identity"] = json.load(response)
            for header in ("Location", "x-ms-operation-id", "Retry-After"):
                value = response.headers.get(header)
                if value:
                    result[header] = value
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Workspace identity provisioning failed with HTTP {error.code}: {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error

    deadline = time.monotonic() + timeout_seconds
    retry_after = result.get("Retry-After")
    if retry_after:
        try:
            initial_delay = max(1, int(retry_after))
        except ValueError:
            initial_delay = poll_interval_seconds
        time.sleep(min(initial_delay, max(1, timeout_seconds)))

    while True:
        workspace = get_workspace(token, workspace_id)
        workspace_identity = workspace.get("workspaceIdentity") or {}
        service_principal_id = workspace_identity.get("servicePrincipalId")

        if service_principal_id:
            result["workspaceIdentity"] = workspace_identity
            result["workspaceIdentityServicePrincipalId"] = service_principal_id
            return result

        if time.monotonic() >= deadline:
            raise RuntimeError(
                "Workspace identity provisioning did not expose a servicePrincipalId "
                f"within {timeout_seconds} seconds."
            )

        time.sleep(poll_interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    parser.add_argument("--workspace-id", required=True, help="Workspace GUID")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
        help="Maximum time to wait for the workspace identity GUID to appear",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=5,
        help="Polling interval for workspace identity lookup",
    )
    args = parser.parse_args()

    if args.timeout_seconds < 1:
        parser.error("--timeout-seconds must be at least 1")
    if args.poll_interval_seconds < 1:
        parser.error("--poll-interval-seconds must be at least 1")

    try:
        result = provision_workspace_identity(
            args.token,
            args.workspace_id,
            timeout_seconds=args.timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
