"""Create a data-minimized prompt for an optional policy-only LLM explanation."""
def build_explanation_prompt(decision: dict) -> str:
    """Send only derived policy facts to Dify; never lead names, email or free text."""
    components = decision["score_components"]
    return (
        "According to the AllSales CRM Sales Lead Qualification & Follow-Up Handbook, "
        "what priority tier and first personalized contact deadline apply to a lead "
        f"scoring {decision['provisional_score']} points (Section 4 — Priority tiers and follow-up times)? "
        "Which lead scoring rules (Section 3 — Lead scoring rules: company fit, purchase urgency, "
        "decision authority and engagement) and sales team routing rules "
        "(Section 5 — Sales team routing) support this synthetic calculation? "
        "Explain the applicable handbook rules, not the identity or private details of a company. "
        "Cite the retrieved handbook sections. If only part is supported, explain that part "
        "and say which remaining information is not specified. Do not invent policies or revise "
        "the authoritative deterministic Python calculation below.\n"
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


