# NoteVision — Agentic AI Notes Converter

> **Phase 2 — Agentic System Transformation**  
> Professional Practices in IT · NCEAC-Aligned Submission

**Team:** Shariq Usman · Azeem Choudhary · Muhammad Omer  
**Version:** 2.0 (Phase 2 — Agentic)  
**Stack:** Python · Streamlit · Google Gemini 2.0 Flash · google-genai · python-docx · Pillow

---

## Overview

NoteVision is an AI-powered web application that converts handwritten university notes — including complex mathematical formulas — into clean, editable digital documents.

Phase 2 transforms the original static tool (Phase 1) into a **Purely Agentic System**. Rather than responding to a single button click, the application now operates as an autonomous agent that perceives its environment, reasons about strategy, acts using discrete tools, reviews its own output, and delivers a refined result — with a mandatory human approval gate before any file is downloaded.

---

## Phase 1 → Phase 2: What Changed

| Dimension | Phase 1 | Phase 2 (Agentic) |
|---|---|---|
| **Control model** | User-driven (click → result) | System-driven agent loop |
| **Intelligence** | Static, single-pass prompt | Adaptive, multi-step reasoning |
| **Behaviour** | Reactive | Proactive and self-correcting |
| **Memory** | None | Short-term session + long-term history |
| **Self-review** | None | Built-in critique and refinement pass |
| **Human oversight** | Implicit | Explicit Human-in-the-Loop gate |
| **Decision logic** | Hardcoded prompt | Rule-based strategy selector driven by perception |
| **Transparency** | Spinner only | Full real-time activity log |

---

## Agentic Architecture

The system implements the canonical **Observe → Interpret → Decide → Act → Learn** cycle using five discrete tools orchestrated by the `NoteVisionAgent` class.

```
┌──────────────────────────────────────────────────────────────────┐
│                        NoteVisionAgent                           │
│                                                                  │
│  Image Upload                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────┐   PERCEIVE    ┌───────────────────────────┐    │
│  │  AgentTools  │ ────────────▶ │  Tool 1: assess_image     │    │
│  │              │               │  Quality · Math · Density │    │
│  │              │               └───────────┬───────────────┘    │
│  │              │                           │ ImageAssessment    │
│  │              │   DECIDE      ┌───────────▼───────────────┐    │
│  │              │ ────────────▶ │  Tool 2: select_strategy  │    │
│  │              │               │  Rule-based router        │    │
│  │              │               └───────────┬───────────────┘    │
│  │              │                           │ (strategy, prompt) │
│  │              │   ACT         ┌───────────▼───────────────┐    │
│  │              │ ────────────▶ │  Tool 3: convert          │    │
│  │              │               │  Gemini Vision + memory   │    │
│  │              │               └───────────┬───────────────┘    │
│  │              │                           │ raw markdown       │
│  │              │   CRITIQUE    ┌───────────▼───────────────┐    │
│  │              │ ────────────▶ │  Tool 4: critique         │    │
│  │              │               │  Self-review pass         │    │
│  │              │               └───────────┬───────────────┘    │
│  │              │                           │ critique text      │
│  │              │   LEARN       ┌───────────▼───────────────┐    │
│  │              │ ────────────▶ │  Tool 5: refine           │    │
│  │              │               │  Feedback-driven fix      │    │
│  └──────────────┘               └───────────┬───────────────┘    │
│                                             │ refined markdown   │
│                                  ┌──────────▼──────────────┐     │
│                                  │  AgentMemory.store()    │     │
│                                  │  Short-term + history   │     │
│                                  └──────────┬──────────────┘     │
│                                             │                    │
│                                  ┌──────────▼──────────────┐     │
│                                  │  Human-in-the-Loop Gate │     │
│                                  │  Accept · Reject · Re-run│    │
│                                  └─────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
```

### Agent Components

#### `AgentMemory`
Maintains two memory layers:
- **Short-term** — sliding window of the last 5 `ConversionResult` objects, injected as context into each new conversion prompt so the agent can adapt to patterns within a session.
- **Long-term** — full history log (persisted in Streamlit `session_state`), displayed in the Memory Dashboard sidebar.

#### `AgentTools`
Five independently callable, typed tools:

