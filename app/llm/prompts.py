"""
All LLM prompt templates for MeetingAI.

Prompts are separated into system and user components.
Each function returns a (system_prompt, user_prompt) tuple.
"""


def meeting_summary_prompts(
    title: str, date: str, participants: str, transcript: str
) -> tuple[str, str]:
    system = """You are an expert meeting summarizer. Your job is to produce clear, concise meeting
summaries that capture the essential information discussed.

Rules:
- Write in past tense, third person
- Lead with the most important outcomes
- Group related topics together
- Keep the summary to 3-6 paragraphs
- Use plain, professional language
- Do not invent information not present in the transcript
- If the transcript is unclear or garbled, note that rather than guessing"""

    user = f"""Summarize the following meeting transcript. Focus on: key topics discussed,
conclusions reached, and any unresolved questions.

Meeting title: {title}
Date: {date}
Participants: {participants}

Transcript:
---
{transcript}
---

Provide a clear, structured summary."""

    return system, user


def action_item_prompts(participants: str, transcript: str) -> tuple[str, str]:
    system = """You are an expert at extracting action items from meeting transcripts.
An action item is a specific task that someone agreed to do.

Rules:
- Only extract explicit commitments, not vague intentions
- Include the assignee if mentioned (use the speaker's name)
- Include due dates only if explicitly stated
- Include a brief verbatim quote from the transcript as evidence
- Set priority based on urgency cues (ASAP/urgent = high, normal = medium, nice-to-have = low)
- If no clear action items exist, return an empty list

Respond with valid JSON only. No markdown, no explanation."""

    user = f"""Extract all action items from this meeting transcript.

Participants: {participants}

Transcript:
---
{transcript}
---

Respond with a JSON array:
[
  {{
    "description": "What needs to be done",
    "assignee": "Person name or null",
    "due_date": "YYYY-MM-DD or null",
    "priority": "low | medium | high",
    "source_quote": "Brief verbatim quote from transcript"
  }}
]"""

    return system, user


def decision_prompts(participants: str, transcript: str) -> tuple[str, str]:
    system = """You are an expert at identifying decisions made during meetings.
A decision is a conclusion or agreement the group reached on a specific topic.

Rules:
- Only extract explicit decisions, not suggestions or ideas still under discussion
- Note who was involved in making the decision
- Include the rationale if stated
- Include a brief verbatim quote as evidence
- If no clear decisions were made, return an empty list

Respond with valid JSON only."""

    user = f"""Extract all decisions made in this meeting transcript.

Participants: {participants}

Transcript:
---
{transcript}
---

Respond with a JSON array:
[
  {{
    "description": "What was decided",
    "participants": ["Person1", "Person2"],
    "rationale": "Why it was decided, or null",
    "source_quote": "Brief verbatim quote from transcript"
  }}
]"""

    return system, user


def incident_postmortem_prompts(
    title: str, severity: str, services: str, incident_text: str
) -> tuple[str, str]:
    system = """You are a senior site reliability engineer writing a postmortem for a production incident.
Your postmortems are thorough, blameless, and focused on systemic issues.

Rules:
- Write in past tense, third person
- Be specific about what happened and why
- Focus on systems and processes, not individual blame
- Executive summary: 2-4 sentences capturing what happened, impact, and resolution
- Root cause analysis: dig into the actual technical root cause, not just symptoms
- Do not invent information not present in the incident description"""

    user = f"""Write a postmortem for the following production incident.

Title: {title}
Severity: {severity}
Services affected: {services}

Incident description / logs:
---
{incident_text}
---

Provide:
1. EXECUTIVE_SUMMARY: A 2-4 sentence summary of the incident, its impact, and resolution.
2. ROOT_CAUSE_ANALYSIS: A detailed analysis of the technical root cause and contributing factors.

Format your response EXACTLY as:
EXECUTIVE_SUMMARY:
<summary text>

ROOT_CAUSE_ANALYSIS:
<rca text>"""

    return system, user


def incident_timeline_prompts(incident_text: str) -> tuple[str, str]:
    system = """You are an expert at reconstructing incident timelines from logs, alerts, and descriptions.
Extract a chronological sequence of events from the provided incident information.

Rules:
- Extract only events explicitly mentioned or strongly implied
- Include detection, escalation, mitigation, and resolution events
- Use event_type: "detection" | "escalation" | "mitigation" | "resolution" | "event"
- If a timestamp is mentioned, include it; otherwise omit occurred_at
- Return 3-10 events maximum

Respond with valid JSON only."""

    user = f"""Extract a timeline of events from this incident description.

Incident description / logs:
---
{incident_text}
---

Respond with a JSON array:
[
  {{
    "occurred_at": "ISO datetime or null",
    "description": "What happened at this point",
    "event_type": "detection | escalation | mitigation | resolution | event"
  }}
]"""

    return system, user


def incident_action_items_prompts(incident_text: str, rca: str) -> tuple[str, str]:
    system = """You are an expert at identifying remediation action items from incident postmortems.
Focus on preventing recurrence and improving reliability.

Rules:
- Extract concrete, actionable tasks (not vague intentions)
- Categorize each item: "prevention" | "detection" | "mitigation" | "process" | "documentation"
- Set priority based on severity of the gap being addressed
- Include assignee only if explicitly mentioned

Respond with valid JSON only."""

    user = f"""Extract remediation action items from this incident and root cause analysis.

Incident description:
---
{incident_text}
---

Root cause analysis:
---
{rca}
---

Respond with a JSON array:
[
  {{
    "description": "What needs to be done",
    "assignee": "Person or team name, or null",
    "priority": "low | medium | high",
    "category": "prevention | detection | mitigation | process | documentation"
  }}
]"""

    return system, user


def rag_qa_prompts(question: str, context_chunks: str) -> tuple[str, str]:
    system = """You are a knowledgeable engineering assistant that answers questions using provided context
excerpts from meetings, incidents, and architecture documents.

Rules:
- Answer based ONLY on the provided context excerpts
- Cite the source (meeting, incident, or document title) when referencing information
- If the context doesn't contain enough information to answer, say so clearly
- Be specific and direct
- Do not make up information that isn't in the provided excerpts"""

    user = f"""Answer the following question using the context excerpts below.

Question: {question}

Context (retrieved from meetings, incidents, and documents):
---
{context_chunks}
---

Each excerpt is labeled with its source type and title.

Provide a clear answer with references to the source material."""

    return system, user
