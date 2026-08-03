# CI Quality Gates

OUPAP CI validates the public framework on Python 3.11 and 3.12.

## Checks

1. Install runtime dependencies from `requirements.txt`.
2. Install development quality tools from `requirements-dev.txt`.
3. Run `ruff check .` as a blocking lint gate.
4. Run `pytest tests/ -q` as a blocking test gate.
5. Reject tracked private runtime paths with the privacy guard.

Ruff is intentionally scoped by `ruff.toml` to correctness and import hygiene. It is no longer invoked with `|| true`; a lint failure fails CI and must be fixed before merge.

## Local verification

```bash
python -m pip install -r requirements-dev.txt
ruff check .
pytest tests/ -q
```

The current audit host did not have `pytest` or `ruff` installed, so local execution requires installing the development requirements. CI remains the authoritative clean-environment verification.
