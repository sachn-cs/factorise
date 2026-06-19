# Security Policy

## Supported Versions

Currently, only the latest major version sequence of the software is formally supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| v0.5.x  | :white_check_mark: |
| v0.4.x  | :white_check_mark: |
| v0.3.x  | :white_check_mark: |
| < 0.3   | :x:                |

## Reporting a Vulnerability

If you discover any security-related issues, please do **not** report them through public GitHub issues. Instead, please email the maintainers at sachncs@gmail.com.

### What to Include

When reporting a vulnerability, please include:

- A description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Any suggested fixes (if applicable)

### Response Expectations

| Action | Timeline |
|--------|----------|
| Acknowledgment of report | Within 48 hours |
| Initial assessment | Within 1 week |
| Regular updates | Weekly until resolved |
| Public disclosure | Coordinated with reporter |

### Disclosure Policy

We follow a coordinated disclosure process:

1. **Report received**: We acknowledge receipt and begin investigation
2. **Assessment**: We evaluate the severity and impact
3. **Fix development**: We develop and test a fix
4. **Release**: We release a patch version
5. **Disclosure**: We publish a security advisory after users have had time to update

We request that reporters:

- Allow reasonable time for a fix before public disclosure
- Avoid exploiting the vulnerability beyond what is necessary to demonstrate it
- Act in good faith to avoid privacy violations and data destruction

## Security Best Practices

### For Users

- Keep `factorise` updated to the latest version
- Use virtual environments to isolate dependencies
- Review dependency updates via Dependabot alerts
- Audit dependencies regularly: `pip-audit`

### For Contributors

- Never commit secrets, API keys, or credentials
- Use environment variables for configuration
- Validate all external inputs (especially for GNFS adapter)
- Run `just security` before submitting PRs
- Review code for potential injection vulnerabilities

### Dependencies

This project has **zero runtime dependencies**, which significantly reduces the attack surface. All algorithms are implemented from scratch using only the Python standard library.

Development dependencies are pinned to minimum versions and audited via:

- `pip-audit` for known vulnerabilities
- Dependabot for automated dependency updates
- CycloneDX SBOM generation for supply chain transparency

## Security Features

- **Input validation**: All public API entry points validate integer inputs
- **Timeout controls**: GNFS adapter enforces configurable timeouts
- **No shell injection**: External tool inputs are sanitized; no `os.system()` usage
- **Deterministic builds**: Reproducible builds via `SOURCE_DATE_EPOCH`
- **Signed releases**: Published via OIDC trusted publishing to PyPI
- **SBOM**: CycloneDX Software Bill of Materials generated for each release
- **Checksums**: SHA256 integrity files for all distribution artifacts
