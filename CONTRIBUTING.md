# Contributing

RMTGuard is being prepared as a reproducible research software project.

## Development setup

```bash
python -m pip install -e ".[scanpy,dev]"
python -m unittest discover -s tests
```

## Pull request checklist

- Add or update tests for algorithm changes.
- Keep benchmark data out of normal git history unless the file is a tiny test fixture.
- Record every public dataset in `metadata/datasets.tsv`.
- Report stochastic settings such as `random_state`.
- Preserve patient privacy and public repository terms of use.
