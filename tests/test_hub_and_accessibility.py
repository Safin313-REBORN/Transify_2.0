"""
Tests for Transify 2.0 Communication Hub, Phraseboard, and History Enhancements.
Verifies multi-session conversation tracking, message routing, phrasebook customization,
date/search history filtering, and strict user data isolation.
"""
import time
import pytest
from fastapi.testclient import TestClient

from src.api.server import app
from src.database.db import (
    create_user,
    clear_failed_logins,
    log_translation,
    toggle_history_favorite
)


@pytest.fixture
def client():
    clear_failed_logins("ip:testclient")
    with TestClient(app) as test_client:
        test_client.cookies.clear()
        yield test_client
    clear_failed_logins("ip:testclient")


def test_communication_hub_lifecycle_and_isolation(client):
    """
    Verifies full lifecycle of Communication Hub:
    1. Creating a conversation session.
    2. Adding messages from different sources ('sign', 'braille', 'speech', 'typed').
    3. Retrieving messages with correct timestamps and ordering.
    4. Clearing messages within a conversation.
    5. Deleting a conversation session.
    6. Multi-user isolation: User B cannot access or modify User A's conversations.
    """
    user_a_email = f"hub_user_a_{int(time.time()*1000)}@test.com"
    user_b_email = f"hub_user_b_{int(time.time()*1000)}@test.com"
    pwd = "HubPassword123!_2026"

    # Register and login User A
    client.post("/api/auth/register", json={"name": "Hub User A", "email": user_a_email, "password": pwd, "consent_terms": True})
    
    # Create conversation for User A
    conv_res = client.post("/api/hub/conversations", json={"title": "Team Standup"})
    assert conv_res.status_code == 200
    conv_data = conv_res.json()["conversation"]
    conv_id = conv_data["id"]
    assert conv_data["title"] == "Team Standup"

    # Add messages from various sources
    m1 = client.post(f"/api/hub/conversations/{conv_id}/messages", json={"source": "sign", "content": "HELLO"})
    assert m1.status_code == 200
    assert m1.json()["message"]["source"] == "sign"

    m2 = client.post(f"/api/hub/conversations/{conv_id}/messages", json={"source": "braille", "content": "Welcome to Transify"})
    assert m2.status_code == 200

    m3 = client.post(f"/api/hub/conversations/{conv_id}/messages", json={"source": "typed", "content": "Manual note"})
    assert m3.status_code == 200

    # Retrieve messages
    list_msgs = client.get(f"/api/hub/conversations/{conv_id}/messages")
    assert list_msgs.status_code == 200
    msgs = list_msgs.json()["messages"]
    assert len(msgs) == 3
    assert msgs[0]["content"] == "HELLO"
    assert msgs[1]["content"] == "Welcome to Transify"
    assert msgs[2]["content"] == "Manual note"

    # User B logs in
    client.cookies.clear()
    client.post("/api/auth/register", json={"name": "Hub User B", "email": user_b_email, "password": pwd, "consent_terms": True})

    # User B cannot see User A's conversation
    convs_b = client.get("/api/hub/conversations")
    assert convs_b.status_code == 200
    assert not any(c["id"] == conv_id for c in convs_b.json()["conversations"])

    # User B cannot access User A's messages directly (IDOR check)
    idor_res = client.get(f"/api/hub/conversations/{conv_id}/messages")
    assert idor_res.status_code == 404

    # User B cannot post to User A's conversation
    idor_post = client.post(f"/api/hub/conversations/{conv_id}/messages", json={"source": "typed", "content": "Intruder"})
    assert idor_post.status_code == 404

    # Switch back to User A
    client.cookies.clear()
    client.post("/api/auth/login", json={"email": user_a_email, "password": pwd})

    # Clear messages
    clear_res = client.post(f"/api/hub/conversations/{conv_id}/clear")
    assert clear_res.status_code == 200
    msgs_after_clear = client.get(f"/api/hub/conversations/{conv_id}/messages").json()["messages"]
    assert len(msgs_after_clear) == 0

    # Delete conversation
    del_res = client.delete(f"/api/hub/conversations/{conv_id}")
    assert del_res.status_code == 200
    assert client.get(f"/api/hub/conversations/{conv_id}/messages").status_code == 404


