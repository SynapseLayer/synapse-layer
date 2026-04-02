# Contributing to Synapse Layer

We welcome contributions!

## Development Setup

```bash
git clone https://github.com/SynapseLayer/synapse-layer.git
cd synapse-layer
pip install -e ".[dev]"
pytest
```

## How to Contribute

### Reporting Bugs
- Open a GitHub Issue with clear title and description
- Include: OS, Python version, error message, reproduction steps
- Security issues: See SECURITY.md

### Proposing Features
- Open a GitHub Discussion
- Describe the use case and expected behavior

### Submitting PRs
1. Fork and create a feature branch
2. Make your changes and test
3. Format: `black . && ruff check .`
4. Commit with clear messages
5. Push and open a PR

## Code of Conduct

Be respectful, inclusive, and professional.

## License

By contributing, you agree your work is licensed under Apache 2.0.
