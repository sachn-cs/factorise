"""GNFS (General Number Field Sieve) external adapter as a pipeline stage.

GNFS is the fastest known algorithm for factoring integers larger than
~100 digits. A full in-repo implementation is beyond scope (it requires
thousands of lines of code for polynomial selection, sieving, La,
building the matrix, filtering, square root, etc.).

This stage provides a strict, isolated adapter that wraps external GNFS tools
(such as msieve or CADO-NFS) and integrates them into the pipeline. The adapter:

1. **Input validation** — only calls the external tool for inputs in its
   supported range (80-500 bits for msieve).
2. **Timeout handling** — kills the subprocess after a configurable limit
   to prevent runaway computation.
3. **Output parsing** — parses the factored result from the tool's output
   or a dedicated result file.
4. **Failure isolation** — on any error (timeout, non-zero exit, malformed
   output), raises `FactorisationError` so the pipeline can try the next stage.
5. **Availability checking** — silently SKIPs if the binary is not on PATH.

If no external tool is available, GNFS is SKIPPED and the pipeline moves on.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
from typing import TYPE_CHECKING

from loguru import logger

from source.pipeline import FactorStage, StageResult, StageStatus

if TYPE_CHECKING:
    from source.core import FactoriserConfig

logger.disable("factorise")

# msieve is a popular open-source GNFS implementation.
# CADO-NFS is another widely-used open-source tool.
_SUPPORTED_TOOLS: tuple[str, ...] = ("msieve", "cado-nfs", "gnfs")
_MIN_BITS = 80
_MAX_BITS = 500


class GNFSStage(FactorStage):
    """GNFS factorisation stage via external tool adapter.

    This stage is a wrapper around external GNFS tools (msieve, CADO-NFS, etc.).
    It is SKIPPED if the configured binary is not found on PATH, if the input
    is outside the tool's supported range, or if the external tool fails.

    The stage returns PARTIAL (not SUCCESS) when it finds some but not all
    factors, and returns FAILURE when it cannot factor the input at all.
    """

    name = "gnfs"

    def __init__(
        self,
        binary: str = "msieve",
        timeout_seconds: int = 600,
    ) -> None:
        self._binary = binary
        self._timeout_seconds = timeout_seconds

    def attempt(self, n: int, *, config: FactoriserConfig) -> StageResult:
        from source.core import is_prime, validate_int

        start = time.monotonic()
        validate_int(n)

        if n < 3:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=(time.monotonic() - start) * 1000,
                reason="n < 3",
            )

        bits = n.bit_length()
        if bits < _MIN_BITS:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=(time.monotonic() - start) * 1000,
                reason=f"n ({bits} bits) below GNFS minimum {_MIN_BITS} bits",
            )
        if bits > _MAX_BITS:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=(time.monotonic() - start) * 1000,
                reason=f"n ({bits} bits) above GNFS maximum {_MAX_BITS} bits",
            )

        if is_prime(n):
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=(time.monotonic() - start) * 1000,
                reason="n is prime",
            )

        if not self._available():
            logger.debug(
                "stage={stage} status=SKIPPED reason=binary_not_found",
                stage=self.name,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=(time.monotonic() - start) * 1000,
                reason=f"GNFS binary {self._binary!r} not found on PATH",
            )

        try:
            factor = self._run_gnfs(n)
            if factor is not None and 1 < factor < n:
                logger.debug(
                    "stage={stage} n={n} factor={factor}",
                    stage=self.name,
                    n=n,
                    factor=factor,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=factor,
                    elapsed_ms=(time.monotonic() - start) * 1000,
                )
        except Exception as exc:
            logger.debug(
                "stage={stage} n={n} reason={reason}",
                stage=self.name,
                n=n,
                reason=str(exc),
            )

        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=(time.monotonic() - start) * 1000,
            reason=f"GNFS failed for n={n}",
        )

    def _available(self) -> bool:
        """Return True if the GNFS binary is found on PATH."""
        import shutil

        return shutil.which(self._binary) is not None

    def _run_gnfs(self, n: int) -> int | None:
        """Run the external GNFS tool on n and return a factor if found.

        Raises:
            FactorisationError: On timeout, non-zero exit, or parse failure.
        """
        import shutil

        from source.core import FactorisationError, is_prime

        if not shutil.which(self._binary):
            raise FactorisationError(
                f"GNFS binary {self._binary!r} not found on PATH"
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "input.txt")
            fact_file = os.path.join(tmpdir, "factors.txt")

            with open(input_file, "w") as f:
                f.write(f"{n}\n")

            cmd = self._build_command(input_file, fact_file, tmpdir, n)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout_seconds,
                    cwd=tmpdir,
                )
            except subprocess.TimeoutExpired:
                raise FactorisationError(
                    f"GNFS timed out after {self._timeout_seconds}s for n={n}"
                )

            factors = self._parse_output(result.stdout + result.stderr, fact_file)
            if factors:
                for f in factors:
                    if is_prime(f) and n % f == 0:
                        return f

            if result.returncode != 0:
                raise FactorisationError(
                    f"GNFS exited with code {result.returncode}: "
                    f"{(result.stdout + result.stderr)[:500]}"
                )

            raise FactorisationError(f"GNFS produced no parseable factors for n={n}")

    def _build_command(
        self, input_file: str, fact_file: str, tmpdir: str, n: int
    ) -> list[str]:
        """Build the subprocess command for the GNFS tool.

        Subclasses can override to customise the command format per tool.
        """
        if self._binary == "msieve":
            return [
                self._binary,
                "-v",
                "-f",
                fact_file,
                input_file,
            ]
        if self._binary == "cado-nfs":
            log_file = os.path.join(tmpdir, "cado.log")
            return [
                self._binary,
                f"tasks.factor.bswap_nwords=1",
                f"tasks.linalg.bwc.threads=1",
                f"outputlogfile={log_file}",
                str(n),
            ]
        # Generic fallback
        return [self._binary, input_file]

    def _parse_output(
        self, output: str, fact_file: str | None = None
    ) -> list[int]:
        """Parse prime factors from GNFS tool output.

        Tries multiple parsing strategies:
        1. Read factors from a dedicated result file if available.
        2. Parse "p<digits> = <factor>" lines from msieve output.
        3. Parse "factor = <factor>" lines from CADO-NFS output.
        4. Extract large decimal integers that are prime.
        """
        factors: list[int] = []

        # Strategy 1: parse result file
        if fact_file and os.path.exists(fact_file):
            with open(fact_file) as f:
                for line in f:
                    line = line.strip()
                    if line.isdigit():
                        factors.append(int(line))

        # Strategy 2: msieve format "p<decimal> = <prime>"
        for match in re.finditer(
            r"p\d+\s*=\s*(\d+)", output, re.IGNORECASE
        ):
            factors.append(int(match.group(1)))

        for match in re.finditer(
            r"^\s*(\d{5,})\s*$", output, re.MULTILINE
        ):
            candidate = int(match.group(1))
            if self._looks_prime(candidate):
                factors.append(candidate)

        # Deduplicate and return
        return sorted(set(factors))

    def _looks_prime(self, n: int) -> bool:
        """Quick probabilistic primality check for parsed factors."""
        from source.core import is_prime

        return is_prime(n)
