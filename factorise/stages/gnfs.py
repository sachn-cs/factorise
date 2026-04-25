"""GNFS (General Number Field Sieve) external adapter as a pipeline stage."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from loguru import logger

from factorise.core import FactorisationError
from factorise.core import ensure_integer_input
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
    """

    name = "gnfs"

    def __init__(
        self,
        binary: str = "msieve",
        timeout_seconds: int = 600,
    ) -> None:
        """Initialise the GNFS stage.

        Args:
            binary: The name or path of the external GNFS tool.
            timeout_seconds: Maximum runtime for the external tool.

        """
        self._binary = binary
        self._timeout_seconds = timeout_seconds

    def attempt(self, n: int) -> StageResult:
        """Attempt to factor *n* using an external GNFS tool."""
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
                reason=(f"n ({bit_length} bits) below GNFS minimum "
                        f"{GNFS_MIN_BIT_LENGTH} bits"),
            )
        if bit_length > GNFS_MAX_BIT_LENGTH:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=(time.monotonic() - start) * 1000,
                reason=(f"n ({bit_length} bits) above GNFS maximum "
                        f"{GNFS_MAX_BIT_LENGTH} bits"),
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
                reason=f"GNFS binary {self._binary!r} not found on PATH",
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
        except FactorisationError:
            raise
        except (
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
        ) as exc:
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
        return shutil.which(self._binary) is not None

    def run_external_gnfs(self, n: int) -> int | None:
        """Run the external GNFS tool on n and return a factor if found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            fact_file = Path(tmpdir) / "factors.txt"

            with input_file.open("w") as inp:
                inp.write(f"{n}\n")

            cmd = self.build_command(str(input_file), str(fact_file), tmpdir, n)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout_seconds,
                    cwd=tmpdir,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                raise FactorisationError(
                    f"GNFS timed out after {self._timeout_seconds}s for n={n}",
                ) from None

            factors = self.parse_factor_output(
                result.stdout + result.stderr,
                str(fact_file),
            )
            if factors:
                for f in factors:
                    if is_prime(f) and n % f == 0:
                        return f

            if result.returncode != 0:
                raise FactorisationError(
                    f"GNFS exited with code {result.returncode}: "
                    f"{(result.stdout + result.stderr)[:500]}",)

            raise FactorisationError(
                f"GNFS produced no parseable factors for n={n}",)

    def build_command(
        self,
        input_file: str,
        fact_file: str,
        tmpdir: str,
        n: int,
    ) -> list[str]:
        """Build the subprocess command for the GNFS tool."""
        if self._binary == "msieve":
            return [
                self._binary,
                "-v",
                "-f",
                fact_file,
                input_file,
            ]
        if self._binary == "cado-nfs":
            log_file = str(Path(tmpdir) / "cado.log")
            return [
                self._binary,
                "tasks.factor.bswap_nwords=1",
                "tasks.linalg.bwc.threads=1",
                f"outputlogfile={log_file}",
                str(n),
            ]
        return [self._binary, input_file]

    def parse_factor_output(
        self,
        output: str,
        fact_file: str | None = None,
    ) -> list[int]:
        """Parse prime factors from GNFS tool output."""
        factors: list[int] = []

        if fact_file and Path(fact_file).exists():
            with Path(fact_file).open() as fh:
                for raw_line in fh:
                    line = raw_line.strip()
                    if line.isdigit():
                        factors.append(int(line))

        for match in re.finditer(r"p\d+\s*=\s*(\d+)", output, re.IGNORECASE):
            factors.append(int(match.group(1)))

        for match in re.finditer(r"^\s*(\d{5,})\s*$", output, re.MULTILINE):
            candidate = int(match.group(1))
            if is_prime(candidate):
                factors.append(candidate)

        return sorted(set(factors))