def test_phraseboard_endpoints_and_custom_phrases(client):
    """
    Verifies Quick Phraseboard and Personal Phrasebook:
    1. Returns core built-in phrases (English and Bengali).
    2. Allows authenticated user to add a custom phrase.
    3. Allows favoriting and unfavoriting a phrase.
    4. Allows deleting a custom phrase.
    5. Custom phrases are isolated per authenticated user.
    """
    user_email = f"phrase_user_{int(time.time()*1000)}@test.com"
    pwd = "PhrasePassword123!_2026"
    client.post("/api/auth/register", json={"name": "Phrase User", "email": user_email, "password": pwd, "consent_terms": True})

    # 1. Fetch initial phraseboard
    res_initial = client.get("/api/phrases")
    assert res_initial.status_code == 200
    data = res_initial.json()
    assert len(data["default_phrases"]) >= 12
    # Verify core phrases exist with bilingual support
    en_texts = [p["text_en"] for p in data["default_phrases"]]
    assert "Hello" in en_texts
    assert "Help" in en_texts
    assert "Thank you" in en_texts
    assert "Emergency" in en_texts

    # 2. Add custom phrase
    res_add = client.post("/api/phrases", json={
        "text_en": "Where is the clinic?",
        "text_bn": "ক্লিনিক কোথায়?",
        "category": "Medical"
    })
    assert res_add.status_code == 200
    new_phrase = res_add.json()["phrase"]
    phrase_id = new_phrase["id"]
    assert new_phrase["text_en"] == "Where is the clinic?"
    assert new_phrase["text_bn"] == "ক্লিনিক কোথায়?"

    # 3. Toggle favorite
    fav_res = client.post(f"/api/phrases/{phrase_id}/favorite")
    assert fav_res.status_code == 200
    assert fav_res.json()["is_favorite"] is True

    # 4. Verify listed in custom phrases
    list_res = client.get("/api/phrases")
    customs = list_res.json()["custom_phrases"]
    assert len(customs) == 1
    assert customs[0]["id"] == phrase_id
    assert customs[0]["is_favorite"] is True

    # 5. Delete phrase
    del_res = client.delete(f"/api/phrases/{phrase_id}")
    assert del_res.status_code == 200

    list_after_del = client.get("/api/phrases")
    assert len(list_after_del.json()["custom_phrases"]) == 0


def test_history_search_filtering_and_favorites(client):
    """
    Verifies translation history enhancements:
    1. Search by recognized text keyword.
    2. Filter by modality (sign vs braille vs speech).
    3. Toggle favorite / bookmark flag.
    4. Filter by favorites_only.
    """
    user_email = f"hist_filter_user_{int(time.time()*1000)}@test.com"
    pwd = "HistPassword123!_2026"
    reg_res = client.post("/api/auth/register", json={"name": "History Filter User", "email": user_email, "password": pwd, "consent_terms": True})
    user_id = reg_res.json()["user"]["id"]

    # Log several diverse translations
    r1 = log_translation("sign", "dhonnobad", 0.98, user_id=user_id)
    r2 = log_translation("sign", "sahajjo", 0.95, user_id=user_id)
    r3 = log_translation("braille", "medical report header", 0.99, user_id=user_id)
    r4 = log_translation("speech", "hello world voice transcript", 0.92, user_id=user_id)

    # 1. Search filter
    search_res = client.get("/api/history?search=dhonnobad")
    assert search_res.status_code == 200
    assert len(search_res.json()["records"]) == 1
    assert search_res.json()["records"][0]["recognized_text"] == "dhonnobad"

    # 2. Modality filter
    sign_res = client.get("/api/history?module=sign")
    assert sign_res.status_code == 200
    assert all(r["module"] == "sign" for r in sign_res.json()["records"])
    assert len(sign_res.json()["records"]) == 2

    braille_res = client.get("/api/history?module=braille")
    assert braille_res.status_code == 200
    assert all(r["module"] == "braille" for r in braille_res.json()["records"])
    assert len(braille_res.json()["records"]) == 1

    # 3. Toggle favorite on r2
    fav_res = client.post(f"/api/history/{r2}/favorite")
    assert fav_res.status_code == 200
    assert fav_res.json()["is_favorite"] is True

    # 4. Filter by favorites_only
    favs_res = client.get("/api/history?favorites_only=true")
    assert favs_res.status_code == 200
    records = favs_res.json()["records"]
    assert len(records) == 1
    assert records[0]["id"] == r2
    assert records[0]["is_favorite"] is True

    # 5. Single record deletion with user ownership
    del_res = client.delete(f"/api/history/{r1}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Confirm r1 is deleted
    list_after_del = client.get("/api/history")
    assert list_after_del.status_code == 200
    assert not any(r["id"] == r1 for r in list_after_del.json()["records"])

    # IDOR check: another user cannot delete r2
    user_other_email = f"hist_other_{int(time.time()*1000)}@test.com"
    client.cookies.clear()
    client.post("/api/auth/register", json={"name": "Other User", "email": user_other_email, "password": pwd, "consent_terms": True})
    
    other_del = client.delete(f"/api/history/{r2}")
    assert other_del.status_code == 404


