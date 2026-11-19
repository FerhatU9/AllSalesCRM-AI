"""Contract and edge-case tests for handbook v1.0 lead decision workflow."""
from fastapi.testclient import TestClient
from allsales.lead_qualification import LeadInput, evaluate_lead, market_region
from backend import api


def sample(**overrides):
    payload = dict(
        company_name="ExampleTech Ltd", country="Netherlands", employee_count=120,
        industry="SaaS", contact_name="Demo Buyer", business_email="buyer@example.com",
        stated_use_case="Manage inbound sales", lead_source="Website",
        consent_status="Opted In", assigned_owner="Demo Rep",
        decision_days=20, decision_authority="final", engagement="none",
    )
    payload.update(overrides)
    return LeadInput(**payload)


def test_example_lead_85_priority_a_smb_one_business_day():
    d = evaluate_lead(sample())
    assert d.provisional_score == 85
    assert d.score_components == {"company_fit": 40, "purchase_urgency": 25,
                                  "decision_authority": 20, "engagement": 0}
    assert d.qualification_status == "Qualified" and d.priority_tier == "A"
    assert d.recommended_routing == "SMB Sales Team"
    assert "1 business day" in d.follow_up_target
    assert d.automated_actions_taken == 0


def test_fit_requires_exactly_two_criteria_for_20():
    d = evaluate_lead(sample(industry="Manufacturing"))
    assert d.score_components["company_fit"] == 20


def test_fit_one_criterion_is_zero():
    d = evaluate_lead(sample(country="United States", industry="Manufacturing"))
    assert d.score_components["company_fit"] == 0


def test_urgency_thresholds():
    for days, expected in [(0,25), (30,25), (31,10), (90,10), (91,0)]:
        assert evaluate_lead(sample(decision_days=days)).score_components["purchase_urgency"] == expected


def test_engagement_levels():
    for level, expected in [("none",0), ("email_replied",5), ("demo_booked",15)]:
        assert evaluate_lead(sample(engagement=level)).score_components["engagement"] == expected


def test_authority_levels():
    for level, expected in [("none",0), ("influencer",10), ("final",20)]:
        assert evaluate_lead(sample(decision_authority=level)).score_components["decision_authority"] == expected


def test_missing_country_blocks_priority_even_when_score_otherwise_high():
    d = evaluate_lead(sample(country=""))
    assert d.qualification_status == "Incomplete"
    assert d.priority_tier is None
    assert "country" in d.missing_fields


def test_missing_email_blocks_priority():
    for email in ["", "not-an-email"]:
        d = evaluate_lead(sample(business_email=email))
        assert d.qualification_status == "Incomplete"
        assert d.priority_tier is None
        assert "business_email" in d.missing_fields


def test_other_mandatory_fields_block_active_queue():
    d = evaluate_lead(sample(stated_use_case="", lead_source="", assigned_owner="", consent_status="Missing"))
    assert set(["stated_use_case", "lead_source", "assigned_owner", "consent_status"]) <= set(d.missing_fields)
    assert d.priority_tier is None and d.queue_status.startswith("On hold")


def test_unknown_decision_authority_does_not_assume_zero():
    d = evaluate_lead(sample(decision_authority="unknown"))
    assert d.provisional_score is None
    assert d.qualification_status == "Needs clarification"
    assert d.priority_tier is None
    assert d.human_review_required


def test_unknown_engagement_does_not_assume_zero():
    d = evaluate_lead(sample(engagement="unknown"))
    assert "engagement" in d.unclear_scoring_factors and d.priority_tier is None


def test_unknown_decision_days_does_not_assume_no_urgency():
    d = evaluate_lead(sample(decision_days=None))
    assert "purchase_urgency" in d.unclear_scoring_factors and d.priority_tier is None


def test_unknown_country_requires_market_review():
    d = evaluate_lead(sample(country="Made-up country"))
    assert d.market_region == "Unverified"
    assert d.provisional_score is None and d.priority_tier is None
    assert d.recommended_routing == "Sales Manager — region verification"
    assert d.human_review_required


def test_outside_eu_uk_requires_review_not_rejection():
    d = evaluate_lead(sample(country="Australia"))
    assert d.market_region == "Outside target regions"
    assert d.human_review_required
    assert "market-eligibility" in d.recommended_routing
    assert "On hold" in d.queue_status
    assert d.priority_tier is not None


def test_large_enterprise_review():
    d = evaluate_lead(sample(employee_count=600))
    assert d.recommended_routing.startswith("Enterprise Sales Manager")
    assert d.human_review_required
    assert "On hold" in d.queue_status


def test_small_company_nurture_even_with_priority_b():
    d = evaluate_lead(sample(employee_count=8))
    assert d.provisional_score == 65 and d.priority_tier == "B"
    assert d.recommended_routing == "Nurture queue" and d.queue_status == "Nurture queue"


