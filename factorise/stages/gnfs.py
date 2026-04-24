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
import shutil
import subprocess
import tempfile
import time

from loguru import logger

from factorise.core import FactorisationError
from factorise.core import FactoriserConfig
from factorise.core import is_prime
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus

logger.disable("factorise")

SUPPORTED_GNFS_TOOLS: tuple[str, ...] = ("msieve", "cado-nfs", "gnfs")
GNFS_MIN_BIT_LENGTH: int = 80
GNFS_MAX_BIT_LENGTH: int = 500


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
        self.__binary = binary
        self.__timeout_seconds = timeout_seconds

    def attempt(self, n: int, *, config: FactoriserConfig) -> StageResult:
        from factorise.core import ensure_integer_input

        start = time.monotonic()
        ensure_integer_input(n)

        if n < 3:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=(time.monotonic() - start) * 1000,
                reason="n < 3",
            )

        bit_length = n.bit_length()
        if bit_length < GNFS_MIN_BIT_LENGTH:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=(time.monotonic() - start) * 1000,
                reason=
                f"n ({bit_length} bits) below GNFS minimum {GNFS_MIN_BIT_LENGTH} bits",
            )
        if bit_length > GNFS_MAX_BIT_LENGTH:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=(time.monotonic() - start) * 1000,
                reason=
                f"n ({bit_length} bits) above GNFS maximum {GNFS_MAX_BIT_LENGTH} bits",
            )

        if is_prime(n):
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=(time.monotonic() - start) * 1000,
                reason="n is prime",
            )

        if not self.is_tool_available():
            logger.debug(
                "stage={stage} status=SKIPPED reason=binary_not_found",
                stage=self.name,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=(time.monotonic() - start) * 1000,
                reason=f"GNFS binary {self.__binary!r} not found on PATH",
            )

        try:
            factor = self.run_external_gnfs(n)
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

    def is_tool_available(self) -> bool:
        """Return True if the GNFS binary is found on PATH."""
        return shutil.which(self.__binary) is not None

    def run_external_gnfs(self, n: int) -> int | None:
        """Run the external GNFS tool on n and return a factor if found."""
        if not shutil.which(self.__binary):
            raise FactorisationError(
                f"GNFS binary {self.__binary!r} not found on PATH")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "input.txt")
            fact_file = os.path.join(tmpdir, "factors.txt")

            with open(input_file, "w") as inp:
                inp.write(f"{n}\n")

            cmd = self.build_command(input_file, fact_file, tmpdir, n)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.__timeout_seconds,
                    cwd=tmpdir,
                )
            except subprocess.TimeoutExpired:  # noqa: B904
                raise FactorisationError(  # noqa: B904
                    f"GNFS timed out after {self.__timeout_seconds}s for n={n}"
                ) from None

            factors = self.parse_factor_output(result.stdout + result.stderr,
                                               fact_file)
            if factors:
                for f in factors:
                    if is_prime(f) and n % f == 0:
                        return f

            if result.returncode != 0:
                raise FactorisationError(
                    f"GNFS exited with code {result.returncode}: "
                    f"{(result.stdout + result.stderr)[:500]}")

            raise FactorisationError(
                f"GNFS produced no parseable factors for n={n}")

    def build_command(self, input_file: str, fact_file: str, tmpdir: str,
                      n: int) -> list[str]:
        """Build the subprocess command for the GNFS tool."""
        if self.__binary == "msieve":
            return [
                self.__binary,
                "-v",
                "-f",
                fact_file,
                input_file,
            ]
        if self.__binary == "cado-nfs":
            log_file = os.path.join(tmpdir, "cado.log")
            return [
                self.__binary,
                "tasks.factor.bswap_nwords=1",
                "tasks.linalg.bwc.threads=1",
                f"outputlogfile={log_file}",
                str(n),
            ]
        return [self.__binary, input_file]

    def parse_factor_output(self,
                            output: str,
                            fact_file: str | None = None) -> list[int]:
        """Parse prime factors from GNFS tool output."""
        factors: list[int] = []

        if fact_file and os.path.exists(fact_file):
            with open(fact_file) as fh:
                for line in fh:
                    line = line.strip()
                    if line.isdigit():
                        factors.append(int(line))

        for match in re.finditer(r"p\d+\s*=\s*(\d+)", output, re.IGNORECASE):
            factors.append(int(match.group(1)))

        for match in re.finditer(r"^\s*(\d{5,})\s*$", output, re.MULTILINE):
            candidate = int(match.group(1))
            if self.looks_like_prime(candidate):
                factors.append(candidate)

        return sorted(set(factors))

    def looks_like_prime(self, n: int) -> bool:
        """Quick primality check for parsed factors."""
        return is_prime(n)
