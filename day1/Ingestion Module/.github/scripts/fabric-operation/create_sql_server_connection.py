"""Create a Fabric SQL Server connection using workspace identity."""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from typing import Any

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
CONNECTIONS_URL = f"{FABRIC_RESOURCE}/v1/connections"


def create_sql_connection_with_workspace_identity(
    access_token: str,
    display_name: str,
    server: str,
    database: str,
    *,
    privacy_level: str = "Organizational",
    connectivity_type: str = "ShareableCloud",
    skip_test_connection: bool = False,
) -> dict[str, Any]:
    """Create a new SQL connection using Workspace Identity credentials."""
    connection_server = re.sub(r",\d+$", "", server)
    payload = {
        "displayName": display_name,
        "connectivityType": connectivity_type,
        "connectionDetails": {
            "type": "SQL",
            "creationMethod": "SQL",
            "parameters": [
                {"dataType": "Text", "name": "server", "value": connection_server},
                {"dataType": "Text", "name": "database", "value": database},
            ],
        },
        "privacyLevel": privacy_level,
        "credentialDetails": {
            "singleSignOnType": "None",
            "connectionEncryption": "Encrypted",
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
            f"Failed to create SQL connection (status {error.code}). {error_body}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Failed to reach Fabric API: {error.reason}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    parser.add_argument("--name", required=True, help="Fabric connection display name")
    parser.add_argument("--server", required=True, help="SQL Server host name")
    parser.add_argument("--database", required=True, help="SQL Server database name")
    parser.add_argument("--privacy-level", default="Organizational")
    parser.add_argument("--connectivity-type", default="ShareableCloud")
    parser.add_argument("--skip-test-connection", action="store_true")
    args = parser.parse_args()

    try:
        result = create_sql_connection_with_workspace_identity(
            args.token,
            args.name,
            args.server,
            args.database,
            privacy_level=args.privacy_level,
            connectivity_type=args.connectivity_type,
            skip_test_connection=args.skip_test_connection,
        )
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
