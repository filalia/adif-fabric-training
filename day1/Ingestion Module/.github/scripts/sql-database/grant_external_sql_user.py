"""Create an external SQL user and grant selected database permissions."""

import argparse
import struct
import sys
from typing import Any

SQL_COPT_SS_ACCESS_TOKEN = 1256
ROLE_STATEMENTS = {
    "reader": "ALTER ROLE [db_datareader] ADD MEMBER {user};",
    "writer": "ALTER ROLE [db_datawriter] ADD MEMBER {user};",
    "exec": "GRANT EXECUTE TO {user};",
}


def _quote_identifier(identifier: str) -> str:
    """Quote a SQL Server identifier as a bracketed identifier."""
    if not identifier or "\x00" in identifier:
        raise ValueError("External user name must be non-empty and contain no null bytes.")
    return f"[{identifier.replace(']', ']]')}]"


def _access_token_attribute(access_token: str) -> bytes:
    """Encode an Azure SQL token for the pyodbc access-token connection attribute."""
    token_bytes = access_token.encode("utf-16-le") + b"\x00\x00"
    return struct.pack(f"=I{len(token_bytes)}s", len(token_bytes), token_bytes)


def grant_external_sql_user(
    access_token: str,
    server: str,
    database: str,
    external_user: str,
    roles: list[str],
    driver: str = "ODBC Driver 18 for SQL Server",
) -> dict[str, Any]:
    """Connect to Azure SQL and create/grant an external user in one transaction."""
    try:
        import pyodbc
    except ImportError as error:
        raise RuntimeError(
            "pyodbc is required. Install it with: python -m pip install pyodbc"
        ) from error

    user_identifier = _quote_identifier(external_user)
    statements = [
        f"IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'{external_user.replace(chr(39), chr(39) * 2)}') "
        f"CREATE USER {user_identifier} FROM EXTERNAL PROVIDER;"
    ]
    statements.extend(ROLE_STATEMENTS[role].format(user=user_identifier) for role in roles)

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )
    connection = None
    try:
        connection = pyodbc.connect(
            connection_string,
            attrs_before={SQL_COPT_SS_ACCESS_TOKEN: _access_token_attribute(access_token)},
        )
        cursor = connection.cursor()
        for statement in statements:
            cursor.execute(statement)
        connection.commit()
    except pyodbc.Error as error:
        if connection is not None:
            connection.rollback()
        raise RuntimeError(f"SQL user provisioning failed: {error}") from error
    finally:
        if connection is not None:
            connection.close()

    return {
        "externalUser": external_user,
        "roles": roles,
        "database": database,
        "server": server,
        "status": "created_or_updated",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Azure SQL access token")
    parser.add_argument("--server", required=True, help="Azure SQL server host")
    parser.add_argument("--database", required=True, help="Target database name")
    parser.add_argument("--user", required=True, help="External user email or UPN")
    parser.add_argument(
        "--role",
        dest="roles",
        action="append",
        choices=sorted(ROLE_STATEMENTS),
        required=True,
        help="Permission to grant; repeat for reader, writer, or exec",
    )
    parser.add_argument("--driver", default="ODBC Driver 18 for SQL Server")
    args = parser.parse_args()

    try:
        result = grant_external_sql_user(
            args.token,
            args.server,
            args.database,
            args.user,
            args.roles,
            args.driver,
        )
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())