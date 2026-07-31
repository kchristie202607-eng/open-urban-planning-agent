# Contributing to OUPAP

Thanks for your interest in the **Open Urban Planning Agent Platform (OUPAP)**!
This document explains how to propose changes.

## Code of Conduct

By participating, you agree to our [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to Contribute

- Report bugs via the **Bug Report** issue template.
- Suggest features via the **Feature Request** issue template.
- Improve documentation via the **Docs** issue template.
- Submit pull requests against the `main` branch.

## Development Setup

```bash
# 1. Clone
git clone https://github.com/kchristie202607-eng/open-urban-planning-agent.git
cd open-urban-planning-agent

# 2. Create a local Python environment (private; not committed)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Run the test suite
pytest tests/
```

## Public / Private Boundary

OUPAP is **local-first**. When contributing:

- Do **not** add any private project data, GIS files, satellite imagery, or
  planning documents to the repository.
- Keep the public framework decoupled from private knowledge.
- Tests must run against **synthetic** fixtures only.

## Pull Request Guidelines

1. Fork and create a feature branch (`feat/...`, `fix/...`, `docs/...`).
2. Keep changes focused; one concern per PR.
3. Add or update tests for behavior changes.
4. Ensure CI is green (lint + tests).
5. Update `CHANGELOG.md` under `## [Unreleased]`.
6. Fill in the PR template and link the related issue.

## License

By contributing, you agree your contributions are licensed under the
[Apache License 2.0](LICENSE).
