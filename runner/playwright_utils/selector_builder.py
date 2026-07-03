from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SelectorCandidate:
    primary: str
    fallbacks: list[str] = field(default_factory=list)
    locator_type: str = "css"
    locator_value: str = ""
    role: str | None = None
    name: str | None = None


def build_selector_from_element_info(info: dict[str, Any]) -> SelectorCandidate:
    """Build selector using preference order from brief."""
    test_id = info.get("testId") or info.get("data-testid")
    role = info.get("role")
    accessible_name = info.get("accessibleName") or info.get("aria_label")
    aria_label = info.get("aria_label")
    label_text = info.get("label")
    text = info.get("text")
    css_path = info.get("cssPath") or info.get("css_path") or "body"

    fallbacks: list[str] = []

    if test_id:
        primary = f'[data-testid="{test_id}"]'
        fallbacks.extend(_other_selectors(info, exclude=primary))
        return SelectorCandidate(
            primary=primary,
            fallbacks=fallbacks,
            locator_type="testid",
            locator_value=test_id,
        )

    if role and accessible_name:
        primary = f'role={role}[name="{accessible_name}"]'
        fallbacks.extend(_other_selectors(info, exclude=primary))
        return SelectorCandidate(
            primary=primary,
            fallbacks=fallbacks,
            locator_type="role",
            locator_value=accessible_name,
            role=role,
            name=accessible_name,
        )

    if aria_label:
        primary = f'[aria-label="{aria_label}"]'
        fallbacks.extend(_other_selectors(info, exclude=primary))
        return SelectorCandidate(primary=primary, fallbacks=fallbacks, locator_type="aria", locator_value=aria_label)

    if label_text:
        primary = f'label="{label_text}"'
        fallbacks.extend(_other_selectors(info, exclude=primary))
        return SelectorCandidate(primary=primary, fallbacks=fallbacks, locator_type="label", locator_value=label_text)

    if text and len(text) <= 80:
        primary = f'text="{text.strip()}"'
        fallbacks.extend(_other_selectors(info, exclude=primary))
        return SelectorCandidate(primary=primary, fallbacks=fallbacks, locator_type="text", locator_value=text.strip())

    fallbacks.extend(_other_selectors(info, exclude=css_path))
    return SelectorCandidate(primary=css_path, fallbacks=fallbacks, locator_type="css", locator_value=css_path)


def _other_selectors(info: dict[str, Any], exclude: str) -> list[str]:
    candidates: list[str] = []
    for key in ("cssPath", "css_path", "aria_label", "text"):
        val = info.get(key)
        if val and val != exclude and str(val) not in candidates:
            if key in ("cssPath", "css_path"):
                candidates.append(str(val))
            elif key == "aria_label":
                candidates.append(f'[aria-label="{val}"]')
            elif key == "text" and len(str(val)) <= 80:
                candidates.append(f'text="{str(val).strip()}"')
    return candidates[:5]


def selector_to_playwright_locator(selector: str) -> str:
    """Convert stored selector string to Playwright locator expression."""
    if selector.startswith("role="):
        # role=button[name="Submit"]
        import re

        match = re.match(r'role=(\w+)\[name="(.+)"\]', selector)
        if match:
            role, name = match.groups()
            return f"page.getByRole('{role}', {{ name: '{name}' }})"
    if selector.startswith('[data-testid="'):
        test_id = selector.split('"')[1]
        return f"page.getByTestId('{test_id}')"
    if selector.startswith('text="'):
        text = selector[6:-1]
        return f"page.getByText('{text}')"
    if selector.startswith('label="'):
        label = selector[7:-1]
        return f"page.getByLabel('{label}')"
    if selector.startswith('[aria-label="'):
        label = selector.split('"')[1]
        return f"page.locator('[aria-label=\"{label}\"]')"
    escaped = selector.replace("'", "\\'")
    return f"page.locator('{escaped}')"