| Tool | Purpose | Type |
|---|---|---|
| `assess_image` | Perception — Gemini analyses quality, math presence, density | LLM |
| `select_strategy` | Decision — maps assessment to named strategy + prompt | Rule-based |
| `convert` | Action — Gemini Vision conversion with retry and memory context | LLM |
| `critique` | Self-review — Gemini evaluates its own output for gaps | LLM |
| `refine` | Learning — passes critique back to Gemini to fix issues found | LLM |

#### `NoteVisionAgent`
Top-level orchestrator. Calls tools in sequence, builds a typed `ConversionResult`, stores it in memory, and returns it to the UI.

#### Agent Type
**Goal-based learning agent** — it has an explicit quality goal (accurate, structured markdown) and learns within a session by incorporating prior results as context. Autonomy level is **semi-autonomous**: the agent completes the full pipeline independently but requires human approval before producing output.

---

## Strategies

The strategy selector produces five distinct behaviours based on the image assessment:

| Strategy | Trigger Condition | Behaviour |
|---|---|---|
| `math_focused` | Good quality + math detected | Prioritises LaTeX precision |
| `careful_reconstruction` | Poor quality or low confidence | Marks uncertain words, uses `[ILLEGIBLE]` |
| `structure_aware` | Diagrams detected | Generates Mermaid/ASCII representations |
| `detail_preserving` | Sparse handwriting | Preserves margin notes, underlines, emphasis |
| `standard` | Default case | Balanced conversion |

---

## Memory & Context

```
Short-term window (last 5 conversions)
  └─ Injected into each convert() call
       └─ Agent adapts prompt context to session history

Long-term log (all conversions)
  └─ Displayed in sidebar Memory Dashboard
       └─ Includes: timestamp, filename, quality, strategy, confidence
```

---

## Human-in-the-Loop

Every agent run concludes with an explicit human control gate. Downloads are locked until the user makes a choice:

- **Accept** — confirms the output and unlocks DOCX/Markdown downloads
- **Reject** — discards the result; user may upload a new image
- **Re-run** — triggers a fresh agent pass on the same image

This design satisfies the **ethical requirement for human oversight** in agentic AI systems: no autonomous action (file generation) occurs without informed user approval.

---

## Ethical Design

### Principles Applied

| Principle | Implementation |
|---|---|
| **Transparency** | Full real-time activity log; user sees every agent step |
| **Human control** | HITL gate; agent cannot produce downloadable output without approval |
| **Privacy** | No images or text are stored server-side; all processing is session-scoped and ephemeral |
| **Bias awareness** | Strategy selection is rule-based and deterministic, not learned from user data |
| **Non-deception** | Confidence score and critique are surfaced to the user, including when the agent is uncertain |

### ACM/IEEE Code of Ethics

The system was designed in alignment with the following principles from the ACM Code of Ethics and the IEEE Software Engineering Code:

