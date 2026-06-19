# Deployment

This document covers publishing `factorise` to PyPI and integrating it into your projects.

## Publishing to PyPI

### Prerequisites

- PyPI account with API token or OIDC trusted publishing configured
- `build` and `twine` installed (`pip install build twine`)

### Build

```bash
# Clean previous builds
just clean

# Build sdist and wheel
python -m build
```

This creates:

- `dist/factorise-X.Y.Z.tar.gz` (source distribution)
- `dist/factorise-X.Y.Z-py3-none-any.whl` (wheel)
- `dist/SHA256SUMS` (integrity checksums)
- `dist/sbom.cdx.json` (CycloneDX SBOM)

### Verify

```bash
# Check distribution
twine check dist/*

# Test wheel installation
python -m venv verify-wheel
source verify-wheel/bin/activate
pip install dist/factorise-*.whl
python -c "from factorise import factorise; print(factorise(123).expression())"
deactivate
rm -rf verify-wheel

# Test sdist installation
python -m venv verify-sdist
source verify-sdist/bin/activate
pip install dist/factorise-*.tar.gz
python -c "from factorise import factorise; print(factorise(123).expression())"
deactivate
rm -rf verify-sdist
```

### Publish

```bash
# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

### Automated Publishing

The CI/CD pipeline automatically publishes on version tags:

1. Create a version tag:
   ```bash
   git tag v0.6.0
   git push origin v0.6.0
   ```

2. GitHub Actions will:
   - Build sdist and wheel
   - Generate SBOM and checksums
   - Test installations
   - Publish to PyPI via OIDC

## Version Management

### Semantic Versioning

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking API changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Version Locations

Update version in:

1. `factorise/__init__.py`: `__version__ = "X.Y.Z"`
2. Git tag: `git tag vX.Y.Z`

The build system reads version from `__init__.py` via Hatchling.

## Integration

### As a Dependency

```bash
# Add to requirements.txt
factorise>=0.5.0

# Or install directly
pip install factorise
```

### In pyproject.toml

```toml
[project]
dependencies = [
    "factorise>=0.5.0",
]
```

### Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install factorise
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) provides:

### On Push/PR

- Lint and type check
- Test across Python 3.10-3.13
- Security audit
- Stress testing

### On Version Tag

- Build sdist and wheel
- Generate SBOM
- Generate checksums
- Test installations
- Publish to PyPI

## Release Checklist

- [ ] Update version in `factorise/__init__.py`
- [ ] Update `CHANGELOG.md` with release notes
- [ ] Run full CI suite: `just ci-full`
- [ ] Create version tag: `git tag vX.Y.Z`
- [ ] Push tag: `git push origin vX.Y.Z`
- [ ] Verify PyPI publication
- [ ] Verify installation: `pip install factorise==X.Y.Z`
- [ ] Update documentation if needed

## Troubleshooting

### Build Failures

- Ensure `build` and `twine` are installed
- Run `just clean` before building
- Check `pyproject.toml` for syntax errors

### Upload Failures

- Verify PyPI credentials
- Check if version already exists (PyPI is immutable)
- Ensure `twine check dist/*` passes

### Version Conflicts

- PyPI does not allow re-uploading the same version
- Bump version and create new tag if needed
