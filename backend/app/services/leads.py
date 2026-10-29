def count_leads_by_source(leads: list[dict]) -> dict[str, int]:
    results = {}

    for lead in leads:
        source = lead.get("source") or "unknown"
        results[source] = results.get(source, 0) + 1

    return results

