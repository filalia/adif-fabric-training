"""Create a Microsoft Fabric SQL database in a workspace."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
ITEMS_ENDPOINT = f"{FABRIC_RESOURCE}/v1/workspaces"
FOLDERS_ENDPOINT = f"{FABRIC_RESOURCE}/v1/workspaces"


def _request_json(request: Request) -> dict:
    try:
        with urlopen(request) as response:
            return json.load(response)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Fabric folder request failed with HTTP {error.code}: {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error


def create_or_get_folder(token: str, workspace_id: str, folder_name: str) -> dict:
    """Return an existing workspace folder or create it and return its ID."""
    continuation_token = None
    while True:
        endpoint = f"{FOLDERS_ENDPOINT}/{workspace_id}/folders"
        if continuation_token:
            endpoint = f"{endpoint}?{urlencode({'continuationToken': continuation_token})}"
        request = Request(
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        payload = _request_json(request)
        for folder in payload.get("value", []):
            if folder.get("displayName", "").casefold() == folder_name.casefold():
                return {
                    "folderName": folder.get("displayName", folder_name),
                    "folderId": folder.get("id"),
                    "created": False,
                }
        continuation_token = payload.get("continuationToken")
        if not continuation_token:
            break

    request = Request(
        f"{FOLDERS_ENDPOINT}/{workspace_id}/folders",
        data=json.dumps({"displayName": folder_name}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    folder = _request_json(request)
    return {
        "folderName": folder.get("displayName", folder_name),
        "folderId": folder.get("id"),
        "created": True,
    }


def create_sql_database(
    token: str,
    workspace_id: str,
    database_name: str,
    description: str | None = None,
    collation: str | None = None,
    folder_id: str | None = None,
    folder_name: str | None = None,
) -> dict:
    """Create a SQLDatabase item using one Fabric API call."""
    if folder_id and folder_name:
        raise ValueError("Specify either folder_id or folder_name, not both.")
    
    if folder_name:
        folder_id = create_or_get_folder(token, workspace_id, folder_name)["folderId"]

    endpoint = f"{ITEMS_ENDPOINT}/{workspace_id}/items"
    creation_payload = {"creationMode": "new"}
    if collation:
        creation_payload["collation"] = collation

    payload = {
        "displayName": database_name,
        "type": "SQLDatabase",
        "creationPayload": creation_payload,
    }
    if folder_id:
        payload["folderId"] = folder_id
    if description:
        payload["description"] = description

    request = Request(
        endpoint,
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
                "message": "SQL database creation accepted.",
            }
            if response.status not in (202, 204):
                result["database"] = json.load(response)
            for header in ("Location", "x-ms-operation-id", "Retry-After"):
                value = response.headers.get(header)
                if value:
                    result[header] = value
            return result
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Fabric SQL database creation failed with HTTP {error.code}: {error_body}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    parser.add_argument("--workspace-id", required=True, help="DE workspace GUID")
    parser.add_argument("--name", required=True, help="SQL database display name")
    parser.add_argument("--description", help="Optional database description")
    parser.add_argument("--collation", help="Optional database collation")
    parser.add_argument("--folder-id", help="Optional workspace folder GUID")
    parser.add_argument("--folder-name", help="Create or reuse a workspace folder by name")
    args = parser.parse_args()

    try:
        result = create_sql_database(
            args.token,
            args.workspace_id,
            args.name,
            args.description,
            args.collation,
            args.folder_id,
            args.folder_name,
        )
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
