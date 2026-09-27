"""Create a Fabric Data Pipeline connection using workspace identity."""

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
CONNECTIONS_URL = f"{FABRIC_RESOURCE}/v1/connections"
CONNECTION_TYPE = "FabricDataPipelines"
CREATION_METHOD = "FabricDataPipelines.Actions"


def parse_connection_parameter(raw_parameter: str) -> dict[str, str]:
    """Parse a connection parameter from name=value or name:dataType=value."""
    if "=" not in raw_parameter:
        raise ValueError(
            f"Invalid parameter '{raw_parameter}'. Use name=value or name:dataType=value."
        )

    name_and_type, value = raw_parameter.split("=", 1)
    if not name_and_type:
        raise ValueError(f"Invalid parameter '{raw_parameter}'. Parameter name is required.")

    if ":" in name_and_type:
        name, data_type = name_and_type.split(":", 1)
    else:
        name, data_type = name_and_type, "Text"

    if not name:
        raise ValueError(f"Invalid parameter '{raw_parameter}'. Parameter name is required.")
    if not data_type:
        raise ValueError(f"Invalid parameter '{raw_parameter}'. Data type is required.")

    return {
        "dataType": data_type,
        "name": name,
        "value": value,
    }


def create_data_pipeline_connection_with_workspace_identity(
    access_token: str,
    display_name: str,
    parameters: list[dict[str, str]] | None = None,
    *,
    privacy_level: str = "Organizational",
    connectivity_type: str = "ShareableCloud",
    skip_test_connection: bool = False,
) -> dict[str, Any]:
    """Create a new Fabric cloud connection for Data Pipeline use."""
    resolved_parameters = parameters or []
    payload = {
        "displayName": display_name,
        "connectivityType": connectivity_type,
        "connectionDetails": {
            "type": CONNECTION_TYPE,
            "creationMethod": CREATION_METHOD,
            "parameters": resolved_parameters,
        },
        "privacyLevel": privacy_level,
        "credentialDetails": {
            "singleSignOnType": "None",
            "connectionEncryption": "NotEncrypted",
            "skipTestConnection": skip_test_connection,
            "credentials": {
                "credentialType": "WorkspaceIdentity",
            },
        },
    }
    request = urllib.request.Request(
        CONNECTIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Failed to create Data Pipeline connection (status {error.code}). {error_body}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Failed to reach Fabric API: {error.reason}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    parser.add_argument("--name", required=True, help="Fabric connection display name")
    args = parser.parse_args()

    try:
        result = create_data_pipeline_connection_with_workspace_identity(args.token, args.name)
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())