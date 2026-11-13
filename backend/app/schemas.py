from pydantic import BaseModel, Field
from typing import List, Optional

class ActionItemBase(BaseModel):
    description: str
    assignee: str
    due_date: Optional[str] = "Next Sprint"
    priority: str = "MEDIUM"
    status: str = "PENDING"
    confidence_score: float = 0.85

class ActionItemCreate(ActionItemBase):
    pass

class ActionItemUpdate(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None

class ActionItemOut(ActionItemBase):
    id: str
    meeting_id: str
    created_at: str

class DecisionOut(BaseModel):
    id: str
    meeting_id: str
    decision_text: str
    category: str
    rationale: Optional[str] = None
    timestamp_str: Optional[str] = None
    created_at: str

class SpeakerMetricOut(BaseModel):
    id: str
    meeting_id: str
    speaker_name: str
    turn_count: int
    word_count: int
    talk_time_percentage: float
    sentiment_tone: str

class TranscriptTurnOut(BaseModel):
    id: str
    meeting_id: str
    speaker: str
    timestamp_str: Optional[str] = None
    content: str
    sequence_order: int

class MeetingIngestRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    meeting_date: Optional[str] = None
    duration_minutes: Optional[int] = 45
    raw_transcript: str = Field(..., min_length=15)

class MeetingListItemOut(BaseModel):
    id: str
    title: str
    meeting_date: str
    duration_minutes: int
    participant_count: int
    executive_summary_snippet: str
    action_item_count: int
    decision_count: int
    created_at: str

class MeetingDetailOut(BaseModel):
    id: str
    title: str
    meeting_date: str
    duration_minutes: int
    raw_transcript: str
    executive_summary: str
    participant_count: int
    created_at: str
    transcripts: List[TranscriptTurnOut]
    action_items: List[ActionItemOut]
    decisions: List[DecisionOut]
    speaker_metrics: List[SpeakerMetricOut]

class AnalyticsOverviewOut(BaseModel):
    total_meetings: int
    total_action_items: int
    completed_action_items: int
    action_item_completion_rate: float
    total_decisions: int
    total_speakers: int
    recent_meetings: List[MeetingListItemOut]
