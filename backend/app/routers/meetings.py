import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional

from app.database import get_db_connection
from app.schemas import (
    MeetingIngestRequest,
    MeetingDetailOut,
    MeetingListItemOut,
    ActionItemCreate,
    ActionItemUpdate,
    ActionItemOut,
    DecisionOut,
    SpeakerMetricOut,
    TranscriptTurnOut,
    AnalyticsOverviewOut
)
from app.engine.processor import (
    parse_transcript,
    extract_speaker_metrics,
    extract_action_items,
    extract_decisions,
    generate_executive_summary
)

router = APIRouter(prefix="/api/meetings", tags=["meetings"])

@router.post("/process", response_model=MeetingDetailOut, status_code=201)
def process_and_create_meeting(payload: MeetingIngestRequest):
    turns = parse_transcript(payload.raw_transcript)
    if not turns:
        raise HTTPException(status_code=400, detail="Unable to extract dialogue turns from the provided transcript.")

    speaker_metrics = extract_speaker_metrics(turns)
    action_items_raw = extract_action_items(turns)
    decisions_raw = extract_decisions(turns)

    meeting_id = str(uuid.uuid4())
    meeting_date = payload.meeting_date or datetime.utcnow().strftime("%Y-%m-%d")
    exec_summary = generate_executive_summary(payload.title, turns, decisions_raw, action_items_raw)
    participant_count = len(speaker_metrics)

    conn = get_db_connection()
    with conn:
        # Insert Meeting
        conn.execute("""
            INSERT INTO meetings (id, title, meeting_date, duration_minutes, raw_transcript, executive_summary, participant_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (meeting_id, payload.title, meeting_date, payload.duration_minutes or 45, payload.raw_transcript, exec_summary, participant_count))

        # Insert Turns
        for t in turns:
            turn_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO transcripts (id, meeting_id, speaker, timestamp_str, content, sequence_order)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (turn_id, meeting_id, t.speaker, t.timestamp_str, t.content, t.sequence))

        # Insert Speaker Metrics
        for sm in speaker_metrics:
            sm_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO speaker_metrics (id, meeting_id, speaker_name, turn_count, word_count, talk_time_percentage, sentiment_tone)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sm_id, meeting_id, sm["speaker_name"], sm["turn_count"], sm["word_count"], sm["talk_time_percentage"], sm["sentiment_tone"]))

        # Insert Action Items
        for ai in action_items_raw:
            ai_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO action_items (id, meeting_id, description, assignee, due_date, priority, status, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ai_id, meeting_id, ai["description"], ai["assignee"], ai["due_date"], ai["priority"], ai["status"], ai["confidence_score"]))

        # Insert Decisions
        for dec in decisions_raw:
            dec_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO decisions (id, meeting_id, decision_text, category, rationale, timestamp_str)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (dec_id, meeting_id, dec["decision_text"], dec["category"], dec["rationale"], dec["timestamp_str"]))

    return get_meeting_detail(meeting_id)

@router.get("", response_model=List[MeetingListItemOut])
def list_meetings(q: Optional[str] = Query(None, description="Search by title or summary")):
    conn = get_db_connection()
    query = """
        SELECT m.id, m.title, m.meeting_date, m.duration_minutes, m.participant_count, m.executive_summary, m.created_at,
               (SELECT COUNT(*) FROM action_items WHERE meeting_id = m.id) as action_item_count,
               (SELECT COUNT(*) FROM decisions WHERE meeting_id = m.id) as decision_count
        FROM meetings m
    """
    params = []
    if q:
        query += " WHERE m.title LIKE ? OR m.executive_summary LIKE ?"
        term = f"%{q}%"
        params.extend([term, term])
    query += " ORDER BY m.created_at DESC"

    rows = conn.execute(query, params).fetchall()
    results = []
    for r in rows:
        summary_snippet = r["executive_summary"].split("\n")[0] if r["executive_summary"] else ""
        results.append(MeetingListItemOut(
            id=r["id"],
            title=r["title"],
            meeting_date=r["meeting_date"],
            duration_minutes=r["duration_minutes"],
            participant_count=r["participant_count"],
            executive_summary_snippet=summary_snippet[:150],
            action_item_count=r["action_item_count"],
            decision_count=r["decision_count"],
            created_at=str(r["created_at"])
        ))
    return results

@router.get("/{meeting_id}", response_model=MeetingDetailOut)
def get_meeting_detail(meeting_id: str):
    conn = get_db_connection()
    meeting = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting record not found")

    transcripts_rows = conn.execute("SELECT * FROM transcripts WHERE meeting_id = ? ORDER BY sequence_order ASC", (meeting_id,)).fetchall()
    actions_rows = conn.execute("SELECT * FROM action_items WHERE meeting_id = ? ORDER BY created_at ASC", (meeting_id,)).fetchall()
    decisions_rows = conn.execute("SELECT * FROM decisions WHERE meeting_id = ? ORDER BY created_at ASC", (meeting_id,)).fetchall()
    speaker_rows = conn.execute("SELECT * FROM speaker_metrics WHERE meeting_id = ? ORDER BY word_count DESC", (meeting_id,)).fetchall()

    return MeetingDetailOut(
        id=meeting["id"],
        title=meeting["title"],
        meeting_date=meeting["meeting_date"],
        duration_minutes=meeting["duration_minutes"],
        raw_transcript=meeting["raw_transcript"],
        executive_summary=meeting["executive_summary"],
        participant_count=meeting["participant_count"],
        created_at=str(meeting["created_at"]),
        transcripts=[TranscriptTurnOut(**dict(r)) for r in transcripts_rows],
        action_items=[ActionItemOut(**dict(r)) for r in actions_rows],
        decisions=[DecisionOut(**dict(r)) for r in decisions_rows],
        speaker_metrics=[SpeakerMetricOut(**dict(r)) for r in speaker_rows]
    )

@router.delete("/{meeting_id}", status_code=204)
def delete_meeting(meeting_id: str):
    conn = get_db_connection()
    with conn:
        res = conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Meeting not found")
    return None

@router.patch("/{meeting_id}/action-items/{action_id}", response_model=ActionItemOut)
def update_action_item(meeting_id: str, action_id: str, payload: ActionItemUpdate):
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM action_items WHERE id = ? AND meeting_id = ?", (action_id, meeting_id)).fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    new_status = payload.status if payload.status is not None else item["status"]
    new_assignee = payload.assignee if payload.assignee is not None else item["assignee"]
    new_priority = payload.priority if payload.priority is not None else item["priority"]
    new_due_date = payload.due_date if payload.due_date is not None else item["due_date"]

    with conn:
        conn.execute("""
            UPDATE action_items
            SET status = ?, assignee = ?, priority = ?, due_date = ?
            WHERE id = ? AND meeting_id = ?
        """, (new_status, new_assignee, new_priority, new_due_date, action_id, meeting_id))

    updated = conn.execute("SELECT * FROM action_items WHERE id = ?", (action_id,)).fetchone()
    return ActionItemOut(**dict(updated))

@router.post("/{meeting_id}/action-items", response_model=ActionItemOut, status_code=201)
def add_action_item(meeting_id: str, payload: ActionItemCreate):
    conn = get_db_connection()
    meeting = conn.execute("SELECT id FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    new_id = str(uuid.uuid4())
    with conn:
        conn.execute("""
            INSERT INTO action_items (id, meeting_id, description, assignee, due_date, priority, status, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_id, meeting_id, payload.description, payload.assignee, payload.due_date, payload.priority, payload.status, payload.confidence_score))

    inserted = conn.execute("SELECT * FROM action_items WHERE id = ?", (new_id,)).fetchone()
    return ActionItemOut(**dict(inserted))

