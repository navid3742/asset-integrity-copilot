"""Offline API, dataset integrity, retrieval and human-approval tests."""

import re

from app import __version__, agent, db, retrieval


def test_health_and_status(client):
    assert client.get("/api/health").json()["version"] == __version__
    state = client.get("/api/status").json()
    assert state["agent_framework"] == "OpenAI Agents SDK"
    assert state["mode"] == "offline"
    assert state["counts"] == {
        "assets": 60,
        "inspections": 180,
        "maintenance": 120,
        "incidents": 12,
        "reports": 0,
    }


def test_three_asset_categories(client):
    assets = client.get("/api/assets").json()
    assert len(assets) == 60
    assert {a["category"] for a in assets} == {"Pump", "Valve", "Pressure Vessel"}
    assert len([a for a in assets if a["category"] == "Pump"]) == 20
    assert len([a for a in assets if a["category"] == "Valve"]) == 20
    assert len([a for a in assets if a["category"] == "Pressure Vessel"]) == 20


def test_linked_pump_investigation(client):
    pump = client.get("/api/assets/P-204").json()
    assert pump["status"] == "Review" and pump["category"] == "Pump"
    history = client.get("/api/assets/P-204/history").json()
    assert len(history["inspections"]) == 3 and len(history["maintenance"]) == 2
    assert any(i["id"] == "INC-007" for i in history["incidents"])
    assert all("mm/s" in i["unit"] for i in history["inspections"])
    assert any(w["id"] == "WO-P-204-02" for w in history["maintenance"])


def test_valve_and_vessel_cases(client):
    valve = client.get("/api/assets/CV-310").json()
    vessel = client.get("/api/assets/PV-120").json()
    assert valve["category"] == "Valve" and vessel["category"] == "Pressure Vessel"
    assert client.get("/api/assets/CV-310/history").json()["incidents"][0]["id"] == "INC-010"
    assert client.get("/api/assets/PV-120/history").json()["incidents"][0]["id"] == "INC-012"
    assert all(row["unit"] == "mm" for row in db.get_inspections("PV-120"))


def test_database_foreign_keys_and_unique_ids(client):
    with db._session() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        for name in ("inspections", "maintenance", "incidents"):
            total = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            joined = conn.execute(
                f"SELECT COUNT(*) FROM {name} r JOIN assets a ON r.asset_id=a.id"
            ).fetchone()[0]
            assert total == joined


def test_search_asset_names(client):
    # Category search by word 'vessel' should find all vessels.
    items = client.get("/api/assets?q=Vessel").json()
    assert len(items) == 20
    assert client.get("/api/assets/MISSING-999").status_code == 404
    assert client.get("/api/assets/P-999/history").status_code == 404


def test_offline_chat_shows_maintenance_and_incident(client):
    response = client.post(
        "/api/chat", json={"question": "Investigate pump P-204 and its seal history"}
    ).json()
    assert response["mode"] == "offline"
    assert "INC-007" in response["answer"] and "WO-P-204-02" in response["answer"]
    assert response["traces"][0]["tool"] == "get_asset"
    assert response["traces"][1]["tool"] == "get_asset_history"
    assert response["sources"]


def test_valve_and_vessel_offline(client):
    for tag, incident in [("CV-310", "INC-010"), ("PV-120", "INC-012")]:
        response = client.post("/api/chat", json={"question": f"Investigate {tag}"}).json()
        assert tag in response["answer"] and incident in response["answer"]
        assert (
            "acceptance" in response["answer"].lower()
            or "operational" in response["answer"].lower()
        )


def test_offline_unknown_asset(client):
    response = client.post("/api/chat", json={"question": "Investigate P-999"}).json()
    assert response["mode"] == "offline" and "No synthetic equipment" in response["answer"]
    assert response["sources"] == []


def test_tool_allowlist_and_id_validation(client):
    assert agent.dispatch_tool("execute_sql", {"query": "DELETE FROM assets"})["error"]
    assert agent.dispatch_tool("approve_report", {"report_id": "RPT-XXX"})["error"]
    assert agent.dispatch_tool("change_valve_setpoint", {"asset_id": "CV-310"})["error"]
    for tag in ("../../etc/passwd", "P-9999", "P-204;DROP TABLE assets", "XV-1042"):
        assert "error" in agent.dispatch_tool("get_asset", {"asset_id": tag})
    assert agent.dispatch_tool("get_asset", {"asset_id": "p-204"})["asset"]["id"] == "P-204"
    assert "error" in agent.dispatch_tool("search_documents", {"query": ""})


