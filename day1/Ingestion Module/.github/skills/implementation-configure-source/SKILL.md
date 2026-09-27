---
name: implementation-configure-source
description: 'Generate a source configuration SQL script from .github/templates/source.sql by replacing all <%=$...%> placeholders with provided values. Use for implementation-configure-source, source SQL generation, filling source template parameters, and creating Source table configuration scripts.'
argument-hint: '[source name] [source type] [instance url] [authentification mode] [username] [secret name] [instance name]'
---

# Configure Source

Generate a source configuration SQL script by taking the template in [source.sql](../../templates/source.sql) and replacing every placeholder between `<%=$...%>` with the provided values.

This skill is for generating the SQL script content. It should preserve the source template and write the filled result into the `temp` folder at the repository root for review or execution.

Read [mandatory_parameters.json](./mandatory_parameters.json) to identify the required information before generating the source configuration.

## Template Parameters

The template expects these parameters:

- `sourcename`
- `sourcetype`
- `instanceurl`
- `authentificationmode`
- `username`
- `secretname`
- `instancename`

## Required Inputs

Ask for and confirm the template fields needed to fill [source.sql](../../templates/source.sql):

- Source name
- Source type
- Instance URL
- Authentification mode
- User name
- Secret name
- Instance name

Read [mandatory_parameters.json](./mandatory_parameters.json) first to determine whether more information is required before generating the SQL script.

## Procedure

1. Read [mandatory_parameters.json](./mandatory_parameters.json) to identify the required information for source configuration.
2. Read the SQL template from [source.sql](../../templates/source.sql).
3. List the required placeholders from the template and map each one to the confirmed user-provided parameter.
4. Replace every placeholder in the template with the confirmed values.
5. Create or reuse the `temp` folder in the repository root.
6. Generate the filled SQL script without changing the source template file.
7. If multiple source configurations are requested, generate one filled SQL block per source and combine all blocks into a single output file.
8. Separate each generated SQL block in that combined file with `GO` on its own line.
9. Save the generated SQL script into the root `temp` folder.
10. Present the saved output path and the generated SQL script for review.

## Decision Points

- If any required parameter is missing, stop and ask for that value before generating the script.
- If the user wants multiple source configurations generated, generate one filled SQL block per source configuration and compile all generated blocks into one output file separated by `GO`.
- If a value should remain empty, confirm whether it should be an empty string or `NULL`-like literal text in the generated SQL.
- If the user provides a URL, secret name, or username containing quotes, preserve valid SQL quoting in the generated output.
- If the `temp` folder does not exist, create it before writing the result.

## Completion Checks

- Every placeholder from [source.sql](../../templates/source.sql) is replaced.
- The source template file remains unchanged.
- The generated SQL file is stored under the repository root `temp` folder.
- When multiple source configurations are requested, all generated SQL blocks are stored in one file and separated by `GO`.
- The generated SQL includes the expected source and connection values.
- The output is ready for review or execution against the `Source` table.
