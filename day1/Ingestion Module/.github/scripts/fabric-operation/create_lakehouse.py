"""Create a schema-enabled Microsoft Fabric Lakehouse."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
ONELAKE_DFS = "https://onelake.dfs.fabric.microsoft.com"
WORKSPACE_FOLDERS_ENDPOINT = f"{FABRIC_RESOURCE}/v1/workspaces"


def _request_json(request: Request) -> dict:
    try:
        with urlopen(request) as response:
            return json.load(response)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Fabric workspace folder request failed with HTTP {error.code}: {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error


def create_or_get_workspace_folder(
    token: str, workspace_id: str, folder_name: str
) -> dict:
    """Return an existing workspace folder or create it and return its ID."""
    continuation_token = None
    while True:
        endpoint = f"{WORKSPACE_FOLDERS_ENDPOINT}/{workspace_id}/folders"
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
        f"{WORKSPACE_FOLDERS_ENDPOINT}/{workspace_id}/folders",
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


def create_lakehouse_folder(
    onelake_token: str, workspace_id: str, lakehouse_id: str, folder_path: str
) -> dict:
    """Create a folder in a Lakehouse Files area."""
    normalized_path = folder_path.strip("/")
    if not normalized_path:
        raise ValueError("Folder path must not be empty.")

    endpoint = (
        f"{ONELAKE_DFS}/{workspace_id}/{lakehouse_id}/Files/"
        f"{quote(normalized_path, safe='/')}?resource=directory"
    )
    request = Request(
        endpoint,
        headers={
            "Authorization": f"Bearer {onelake_token}",
            "x-ms-version": "2023-11-03",
        },
        method="PUT",
    )

    try:
        with urlopen(request) as response:
            return {
                "status": response.status,
                "message": "Lakehouse folder created or already exists.",
                "folderPath": f"Files/{normalized_path}",
            }
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Lakehouse folder creation failed with HTTP {error.code}: {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the OneLake API: {error.reason}") from error


def create_lakehouse(
    token: str,
    workspace_id: str,
    lakehouse_name: str,
    folder_path: str | None = None,
    onelake_token: str | None = None,
    workspace_folder_name: str | None = None,
) -> dict:
    """Create a schema-enabled Lakehouse and optionally add a Files folder."""
    endpoint = f"{FABRIC_RESOURCE}/v1/workspaces/{workspace_id}/lakehouses"
    payload = {
        "displayName": lakehouse_name,
        "creationPayload": {"enableSchemas": True},
    }
    if workspace_folder_name:
        workspace_folder = create_or_get_workspace_folder(
            token, workspace_id, workspace_folder_name
        )
        payload["folderId"] = workspace_folder["folderId"]
    payload = json.dumps(payload).encode("utf-8")
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
                "message": "Lakehouse created with schemas enabled.",
            }
            if response.status != 202:
                lakehouse = json.load(response)
                result["lakehouse"] = lakehouse
                if folder_path:
                    if not onelake_token:
                        raise ValueError(
                            "An OneLake token is required when specifying --folder-path."
                        )
                    result["folder"] = create_lakehouse_folder(
                        onelake_token, workspace_id, lakehouse["id"], folder_path
                    )
            for header in ("Location", "x-ms-operation-id", "Retry-After"):
                value = response.headers.get(header)
                if value:
                    result[header] = value
            return result
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Fabric Lakehouse creation failed with HTTP {error.code}: {error_body}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    parser.add_argument("--workspace-id", required=True, help="Workspace GUID")
    parser.add_argument("--name", help="Lakehouse display name")
    parser.add_argument("--lakehouse-id", help="Existing Lakehouse GUID for folder creation")
    parser.add_argument("--folder-path", help="Optional folder path under the Lakehouse Files area")
    parser.add_argument("--onelake-token", help="OneLake storage access token for folder creation")
    parser.add_argument(
        "--workspace-folder-name",
        help="Optional workspace folder name for a new Lakehouse",
    )
    args = parser.parse_args()

    try:
        if args.lakehouse_id:
            if not args.folder_path:
                raise ValueError("--folder-path is required with --lakehouse-id.")
            if not args.onelake_token:
                raise ValueError("--onelake-token is required with --folder-path.")
            result = create_lakehouse_folder(
                args.onelake_token,
                args.workspace_id,
                args.lakehouse_id,
                args.folder_path,
            )
        else:
            if not args.name:
                raise ValueError("--name is required when creating a Lakehouse.")
            result = create_lakehouse(
                args.token,
                args.workspace_id,
                args.name,
                args.folder_path,
                args.onelake_token,
                args.workspace_folder_name,
            )
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
