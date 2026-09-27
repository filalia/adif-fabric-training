"""Get SQL Server and catalog details for a Fabric SQL database."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
SQL_DATABASES_ENDPOINT = f"{FABRIC_RESOURCE}/v1/workspaces"


def _find_value(item: dict, names: tuple[str, ...]) -> str | None:
    """Find a named value in the item or its properties."""
    containers = [item, item.get("properties", {})]
    for container in containers:
        for name in names:
            value = container.get(name)
            if isinstance(value, str) and value:
                return value
    return None


def get_sql_database_server_catalog(
    token: str, workspace_id: str, database_name: str
) -> dict:
    """Return server and catalog details for a named SQL database."""
    databases = []
    continuation_token = None

    while True:
        endpoint = f"{SQL_DATABASES_ENDPOINT}/{workspace_id}/sqlDatabases"
        if continuation_token:
            endpoint = f"{endpoint}?{urlencode({'continuationToken': continuation_token})}"

        request = Request(
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        try:
            with urlopen(request) as response:
                payload = json.load(response)
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Fabric SQL database request failed with HTTP {error.code}: {details}"
            ) from error
        except URLError as error:
            raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error

        databases.extend(payload.get("value", []))
        continuation_token = payload.get("continuationToken")
        if not continuation_token:
            break

    for database in databases:
        display_name = database.get("displayName", "")
        if display_name.casefold() != database_name.casefold():
            continue

        properties = database.get("properties", {})
        connection_string = _find_value(
            database, ("connectionString", "sqlConnectionString")
        ) or properties.get("connectionString")
        server = _find_value(
            database, ("server", "serverFqdn", "serverName", "sqlEndpoint")
        )
        catalog = _find_value(
            database, ("catalogName", "databaseName", "database", "sqlDatabaseName")
        ) or display_name

        return {
            "exists": True,
            "databaseName": display_name,
            "databaseId": database.get("id"),
            "server": server,
            "catalogName": catalog,
            "connectionString": connection_string,
            "rawDatabase": database,
        }

    return {
        "exists": False,
        "databaseName": database_name,
        "message": "SQL database does not exist or you do not have access to it.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    parser.add_argument("--workspace-id", required=True, help="Workspace GUID")
    parser.add_argument("--name", required=True, help="SQL database display name")
    args = parser.parse_args()

    try:
        result = get_sql_database_server_catalog(
            args.token, args.workspace_id, args.name
        )
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0 if result["exists"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
