"""Static contract checks for the credential-free, single-lead n8n template."""
import json
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / "n8n-workflows" / "sales_followup_automation.json"


def test_sales_followup_workflow_template():
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    assert set(workflow) == {"name", "nodes", "connections", "settings", "active", "pinData"}
    assert workflow["active"] is False
    assert workflow["pinData"] == {}
    nodes = {node["name"]: node for node in workflow["nodes"]}
    names = list(nodes)
    assert len(nodes) == len(workflow["nodes"]) == 10
    assert len({node["id"] for node in nodes.values()}) == 10
    assert nodes[names[0]]["type"] == "n8n-nodes-base.manualTrigger"
    assert names[1:] == [
        "Demo Configuration", "Check API Health", "List Assigned Organizations",
        "List Demo Leads", "Filter Qualified Leads", "Request Sales Follow-up",
        "Check Follow-up Status", "Verify Approved Request", "Execute Approved Follow-up",
    ]
    assert workflow["connections"] == {
        source: {"main": [[{"node": target, "type": "main", "index": 0}]]}
        for source, target in zip(names, names[1:])
    }

    config = json.loads(nodes["Demo Configuration"]["parameters"]["jsonOutput"])
    assert config == {"company_name": "Nordvale Technologies", "request_key": "REPLACE_WITH_NEW_UUID"}

    protected = set()
    for name, node in nodes.items():
        assert "credentials" not in node
        params = node["parameters"]
        if node["type"] != "n8n-nodes-base.httpRequest":
            continue
        assert params["url"].lstrip("=").startswith("http://host.docker.internal:8001/")
        assert not params.get("sendHeaders")
        assert "headerParameters" not in params
        if name != "Check API Health":
            assert params["authentication"] == "genericCredentialType"
            assert params["genericAuthType"] == "oAuth2Api"
            protected.add(name)
    assert protected == {
        "List Assigned Organizations", "List Demo Leads", "Request Sales Follow-up",
        "Check Follow-up Status", "Execute Approved Follow-up",
    }
    request = nodes["Request Sales Follow-up"]["parameters"]
    assert request["method"] == "POST"
    assert request["bodyParameters"]["parameters"] == [
        {"name": "request_key", "value": "={{ $('Demo Configuration').first().json.request_key }}"}
    ]
    gate = nodes["Verify Approved Request"]["parameters"]["conditions"]
    assert gate["combinator"] == "and"
    assert [(c["leftValue"], c["operator"]["operation"], c["rightValue"]) for c in gate["conditions"]] == [
        ("={{ $json.id }}", "equals", "={{ $('Request Sales Follow-up').first().json.id }}"),
        ("={{ $json.status }}", "equals", "approved"),
    ]
    execute = nodes["Execute Approved Follow-up"]["parameters"]
    assert execute["method"] == "POST"
    assert execute["url"].endswith("/followups/{{ $json.id }}/execute")
    assert not execute.get("sendBody")
