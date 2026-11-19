"""Offline checks for the sanitized public Dify workflow packages.

No API calls and no knowledge-base credentials are needed.
"""
import hashlib
import re
from pathlib import Path
from zipfile import ZipFile

import pytest

EXPORTS = Path(__file__).resolve().parents[1] / "dify_exports"


@pytest.mark.parametrize("name,model", [
    ("gemini-chatflow.ifpkg", "gemini-3.5-flash-lite"),
    ("claude-chatflow.ifpkg", "claude-sonnet-5-5"),
])
def test_export_integrity_and_model(name, model):
    with ZipFile(EXPORTS / name) as pkg:
        assert set(pkg.namelist()) == {"manifest.yaml", "app.yaml"}
        app = pkg.read("app.yaml")
        manifest = pkg.read("manifest.yaml").decode("utf-8")
    digest = hashlib.sha256(app).hexdigest()
    assert f"sha256: {digest}" in manifest
    assert f"size: {len(app)}" in manifest
    assert model.encode("utf-8") in app
    assert b"Knowledge Retrieval" in app
    assert b"retriever_resource:" in app
    assert b"dataset_ids: []" in app  # Must rebind after import.
    assert b"environment_variables: []" in app
    assert not re.search(rb"sk-ant-[A-Za-z0-9_-]{15,}|AIza[A-Za-z0-9_-]{25,}", app)


def test_equal_policy_prompt_and_retrieval_settings():
    with ZipFile(EXPORTS / "gemini-chatflow.ifpkg") as z:
        gem = z.read("app.yaml").decode()
    with ZipFile(EXPORTS / "claude-chatflow.ifpkg") as z:
        claude = z.read("app.yaml").decode()
    expected = [
        "You are the AllSales CRM Sales Policy Assistant.",
        "1. Answer the question directly. Do not greet the user or introduce yourself.",
        "2. Use only facts supported by the retrieved context.",
        "6. Do not invent policies or use outside information.",
        "{{#context#}}", "{{#sys.query#}}", "top_k: 10",
        "keyword_weight: 0.5", "vector_weight: 0.5", "reranking_enable: false",
    ]
    for snippet in expected:
        assert snippet in gem
        assert snippet in claude
