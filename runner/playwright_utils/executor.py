from __future__ import annotations

import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def execute_specs(
    spec_paths: list[str],
    output_dir: Path,
    base_url: str | None = None,
    max_workers: int = 1,
) -> list[dict[str, Any]]:
    """Execute Playwright test files and collect structured results."""
    output_dir.mkdir(parents=True, exist_ok=True)
    workers = max(1, max_workers)

    if workers == 1 or len(spec_paths) <= 1:
        return [_execute_single_spec(path, output_dir, base_url, index=idx) for idx, path in enumerate(spec_paths)]

    indexed_results: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(spec_paths))) as pool:
        futures = {
            pool.submit(_execute_single_spec, path, output_dir, base_url, idx): idx
            for idx, path in enumerate(spec_paths)
        }
        for future in as_completed(futures):
            indexed_results[futures[future]] = future.result()

    return [indexed_results[idx] for idx in range(len(spec_paths))]


def _execute_single_spec(
    spec_path: str,
    output_dir: Path,
    base_url: str | None,
    index: int = 0,
) -> dict[str, Any]:
    spec_file = Path(spec_path)
    spec_output = output_dir / f"{index:04d}_{spec_file.stem}"
    spec_output.mkdir(parents=True, exist_ok=True)

    if not spec_file.exists():
        return {
            "spec_path": spec_path,
            "status": "failed",
            "duration_ms": 0,
            "error_message": f"Spec file not found: {spec_path}",
            "failure_category": "environment issue",
        }

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
        for artifact in spec_output.glob("**/*"):
            if artifact.suffix == ".png" and status == "failed":
                screenshot_path = str(artifact)
            if artifact.suffix == ".zip" and "trace" in artifact.name:
                trace_path = str(artifact)

        failure_category = None
        if status == "failed" and error_message:
            failure_category = _categorize_failure(error_message)

        return {
            "spec_path": spec_path,
            "status": status,
            "duration_ms": duration_ms,
            "error_message": error_message,
            "failure_category": failure_category,
            "screenshot_path": screenshot_path,
            "trace_path": trace_path,
            "video_path": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "spec_path": spec_path,
            "status": "failed",
            "duration_ms": 120000,
            "error_message": "Test execution timed out",
            "failure_category": "flaky timing issue",
        }
    except Exception as exc:
        return {
            "spec_path": spec_path,
            "status": "failed",
            "duration_ms": 0,
            "error_message": str(exc),
            "failure_category": "environment issue",
        }


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