@router.get("/analytics/overview", response_model=AnalyticsOverviewOut)
def get_analytics_overview():
    conn = get_db_connection()
    total_meetings = conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
    total_action_items = conn.execute("SELECT COUNT(*) FROM action_items").fetchone()[0]
    completed_action_items = conn.execute("SELECT COUNT(*) FROM action_items WHERE status = 'COMPLETED'").fetchone()[0]
    total_decisions = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    total_speakers = conn.execute("SELECT COUNT(DISTINCT speaker_name) FROM speaker_metrics").fetchone()[0]

    completion_rate = round((completed_action_items / max(total_action_items, 1)) * 100, 1)

    recent_rows = conn.execute("""
        SELECT m.id, m.title, m.meeting_date, m.duration_minutes, m.participant_count, m.executive_summary, m.created_at,
               (SELECT COUNT(*) FROM action_items WHERE meeting_id = m.id) as action_item_count,
               (SELECT COUNT(*) FROM decisions WHERE meeting_id = m.id) as decision_count
        FROM meetings m
        ORDER BY m.created_at DESC
        LIMIT 5
    """).fetchall()

    recent_meetings = [
        MeetingListItemOut(
            id=r["id"],
            title=r["title"],
            meeting_date=r["meeting_date"],
            duration_minutes=r["duration_minutes"],
            participant_count=r["participant_count"],
            executive_summary_snippet=r["executive_summary"].split("\n")[0] if r["executive_summary"] else "",
            action_item_count=r["action_item_count"],
            decision_count=r["decision_count"],
            created_at=str(r["created_at"])
        )
        for r in recent_rows
    ]

    return AnalyticsOverviewOut(
        total_meetings=total_meetings,
        total_action_items=total_action_items,
        completed_action_items=completed_action_items,
        action_item_completion_rate=completion_rate,
        total_decisions=total_decisions,
        total_speakers=total_speakers,
        recent_meetings=recent_meetings
    )
