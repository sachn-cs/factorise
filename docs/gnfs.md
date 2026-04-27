# General Number Field Sieve (GNFS)

GNFS is the most efficient known classical algorithm for factoring large integers (> 100 digits).

## Implementations

This package provides two GNFS implementations:

1. **Pure Python** (`OptimizedGNFSStage`): Single-polynomial GNFS with lattice sieving,
   practical for inputs in the 60-100 bit range with careful parameter tuning.
2. **External Tool Adapter** (`ExternalGNFSStage`): Wraps `msieve` or `CADO-NFS`
   for 80-500+ bit inputs.

The `GNFSStage` pipeline stage tries pure Python first, then falls back to an
external binary if available.

## Features

- **Input validation**: Rejects inputs outside the 80-500 bit range (pipeline stage).
- **Timeout handling** (external): Configurable timeout for the subprocess.
- **Output parsing** (external): Parses the factor list from the external tool's output.
- **Graceful degradation**: Silently skips if the binary is not on PATH.
- **Pure Python GNFS**: Lattice sieving, GF(2) Gaussian elimination, and square-root
  extraction — all in pure Python with auto-scaled parameters.

## When to Use

- Pure Python: 60-100 bit inputs, no external dependencies needed.
- External tools: 80-500+ bit inputs (msieve or CADO-NFS required).

## Pure Python Usage

```python
from factorise.stages.gnfs_optimized import OptimizedGNFSStage

stage = OptimizedGNFSStage()
result = stage.attempt(1234567890123456789 * 9876543210987654321)
print(result.factor)  # found a factor
```

## External Tool Usage

```python
from factorise.stages.gnfs import GNFSStage

stage = GNFSStage(binary="msieve", timeout_seconds=600)
result = stage.attempt(12345678901234567890123456789012345678901234567890)
print(result.factor)
```

## Prerequisites (External)

Install one of the following external tools:
- [msieve](https://sourceforge.net/projects/msieve/)
- [CADO-NFS](https://cado-nfs.gitlabpages.inria.fr/)