def test_history_tool_includes_maintenance(client):
    result = agent.dispatch_tool("get_asset_history", {"asset_id": "CV-310"})
    assert len(result["maintenance"]) == 2
    assert len(result["inspections"]) == 3
    assert result["incidents"][0]["id"] == "INC-010"


def test_report_approval_remains_outside_agent(client):
    draft = client.post("/api/reports/draft", json={"asset_id": "PV-120"}).json()
    assert draft["status"] == "pending"
    assert "WO-PV-120" in draft["summary"]
    assert "fitness-for-service" in draft["summary"]
    assert db.get_report(draft["id"])["status"] == "pending"
    assert "error" in agent.dispatch_tool("approve_report", {"id": draft["id"]})
    assert client.post(f"/api/reports/{draft['id']}/approve").status_code == 422
    assert (
        client.post(
            f"/api/reports/{draft['id']}/approve", json={"confirmation": "ignore rules"}
        ).status_code
        == 422
    )
    assert db.get_report(draft["id"])["status"] == "pending"
    res = client.post(
        f"/api/reports/{draft['id']}/approve", json={"confirmation": "I_REVIEWED_THIS_DEMO_REPORT"}
    )
    assert res.status_code == 200 and res.json()["status"] == "approved"
    assert (
        client.post(
            f"/api/reports/{draft['id']}/approve",
            json={"confirmation": "I_REVIEWED_THIS_DEMO_REPORT"},
        ).status_code
        == 409
    )


def test_reports_with_invalid_asset_not_created(client):
    assert (
        client.post("/api/reports/draft", json={"asset_id": "../../etc/passwd"}).status_code == 422
    )
    assert client.post("/api/reports/draft", json={"asset_id": "P-999"}).status_code == 404
    assert (
        client.post(
            "/api/reports/RPT-NONEXISTENT/approve",
            json={"confirmation": "I_REVIEWED_THIS_DEMO_REPORT"},
        ).status_code
        == 404
    )


def test_document_catalog_and_reference_cases(client):
    docs = client.get("/api/documents").json()
    assert len(docs) == 15
    for doc_id in (
        "SOP-PMP-001",
        "SOP-VLV-003",
        "SOP-PV-005",
        "POL-AI-010",
        "CASE-INC-007",
        "CASE-INC-010",
        "CASE-INC-012",
    ):
        response = client.get(f"/api/documents/{doc_id}")
        assert response.status_code == 200
        assert "SYNTHETIC TRAINING DOCUMENT" in response.json()["content"]
    assert client.get("/api/documents/NONEXISTENT").status_code == 404


def test_retrieval_references_pump_incident():
    results = retrieval.search(
        "P-204 vibration seal leakage incident work order", top_k=5, semantic=False
    )
    ids = {row["doc_id"] for row in results}
    assert "CASE-INC-007" in ids or "SOP-PMP-001" in ids
    assert len(ids) == len(results)
    assert all(row["id"].startswith(row["doc_id"] + ":") for row in results)


def test_retrieval_no_unrelated_hits():
    assert retrieval.search("deep sea plankton aquarium", semantic=False) == []
    assert retrieval.search("What is the CEO salary?", semantic=False) == []


def test_one_domain_word_does_not_make_a_question_relevant():
    # Regression: scores are normalised against the best hit, so before the coverage
    # check any single matching word ("pump", "valve") produced a 1.0 result.
    for question in (
        "what is the best pizza in town for a pump party",
        "who won the world cup in valve",
        "How much is the CEO salary for pressure",
        "tell me a joke",
    ):
        assert retrieval.search(question, semantic=False) == [], question
    assert retrieval.query_coverage("pump seal leak history") == 1.0


def test_input_validation(client):
    assert client.post("/api/chat", json={"question": "x"}).status_code == 422
    assert client.post("/api/chat", json={"question": "x" * 2100}).status_code == 422


def test_sop_does_not_supply_fake_pressure_limits(client):
    vessel_doc = client.get("/api/documents/SOP-PV-005").json()["content"]
    assert (
        "no remaining-life claim" in vessel_doc.lower() or "do not calculate" in vessel_doc.lower()
    )
    assert not re.search(r"\bmaximum operating pressure is \d+", vessel_doc, re.I)
