# General Number Field Sieve (GNFS)

GNFS is the most efficient known classical algorithm for factoring large integers (> 100 digits).

## External Tool Adapter

The `GNFSStage` is a strict external tool adapter that wraps `msieve` or `CADO-NFS`. It does not implement GNFS in pure Python.

## Features

- **Input validation**: Rejects inputs outside the 80-500 bit range.
- **Timeout handling**: Configurable timeout for the subprocess.
- **Output parsing**: Parses the factor list from the external tool's output.
- **Graceful degradation**: Silently skips if the binary is not on PATH.

## When to Use

- For very large inputs (~80+ bits) where QS is impractical.
- Requires `msieve` or `cado-nfs` to be installed and on PATH.

## Implementation

```python
from factorise.stages.gnfs import GNFSStage

stage = GNFSStage(binary="msieve", timeout_seconds=600)
result = stage.attempt(12345678901234567890123456789012345678901234567890)
print(result.factor)
```

## Prerequisites

Install one of the following external tools:
- [msieve](https://sourceforge.net/projects/msieve/)
- [CADO-NFS](https://cado-nfs.gitlabpages.inria.fr/)
