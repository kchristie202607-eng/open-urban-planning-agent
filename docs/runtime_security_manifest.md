# OUPAP Runtime Security Manifest

## Architecture

### Public Repository

- Framework
- Interfaces
- Schemas
- Synthetic examples

### Private Runtime

- Knowledge database
- Vector indexes
- Project documents
- GIS
- Photos
- Reports

The public framework consumes a knowledge-adapter contract and does not publish or embed user-owned records in the repository.

## Storage Boundary

```text
OUPAP Workspace/
  data/
    knowledge/
    chunks/
    index/
  output/
  project_state/
```

`.gitignore` excludes these paths and CI checks that they are not tracked.

## Permission Model

```text
Developer     →  Public Framework
Planner       →  Private Knowledge
Project User  →  Project Workspace
```

Developers change public code and schemas but do not receive project records by default. Planners use the private knowledge adapter within the permitted workspace. Project users control project documents, derived indexes, outputs, and retention.

## Security Rules

Never commit or upload project data, client files, GIS, credentials, vector databases, photos, or reports containing project information. Use environment-injected credentials, local filesystem permissions, synthetic fixtures, and reviewable provenance metadata. Cloud-assisted maintenance uses public or synthetic content only.
