# ADIF Skills Catalog

This repository keeps skill folders flat under `.github/skills/<skill-name>/` so skill discovery remains predictable.

Use categories in this catalog for organization instead of nesting skill folders by category.

## Folder Rule

- Keep every skill directly under `.github/skills/`
- Keep the folder name matched with the `name:` field in `SKILL.md`
- Do not create nested category folders such as `.github/skills/Deployment/...`

## Categories

### Deployment

Current repository skills are classified as deployment skills and use a `deployment-` prefix:

- `deployment-install-adif`
- `deployment-install-adif-workspaces`
- `deployment-install-adif-lakehouses`
- `deployment-adif-create-jobs-lakehouse`
- `deployment-adif-configure-spark-environment`
- `deployment-adif-configure-metastore`
- `deployment-publish-adif-data-pipelines`
- `deployment-publish-variable-library`
- `deployment-build-difforfabric`
- `deployment-add-new-function-to-adif-library`

### Enhancement

Current repository skills classified as enhancement skills use an `enhancement-` prefix:

- `enhancement-python-code-structure`

Use this category for skills that improve code quality, add reusable patterns, or support general development workflows beyond direct deployment or Fabric setup.

### Implementation

Current repository skills in the implementation category use an `implementation-` prefix:

- `implementation-configure-source`
- `implementation-configure-standardization`
- `implementation-create-data-ingestion-pipeline`

Use this category for future skills that focus on changing application code, adding features, or refactoring implementation details rather than deploying or configuring Fabric resources.

## Naming Guidance

For future skills, keep the folder layout flat and use the catalog to group them logically.

Current naming convention:

- `deployment-<skill-name>`
- `enhancement-<skill-name>`
- `implementation-<skill-name>`

When you rename a skill, rename both the folder and the `name:` field together.
