"""Create a Fabric Spark job definition with Lakehouse and environment bindings."""

import argparse
import base64
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"


def with_executable_workspace_id(executable_file: str, workspace_id: str) -> str:
    """Replace an ABFSS executable URI's workspace segment with a workspace GUID."""
    parsed = urlsplit(executable_file)
    if parsed.scheme != "abfss" or "@" not in parsed.netloc:
        raise ValueError(
            "Spark job executableFile must be an ABFSS URI with a workspace authority."
        )

    _, onelake_host = parsed.netloc.split("@", maxsplit=1)
    return urlunsplit(
        (
            parsed.scheme,
            f"{workspace_id}@{onelake_host}",
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )


def verify_lakehouse(token: str, workspace_id: str, lakehouse_id: str) -> None:
    """Verify that a referenced Lakehouse is accessible in its workspace."""
    request = Request(
        f"{FABRIC_RESOURCE}/v1/workspaces/{workspace_id}/lakehouses/{lakehouse_id}",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urlopen(request):
            pass
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Lakehouse {lakehouse_id} is unavailable in workspace {workspace_id}: "
            f"HTTP {error.code}: {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error


def create_spark_job(
    token: str,
    workspace_id: str,
    job_name: str,
    definition_path: Path,
    default_lakehouse_id: str,
    default_lakehouse_workspace_id: str,
    environment_id: str,
    additional_lakehouse_ids: list[str],
    additional_lakehouse_workspace_ids: list[str],
    executable_workspace_id: str,
    spark_job_id: str | None = None,
) -> dict:
    """Create or update a Spark job definition with its requested Fabric bindings."""
    if not definition_path.is_file():
        raise ValueError(f"Spark job definition does not exist: {definition_path}")
    if len(additional_lakehouse_ids) != len(additional_lakehouse_workspace_ids):
        raise ValueError(
            "Each --additional-lakehouse-id requires a matching "
            "--additional-lakehouse-workspace-id."
        )

    verify_lakehouse(token, default_lakehouse_workspace_id, default_lakehouse_id)
    for lakehouse_id, lakehouse_workspace_id in zip(
        additional_lakehouse_ids, additional_lakehouse_workspace_ids, strict=True
    ):
        verify_lakehouse(token, lakehouse_workspace_id, lakehouse_id)

    definition = json.loads(definition_path.read_text(encoding="utf-8"))
    definition["defaultLakehouseArtifactId"] = default_lakehouse_id
    definition["additionalLakehouseIds"] = additional_lakehouse_ids
    definition["environmentArtifactId"] = environment_id
    definition["executableFile"] = with_executable_workspace_id(
        definition["executableFile"], executable_workspace_id
    )
    definition_payload = base64.b64encode(
        json.dumps(definition, indent=2).encode("utf-8")
    ).decode("ascii")

    definition_request = {
        "displayName": job_name,
        "definition": {
            "format": "SparkJobDefinitionV1",
            "parts": [
                {
                    "path": "SparkJobDefinitionV1.json",
                    "payload": definition_payload,
                    "payloadType": "InlineBase64",
                }
            ],
        },
    }
    if spark_job_id:
        endpoint = f"{FABRIC_RESOURCE}/v1/workspaces/{workspace_id}/items/{spark_job_id}/updateDefinition"
        payload = {"definition": definition_request["definition"]}
    else:
        endpoint = f"{FABRIC_RESOURCE}/v1/workspaces/{workspace_id}/sparkJobDefinitions"
        payload = definition_request
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
                "sparkJobName": job_name,
                "defaultLakehouseId": default_lakehouse_id,
                "defaultLakehouseWorkspaceId": default_lakehouse_workspace_id,
                "additionalLakehouses": [
                    {"workspaceId": workspace_id, "lakehouseId": lakehouse_id}
                    for lakehouse_id, workspace_id in zip(
                        additional_lakehouse_ids,
                        additional_lakehouse_workspace_ids,
                        strict=True,
                    )
                ],
                "environmentId": environment_id,
                "executableWorkspaceId": executable_workspace_id,
                "executableFile": definition["executableFile"],
            }
            if spark_job_id:
                result["sparkJobId"] = spark_job_id
            elif response.status not in (202, 204):
                spark_job = json.load(response)
                result["sparkJobId"] = spark_job.get("id")
            for header in ("Location", "x-ms-operation-id", "Retry-After"):
                value = response.headers.get(header)
                if value:
                    result[header] = value
            return result
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Fabric Spark job creation failed with HTTP {error.code}: {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    parser.add_argument("--workspace-id", required=True, help="Workspace GUID")
    parser.add_argument("--name", required=True, help="Spark job display name")
    parser.add_argument(
        "--spark-job-id",
        help="Existing Spark job GUID to update instead of creating a new job",
    )
    parser.add_argument(
        "--definition-path",
        type=Path,
        required=True,
        help="Path to a SparkJobDefinitionV1.json template",
    )
    parser.add_argument(
        "--default-lakehouse-id", required=True, help="Default Lakehouse GUID"
    )
    parser.add_argument(
        "--default-lakehouse-workspace-id",
        help="Workspace GUID containing the default Lakehouse; defaults to --workspace-id",
    )
    parser.add_argument("--environment-id", required=True, help="Spark environment GUID")
    parser.add_argument(
        "--executable-workspace-id",
        help="Workspace GUID used in the executableFile ABFSS URI; defaults to --workspace-id",
    )
    parser.add_argument(
        "--additional-lakehouse-id",
        action="append",
        default=[],
        help="Optional additional Lakehouse GUID; repeat for each Lakehouse",
    )
    parser.add_argument(
        "--additional-lakehouse-workspace-id",
        action="append",
        help="Workspace GUID for an additional Lakehouse; repeat in matching order",
    )
    args = parser.parse_args()

    try:
        result = create_spark_job(
            args.token,
            args.workspace_id,
            args.name,
            args.definition_path,
            args.default_lakehouse_id,
            args.default_lakehouse_workspace_id or args.workspace_id,
            args.environment_id,
            args.additional_lakehouse_id,
            args.additional_lakehouse_workspace_id or [args.workspace_id]
            * len(args.additional_lakehouse_id),
            args.executable_workspace_id or args.workspace_id,
            args.spark_job_id,
        )
    except (RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())