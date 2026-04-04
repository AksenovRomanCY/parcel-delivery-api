import pytest

_unit_marker = pytest.mark.unit


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-apply the ``unit`` marker to every test under tests/unit/."""
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(_unit_marker)
