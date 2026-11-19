"""Create a data-minimized prompt for an optional policy-only LLM explanation."""
def build_explanation_prompt(decision: dict) -> str:
    """Send only derived policy facts to Dify; never lead names, email or free text."""
    components = decision["score_components"]
    return (
        "Explain the following fictional lead recommendation using only the AllSales CRM "
        "synthetic sales handbook. Identify applicable sections, and explain important "
        "conditions or necessary human reviews. Do not invent missing data or change the "
        "computed score. The deterministic Python decision is authoritative.\n"
        f"Region classification: {decision['market_region']}\n"
        f"Scoring components: company fit={components['company_fit']}, "
        f"urgency={components['purchase_urgency']}, "
        f"authority={components['decision_authority']}, engagement={components['engagement']}\n"
        f"Score: {decision['provisional_score']}\n"
        f"Qualification: {decision['qualification_status']}\n"
        f"Priority: {decision['priority_tier']}\n"
        f"Routing: {decision['recommended_routing']}\n"
        f"Queue status: {decision['queue_status']}\n"
        f"Follow-up: {decision['follow_up_target']}\n"
        "The original record fields and contact identifiers are intentionally withheld."
    )


