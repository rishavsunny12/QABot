from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class VisualDiffResult:
    diff_percent: float
    passed: bool
    diff_path: str | None
    width: int
    height: int


def compare_images(
    baseline_path: str | Path,
    current_path: str | Path,
    diff_output_path: str | Path,
    threshold_percent: float = 1.0,
) -> VisualDiffResult:
    """Compare two PNG screenshots and write a highlighted diff image."""
    from PIL import Image, ImageChops, ImageDraw

    baseline = Image.open(baseline_path).convert("RGB")
    current = Image.open(current_path).convert("RGB")

    if baseline.size != current.size:
        current = current.resize(baseline.size)

    diff = ImageChops.difference(baseline, current)
    width, height = baseline.size
    total_pixels = width * height

    diff_pixels = sum(1 for px in diff.getdata() if px != (0, 0, 0))
    diff_percent = (diff_pixels / total_pixels) * 100 if total_pixels else 0.0
    passed = diff_percent <= threshold_percent

    diff_path: str | None = None
    if not passed:
        out = Path(diff_output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        overlay = current.copy()
        mask = diff.convert("L").point(lambda p: 255 if p > 20 else 0)
        red = Image.new("RGB", baseline.size, (255, 0, 0))
        overlay.paste(red, mask=mask)
        draw = ImageDraw.Draw(overlay)
        draw.text((10, 10), f"Diff: {diff_percent:.2f}%", fill=(255, 255, 255))
        overlay.save(out)
        diff_path = str(out)

    return VisualDiffResult(
        diff_percent=round(diff_percent, 4),
        passed=passed,
        diff_path=diff_path,
        width=width,
        height=height,
    )
