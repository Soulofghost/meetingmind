const API_BASE = window.location.origin;

// State
let currentMeeting = null;
let activeMeetingsList = [];

// Sample Benchmarks
const SAMPLES = {
  cloud: {
    title: "Q3 Cloud Infrastructure & Architecture Sync",
    duration: 45,
    date: "2026-11-12",
    transcript: `[00:00:15] Sarah Chen: Good morning everyone. Welcome to our Q3 Architecture and Scalability review.
[00:00:45] Marcus Vance: Thanks Sarah. On the database side, we decided to adopt PostgreSQL partitioned tables for the high-throughput events stream.
[00:01:20] Elena Rostova: That is a solid choice. I will deploy the Redis caching cluster by next Friday to buffer peak traffic.
[00:02:00] Sarah Chen: Excellent. Marcus will migrate the user service schemas before end of sprint. This is critical for our Q3 timeline.
[00:02:40] David Kim: Action Item: audit our IAM permissions and rotate all service tokens by Wednesday.
[00:03:10] Marcus Vance: Agreed to allocate $15,000 budget for automated load testing infrastructure.
[00:03:45] Sarah Chen: Perfect. Let's make sure to prepare the staging benchmark report before tomorrow.`
  },
  board: {
    title: "Executive Strategy & Capital Allocation",
    duration: 60,
    date: "2026-11-10",
    transcript: `[00:02:10] Victoria Sterling: The board is convened. Let us review the capital allocation for international expansion.
[00:03:00] Arthur Pendelton: Our financial model indicates a 32% margin in European enterprise accounts. We decided to expand into the DACH region by Q1.
[00:04:15] Victoria Sterling: Approved the $250,000 preliminary marketing and compliance budget for European headquarters setup.
[00:05:00] Michael Zhao: I will finalize the local entity incorporation filings with counsel before end of month.
[00:05:40] Victoria Sterling: Action Item: Arthur will deliver the finalized hiring plan for regional directors by Friday.`
  },
  product: {
    title: "Product Launch Cadence & Security Review",
    duration: 30,
    date: "2026-11-13",
    transcript: `[00:01:00] Jessica Day: Team, we are two weeks out from the v2.0 general availability release.
[00:01:45] Tariq Mansoor: The vulnerability assessment on the payment gateway passed with zero critical CVEs.
[00:02:30] Jessica Day: That is fantastic news. We decided to freeze the feature branch this Wednesday at midnight.
[00:03:10] Tariq Mansoor: I will run the final penetration test and verify automated failover by Thursday.
[00:03:50] Jessica Day: Action Item: coordinate with customer success to distribute the release notes by Friday morning.`
  }
};

// DOM Elements
const kpiMeetings = document.getElementById("kpi-meetings");
const kpiActions = document.getElementById("kpi-actions");
const kpiDecisions = document.getElementById("kpi-decisions");
const kpiRate = document.getElementById("kpi-rate");

const meetingList = document.getElementById("meeting-list");
const archiveSearch = document.getElementById("archive-search");
const btnNewMeeting = document.getElementById("btn-new-meeting");

const ingestPanel = document.getElementById("ingest-panel");
const detailPanel = document.getElementById("detail-panel");

const ingestForm = document.getElementById("ingest-form");
const sampleSelect = document.getElementById("sample-select");
const inputTitle = document.getElementById("meeting-title");
const inputDate = document.getElementById("meeting-date");
const inputDuration = document.getElementById("meeting-duration");
const inputTranscript = document.getElementById("raw-transcript");
const btnClearIngest = document.getElementById("btn-clear-ingest");

const detailTitle = document.getElementById("detail-title");
const detailDate = document.getElementById("detail-date");
const detailDuration = document.getElementById("detail-duration");
const detailAttendees = document.getElementById("detail-attendees");
const detailSummaryContent = document.getElementById("detail-summary-content");
const actionItemsList = document.getElementById("action-items-list");
const decisionsList = document.getElementById("decisions-list");
const speakersList = document.getElementById("speakers-list");
const transcriptStream = document.getElementById("transcript-stream");
const actionTabCount = document.getElementById("action-tab-count");
const decisionTabCount = document.getElementById("decision-tab-count");

const btnExportMarkdown = document.getElementById("btn-export-markdown");
const btnDeleteMeeting = document.getElementById("btn-delete-meeting");