- **ACM 1.1 — Contribute to society and human well-being**: NoteVision democratises access to note digitisation, supporting students with disabilities and those in remote learning environments.
- **ACM 1.6 — Respect privacy**: No user content is logged, retained, or transmitted beyond the active session and the Google Gemini API (governed by Google's data processing agreements).
- **IEEE 3.12 — Work within competence**: The system clearly marks low-confidence output with `(?)` annotations and `[ILLEGIBLE]` flags rather than fabricating content.

**Potential tension — ACM 2.9 (Design and implement systems that are robustly and usably secure)**: The current rate limiting is session-based and can be reset by refreshing the page. A production deployment would require persistent user authentication to enforce meaningful usage controls.

### Ethical Decision: Speed vs. Quality

A key Phase 1 decision was to use a single-pass, single-prompt approach — fast, but with no quality assurance. Phase 2 resolves this by introducing a critique-and-refine loop. This adds latency but directly serves the user's interest in accurate output, reflecting a professional ethics stance: responsibility to the user outweighs developer convenience.

### Ethical Agent Design

- **No addictive patterns**: The application has no engagement loop, push notifications, or incentive to over-use. Rate limiting actively discourages excessive consumption.
- **Deontological alignment**: The agent follows fixed rules (the strategy selector is deterministic) rather than optimising purely for outcome, ensuring predictable and auditable behaviour.
- **Utilitarian consideration**: The refinement step increases total processing time by ~30–40% but improves output quality for all users — an acceptable trade-off.

---

## Legal & IPR

### Intellectual Property
- All source code in this repository is original work authored by the team.
- The application does not reproduce, store, or redistribute third-party copyrighted content.
- User-uploaded images are processed transiently and are never persisted.

### Licensing
- **Application code**: For educational and non-commercial use. All rights reserved by the authors.
- **Dependencies** (Streamlit, google-genai, python-docx, Pillow): All carry permissive open-source licences (Apache 2.0, MIT, HPND) compatible with educational use.
- **Google Gemini API**: Usage is subject to Google's Terms of Service and the Generative AI Prohibited Use Policy.

### Data Protection
- No personally identifiable information (PII) is collected.
- No database or persistent storage is used; all state is session-scoped in Streamlit.
- Image data is transmitted to the Gemini API solely for processing and is not retained by this application.
- In a production context, full GDPR compliance would require a privacy notice, data processing agreement with Google, and a mechanism for users to request deletion of any retained data.

### Computer Crimes & Risks
The following risks were identified and mitigated:

| Risk | Mitigation |
|---|---|
| API key exposure | Key stored in Streamlit secrets, excluded from version control via `.gitignore` |
| API abuse / cost overrun | Session-based rate limiting (20/session, 10 s cooldown) + Google Cloud quota |
| Unauthorised content generation | HITL gate ensures a human reviews all output before it is produced as a file |
| Prompt injection via image content | System prompt is fixed; image content feeds the model as binary data, not text |

---

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| Frontend / Backend | Streamlit | 1.31.0 |
| AI Model | Google Gemini Vision | 2.0-flash |
| Image Processing | Pillow (PIL) | 10.2.0 |
| Document Export | python-docx | 1.1.0 |
| API Client | google-genai | 0.3.0 |

---

## Project Structure

```
NoteVision/
├── app.py              # Phase 2 agentic Streamlit UI
├── agent.py            # Agent core: AgentMemory, AgentTools, NoteVisionAgent
├── requirements.txt    # Python dependencies
├── .gitignore          # Excludes secrets and cache
├── .streamlit/
│   └── secrets.toml.example   # API key template
└── README.md           # This document
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API key
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml and add: GEMINI_API_KEY = "your-key-here"

# 3. Run the application
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### Cloud Deployment (Streamlit Cloud)
1. Push to a GitHub repository (ensure `secrets.toml` is in `.gitignore`)
2. Deploy via [share.streamlit.io](https://share.streamlit.io/)
3. Add `GEMINI_API_KEY` under **Settings → Secrets** in the Streamlit Cloud dashboard

---

## NCEAC Learning Domain Alignment

| CLO | Domain | Implementation |
|---|---|---|
| CLO 4 | Ethical Understanding | HITL gate, confidence transparency, critique disclosure, privacy-by-design |
| CLO 5 | Legal Awareness | IPR section, API ToS compliance, GDPR mindset, no data retention |
| CLO 6 | IPR & Contracts | Original authorship, dependency licensing review, API usage terms |
| CLO 8 | Industry & Career | Agentic AI architecture, professional code structure, tool-based design pattern |

---

## Comparative Analysis

```
┌────────────────────┬─────────────────────┬─────────────────────────────┐
│ Feature            │ Phase 1             │ Phase 2 (Agentic)           │
├────────────────────┼─────────────────────┼─────────────────────────────┤
│ Control            │ User-driven         │ System-driven               │
│ Intelligence       │ Static              │ Adaptive (5-tool pipeline)  │
│ Behaviour          │ Reactive            │ Proactive & self-correcting │
│ Memory             │ None                │ Short-term + long-term      │
│ Quality assurance  │ None                │ Critique + refinement pass  │
│ Human oversight    │ Implicit            │ Explicit HITL gate          │
│ Transparency       │ Spinner             │ Full real-time activity log │
│ Strategy selection │ Fixed               │ Dynamic, perception-driven  │
└────────────────────┴─────────────────────┴─────────────────────────────┘
```

---

*Built with Streamlit and Google Gemini Vision · NoteVision Phase 2 · Professional Practices in IT*
