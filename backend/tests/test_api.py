import os
import pytest
from fastapi.testclient import TestClient

# Configure in-memory shared database for tests
TEST_DB = "file:meetingmind_test?mode=memory&cache=shared"
os.environ["MEETINGMIND_DB_PATH"] = TEST_DB

from app.database import init_db, get_db_connection
from app.main import app

client = TestClient(app)

# Hold a persistent connection so the shared in-memory DB is preserved across test requests
holding_conn = None

@pytest.fixture(scope="session", autouse=True)
def setup_database_session():
    global holding_conn
    holding_conn = init_db(TEST_DB)
    yield
    if holding_conn:
        holding_conn.close()

SAMPLE_TRANSCRIPT = """
[00:00:15] Elena Rostova: Team, we need to finalize the microservices migration plan today.
[00:00:45] Arthur Dent: I will write the OpenAPI specifications by Thursday.
[00:01:10] Elena Rostova: We decided to deploy our cluster on AWS EKS with Terraform.
[00:01:40] Arthur Dent: Action Item: configure GitHub Actions CI pipeline for automated container scanning.
"""

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "MeetingMind"

def test_meeting_process_and_crud_lifecycle():
    # 1. Ingest meeting
    payload = {
        "title": "Cloud Infrastructure Planning",
        "meeting_date": "2026-11-12",
        "duration_minutes": 35,
        "raw_transcript": SAMPLE_TRANSCRIPT
    }
    create_res = client.post("/api/meetings/process", json=payload)
    assert create_res.status_code == 201
    meeting = create_res.json()
    meeting_id = meeting["id"]
    assert meeting["title"] == "Cloud Infrastructure Planning"
    assert meeting["participant_count"] == 2
    assert len(meeting["transcripts"]) == 4
    assert len(meeting["action_items"]) >= 2
    assert len(meeting["decisions"]) >= 1

    # 2. Get Meeting Detail
    detail_res = client.get(f"/api/meetings/{meeting_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == meeting_id

    # 3. List Meetings
    list_res = client.get("/api/meetings?q=Infrastructure")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert items[0]["id"] == meeting_id

    # 4. Update Action Item Status
    action_item = meeting["action_items"][0]
    action_id = action_item["id"]
    update_res = client.patch(
        f"/api/meetings/{meeting_id}/action-items/{action_id}",
        json={"status": "COMPLETED", "priority": "HIGH"}
    )
    assert update_res.status_code == 200
    updated_item = update_res.json()
    assert updated_item["status"] == "COMPLETED"
    assert updated_item["priority"] == "HIGH"

    # 5. Add Manual Action Item
    manual_payload = {
        "description": "Schedule follow-up security review with DevOps lead",
        "assignee": "Elena Rostova",
        "due_date": "Friday",
        "priority": "HIGH",
        "status": "PENDING",
        "confidence_score": 1.0
    }
    add_res = client.post(f"/api/meetings/{meeting_id}/action-items", json=manual_payload)
    assert add_res.status_code == 201
    assert add_res.json()["description"] == manual_payload["description"]

    # 6. Verify Analytics Overview
    overview_res = client.get("/api/meetings/analytics/overview")
    assert overview_res.status_code == 200
    stats = overview_res.json()
    assert stats["total_meetings"] >= 1
    assert stats["total_action_items"] >= 3
    assert stats["completed_action_items"] >= 1
    assert stats["total_decisions"] >= 1

    # 7. Delete Meeting
    del_res = client.delete(f"/api/meetings/{meeting_id}")
    assert del_res.status_code == 204

    # Verify deleted
    verify_res = client.get(f"/api/meetings/{meeting_id}")
    assert verify_res.status_code == 404

def test_validation_errors():
    # Empty transcript
    res = client.post("/api/meetings/process", json={"title": "Short", "raw_transcript": "Short"})
    assert res.status_code == 422  # pydantic validation min_length=15
