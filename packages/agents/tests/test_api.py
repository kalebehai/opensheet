def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "llm": "stub"}


def test_sheet_crud(client):
    r = client.post("/sheets", json={"name": "Q3"})
    assert r.status_code == 201
    sheet = r.json()
    assert sheet["rows"] == 100 and sheet["cols"] == 26

    assert [s["id"] for s in client.get("/sheets").json()] == [sheet["id"]]
    assert client.get(f"/sheets/{sheet['id']}").json()["name"] == "Q3"

    r = client.patch(f"/sheets/{sheet['id']}", json={"name": "Q4"})
    assert r.status_code == 200 and r.json()["name"] == "Q4"

    assert client.delete(f"/sheets/{sheet['id']}").status_code == 204
    assert client.get(f"/sheets/{sheet['id']}").status_code == 404
    assert client.delete(f"/sheets/{sheet['id']}").status_code == 404


def test_create_sheet_validation(client):
    assert client.post("/sheets", json={"name": ""}).status_code == 422


def test_patch_cell_variants(client, sheet):
    sid = sheet["id"]
    r = client.patch(f"/sheets/{sid}/cells/a1", json={"content": {"type": "raw", "value": 42}})
    assert r.status_code == 200
    assert r.json()["ref"] == "A1" and r.json()["value"] == 42

    r = client.patch(
        f"/sheets/{sid}/cells/B2",
        json={"content": {"type": "formula", "expression": "=SUM(A1:A3)"}},
    )
    assert r.json()["content"]["type"] == "formula"

    r = client.patch(
        f"/sheets/{sid}/cells/C3",
        json={"content": {"type": "agentPrompt", "prompt": "Summarize column A"}},
    )
    assert r.json()["content"]["status"] == "idle"

    cells = client.get(f"/sheets/{sid}").json()["cells"]
    assert set(cells) == {"A1", "B2", "C3"}


def test_patch_cell_errors(client, sheet):
    sid = sheet["id"]
    body = {"content": {"type": "raw", "value": 1}}
    assert client.patch(f"/sheets/{sid}/cells/ZZ1", json=body).status_code == 422  # out of bounds
    assert client.patch(f"/sheets/{sid}/cells/1A", json=body).status_code == 422
    assert client.patch("/sheets/missing/cells/A1", json=body).status_code == 404
    bad = {"content": {"type": "nope"}}
    assert client.patch(f"/sheets/{sid}/cells/A1", json=bad).status_code == 422


def test_agent_run_uses_calculator(client):
    r = client.post("/agents/run", json={"prompt": "Calculate 12 * (3 + 4)"})
    assert r.status_code == 200
    body = r.json()
    assert body["result"] == "84"
    assert body["status"] == "verified"
    assert body["tool_calls"][0]["tool"] == "calculator"
    assert body["trace"] == ["plan", "act", "respond", "verify"]


def test_agent_run_writes_back_to_cell(client, sheet):
    r = client.post(
        "/agents/run",
        json={"prompt": "Find the latest price of ACME", "sheet_id": sheet["id"], "cell_ref": "D4"},
    )
    body = r.json()
    assert body["status"] == "verified"
    assert body["result"].startswith("[stub]")
    assert body["cell"]["content"]["metadata"]["tools"] == ["web_search"]
    stored = client.get(f"/sheets/{sheet['id']}").json()["cells"]["D4"]
    assert stored["content"]["status"] == "verified"


def test_agent_run_no_tools(client):
    body = client.post("/agents/run", json={"prompt": "Say hello"}).json()
    assert body["tool_calls"] == [] and body["trace"] == ["plan", "respond", "verify"]


def test_formula_translate(client):
    r = client.post("/formulas/translate", json={"text": "sum of a1:a10"})
    assert r.status_code == 200
    assert r.json()["formula"] == "=SUM(A1:A10)" and r.json()["source"] == "rules"

    r = client.post("/formulas/translate", json={"text": "average of B2:B20"})
    assert r.json()["formula"] == "=AVERAGE(B2:B20)"

    r = client.post("/formulas/translate", json={"text": "make it pretty"})
    assert r.json()["source"] == "llm" and r.json()["confidence"] < 0.5


def test_cleaning_scan(client):
    payload = {
        "headers": ["name", "amount", "date"],
        "rows": [
            ["Alice", 10, "2026-01-01"],
            ["Bob ", 12, "01/02/2026"],
            ["Cara", 11, "2026-01-03"],
            ["Dan", 9, "2026-01-04"],
            ["Eve", 1000, "2026-01-05"],
            ["Fay", "", "2026-01-06"],
            ["Dan", 9, "2026-01-04"],
        ],
    }
    r = client.post("/cleaning/scan", json=payload)
    assert r.status_code == 200
    report = r.json()
    kinds = {a["kind"] for a in report["anomalies"]}
    assert report["row_count"] == 7
    assert {"duplicate_row", "whitespace", "missing", "outlier", "inconsistent_dates"} <= kinds
    assert report["anomaly_count"] == len(report["anomalies"])
