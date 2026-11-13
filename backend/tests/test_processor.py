import pytest
from app.engine.processor import (
    parse_transcript,
    extract_speaker_metrics,
    extract_action_items,
    extract_decisions,
    generate_executive_summary
)

SAMPLE_TRANSCRIPT = """
[00:00:15] Sarah Chen: Good morning everyone. Welcome to our Q3 Architecture and Scalability review.
[00:00:45] Marcus Vance: Thanks Sarah. On the database side, we decided to adopt PostgreSQL partitioned tables for the events stream.
[00:01:20] Elena Rostova: That is a solid choice. I will deploy the Redis caching cluster by next Friday to buffer peak traffic.
[00:02:00] Sarah Chen: Excellent. Marcus will migrate the user service schemas before end of sprint. This is critical for our Q3 timeline.
[00:02:40] David Kim: Action Item: audit our IAM permissions and rotate all service tokens by Wednesday.
[00:03:10] Marcus Vance: Agreed to allocate $15,000 budget for automated load testing infrastructure.
[00:03:45] Sarah Chen: Perfect. Let's make sure to prepare the staging benchmark report before tomorrow.
"""

def test_parse_transcript_formats():
    turns = parse_transcript(SAMPLE_TRANSCRIPT)
    assert len(turns) == 7
    assert turns[0].speaker == "Sarah Chen"
    assert turns[0].timestamp_str == "00:00:15"
    assert "Architecture" in turns[0].content

    # Test alternate format: Name (00:01:20): message
    alt_text = "Alice (00:01:20): Hello team!\nBob: Good day"
    alt_turns = parse_transcript(alt_text)
    assert len(alt_turns) == 2
    assert alt_turns[0].speaker == "Alice"
    assert alt_turns[0].timestamp_str == "00:01:20"
    assert alt_turns[1].speaker == "Bob"

def test_extract_speaker_metrics():
    turns = parse_transcript(SAMPLE_TRANSCRIPT)
    metrics = extract_speaker_metrics(turns)
    assert len(metrics) == 4
    speakers = {m["speaker_name"] for m in metrics}
    assert "Sarah Chen" in speakers
    assert "Marcus Vance" in speakers
    assert "Elena Rostova" in speakers
    assert "David Kim" in speakers

    total_pct = sum(m["talk_time_percentage"] for m in metrics)
    assert 99.0 <= total_pct <= 101.0

def test_extract_action_items():
    turns = parse_transcript(SAMPLE_TRANSCRIPT)
    actions = extract_action_items(turns)
    assert len(actions) >= 3

    # Check Elena's action item
    elena_action = next((a for a in actions if a["assignee"] == "Elena Rostova"), None)
    assert elena_action is not None
    assert "deploy the redis caching cluster" in elena_action["description"].lower()

    # Check David's action item
    david_action = next((a for a in actions if a["assignee"] == "David Kim"), None)
    assert david_action is not None
    assert "audit our iam permissions" in david_action["description"].lower()
    assert david_action["confidence_score"] >= 0.90

    # Check High priority detection on Marcus's task
    marcus_action = next((a for a in actions if a["assignee"] == "Marcus Vance"), None)
    if marcus_action:
        assert marcus_action["priority"] == "HIGH"

def test_extract_decisions():
    turns = parse_transcript(SAMPLE_TRANSCRIPT)
    decisions = extract_decisions(turns)
    assert len(decisions) >= 2

    # Check database decision
    db_decision = next((d for d in decisions if "postgresql" in d["decision_text"].lower()), None)
    assert db_decision is not None

    # Check budget decision
    budget_decision = next((d for d in decisions if "$15,000" in d["decision_text"] or "budget" in d["decision_text"].lower()), None)
    assert budget_decision is not None
    assert budget_decision["category"] in ["Budgetary", "Strategic"]

def test_executive_summary_generation():
    turns = parse_transcript(SAMPLE_TRANSCRIPT)
    decisions = extract_decisions(turns)
    actions = extract_action_items(turns)
    summary = generate_executive_summary("Q3 Architecture Sync", turns, decisions, actions)

    assert "Q3 Architecture Sync" in summary
    assert "Key Decisions" in summary
    assert "Immediate Action Items" in summary
    assert "Sarah Chen" in summary
