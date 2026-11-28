"""Persistent reviewed decisions, migrations, idempotency and tenant boundaries."""
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from allsales.auth import VerifiedIdentity, get_verified_identity
from allsales.dify_client import DifyClient
from allsales.models import FollowupRequest, Identity, LeadAuditEvent, LeadRecord, Membership, Organization, QualificationRecord
from backend import api, lead_routes

FACTS = {
    "country": "Netherlands", "employee_count": 120, "industry": "SaaS",
    "contact_name": "Do not store this fictional name", "business_email": "hidden@example.test",
    "lead_source": "Synthetic source sentinel", "consent_status": "Opted In",
    "assigned_owner": "Synthetic owner sentinel", "decision_days": 20,
    "decision_authority": "final", "engagement": "none",
}


def test_migrated_history_dashboard_and_security(monkeypatch, tmp_path):
    url = "sqlite+pysqlite:///" + str(tmp_path / "qualifications.sqlite")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("ALLSALES_ENV", "local")
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "005_automation_membership")
    engine = create_engine(url)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    issuer = "https://identity.example/"
    with Session(engine) as db:
        a, b = Organization(slug="a", display_name="A"), Organization(slug="b", display_name="B")
        people = {name: Identity(issuer=issuer,subject=name) for name in ("owner", "sales", "viewer", "other", "robot@clients")}
        db.add_all([a, b, *people.values()])
        db.flush()
        for name, org, role in (("owner",a,"owner"),("sales",a,"sales"),("viewer",a,"viewer"),
                                ("other",b,"owner"),("robot@clients",a,"automation")):
            db.add(Membership(organization_id=org.id, identity_id=people[name].id, role=role))
        leads = [LeadRecord(organization_id=org.id,created_by_identity_id=people[name].id,
                            company_name=company,summary="Synthetic use case",status=status)
                 for org,name,company,status in [
                     (a,"owner","A-one","qualified"),(a,"owner","A-two","new"),(a,"owner","A-three","new"),
                     (a,"owner","A-archive","archived"),(b,"other","B-secret","qualified")
                 ]]
        db.add_all(leads)
        db.flush()
        org_a, org_b = a.id, b.id
        first, second, third, archive, foreign = [x.id for x in leads]
        actor_id = people["owner"].id
        db.commit()

    # Demonstrate an additive 005 -> 006 migration on populated leads.
    command.upgrade(cfg, "head")
    assert "qualification_records" in inspect(engine).get_table_names()
    monkeypatch.setattr(lead_routes, "session_factory", lambda: factory)

    def login(name):
        api.app.dependency_overrides[get_verified_identity] = lambda: VerifiedIdentity(
            issuer=issuer,subject=name, scopes=frozenset({"request:followups","execute:followups"})
        )

    def path(lead=first, org=org_a):
        return f"/v1/organizations/{org}/leads/{lead}"

    def dashboard(org=org_a):
        return f"/v1/organizations/{org}/qualification-dashboard"

    def preview(client, lead=first, facts=FACTS, org=org_a):
        r = client.post(path(lead,org)+"/qualification-preview",
                        json={"facts":facts,"confirm_synthetic":True})
        assert r.status_code == 200, r.text
        return r.json()["review_digest"]

    def payload(digest, facts=FACTS):
        return {"facts":facts,"confirm_synthetic":True,"request_key":str(uuid4()),"review_digest":digest}

    def unexpected_provider(*a,**k):
        raise AssertionError("Save and dashboard must never call a model")

    monkeypatch.setattr(DifyClient,"ask",unexpected_provider)
    try:
        with TestClient(api.app) as client:
            assert client.get(dashboard()).status_code == 401
            login("owner")
            initial = client.get(dashboard()).json()
            assert initial["total_active"] == 3 and initial["not_evaluated"] == 3
            digest = preview(client)
            with Session(engine) as db:
                assert db.scalar(select(func.count()).select_from(QualificationRecord)) == 0
            data = payload(digest)
            url_save = path()+"/qualifications"
            assert client.post(url_save,json={**data,"score":100}).status_code == 422
            assert client.post(url_save,json={**data,"review_digest":"0"*64}).status_code == 409
            assert client.post(url_save,json={**data,"confirm_synthetic":False}).status_code == 422
            saved = client.post(url_save,json=data)
            assert saved.status_code == 201, saved.text
            saved = saved.json()
            assert saved["decision"]["provisional_score"] == 85
            assert saved["decision"]["priority_tier"] == "A"
            assert saved["stored_status"] == "qualified"
            assert saved["created_at"].endswith(("Z","+00:00"))
            retry = client.post(url_save,json=data)
            assert retry.status_code == 200 and retry.json() == saved
            assert client.post(url_save,json={**data,"review_digest":"f"*64}).status_code == 409
            assert client.post(path(archive)+"/qualifications",json=data).status_code == 409
            assert client.get(path(foreign)+"/qualifications").status_code == 404
            assert client.get(dashboard(org_b)).status_code == 404

            login("sales")
            assert client.post(url_save,json=data).status_code == 409
            incomplete = {**FACTS,"business_email":""}
            d2 = preview(client, second, incomplete)
            result = client.post(path(second)+"/qualifications",json=payload(d2,incomplete))
            assert result.status_code == 201
            assert result.json()["decision"]["priority_tier"] is None

            # Latest evaluation changes the aggregate without duplicating the lead.
            lower = {**FACTS,"decision_days":45,"decision_authority":"none"}
            d3 = preview(client,first,lower)
            assert client.post(url_save,json=payload(d3,lower)).status_code == 201
            history = client.get(url_save).json()
            assert [item["decision"]["priority_tier"] for item in history] == ["B","A"]
            d = client.get(dashboard()+"?limit=1").json()
            assert {k:d[k] for k in ("total_active","evaluated","not_evaluated","needs_clarification","tier_a","tier_b","tier_c")} == {
                "total_active":3,"evaluated":2,"not_evaluated":1,"needs_clarification":1,"tier_a":0,"tier_b":1,"tier_c":0
            }
            assert len(d["leads"]) == 1
            assert d["leads"][0]["latest"]["decision"]["priority_tier"] == "B"
            assert client.get(dashboard()+"?limit=1&offset=2").json()["leads"][0]["id"] == str(second)

            # Stale reviewed result cannot be saved after a status change.
            d4 = preview(client,third)
            assert client.patch(path(third),json={"status":"qualified"}).status_code == 200
            assert client.post(path(third)+"/qualifications",json=payload(d4)).status_code == 409
            assert client.patch(path(first),json={"status":"archived"}).status_code == 200
            assert client.get(dashboard()).json()["total_active"] == 2
            assert len(client.get(url_save).json()) == 2  # Archived history retained.

            login("viewer")
            assert client.get(url_save).status_code == 200
            assert client.get(dashboard()).status_code == 200
            assert client.post(path(second)+"/qualifications",json=payload(d2,incomplete)).status_code == 403
            login("robot@clients")
            assert client.get(url_save).status_code == 403
            assert client.get(dashboard()).status_code == 403
            assert client.post(path(second)+"/qualifications",json=payload(d2,incomplete)).status_code == 403
            login("other")
            assert client.get(url_save).status_code == 404
            assert client.get(dashboard()).status_code == 404
            foreign_digest = preview(client,foreign,org=org_b)
            assert client.post(path(foreign,org_b)+"/qualifications",json=payload(foreign_digest)).status_code == 201
            assert client.get(dashboard(org_b)).json()["tier_a"] == 1

        with Session(engine) as db:
            records = db.scalars(select(QualificationRecord).order_by(QualificationRecord.sequence)).all()
            assert len(records) == 4 and records[0].actor_identity_id == actor_id
            assert db.get(LeadRecord,second).status == "new"
            assert db.scalar(select(func.count()).select_from(FollowupRequest)) == 0
            assert db.scalar(select(func.count()).select_from(LeadAuditEvent)) == 2  # Only explicit status changes.
            for r in records:
                serialized = str(r.decision)
                for raw in ("hidden@example.test","Do not store this fictional name","Synthetic source sentinel","Synthetic owner sentinel","Synthetic use case"):
                    assert raw not in serialized
    finally:
        api.app.dependency_overrides.clear()
        engine.dispose()

    command.downgrade(cfg,"005_automation_membership")
    engine = create_engine(url)
    assert "qualification_records" not in inspect(engine).get_table_names()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(LeadRecord)) == 5
    engine.dispose()
