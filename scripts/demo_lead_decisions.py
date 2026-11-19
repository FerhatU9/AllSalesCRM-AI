"""Free offline demo of the v0.8 synthetic lead decision engine.

Run: python -m scripts.demo_lead_decisions
"""
from allsales.lead_qualification import LeadInput, evaluate_lead

BASE = dict(
    company_name="ExampleTech Ltd", country="Netherlands", employee_count=120,
    industry="SaaS", contact_name="Example Contact", business_email="example@example.com",
    stated_use_case="Manage inbound leads", lead_source="Website", consent_status="Opted In",
    assigned_owner="Example Sales Rep", decision_days=20,
    decision_authority="final", engagement="none",
)


def main() -> None:
    examples = [
        ("Qualified SaaS prospect", {}),
        ("Incomplete lead — country missing", {"country": ""}),
        ("Large enterprise special review", {"employee_count": 600}),
        ("Manager approval for 15% discount", {"proposed_discount_pct": 15}),
        ("Urgent security incident", {"suspected_security_incident": True}),
    ]
    for label, changes in examples:
        decision = evaluate_lead(LeadInput(**{**BASE, **changes}))
        print(f"\n{label}")
        print(f"  Status: {decision.qualification_status}")
        print(f"  Score: {decision.provisional_score}; priority: {decision.priority_tier}")
        print(f"  Routing: {decision.recommended_routing}")
        print(f"  Queue: {decision.queue_status}")
        for action in decision.actions:
            print(f"  - [{action.handbook_section}] {action.owner}: {action.action}")


if __name__ == "__main__":
    main()
