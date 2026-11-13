import re
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

class TranscriptTurn:
    def __init__(self, speaker: str, content: str, timestamp_str: Optional[str] = None, sequence: int = 0):
        self.speaker = speaker.strip()
        self.content = content.strip()
        self.timestamp_str = timestamp_str or ""
        self.sequence = sequence

def parse_transcript(raw_text: str) -> List[TranscriptTurn]:
    """
    Parses transcripts across standard formats:
    - [00:12:45] Alice: Hello team
    - Alice (00:12:45): Hello team
    - 00:12:45 - Bob: We should proceed
    - Charlie: I will deploy the build
    - [David]: Sounds good
    """
    lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]
    turns: List[TranscriptTurn] = []
    current_turn: Optional[TranscriptTurn] = None
    seq = 0

    # Pattern 1: [00:12:34] Alice: message or 00:12:34 Alice: message
    pattern_timed_bracket = re.compile(r'^(?:\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*[-–]?\s*)([A-Za-z0-9_\s\.\(\)]+?)(?:\s*\(.*?\))?:\s*(.+)$')
    # Pattern 2: Alice (00:12:34): message
    pattern_name_timed = re.compile(r'^([A-Za-z0-9_\s\.\-]+?)\s*\((?:(\d{1,2}:\d{2}(?::\d{2})?))\):\s*(.+)$')
    # Pattern 3: [Alice]: message or Alice: message
    pattern_simple_speaker = re.compile(r'^(?:\[([A-Za-z0-9_\s\.\-]+)\]|([A-Za-z0-9_\s\.\-]+)):\s*(.+)$')

    for line in lines:
        m1 = pattern_timed_bracket.match(line)
        if m1:
            seq += 1
            ts, spk, text = m1.group(1), m1.group(2).strip(), m1.group(3).strip()
            current_turn = TranscriptTurn(spk, text, ts, seq)
            turns.append(current_turn)
            continue

        m2 = pattern_name_timed.match(line)
        if m2:
            seq += 1
            spk, ts, text = m2.group(1).strip(), m2.group(2), m2.group(3).strip()
            current_turn = TranscriptTurn(spk, text, ts, seq)
            turns.append(current_turn)
            continue

        m3 = pattern_simple_speaker.match(line)
        if m3:
            seq += 1
            spk = (m3.group(1) or m3.group(2)).strip()
            text = m3.group(3).strip()
            current_turn = TranscriptTurn(spk, text, "", seq)
            turns.append(current_turn)
            continue

        # If line doesn't match a new speaker, append to previous turn if exists, else assign default speaker
        if current_turn:
            current_turn.content += " " + line
        else:
            seq += 1
            current_turn = TranscriptTurn("Speaker 1", line, "", seq)
            turns.append(current_turn)

    return turns

def extract_speaker_metrics(turns: List[TranscriptTurn]) -> List[Dict[str, Any]]:
    stats: Dict[str, Dict[str, Any]] = {}
    total_words = 0

    positive_keywords = {"agree", "great", "excellent", "aligned", "approved", "excited", "progress", "resolved", "solid", "fantastic"}
    critical_keywords = {"risk", "blocker", "concern", "issue", "bug", "delay", "failed", "critical", "warning", "bottleneck"}
    urgent_keywords = {"urgent", "asap", "deadline", "emergency", "immediately", "today"}

    for t in turns:
        spk = t.speaker
        words = len(t.content.split())
        total_words += words

        if spk not in stats:
            stats[spk] = {
                "turn_count": 0,
                "word_count": 0,
                "sentiment_score": 0,
                "urgent_hits": 0,
            }
        stats[spk]["turn_count"] += 1
        stats[spk]["word_count"] += words

        lower_text = t.content.lower()
        for w in positive_keywords:
            if w in lower_text:
                stats[spk]["sentiment_score"] += 1
        for w in critical_keywords:
            if w in lower_text:
                stats[spk]["sentiment_score"] -= 1
        for w in urgent_keywords:
            if w in lower_text:
                stats[spk]["urgent_hits"] += 1

    results = []
    for spk, data in stats.items():
        pct = round((data["word_count"] / max(total_words, 1)) * 100, 1)
        score = data["sentiment_score"]
        urgency = data["urgent_hits"]

        if urgency >= 2:
            tone = "Urgent / Focused"
        elif score > 1:
            tone = "Constructive / Collaborative"
        elif score < -1:
            tone = "Critical / Risk-Focused"
        else:
            tone = "Objective / Neutral"

        results.append({
            "speaker_name": spk,
            "turn_count": data["turn_count"],
            "word_count": data["word_count"],
            "talk_time_percentage": pct,
            "sentiment_tone": tone
        })

    results.sort(key=lambda x: x["word_count"], reverse=True)
    return results