def test_enterprise_sales_routing_separate_from_priority():
    d = evaluate_lead(sample(employee_count=250, decision_days=45,
                             decision_authority="influencer", engagement="email_replied"))
    assert d.recommended_routing == "Enterprise Sales Team"
    assert d.provisional_score == 65 and d.priority_tier == "B"
    assert "3 business days" in d.follow_up_target


def test_priority_c_needs_30_calendar_day_review():
    d = evaluate_lead(sample(industry="Manufacturing", decision_days=100,
                             decision_authority="none", engagement="none"))
    assert d.provisional_score == 20 and d.priority_tier == "C"
    assert "30 calendar days" in d.follow_up_target


def test_no_marketing_to_opted_out():
    d = evaluate_lead(sample(consent_status="Opted Out"))
    assert any("Do not send marketing" in a.action for a in d.actions)


def test_unknown_consent_not_permission():
    d = evaluate_lead(sample(consent_status="Unknown"))
    assert d.qualification_status == "Qualified"
    assert any("not treat Unknown consent" in a.action for a in d.actions)


def test_over_10_pct_discount_written_approval():
    d = evaluate_lead(sample(proposed_discount_pct=15))
    assert d.human_review_required
    assert any("written sales manager approval" in a.action for a in d.actions)
    # Approval to offer a discount does not itself block queue assignment.
    assert "Eligible" in d.queue_status


def test_exactly_10_pct_no_approval():
    d = evaluate_lead(sample(proposed_discount_pct=10))
    assert not d.human_review_required
    assert not any("written sales manager approval" in a.action for a in d.actions)


def test_custom_terms_go_to_manager():
    d = evaluate_lead(sample(custom_contract_terms=True))
    assert any("custom contract" in a.action for a in d.actions)


def test_security_escalation_priority_over_normal_followup():
    d = evaluate_lead(sample(suspected_security_incident=True))
    assert d.actions[0].owner == "Security Team"
    assert d.actions[0].deadline == "Same business day"


def test_service_outage_escalation_priority_over_normal_followup():
    d = evaluate_lead(sample(urgent_service_outage=True))
    assert d.actions[0].owner == "Customer Support"
    assert d.actions[0].deadline == "Within 4 business hours"


def test_escalations_even_when_incomplete():
    d = evaluate_lead(sample(country="", suspected_security_incident=True))
    assert d.priority_tier is None
    assert d.actions[0].owner == "Security Team"


def test_region_classification():
    assert market_region("Netherlands") == "EU"
    assert market_region("United Kingdom") == "UK"
    assert market_region("Türkiye") == "Outside target regions"
    assert market_region("Not-a-country") == "Unverified"


def test_api_requires_local_token(monkeypatch):
    monkeypatch.setenv("API_APP_TOKEN", "test-local-token")
    c = TestClient(api.app)
    payload = sample().model_dump()
    assert c.post("/v1/leads/evaluate", json=payload).status_code == 401
    assert c.post("/v1/leads/evaluate", headers={"X-API-Key":"wrong"}, json=payload).status_code == 401


def test_api_returns_deterministic_report_without_dify_call(monkeypatch):
    monkeypatch.setenv("API_APP_TOKEN", "test-local-token")
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Should not call Dify")
    monkeypatch.setattr(api.DifyClient, "ask", fail_if_called)
    c = TestClient(api.app)
    r = c.post("/v1/leads/evaluate", headers={"X-API-Key":"test-local-token"}, json=sample().model_dump())
    assert r.status_code == 200
    assert r.json()["provisional_score"] == 85
    assert r.json()["priority_tier"] == "A"
    assert r.json()["automated_actions_taken"] == 0


def test_api_rejects_invalid_employees_and_discount(monkeypatch):
    monkeypatch.setenv("API_APP_TOKEN", "test-local-token")
    c = TestClient(api.app)
    for changes in ({"employee_count":-1}, {"proposed_discount_pct":101}, {"decision_days":-1}):
        payload = sample().model_dump();payload.update(changes)
        r = c.post("/v1/leads/evaluate", headers={"X-API-Key":"test-local-token"}, json=payload)
        assert r.status_code == 422


def test_ai_explanation_contains_no_customer_contact_details():
    from allsales.lead_explanation import build_explanation_prompt
    d = evaluate_lead(sample(company_name="TOP SECRET LTD", contact_name="Private Person",
                             business_email="private@example.com", stated_use_case="Secret plan"))
    prompt = build_explanation_prompt(d.model_dump())
    assert "85" in prompt and "SMB Sales Team" in prompt
    for raw in ["TOP SECRET LTD", "Private Person", "private@example.com", "Secret plan"]:
        assert raw not in prompt
