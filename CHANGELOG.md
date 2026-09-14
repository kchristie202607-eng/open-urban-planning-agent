# Changelog

Release preparation completed and published to GitHub via SSH on 2026-08-03.

## Unreleased

### Added

- `docs/methodology/` — nine de-identified methodology documents distilled from
  real planning production work, plus an index. Covers the GIS data chain
  (CAD→GIS conversion, MapGIS delivery and error remediation, land-use colour
  standards and MXD symbology, road red-line polygonization) and general
  practice (figure management, offline PDF OCR and citation status, admin and
  development boundary statistics, government briefing standards, technical bid
  framework). All project-identifying information removed.
- Root README (EN and zh-CN) now links to the methodology collection so it is
  discoverable.

### Fixed

- `.gitignore`: Git does not support end-of-line comments, so lines such as
  `data/    # private` were parsed as a single pattern and never matched.
  All eight private-boundary rules (`data/`, `output/`, `project_state/`,
  `backups/`, `tmp/`, `.workbuddy/`, `.deps/` and the newly added `AUDIT/` and
  `WORK_LOG.md`) were therefore inert. Comments moved onto their own lines and
  a warning header added; verified with `git check-ignore`.

## v0.1.0-alpha

Initial public foundation release.

Includes:

- Open-source architecture
- Privacy-first knowledge boundary
- Documentation framework
- Community workflow
- Contribution structure
- Common provenance metadata schema
- Runtime security manifest
- Blocking CI quality gates for Ruff and pytest
- Codex application preparation materials