// Modal Elements
const taskModal = document.getElementById("task-modal");
const btnAddActionModal = document.getElementById("btn-add-action-modal");
const btnCloseModal = document.getElementById("btn-close-modal");
const btnCancelTask = document.getElementById("btn-cancel-task");
const manualTaskForm = document.getElementById("manual-task-form");

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  // Set default date
  inputDate.value = new Date().toISOString().split("T")[0];
  
  loadAnalytics();
  loadMeetings();
  setupEventListeners();
});

function setupEventListeners() {
  btnNewMeeting.addEventListener("click", showIngestPanel);
  btnClearIngest.addEventListener("click", () => {
    ingestForm.reset();
    inputDate.value = new Date().toISOString().split("T")[0];
  });

  sampleSelect.addEventListener("change", (e) => {
    const val = e.target.value;
    if (SAMPLES[val]) {
      const s = SAMPLES[val];
      inputTitle.value = s.title;
      inputDate.value = s.date;
      inputDuration.value = s.duration;
      inputTranscript.value = s.transcript;
    }
  });

  ingestForm.addEventListener("submit", handleIngestSubmit);

  archiveSearch.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    const filtered = activeMeetingsList.filter(m => 
      m.title.toLowerCase().includes(q) || (m.executive_summary_snippet && m.executive_summary_snippet.toLowerCase().includes(q))
    );
    renderMeetingList(filtered);
  });

  // Tab Switching
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.dataset.tab;
      document.getElementById(targetId).classList.add("active");
    });
  });

  // Export
  btnExportMarkdown.addEventListener("click", exportMarkdown);

  // Delete
  btnDeleteMeeting.addEventListener("click", deleteCurrentMeeting);

  // Modal Handlers
  btnAddActionModal.addEventListener("click", () => taskModal.classList.remove("hidden"));
  btnCloseModal.addEventListener("click", () => taskModal.classList.add("hidden"));
  btnCancelTask.addEventListener("click", () => taskModal.classList.add("hidden"));
  manualTaskForm.addEventListener("submit", handleManualTaskSubmit);
}

async function loadAnalytics() {
  try {
    const res = await fetch(`${API_BASE}/api/meetings/analytics/overview`);
    if (!res.ok) return;
    const data = await res.json();
    kpiMeetings.textContent = data.total_meetings;
    kpiActions.textContent = data.total_action_items;
    kpiDecisions.textContent = data.total_decisions;
    kpiRate.textContent = `${data.action_item_completion_rate}%`;
  } catch (err) {
    console.error("Failed to load analytics:", err);
  }
}

async function loadMeetings() {
  try {
    const res = await fetch(`${API_BASE}/api/meetings`);
    if (!res.ok) throw new Error("Failed to load meetings");
    activeMeetingsList = await res.json();
    renderMeetingList(activeMeetingsList);

    // Auto-select first meeting if exists and nothing is selected
    if (activeMeetingsList.length > 0 && !currentMeeting) {
      loadMeetingDetail(activeMeetingsList[0].id);
    }
  } catch (err) {
    meetingList.innerHTML = `<div class="empty-state">No archived meetings found.</div>`;
  }
}

function renderMeetingList(list) {
  if (list.length === 0) {
    meetingList.innerHTML = `<div class="empty-state" style="padding:1rem;color:var(--text-muted);font-size:0.8rem;">No meetings matched.</div>`;
    return;
  }

  meetingList.innerHTML = list.map(m => `
    <div class="archive-card ${currentMeeting && currentMeeting.id === m.id ? 'active' : ''}" onclick="loadMeetingDetail('${m.id}')">
      <div class="archive-card-title">${escapeHtml(m.title)}</div>
      <div class="archive-card-meta">
        <span>${m.meeting_date}</span>
        <span>${m.action_item_count} actions · ${m.decision_count} decisions</span>
      </div>
    </div>
  `).join("");
}

