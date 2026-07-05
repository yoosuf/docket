"""Format conversion via headless LibreOffice.

Two conversions share the same underlying mechanics:
- `convert_to_pdf`: the final output step for `output_format: "pdf"`.
- `convert_to_docx`: a pre-processing step for legacy `.doc` templates —
  docxtpl only understands the OOXML `.docx` structure, so a `.doc`
  template is converted to `.docx` *before* Jinja2 rendering ever runs
  (see `service.py`). LibreOffice has full native support for the old
  binary `.doc` format, so this conversion is exact, not a lossy
  approximation.

Each invocation gets its own `UserInstallation` profile directory:
concurrent `soffice` processes sharing a profile hit lock-file
contention, the most common production gotcha with this approach.
"""
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from app.modules.documents.exceptions import ConversionUnavailableError, DocumentConversionError


class LibreOfficeConverter:
    def __init__(self, binary: str = "soffice", timeout_seconds: int = 60) -> None:
        self._binary = binary
        self._timeout_seconds = timeout_seconds

    def _resolve_binary(self) -> str:
        resolved = shutil.which(self._binary)
        if resolved is None:
            raise ConversionUnavailableError(
                f"LibreOffice binary '{self._binary}' was not found on PATH. "
                "Install LibreOffice to enable format conversion."
            )
        return resolved

    def convert_to_pdf(self, docx_bytes: bytes) -> bytes:
        return self._convert(docx_bytes, source_suffix=".docx", target_format="pdf")

    def convert_to_docx(self, doc_bytes: bytes) -> bytes:
        return self._convert(doc_bytes, source_suffix=".doc", target_format="docx")

    def _convert(self, content: bytes, source_suffix: str, target_format: str) -> bytes:
        binary = self._resolve_binary()

        with tempfile.TemporaryDirectory(prefix="docket-convert-") as workdir:
            work_path = Path(workdir)
            source_path = work_path / f"{uuid.uuid4().hex}{source_suffix}"
            source_path.write_bytes(content)

            profile_dir = work_path / "profile"
            profile_dir.mkdir()

            command = [
                binary,
                "--headless",
                "--norestore",
                f"-env:UserInstallation=file://{profile_dir}",
                "--convert-to",
                target_format,
                "--outdir",
                str(work_path),
                str(source_path),
            ]

            try:
                result = subprocess.run(
                    command, capture_output=True, timeout=self._timeout_seconds, check=False
                )
            except subprocess.TimeoutExpired as exc:
                raise DocumentConversionError(
                    f"Conversion to {target_format} timed out after {self._timeout_seconds}s."
                ) from exc

            output_path = source_path.with_suffix(f".{target_format}")
            if result.returncode != 0 or not output_path.exists():
                stderr = result.stderr.decode(errors="replace").strip()
                raise DocumentConversionError(
                    f"LibreOffice conversion to {target_format} failed "
                    f"(exit code {result.returncode}): {stderr}"
                )

            return output_path.read_bytes()
