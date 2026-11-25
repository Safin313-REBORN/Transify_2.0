"""
Tests for Transify Model Context Protocol (MCP) JSON-RPC 2.0 and REST Tool Endpoints.
Verifies protocol initialization, tool listing, tool invocation schemas, and ping.
"""

from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)


def test_mcp_initialize():
    """Verifies standard MCP JSON-RPC 2.0 initialize protocol handshake."""
    res = client.post("/api/mcp", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 1
    assert "result" in data
    assert data["result"]["serverInfo"]["name"] == "Transify MCP Server"
    assert data["result"]["serverInfo"]["version"] == "2.0.0"
    assert "tools" in data["result"]["capabilities"]


def test_mcp_tools_list_jsonrpc():
    """Verifies MCP JSON-RPC 2.0 tools/list method returns valid tool manifests."""
    res = client.post("/api/mcp", json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    })
    assert res.status_code == 200
    data = res.json()
    tools = data["result"]["tools"]
    assert len(tools) >= 5
    tool_names = [t["name"] for t in tools]
    assert "resolve_sign_ambiguity" in tool_names
    assert "resolve_braille_ambiguity" in tool_names
    assert "triage_symptom" in tool_names
    assert "calculate_insulin_correction" in tool_names
    assert "chat_assistive_agent" in tool_names


def test_mcp_tools_list_rest():
    """Verifies RESTful /api/mcp/tools endpoint."""
    res = client.get("/api/mcp/tools")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["tools"]) >= 5


def test_mcp_tool_call_triage():
    """Verifies MCP tools/call for symptom triage evaluates clinical red flags."""
    res = client.post("/api/mcp", json={
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "triage_symptom",
            "arguments": {
                "symptoms": "acute crushing chest pain radiating to left arm",
                "severity": 9,
                "patient_age": 60
            }
        }
    })
    assert res.status_code == 200
    data = res.json()
    assert "result" in data
    assert "content" in data["result"]
    assert len(data["result"]["content"]) > 0
    import json
    parsed = json.loads(data["result"]["content"][0]["text"])
    assert parsed["urgency_level"] == "RED"


def test_mcp_tool_call_insulin_safety():
    """Verifies MCP tools/call for insulin calculation adheres to clinical bounds."""
    res = client.post("/api/mcp", json={
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "calculate_insulin_correction",
            "arguments": {
                "current_bg": 180,
                "target_bg": 100,
                "isf": 40
            }
        }
    })
    assert res.status_code == 200
    data = res.json()
    import json
    parsed = json.loads(data["result"]["content"][0]["text"])
    assert parsed["status"] == "NUTRITION_AND_INSULIN_CALCULATED"
    assert "insulin_dosage_recommendation" in parsed
    assert parsed["insulin_dosage_recommendation"]["dosage_breakdown"]["recommended_injection_units"] >= 0.0


def test_mcp_ping():
    """Verifies MCP ping returns empty result."""
    res = client.post("/api/mcp", json={
        "jsonrpc": "2.0",
        "id": 99,
        "method": "ping"
    })
    assert res.status_code == 200
    assert res.json()["result"] == {}