async function handleIngestSubmit(e) {
  e.preventDefault();
  const submitBtn = document.getElementById("btn-submit-ingest");
  submitBtn.disabled = true;
  submitBtn.textContent = "Processing Extraction Engine...";

  const payload = {
    title: inputTitle.value.trim(),
    meeting_date: inputDate.value || undefined,
    duration_minutes: parseInt(inputDuration.value, 10) || 45,
    raw_transcript: inputTranscript.value.trim()
  };

  try {
    const res = await fetch(`${API_BASE}/api/meetings/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Synthesis Failed: ${err.detail || "Unknown error"}`);
      return;
    }

    const meetingData = await res.json();
    await loadMeetings();
    await loadAnalytics();
    displayMeetingDetail(meetingData);
  } catch (err) {
    alert(`Request error: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Synthesize Meeting Intelligence";
  }
}

async function loadMeetingDetail(id) {
  try {
    const res = await fetch(`${API_BASE}/api/meetings/${id}`);
    if (!res.ok) throw new Error("Failed to fetch meeting");
    const data = await res.json();
    displayMeetingDetail(data);
  } catch (err) {
    console.error(err);
  }
}

function displayMeetingDetail(meeting) {
  currentMeeting = meeting;
  ingestPanel.classList.add("hidden");
  detailPanel.classList.remove("hidden");

  // Highlight card in list
  renderMeetingList(activeMeetingsList);

  // Meta
  detailTitle.textContent = meeting.title;
  detailDate.textContent = meeting.meeting_date;
  detailDuration.textContent = `${meeting.duration_minutes} Mins`;
  detailAttendees.textContent = `${meeting.participant_count} Participants`;

  actionTabCount.textContent = meeting.action_items.length;
  decisionTabCount.textContent = meeting.decisions.length;

  // Executive Summary rendering
  renderSummaryHtml(meeting.executive_summary);

  // Action Items rendering
  renderActionItems(meeting.action_items);

  // Decisions rendering
  renderDecisions(meeting.decisions);

  // Speakers rendering
  renderSpeakers(meeting.speaker_metrics);

  // Full Transcript
  renderTranscript(meeting.transcripts);
}

function renderSummaryHtml(summaryText) {
  // Convert basic markdown format to HTML
  const lines = summaryText.split("\n");
  let html = "";
  let inList = false;

  for (const line of lines) {
    if (line.startsWith("### ")) {
      if (inList) { html += "</ul>"; inList = false; }
      html += `<h3>${escapeHtml(line.replace("### ", ""))}</h3>`;
    } else if (line.startsWith("#### ")) {
      if (inList) { html += "</ul>"; inList = false; }
      html += `<h4>${escapeHtml(line.replace("#### ", ""))}</h4>`;
    } else if (line.startsWith("- ")) {
      if (!inList) { html += "<ul>"; inList = true; }
      const item = line.replace("- ", "");
      html += `<li>${formatBold(escapeHtml(item))}</li>`;
    } else if (line.trim()) {
      if (inList) { html += "</ul>"; inList = false; }
      html += `<p style="margin-bottom:0.5rem;color:var(--text-muted);">${formatBold(escapeHtml(line))}</p>`;
    }
  }
  if (inList) html += "</ul>";
  detailSummaryContent.innerHTML = html;
}

function formatBold(str) {
  return str.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}

function renderActionItems(items) {
  if (items.length === 0) {
    actionItemsList.innerHTML = `<div style="grid-column: 1/-1; color: var(--text-muted); padding: 1rem;">No action items detected for this meeting.</div>`;
    return;
  }

  actionItemsList.innerHTML = items.map(item => `
    <div class="action-card ${item.status === 'COMPLETED' ? 'completed' : ''}">
      <div class="action-header">
        <span class="priority-tag ${item.priority}">${item.priority}</span>
        <span style="font-size:0.75rem; color:var(--text-dim);">Due: <strong>${escapeHtml(item.due_date || 'Next Sprint')}</strong></span>
      </div>
      <div class="action-desc">${escapeHtml(item.description)}</div>
      <div class="action-footer">
        <span>Owner: <strong style="color:var(--text-main);">${escapeHtml(item.assignee)}</strong></span>
        <button class="status-toggle-btn ${item.status === 'COMPLETED' ? 'done' : ''}" onclick="toggleActionStatus('${item.id}', '${item.status}')">
          ${item.status === 'COMPLETED' ? '✓ Completed' : '○ Mark Done'}
        </button>
      </div>
    </div>
  `).join("");
}

async function toggleActionStatus(actionId, currentStatus) {
  if (!currentMeeting) return;
  const newStatus = currentStatus === "COMPLETED" ? "PENDING" : "COMPLETED";

  try {
    const res = await fetch(`${API_BASE}/api/meetings/${currentMeeting.id}/action-items/${actionId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      await loadMeetingDetail(currentMeeting.id);
      await loadAnalytics();
    }
  } catch (err) {
    console.error("Status toggle error:", err);
  }
}

