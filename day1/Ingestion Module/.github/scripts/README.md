# ADIF Scripts Environment

This folder contains the Python scripts used by the ADIF deployment workflows.

## Requirements

The scripts use Python's standard library. The SQL database script additionally requires:

- `pyodbc` (installed from `requirements.txt`)
- Microsoft ODBC Driver 18 for SQL Server installed on the machine

## Installation on Windows

From the repository root, run:

```powershell
cd .github\scripts
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run this once for the current user or activate the environment from Command Prompt instead:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Verify the Python dependency:

```powershell
python -c "import pyodbc; print(pyodbc.version)"
```

Install **ODBC Driver 18 for SQL Server** separately from Microsoft if it is not already installed. The SQL script defaults to this driver name and accepts `--driver` when another installed driver should be used.

## Usage

### Grant an external SQL user

Provide an Azure SQL access token and repeat `--role` for each permission:

```powershell
python sql-database\grant_external_sql_user.py `
  --token $env:AZURE_SQL_ACCESS_TOKEN `
  --server <server>.database.windows.net `
  --database <database-name> `
  --user <external-user-upn> `
  --role reader
```

Available roles are `reader`, `writer`, and `exec`. Do not commit access tokens or other secrets to the repository.

### Create a Fabric Data Pipeline connection

```powershell
python fabric-operation\create_data_pipeline_connection.py `
  --token $env:FABRIC_ACCESS_TOKEN `
  --name <connection-display-name>
```

The caller is responsible for acquiring a valid Fabric access token before running the script.

## Deactivate the environment

```powershell
deactivate
```
