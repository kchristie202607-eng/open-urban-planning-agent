# OUPAP Knowledge Architecture Manifest

OUPAP follows **open framework, private knowledge**. The repository contains reusable orchestration, schemas, interfaces, synthetic examples, and evaluation rules. User-owned planning knowledge remains in the local runtime.

## Folder Structure

```text
OUPAP Workspace/
  data/
    knowledge/
    chunks/
    index/
  output/
  project_state/
```

The public repository intentionally excludes these runtime data folders and publishes `src/`, `agents/`, `config/`, `schemas/`, `examples/`, `docs/`, `scripts/`, and `tests/`.

## Metadata Schema

`schemas/common_metadata.schema.json` defines universal provenance fields: `document_id`, `title`, `source_type`, `region`, `authority`, `date`, `topic`, `version`, `confidence`, and `review_status`. Region contains `country`, `province`, `city`, and `district`; authority contains `organization` and `level`; date contains `issued` and `updated`.

Knowledge-item and RAG-chunk schemas attach this model through an optional `metadata` property while retaining specialized retrieval fields.

## Why Spatial and Temporal Metadata Matter

Urban-planning evidence is location-sensitive and time-sensitive. Region and authority prevent retrieval from mixing incompatible jurisdictions. Issued, updated, and version fields help prefer current rules and identify superseded evidence. Topic and confidence support scoped retrieval and human review instead of treating every text fragment as equally authoritative.

## Retrieval Flow

```text
Document → Parser / extraction → Common metadata validation → Chunking
  → Local embedding and vector index → Filtered retriever → Agent workflow
  → Evidence-cited output and quality gates
```

## Security Boundary

Public: framework, interfaces, schemas, synthetic examples, tests, and documentation.

Private: knowledge database, vector indexes, project documents, GIS, photos, reports, credentials, and generated project outputs.