function renderDecisions(decisions) {
  if (decisions.length === 0) {
    decisionsList.innerHTML = `<div style="color:var(--text-muted); padding:1rem;">No explicit decisions recorded in this session.</div>`;
    return;
  }

  decisionsList.innerHTML = decisions.map(d => `
    <div class="decision-card">
      <div class="decision-meta">
        <span class="category-tag">${escapeHtml(d.category)} Decision</span>
        <span style="color:var(--text-dim);">${escapeHtml(d.timestamp_str || 'Session Alignment')}</span>
      </div>
      <div class="decision-text">${escapeHtml(d.decision_text)}</div>
      <div class="decision-rationale">${escapeHtml(d.rationale || '')}</div>
    </div>
  `).join("");
}

function renderSpeakers(speakers) {
  if (speakers.length === 0) {
    speakersList.innerHTML = `<div style="color:var(--text-muted); padding:1rem;">No speaker dialogue breakdown available.</div>`;
    return;
  }

  speakersList.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Participant</th>
          <th>Talk Time Share</th>
          <th>Word Count</th>
          <th>Turn Frequency</th>
          <th>Tone Evaluation</th>
        </tr>
      </thead>
      <tbody>
        ${speakers.map(s => `
          <tr>
            <td><strong style="color:var(--gold-primary);">${escapeHtml(s.speaker_name)}</strong></td>
            <td style="min-width:180px;">
              <span>${s.talk_time_percentage}%</span>
              <div class="bar-wrap">
                <div class="bar-fill" style="width: ${s.talk_time_percentage}%;"></div>
              </div>
            </td>
            <td>${s.word_count.toLocaleString()} words</td>
            <td>${s.turn_count} turns</td>
            <td><span class="badge-pill" style="font-size:0.65rem;">${escapeHtml(s.sentiment_tone)}</span></td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderTranscript(turns) {
  transcriptStream.innerHTML = turns.map(t => `
    <div class="transcript-turn">
      <div class="turn-header">
        <span class="turn-speaker">${escapeHtml(t.speaker)}</span>
        <span class="turn-time">${escapeHtml(t.timestamp_str || '')}</span>
      </div>
      <div class="turn-content">${escapeHtml(t.content)}</div>
    </div>
  `).join("");
}

function showIngestPanel() {
  currentMeeting = null;
  detailPanel.classList.add("hidden");
  ingestPanel.classList.remove("hidden");
  renderMeetingList(activeMeetingsList);
}

async function handleManualTaskSubmit(e) {
  e.preventDefault();
  if (!currentMeeting) return;

  const desc = document.getElementById("task-desc").value.trim();
  const assignee = document.getElementById("task-assignee").value.trim();
  const due = document.getElementById("task-due").value.trim();
  const priority = document.getElementById("task-priority").value;

  const payload = {
    description: desc,
    assignee: assignee,
    due_date: due,
    priority: priority,
    status: "PENDING",
    confidence_score: 1.0
  };

  try {
    const res = await fetch(`${API_BASE}/api/meetings/${currentMeeting.id}/action-items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      taskModal.classList.add("hidden");
      manualTaskForm.reset();
      await loadMeetingDetail(currentMeeting.id);
      await loadAnalytics();
    }
  } catch (err) {
    alert("Failed to create task");
  }
}

async function deleteCurrentMeeting() {
  if (!currentMeeting) return;
  if (!confirm(`Are you sure you want to delete "${currentMeeting.title}"?`)) return;

  try {
    const res = await fetch(`${API_BASE}/api/meetings/${currentMeeting.id}`, { method: "DELETE" });
    if (res.ok) {
      currentMeeting = null;
      await loadMeetings();
      await loadAnalytics();
      showIngestPanel();
    }
  } catch (err) {
    alert("Delete failed");
  }
}

function exportMarkdown() {
  if (!currentMeeting) return;
  const content = `# ${currentMeeting.title}
Date: ${currentMeeting.meeting_date} | Duration: ${currentMeeting.duration_minutes} Mins | Attendees: ${currentMeeting.participant_count}

${currentMeeting.executive_summary}

## All Ratified Decisions
${currentMeeting.decisions.map(d => `- [${d.category}] ${d.decision_text} (${d.timestamp_str || 'Discussion'})`).join('\n')}

## All Tracked Action Items
${currentMeeting.action_items.map(a => `- [${a.status === 'COMPLETED' ? 'x' : ' '}] **${a.assignee}** (${a.priority} Priority, Due: ${a.due_date}): ${a.description}`).join('\n')}
`;

  const blob = new Blob([content], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${currentMeeting.title.toLowerCase().replace(/[^a-z0-9]/g, "_")}_summary.md`;
  a.click();
  URL.revokeObjectURL(url);
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
