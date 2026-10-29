import json

import pytest

from backend.app.services.leads import count_leads_by_source
from backend.app.services.load_leads import Lead, load_leads


def test_count_leads_by_source_handles_missing_and_empty_sources():
    leads = [
        {"source": "facebook"},
        {"source": "google"},
        {"source": "facebook"},
        {},
        {"source": ""},
    ]

    assert count_leads_by_source(leads) == {
        "facebook": 2,
        "google": 1,
        "unknown": 2,
    }


def test_lead_normalizes_fields():
    lead = Lead(
        first_name=" Andrew ",
        email=" ANDREW@EXAMPLE.COM ",
    )

    assert lead.first_name == "Andrew"
    assert lead.email == "andrew@example.com"
    assert lead.source == "unknown"


@pytest.mark.parametrize("email", ["invalid-email", "", "   "])
def test_lead_rejects_invalid_email(email):
    with pytest.raises(ValueError, match="email must be valid"):
        Lead(
            first_name="Andrew",
            email=email,
        )


def test_lead_rejects_empty_first_name():
    with pytest.raises(ValueError, match="first_name must not be empty"):
        Lead(
            first_name="   ",
            email="andrew@example.com",
        )


def test_load_leads_skips_invalid_records():
    data = json.dumps(
        [
            {"first_name": "Andrew", "email": "andrew@example.com"},
            {"first_name": "Dana", "email": "invalid-email"},
            {
                "first_name": "Olga",
                "email": "olga@example.com",
                "source": "linkedin",
            },
        ]
    )

    leads = load_leads(data)

    assert len(leads) == 2
    assert [lead.first_name for lead in leads] == ["Andrew", "Olga"]


def test_load_leads_returns_empty_list_for_invalid_json():
    assert load_leads("not valid json") == []