def extract_action_items(turns: List[TranscriptTurn]) -> List[Dict[str, Any]]:
    action_items = []
    seen_descriptions = set()

    # Regex triggers for tasks
    action_triggers = [
        r'\b(?:i\s+will|i\'ll)\s+([^\.\?\!]+)',
        r'\b(?:we\s+need\s+to|let\'s|we\s+should)\s+([^\.\?\!]+)',
        r'\b(?:action\s+item|todo|task):\s*([^\.\?\!]+)',
        r'\b([A-Z][a-zA-Z]+)\s+(?:will|is\s+going\s+to|should|must|to)\s+([^\.\?\!]+)',
        r'\b(?:please|can\s+you)\s+([A-Z][a-zA-Z]+)?\s*([^\.\?\!]+)'
    ]

    due_patterns = [
        r'\b(?:by|before|due)\s+([A-Za-z]+day|[A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?|eod|tomorrow|next\s+week|end\s+of\s+sprint|\d{4}-\d{2}-\d{2})\b',
        r'\b(?:deadline(?:\s+is)?)\s+([^\,\.\;\!]+)'
    ]

    high_priority_words = {"urgent", "asap", "critical", "blocker", "highest", "immediately", "p0", "p1"}
    low_priority_words = {"eventually", "low priority", "nice to have", "backlog", "future"}

    known_speakers = {t.speaker for t in turns}

    for turn in turns:
        content = turn.content
        sentences = re.split(r'[\.\?\!\n]+', content)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 8:
                continue

            lower_sentence = sentence.lower()

            # Check if this sentence sounds like an action item
            matched = False
            task_desc = ""
            assignee = turn.speaker

            # 1. Direct explicit tags
            if "action item:" in lower_sentence or "todo:" in lower_sentence:
                task_desc = re.sub(r'^(?:action\s+item|todo):\s*', '', sentence, flags=re.IGNORECASE).strip()
                matched = True
            # 2. "I will / I'll"
            elif re.search(r'\b(?:i\s+will|i\'ll)\b', lower_sentence):
                m = re.search(r'\b(?:i\s+will|i\'ll)\s+(.+)', sentence, re.IGNORECASE)
                if m:
                    task_desc = m.group(1).strip()
                    assignee = turn.speaker
                    matched = True
            # 3. Third person: "Bob will update the schema"
            elif any(sentence.startswith(spk) for spk in known_speakers if spk != turn.speaker):
                for spk in known_speakers:
                    if sentence.startswith(spk):
                        m = re.search(rf'^{re.escape(spk)}\s+(?:will|to|should|needs\s+to)\s+(.+)', sentence, re.IGNORECASE)
                        if m:
                            task_desc = m.group(1).strip()
                            assignee = spk
                            matched = True
                            break
            # 4. "Let's / We need to"
            elif re.search(r'\b(?:we\s+need\s+to|let\'s\s+make\s+sure\s+to|we\s+should)\b', lower_sentence):
                m = re.search(r'\b(?:we\s+need\s+to|let\'s\s+make\s+sure\s+to|we\s+should)\s+(.+)', sentence, re.IGNORECASE)
                if m:
                    task_desc = m.group(1).strip()
                    assignee = turn.speaker
                    matched = True

            if matched and task_desc:
                # Clean description
                task_desc = re.sub(r'\s+', ' ', task_desc).strip()
                if len(task_desc) < 5 or task_desc.lower() in seen_descriptions:
                    continue
                seen_descriptions.add(task_desc.lower())

                # Detect Due Date
                due_date = "Next Sprint"
                for dp in due_patterns:
                    dm = re.search(dp, sentence, re.IGNORECASE)
                    if dm:
                        due_date = dm.group(1).strip().capitalize()
                        break

                # Detect Priority
                priority = "MEDIUM"
                if any(w in lower_sentence for w in high_priority_words):
                    priority = "HIGH"
                elif any(w in lower_sentence for w in low_priority_words):
                    priority = "LOW"

                # Confidence Score calculation
                confidence = 0.82
                if "action item" in lower_sentence or "todo" in lower_sentence:
                    confidence = 0.98
                elif "i will" in lower_sentence or "i'll" in lower_sentence:
                    confidence = 0.92
                elif due_date != "Next Sprint":
                    confidence = 0.88

                action_items.append({
                    "description": task_desc[:250],
                    "assignee": assignee,
                    "due_date": due_date,
                    "priority": priority,
                    "status": "PENDING",
                    "confidence_score": round(confidence, 2)
                })

    return action_items

