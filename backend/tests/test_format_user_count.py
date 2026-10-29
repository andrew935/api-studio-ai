import pytest
from backend.app.services.http_client import format_user_count


@pytest.mark.parametrize(
    "count,label",
    [
        (3, "users"),
        (0, "empty"),
        (10, "customers"),
    ],
)
def test_format_user_count(count, label):
    result = format_user_count(count, label)

    assert result == {"count": count, "label": label}
