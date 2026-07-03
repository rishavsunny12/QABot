from pathlib import Path

from playwright_utils.executor import execute_specs


def test_execute_specs_missing_file_sequential():
    results = execute_specs(["/nonexistent/spec.spec.ts"], Path("/tmp/autoqa-test-out"))
    assert len(results) == 1
    assert results[0]["status"] == "failed"
    assert "not found" in results[0]["error_message"].lower()


def test_execute_specs_parallel_preserves_order(tmp_path: Path):
    missing = [str(tmp_path / f"missing_{i}.spec.ts") for i in range(3)]
    results = execute_specs(missing, tmp_path / "out", max_workers=3)
    assert len(results) == 3
    assert all(r["status"] == "failed" for r in results)
    assert [r["spec_path"] for r in results] == missing