def extract_decisions(turns: List[TranscriptTurn]) -> List[Dict[str, Any]]:
    decisions = []
    seen = set()

    decision_patterns = [
        (r'\b(?:we\s+decided\s+to|agreed\s+to|decision\s+is\s+to|unanimously\s+agreed\s+to)\s+([^\.\!\?]+)', "Strategic"),
        (r'\b(?:approved\s+the|sign\s+off\s+on|budget\s+approved\s+for)\s+([^\.\!\?]+)', "Budgetary"),
        (r'\b(?:moving\s+forward\s+with|we\s+will\s+adopt|selected)\s+([^\.\!\?]+)', "Architectural"),
        (r'\b(?:consensus\s+reached\s+on|rule\s+that|policy\s+is)\s+([^\.\!\?]+)', "Governance"),
        (r'\b(?:decision:\s*)([^\.\!\?]+)', "Operational"),
    ]

    for turn in turns:
        content = turn.content
        sentences = re.split(r'[\.\?\!\n]+', content)

        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue

            for pattern, default_cat in decision_patterns:
                m = re.search(pattern, s_clean, re.IGNORECASE)
                if m:
                    extracted = m.group(1).strip()
                    full_text = f"Agreed to {extracted}" if not extracted.lower().startswith(("agreed", "approved", "we decided")) else extracted
                    if full_text.lower() not in seen and len(full_text) > 10:
                        seen.add(full_text.lower())
                        decisions.append({
                            "decision_text": full_text[:250],
                            "category": default_cat,
                            "rationale": f"Discussed by {turn.speaker}: \"{s_clean}\"",
                            "timestamp_str": turn.timestamp_str or "Meeting Discussion"
                        })
                        break

    return decisions

def generate_executive_summary(title: str, turns: List[TranscriptTurn], decisions: List[Dict[str, Any]], action_items: List[Dict[str, Any]]) -> str:
    speakers = sorted(list({t.speaker for t in turns}))
    speaker_list = ", ".join(speakers) if speakers else "All Attendees"
    turn_count = len(turns)
    total_words = sum(len(t.content.split()) for t in turns)

    summary_lines = [
        f"### Executive Summary: {title}",
        f"**Participants:** {speaker_list} ({len(speakers)} total)",
        f"**Session Scope:** {turn_count} interactive turns exchanged across approximately {total_words} words.",
        "",
        "#### Key Discussion & Strategic Focus:"
    ]

    # Generate synopsis from top turning points
    significant_turns = [t for t in turns if len(t.content.split()) > 12]
    if significant_turns:
        for t in significant_turns[:3]:
            snippet = t.content if len(t.content) <= 120 else t.content[:117] + "..."
            summary_lines.append(f"- **{t.speaker}**: {snippet}")
    else:
        summary_lines.append("- Collaborative stakeholder alignment and operational cadence review.")

    summary_lines.append("")
    summary_lines.append("#### Key Decisions Confirmed:")
    if decisions:
        for d in decisions[:4]:
            summary_lines.append(f"- [{d['category']}] {d['decision_text']}")
    else:
        summary_lines.append("- Active discussions ongoing; consensus points to be ratified next session.")

    summary_lines.append("")
    summary_lines.append(f"#### Immediate Action Items ({len(action_items)} identified):")
    if action_items:
        for a in action_items[:5]:
            summary_lines.append(f"- **{a['assignee']}** ({a['priority']} priority, Due {a['due_date']}): {a['description']}")
    else:
        summary_lines.append("- No immediate blocking tasks assigned.")

    return "\n".join(summary_lines)
