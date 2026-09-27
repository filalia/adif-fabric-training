"""Create a Fabric Spark environment with a custom wheel library."""

import argparse
import base64
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
DEFAULT_ENVIRONMENT_NAME = "sparkenv"
DEFAULT_WHEEL_PATH = (
    Path("src")
    / "sparkenv.Environment"
    / "Libraries"
    / "CustomLibraries"
    / "DIFForFabric-1.0-py3-none-any.whl"
)


def create_spark_environment(
    token: str, workspace_id: str, wheel_path: Path, environment_name: str
) -> dict:
    """Create a Spark environment containing the requested custom wheel."""
    if not wheel_path.is_file():
        raise ValueError(f"Custom wheel does not exist: {wheel_path}")

    wheel_payload = base64.b64encode(wheel_path.read_bytes()).decode("ascii")
    payload = {
        "displayName": environment_name,
        "definition": {
            "parts": [
                {
                    "path": f"Libraries/CustomLibraries/{wheel_path.name}",
                    "payload": wheel_payload,
                    "payloadType": "InlineBase64",
                }
            ]
        },
    }
    request = Request(
        f"{FABRIC_RESOURCE}/v1/workspaces/{workspace_id}/environments",
        data=json.dumps(payload).encode("utf-8"),
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
                "environmentName": environment_name,
                "customLibrary": wheel_path.name,
            }
            if response.status not in (202, 204):
                environment = json.load(response)
                result["environmentId"] = environment.get("id")
            for header in ("Location", "x-ms-operation-id", "Retry-After"):
                value = response.headers.get(header)
                if value:
                    result[header] = value
            return result
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Fabric Spark environment creation failed with HTTP {error.code}: {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error


def resolve_environment_id(token: str, workspace_id: str, environment_name: str) -> str | None:
    """Resolve an environment ID by display name from a workspace."""
    base_url = f"{FABRIC_RESOURCE}/v1/workspaces/{workspace_id}/environments"
    continuation_token = None

    while True:
        url = base_url
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
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Unable to resolve Spark environment ID (HTTP {error.code}): {details}"
            ) from error
        except URLError as error:
            raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error

        for environment in payload.get("value", []):
            if environment.get("displayName", "").casefold() == environment_name.casefold():
                return environment.get("id")

        continuation_token = payload.get("continuationToken")
        if not continuation_token:
            return None


def publish_spark_environment(
    token: str, workspace_id: str, environment_id: str, sleep_seconds: int = 20
) -> dict:
    """Publish staged Spark environment changes after a short delay."""
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)

    request = Request(
        (
            f"{FABRIC_RESOURCE}/v1/workspaces/{workspace_id}/environments/"
            f"{environment_id}/staging/publish?beta=False"
        ),
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
                "environmentId": environment_id,
                "publishRequested": True,
            }
            for header in ("Location", "x-ms-operation-id", "Retry-After"):
                value = response.headers.get(header)
                if value:
                    result[header] = value

            location = result.get("Location")
            if response.status == 202 and location:
                while True:
                    poll_request = Request(
                        location,
                        headers={"Authorization": f"Bearer {token}"},
                        method="GET",
                    )
                    with urlopen(poll_request) as poll_response:
                        poll_payload = json.load(poll_response)

                    operation_state = (poll_payload.get("status") or "").casefold()
                    if operation_state in {"succeeded", "failed", "canceled"}:
                        result["operationStatus"] = poll_payload.get("status")
                        if operation_state != "succeeded":
                            raise RuntimeError(
                                f"Spark environment publish did not succeed: {json.dumps(poll_payload)}"
                            )
                        break

                    retry_after = poll_response.headers.get("Retry-After")
                    try:
                        poll_sleep = int(retry_after) if retry_after else 3
                    except ValueError:
                        poll_sleep = 3
                    time.sleep(max(poll_sleep, 1))

            return result
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Fabric Spark environment publish failed with HTTP {error.code}: {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    parser.add_argument("--workspace-id", required=True, help="Workspace GUID")
    parser.add_argument("--name", default=DEFAULT_ENVIRONMENT_NAME, help="Environment display name")
    parser.add_argument(
        "--wheel-path",
        type=Path,
        default=DEFAULT_WHEEL_PATH,
        help="Custom wheel to include in the environment",
    )
    args = parser.parse_args()

    try:
        result = create_spark_environment(
            args.token, args.workspace_id, args.wheel_path, args.name
        )
        environment_id = result.get("environmentId") or resolve_environment_id(
            args.token, args.workspace_id, args.name
        )
        if not environment_id:
            raise RuntimeError(
                "Spark environment was created but its ID could not be resolved for publishing."
            )

        publish_result = publish_spark_environment(
            args.token, args.workspace_id, environment_id, sleep_seconds=20
        )
        result["environmentId"] = environment_id
        result["publish"] = publish_result
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())