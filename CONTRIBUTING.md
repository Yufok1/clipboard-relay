# Contributing

`clipboard-relay` is intentionally small. Contributions should preserve the
operator-consent boundary:

- no automatic clipboard polling in the one-shot API
- no silent reads
- credential-shaped content must be surfaced before processing
- generated state, local logs, and credentials must stay out of the repository

## Local checks

```powershell
python -m pip install -e ".[dev]"
python -m ruff check src tests
python -m mypy src\clipboard_relay
python -m pytest -q
python -m build --sdist --wheel --outdir dist
python -m twine check dist\*
```

## Release posture

Preferred publishing is GitHub Actions plus PyPI Trusted Publishing. Do not
commit PyPI tokens, `.pypirc`, build artifacts, clipboard history, or local
operator transcripts.
