
from playwright_utils.selector_builder import build_selector_from_element_info, selector_to_playwright_locator


def test_prefers_data_testid():
    candidate = build_selector_from_element_info(
        {"data-testid": "submit-btn", "text": "Submit", "cssPath": "button"}
    )
    assert candidate.primary == '[data-testid="submit-btn"]'
    assert candidate.locator_type == "testid"


def test_prefers_role_and_name():
    candidate = build_selector_from_element_info(
        {
            "role": "button",
            "accessibleName": "Save",
            "text": "Save",
            "cssPath": "button",
        }
    )
    assert candidate.primary == 'role=button[name="Save"]'


def test_selector_to_playwright_locator():
    loc = selector_to_playwright_locator('[data-testid="foo"]')
    assert "getByTestId" in loc
