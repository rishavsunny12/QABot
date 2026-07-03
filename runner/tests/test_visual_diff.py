from pathlib import Path

from PIL import Image
from playwright_utils.visual_diff import compare_images


def test_compare_identical_images(tmp_path: Path):
    img_path = tmp_path / "same.png"
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(img_path)
    result = compare_images(img_path, img_path, tmp_path / "diff.png", threshold_percent=1.0)
    assert result.passed is True
    assert result.diff_percent == 0.0


def test_compare_different_images(tmp_path: Path):
    baseline = tmp_path / "baseline.png"
    current = tmp_path / "current.png"
    diff = tmp_path / "diff.png"
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(baseline)
    Image.new("RGB", (100, 100), color=(0, 0, 255)).save(current)
    result = compare_images(baseline, current, diff, threshold_percent=1.0)
    assert result.passed is False
    assert result.diff_percent > 1.0
    assert diff.exists()
