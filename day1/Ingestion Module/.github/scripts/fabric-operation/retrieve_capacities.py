"""Retrieve Microsoft Fabric capacities."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
CAPACITIES_ENDPOINT = f"{FABRIC_RESOURCE}/v1/capacities"
CAPACITY_NOT_FOUND_MESSAGE = "Capacity doesn't exist or you don't have access to it."


def retrieve_capacities(token: str, capacity_name: str | None = None) -> dict:
    """Return all accessible capacities or the requested capacity details."""
    capacities = []
    continuation_token = None

    while True:
        url = CAPACITIES_ENDPOINT
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
            if error.code in (401, 403):
                return {"message": CAPACITY_NOT_FOUND_MESSAGE}
            error_body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Fabric capacity request failed with HTTP {error.code}: {error_body}"
            ) from error
        except URLError as error:
            raise RuntimeError(f"Unable to reach the Fabric API: {error.reason}") from error

        capacities.extend(payload.get("value", []))
        continuation_token = payload.get("continuationToken")
        if not continuation_token:
            break

    if capacity_name is None:
        return {"capacities": capacities}

    for capacity in capacities:
        if capacity.get("displayName", "").casefold() == capacity_name.casefold():
            return {
                "message": f"Capacity exists: {capacity.get('displayName', capacity_name)}",
                "id": capacity.get("id"),
                "displayName": capacity.get("displayName", capacity_name),
            }

    return {"message": CAPACITY_NOT_FOUND_MESSAGE}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Fabric access token acquired by the caller")
    parser.add_argument("--name", help="Optional capacity display name")
    args = parser.parse_args()

    try:
        result = retrieve_capacities(args.token, args.name)
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())