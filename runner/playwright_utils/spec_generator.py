from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Template

from playwright_utils.selector_builder import selector_to_playwright_locator

SPEC_TEMPLATE = Template("""import { test, expect } from '@playwright/test';

test.describe('{{ flow_name }}', () => {
  test('{{ test_title }}', async ({ page }) => {
    test.setTimeout(60000);
{% for step in steps %}
    // Step {{ step.order }}: {{ step.description }}
{% if step.action_type == 'navigate' %}
    await page.goto('{{ step.url }}');
    await expect(page).toHaveURL(/{{ step.url_pattern }}/);
{% elif step.action_type == 'click' %}
    await {{ step.locator }}.click();
{% elif step.action_type == 'fill' %}
    await {{ step.locator }}.fill('{{ step.value }}');
{% elif step.action_type == 'assert_visible' %}
    await expect({{ step.locator }}).toBeVisible();
{% endif %}
{% endfor %}
{% for assertion in assertions %}
    // {{ assertion.description }}
    await expect({{ assertion.locator }}).{{ assertion.matcher }}({{ assertion.expected }});
{% endfor %}
  });
});
""")


def generate_spec_file(
    flow_name: str,
    test_title: str,
    steps: list[dict[str, Any]],
    assertions: list[dict[str, Any]] | None = None,
) -> str:
    rendered_steps = []
    for step in steps:
        rendered = dict(step)
        if "selector" in step:
            rendered["locator"] = selector_to_playwright_locator(step["selector"])
        rendered_steps.append(rendered)

    rendered_assertions = []
    for assertion in assertions or []:
        rendered = dict(assertion)
        if "selector" in assertion:
            rendered["locator"] = selector_to_playwright_locator(assertion["selector"])
        rendered_assertions.append(rendered)

    return SPEC_TEMPLATE.render(
        flow_name=flow_name,
        test_title=test_title,
        steps=rendered_steps,
        assertions=rendered_assertions,
    )


def write_spec(output_path: Path, content: str) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return str(output_path)
