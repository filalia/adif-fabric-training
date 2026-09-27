"""Add a Microsoft Fabric workspace role assignment for a principal."""

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
ALLOWED_PRINCIPAL_TYPES = (
    "User",
    "ServicePrincipal",
    "Group",
    "ServicePrincipalProfile",
    "EntireTenant",
)
ALLOWED_WORKSPACE_ROLES = ("Admin", "Member", "Contributor", "Viewer")


def add_workspace_role_assignment(
    token: str,
    workspace_id: str,
    principal_id: str,
    principal_type: str,
    role: str,
    *,
    display_name: str | None = None,
    user_principal_name: str | None = None,
    service_principal_app_id: str | None = None,
    group_type: str | None = None,
) -> dict[str, Any]:
    """Add a role assignment for a workspace principal."""
    principal: dict[str, Any] = {
        "id": principal_id,
        "type": principal_type,
    }

    if display_name:
        principal["displayName"] = display_name
    if principal_type == "User" and user_principal_name:
        principal["userDetails"] = {"userPrincipalName": user_principal_name}
    if principal_type == "ServicePrincipal" and service_principal_app_id:
        principal["servicePrincipalDetails"] = {"aadAppId": service_principal_app_id}
    if principal_type == "Group" and group_type:
        principal["groupDetails"] = {"groupType": group_type}

    payload = {
        "principal": principal,
        "role": role,
    }
    request = Request(
        f"{FABRIC_RESOURCE}/v1/workspaces/{workspace_id}/roleAssignments",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request) as response:
            result = {
                "status": response.status,
                "workspaceId": workspace_id,
                "principalId": principal_id,
                "principalType": principal_type,
                "role": role,
            }
            if response.headers.get("Location"):
                result["Location"] = response.headers["Location"]

            response_body = response.read().decode("utf-8").strip()
            if response_body:
                result.update(json.loads(response_body))

            return result
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Failed to add workspace role assignment (status {error.code}). {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    parser.add_argument("--workspace-id", required=True, help="Fabric workspace GUID")
    parser.add_argument(
        "--principal-id",
        required=True,
        help="Microsoft Entra object ID of the user, group, service principal, or tenant principal",
    )
    parser.add_argument(
        "--principal-type",
        required=True,
        choices=ALLOWED_PRINCIPAL_TYPES,
        help="Principal type to assign to the workspace",
    )
    parser.add_argument(
        "--role",
        required=True,
        choices=ALLOWED_WORKSPACE_ROLES,
        help="Workspace role to grant",
    )
    parser.add_argument("--display-name", help="Optional principal display name")
    parser.add_argument("--user-principal-name", help="Optional user principal name for User type")
    parser.add_argument(
        "--service-principal-app-id",
        help="Optional Entra app ID for ServicePrincipal type",
    )
    parser.add_argument(
        "--group-type",
        choices=("Unknown", "SecurityGroup", "DistributionList"),
        help="Optional group type for Group principals",
    )
    args = parser.parse_args()

    if args.principal_type != "User" and args.user_principal_name:
        parser.error("--user-principal-name can only be used when --principal-type is User")
    if args.principal_type != "ServicePrincipal" and args.service_principal_app_id:
        parser.error(
            "--service-principal-app-id can only be used when --principal-type is ServicePrincipal"
        )
    if args.principal_type != "Group" and args.group_type:
        parser.error("--group-type can only be used when --principal-type is Group")

    try:
        result = add_workspace_role_assignment(
            args.token,
            args.workspace_id,
            args.principal_id,
            args.principal_type,
            args.role,
            display_name=args.display_name,
            user_principal_name=args.user_principal_name,
            service_principal_app_id=args.service_principal_app_id,
            group_type=args.group_type,
        )
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())