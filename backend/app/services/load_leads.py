import json
from dataclasses import dataclass


@dataclass
class Lead:
    first_name: str
    email: str
    source: str = "unknown"

    def __post_init__(self):
        self.first_name = self.first_name.strip()

        if not self.first_name:
            raise ValueError("first_name must not be empty")

        self.email = self.email.strip().lower()

        if "@" not in self.email:
            raise ValueError("email must be valid")

        self.source = self.source.strip() or "unknown"


def load_leads(data: str) -> list[Lead]:
    try:
        items = json.loads(data)
    except json.JSONDecodeError:
        return []

    leads = []

    for item in items:
        try:
            lead = Lead(**item)
            leads.append(lead)
        except (ValueError, TypeError):
            continue

    return leads

