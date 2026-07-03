from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any


def execute_specs(
    spec_paths: list[str],
    output_dir: Path,
    base_url: str | None = None,
) -> list[dict[str, Any]]:
    """Execute Playwright test files and collect structured results."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for spec_path in spec_paths:
        spec_file = Path(spec_path)
        if not spec_file.exists():
            results.append(
                {
                    "spec_path": spec_path,
                    "status": "failed",
                    "duration_ms": 0,
                    "error_message": f"Spec file not found: {spec_path}",
                    "failure_category": "environment issue",
                }
            )
            continue

        start = time.time()
        env = {"BASE_URL": base_url or ""}
        cmd = [
            "python",
            "-m",
            "playwright",
            "test",
            str(spec_file),
            "--reporter=line",
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(spec_file.parent),
                env={**os.environ, **env},
            )
            duration_ms = int((time.time() - start) * 1000)
            status = "passed" if proc.returncode == 0 else "failed"
            error_message = proc.stderr or proc.stdout if status == "failed" else None

            screenshot_path = None
            trace_path = None
            for artifact in output_dir.glob("**/*"):
                if artifact.suffix == ".png" and status == "failed":
                    screenshot_path = str(artifact)
                if artifact.suffix == ".zip" and "trace" in artifact.name:
                    trace_path = str(artifact)

            failure_category = None
            if status == "failed" and error_message:
                failure_category = _categorize_failure(error_message)

            results.append(
                {
                    "spec_path": spec_path,
                    "status": status,
                    "duration_ms": duration_ms,
                    "error_message": error_message,
                    "failure_category": failure_category,
                    "screenshot_path": screenshot_path,
                    "trace_path": trace_path,
                    "video_path": None,
                }
            )
        except subprocess.TimeoutExpired:
            results.append(
                {
                    "spec_path": spec_path,
                    "status": "failed",
                    "duration_ms": 120000,
                    "error_message": "Test execution timed out",
                    "failure_category": "flaky timing issue",
                }
            )
        except Exception as exc:
            results.append(
                {
                    "spec_path": spec_path,
                    "status": "failed",
                    "duration_ms": 0,
                    "error_message": str(exc),
                    "failure_category": "environment issue",
                }
            )

    return results


def _categorize_failure(error: str) -> str:
    lower = error.lower()
    if "locator" in lower or "selector" in lower or "strict mode violation" in lower:
        return "selector drift"
    if "timeout" in lower or "waiting" in lower:
        return "flaky timing issue"
    if "401" in lower or "403" in lower or "unauthorized" in lower or "login" in lower:
        return "auth/session issue"
    if "navigation" in lower or "net::" in lower:
        return "navigation mismatch"
    if "500" in lower or "api" in lower:
        return "backend/API issue"
    if "expect" in lower or "assertion" in lower:
        return "app bug"
    return "environment issue"
