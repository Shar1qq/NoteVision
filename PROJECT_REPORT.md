# NoteVision Agent — Phase 2 Project Report
## Professional Practices in IT

---

## PROJECT OVERVIEW

**Project Name:** NoteVision Agent  
**Phase:** 2 — Agentic AI System with Ethical & Professional Design  
**Course:** Professional Practices in IT  
**Technology Stack:** Python · Streamlit · Google Gemini 2.5 Flash · Vertex AI · python-docx · PIL  
**Deployment:** Streamlit Cloud (remote accessible)  
**Authentication:** Google Cloud Service Account (Vertex AI)

---

## PHASE 1 RECAP — WHERE WE STARTED

### Problem Statement
University students spend hours manually transcribing handwritten lecture notes into digital formats. Manual transcription is error-prone, time-consuming, and inaccessible for students with disabilities or those who cannot type quickly.

### Phase 1 Solution
A static Streamlit web application that:
- Accepted JPG/PNG uploads of handwritten notes
- Sent the image to Google Gemini Vision API with a single fixed prompt
- Returned Markdown output with LaTeX support
- Allowed export as DOCX

### Phase 1 Limitations
- Single generic prompt for all image types (no adaptation)
- No image quality assessment before conversion
- No output validation or quality feedback loop
- No memory across multiple conversions
- No autonomy — user manually judges output quality
- Zero ethical safeguards (no consent, no safety screening)
- No transparency about AI decisions or limitations

---

## PHASE 2 — THE AGENTIC TRANSFORMATION

### What Changed
Phase 1 was a **reactive tool** — the user drives every decision. Phase 2 is a **proactive agent** — it perceives the image, makes autonomous decisions about strategy, converts, critiques its own output, refines it, and presents results for human approval.

### The 6-Step Agentic Pipeline

**Step 0 — Ethical Safety Screening (HITL Gate 1)**
Before any processing begins, the agent screens the image for sensitive content using Google Gemini Vision. If a concern is detected, the pipeline halts and the user must acknowledge before proceeding.

**Step 1 — Perceive (assess_image)**
The agent analyses the image quality, detects mathematical content, diagrams, and handwriting density. Returns a structured `ImageAssessment` dataclass with: quality, has_math, has_diagrams, handwriting_density, estimated_confidence, notes.

**Step 2 — Decide (select_strategy)**
Using rule-based deterministic logic (no LLM), the agent maps the assessment to one of 6 strategies. This is auditable — the agent can always explain why it chose a strategy.

**Step 3 — Act (convert)**
Calls Google Gemini 2.5 Flash via Vertex AI with the selected strategy prompt and memory context injected. Includes retry logic with exponential backoff (3 attempts).

**Step 4 — Critique (critique)**
The agent reviews its own output, identifying issues like broken LaTeX, missing sections, or structural errors. Returns a concise critique report.

**Step 5 — Refine (refine)**
If critique identifies real issues, the agent sends critique + original image back to Gemini for a corrected version. If output is already good, refinement is skipped.

**HITL Gate 2 — Output Approval**
User reviews refined output, self-critique, activity log, and ethics tab. Must explicitly Accept, Reject, or Re-run before any download is unlocked.

---

## THE 6 CONVERSION STRATEGIES

### 1. math_and_diagrams (Highest Priority)
- **Triggered by:** has_math = true AND has_diagrams = true
- **Behaviour:** Renders all math as LaTeX (inline $ or block $$) AND generates Mermaid xychart-beta blocks for every scientific graph/plot, with 12 data points starting from origin (0,0) for smooth curves. Two-curve graphs get two line entries.
- **Example use case:** Chemistry notes with equations AND adsorption isotherm graphs

### 2. math_focused
- **Triggered by:** has_math = true AND quality = "good"
- **Behaviour:** Deep focus on precise LaTeX — superscripts, subscripts, Greek letters, block equations. No diagram rendering.
- **Example use case:** Pure mathematics or physics formulae notes

### 3. careful_reconstruction
- **Triggered by:** quality = "poor" OR estimated_confidence < 0.4
- **Behaviour:** Attempts best-effort transcription, marks uncertain words with (?), inserts [ILLEGIBLE] for unreadable sections. Prefers accuracy over completeness.
- **Example use case:** Low-resolution photos, blurry or faded handwriting

### 4. structure_aware
- **Triggered by:** has_diagrams = true (without math)
- **Behaviour:** Flowcharts and mind-maps rendered as Mermaid flowchart TD blocks. Scientific plots rendered as Mermaid xychart-beta. All arrows, labels, and relationships preserved.
- **Example use case:** Process flow diagrams, concept maps, network diagrams

### 5. detail_preserving
- **Triggered by:** handwriting_density = "sparse"
- **Behaviour:** Every word is treated as significant. Preserves margin annotations, underlines, emphasis. Uses blockquotes for margin notes.
- **Example use case:** Annotated lecture slides with sparse handwriting

### 6. standard
- **Triggered by:** All other cases (fallback)
- **Behaviour:** Clean markdown with standard heading, bullet, and formatting rules.
- **Example use case:** Regular dense lecture notes with no special features

---

## ETHICAL SAFETY GATE — 4 CONCERN TYPES

The safety_check tool uses Google Gemini Vision to screen every uploaded image before processing. Returns a structured SafetyResult dataclass.

### Concern Types
1. **exam_paper** — Active exam or test with visible questions/answers (academic integrity violation)
2. **personal_data** — Medical records, legal documents, personal ID information (data privacy)
3. **confidential** — Documents explicitly labelled CONFIDENTIAL or RESTRICTED (corporate/legal)
4. **inappropriate** — Clearly harmful, offensive, or illegal content

### When Triggered
- Pipeline halts immediately at Step 0
- User sees amber warning box showing concern type, explanation, and recommendation
- Two choices: "Acknowledge & Take Responsibility" (proceed) or "Cancel — Do Not Process" (abort)
- If user acknowledges, pipeline proceeds with the concern noted in the Ethics tab

### Fallback Behaviour
If the safety screening LLM call itself fails, the gate defaults to `is_safe = True` to prevent the pipeline from being permanently blocked by a network error. This is a deliberate design decision prioritising availability while still providing the screening layer.

---

## MEMORY ARCHITECTURE

### Short-Term Memory (AgentMemory.agent_short_term)
- Stores the last 5 conversion results
- Injected as context into each new conversion prompt
- Ensures consistent formatting, LaTeX style, and heading structure across multiple pages of the same notes
- GDPR consideration: cleared on Streamlit session refresh

### Long-Term Memory (AgentMemory.agent_history)
- Stores all conversions from the current session
- Displayed in sidebar as "Recent History" with filename, quality, strategy, confidence
- Acts as an audit trail for the entire session
- Stored in Streamlit session_state (browser only — never sent to any server)

---

## HUMAN-IN-THE-LOOP (HITL) DESIGN

### Gate 1 — Ethical Safety Screening
- **Location:** Step 0, before any processing
- **Purpose:** Prevent processing of sensitive, confidential, or harmful content
- **User control:** Full — can cancel at any time
- **ACM/IEEE alignment:** §1.6 (Privacy), §2.9 (Inclusion)

### Gate 2 — Output Approval
- **Location:** After all 5 pipeline steps complete
- **Purpose:** Ensure human reviews and approves AI output before use
- **User control:** Accept / Reject / Re-run
- **Download lock:** Markdown and DOCX downloads disabled until user explicitly accepts
- **ACM/IEEE alignment:** §2.5 (Thorough evaluation), §3.1 (Know limitations)

### Design Principle
The agent suggests — the human decides. This is a professional obligation, not a UX convenience. For academic content, errors have real consequences (wrong grades, misunderstanding). No output is ever released without explicit human approval.

---

## TRANSPARENCY FEATURES

### Strategy Badge
Displayed after each run showing which strategy was selected and why the agent chose it.

### Confidence Meter
Visual colour-coded meter (green > 70%, amber 40–70%, red < 40%) showing the agent's self-assessed confidence. Displayed prominently so users know when to be cautious.

### Activity Log Tab
Full chronological log of every decision the agent made: safety screening result, assessment values, strategy selected, critique result, refinement applied or skipped, confidence score.

### Ethics & Compliance Tab
Per-run display showing:
- Safety screening result with concern type
- ACM/IEEE principles applied to this specific run
- Data handling transparency statement
- Bias disclosure notice
- Recommendation for human review

---

## PROFESSIONAL ETHICS — ACM/IEEE CODE OF ETHICS

### Principles Applied

**§1.1 — Contribute to society and human wellbeing**
NoteVision converts inaccessible handwritten content into structured, searchable digital text. It improves academic accessibility for students with writing disabilities, non-native speakers, and anyone who cannot type quickly enough during lectures.

**§1.6 — Respect privacy**
Zero persistent storage design. Images are processed in memory within the API call and discarded immediately after. No user data is written to disk or database. Session memory exists only in the browser and is cleared on refresh. This is GDPR-aligned by design.

**§2.5 — Give comprehensive and thorough evaluations**
The critique + refinement loop validates output quality before delivery. The confidence score is communicated honestly with colour coding. Limitations are disclosed in the Ethics tab.

**§2.9 — Design and implement systems that are robustly and usably secure**
Privacy consent gate, ethical safety screening, rate limiting (20 conversions per session, 10 second cooldown), and service account authentication (not plain API keys) collectively implement defence-in-depth security.

**§3.1 — Understand and respect existing rules pertaining to professional work**
Semi-autonomous design acknowledges AI limitations. Confidence score, HITL gate, and disclaimer that output requires human verification all reflect professional accountability.

### Potential Violation Acknowledged

**§2.5 — Bias in evaluation**
The LLM (Gemini 2.5 Flash) may produce inconsistent or lower-quality results for non-standard handwriting styles, non-English scripts, or content from cultures underrepresented in training data. This is openly disclosed in the Ethics tab. Mitigations: confidence scoring, mandatory HITL approval, re-run option always available.

---

## ETHICAL THEORIES APPLIED

### Utilitarianism — "Greatest good for the greatest number"
The ethical safety gate protects all users. If one student uploads a confidential exam paper, the gate prevents the system from being misused — protecting academic integrity for the entire institution. Maximum benefit, minimum harm.

### Deontology — "Act from duty, regardless of outcome"
Privacy is a professional duty (ACM §1.6), not a feature to be traded away for performance. We do NOT store images even though caching would improve speed and reduce API costs. The duty to protect privacy overrides engineering convenience.

### Human-Centered Design — "Design for the user, not the metric"
Every interface decision prioritises user control and transparency over automation efficiency. No dark patterns, no hidden actions, no auto-processing without consent, no engagement traps.

### Avoiding Addictive Design
No score gamification, no streak incentives, no auto-submit. Every action requires deliberate user intent. The system augments human academic work rather than creating dependency.

---

## ETHICS VS. MORALS — APPLIED

### Morals (Personal Belief)
"AI should not fully replace human judgment in academic settings" — this personal belief directly shaped the decision to make the system semi-autonomous rather than fully automated.

### Ethics (Professional Standard)
ACM §1.6 mandates privacy protection — this professional standard required zero data storage regardless of engineering convenience. The moral belief and the professional standard aligned in this case, reinforcing the design decision.

### Real Tradeoffs Made
- Skipping the critique loop would have been faster → we kept it (quality obligation)
- Storing images would have improved caching → we rejected it (privacy duty)
- Full automation would have been more "impressive" → we chose HITL (professional responsibility)

---

## 4-STEP ETHICAL DECISION MODEL

### Step 1 — Identify the Issue
AI may produce inaccurate or biased output for academic content. Users may upload sensitive documents (exam papers, medical records, confidential files) without realising the legal and ethical implications.

### Step 2 — Analyse Stakeholders
- **Students:** Need accurate transcription — errors affect academic performance
- **Educators:** Need to trust that AI tools used by students maintain academic integrity
- **Society:** Needs AI systems that are transparent, controllable, and ethically designed
- **Developers:** Need to meet professional obligations under ACM/IEEE codes

### Step 3 — Evaluate Alternatives
1. Full automation: Fast, but no oversight. Unacceptable for academic content → **rejected**
2. Manual only (Phase 1): Safe, but not innovative. Misses the project objective → **rejected**
3. Semi-autonomous with HITL: Agent handles intelligence, human handles judgment → **chosen**

### Step 4 — Justified Decision
Semi-autonomous agent with mandatory ethical safety gate (Step 0), confidence scoring, full audit log, and mandatory human approval gate (Step 5). Agent suggests — human decides. This satisfies both the technical requirements (agentic system) and the ethical requirements (human control, transparency, accountability).

---

## LEGAL ASPECTS

### Intellectual Property Rights (IPR)
NoteVision is an original student project. All code, design, and architecture are owned by the development team. Dependencies (Streamlit, google-genai, python-docx) are used under their respective open-source licences (Apache 2.0, MIT, BSD).

**User IPR obligation displayed in UI before every run:**
> "⚖️ IPR Notice: Only upload content you own or have rights to process. Processing third-party copyrighted material without authorisation may violate intellectual property law."

### Data Protection — GDPR Alignment
- No data retained beyond the API call lifetime
- Informed consent obtained via consent gate before accessing the system
- Right to cancel at any time (cancel button, reject output, close browser)
- No data sharing with third parties beyond Google Vertex AI (disclosed in consent gate)
- Session memory cleared on browser refresh

### PECA 2016 (Pakistan Electronic Crimes Act)
Unauthorised access to and processing of others' data is a criminal offence under PECA 2016. The consent gate and safety screening directly address this by ensuring only authorised, consensual use of the system.

### Computer Contracts
The consent gate constitutes an implicit user agreement covering:
- Data handling practices
- AI involvement disclosure
- IPR responsibilities
- Limitation of liability (output requires human verification)
- Acceptable use policy

---

## INDUSTRY PRACTICES & CAREER RELEVANCE

### Professional Practices We Adopted (Beyond Typical Student Project)
- Service account authentication (not plain API keys)
- Credentials stored in Streamlit Secrets (encrypted at rest)
- Rate limiting (20 conversions/session, 10s cooldown)
- Ethical safety gate (AI-powered content screening)
- Full audit log per run
- Version control via Git

### What a Software House Would Add
- CI/CD pipeline with automated testing
- Security penetration testing
- Dedicated AI ethics review board
- Multi-region deployment with SLAs
- Comprehensive unit and integration test suite
- Code review policies and branch protection

### Industry Trend: The Agentic AI Shift
- **2022:** LLMs as question-answering tools (ChatGPT)
- **2023–24:** AI Agents — AutoGPT, LangChain, autonomous task decomposition
- **2025+:** Agentic systems — Google Vertex AI Agents, Claude Computer Use, autonomous pipelines

NoteVision demonstrates this exact evolution: static tool (Phase 1) → agentic system (Phase 2). The industry is moving toward agents that perceive context, make decisions, learn from feedback, and maintain human oversight at critical points.

### Career Impact
The AI industry in 2025 needs professionals who can:
- Design ethical AI systems with human oversight
- Handle data privacy compliance (GDPR, data minimisation)
- Communicate AI limitations honestly to users
- Build auditable, transparent decision pipelines

This project demonstrates all four — making it directly relevant to careers in AI engineering, ML ops, and responsible AI development.

---

## VIRTUAL WORK & SUSTAINABILITY

### Remote Collaboration
- Deployed on Streamlit Cloud — accessible from any device, anywhere
- Code hosted on GitHub — asynchronous collaboration
- Streamlit Secrets for secure credential sharing across team members
- Google Vertex AI managed cloud infrastructure

### Green Computing
- Strategy selection reduces unnecessary API calls — only the right prompt is sent
- No image storage = zero long-term storage overhead
- Vertex AI runs on Google's carbon-neutral infrastructure
- Rate limiting prevents computational waste from excessive API calls

### Work-Life Balance Principle
The Human-in-the-Loop design reflects the broader principle that AI should augment human work, not create dependency or pressure. The student remains the final decision-maker — a sustainable, healthy approach to AI integration in academic life.

---

## TECHNICAL SPECIFICATIONS

### Architecture
```
User Upload → Safety Check (HITL) → assess_image → select_strategy → convert → critique → refine → Output Approval (HITL) → Download
```

### Key Classes
- `ImageAssessment` — dataclass holding image analysis results
- `SafetyResult` — dataclass holding ethical screening results
- `ConversionResult` — dataclass holding full pipeline output
- `AgentMemory` — manages short-term and long-term memory
- `AgentTools` — 6 discrete, independently callable tools
- `NoteVisionAgent` — orchestrates the full agentic loop

### AI Model
- Google Gemini 2.5 Flash via Vertex AI
- GCP Project: Authenticated via service account
- API: google-genai SDK with Vertex AI backend

### Security
- Service account JSON stored in Streamlit Secrets
- No API keys in source code
- Rate limiting: 20 conversions per session, 10-second cooldown between runs
- No persistent data storage of any kind

### Export Formats
- Markdown (.md) with full LaTeX support
- Microsoft Word (.docx) via python-docx

---

## COMPARATIVE ANALYSIS — PHASE 1 vs PHASE 2

| Dimension | Phase 1 (Static Tool) | Phase 2 (Ethical Agent) |
|---|---|---|
| Behaviour | Reactive — waits for input | Proactive — assesses before acting |
| Intelligence | Static — 1 generic strategy | Adaptive — 6 context-aware strategies |
| Decision Making | User-driven entirely | System-driven with HITL checkpoints |
| Quality Assurance | None | Self-critique + refinement on every run |
| Memory | Stateless | Short-term (5 results) + Long-term history |
| Safety | None | Consent gate + AI safety screening + HITL ×2 |
| Transparency | Black box | Strategy badge + confidence + audit log + ethics tab |
| Legal Compliance | None | IPR notice + GDPR-aligned + PECA-aware |
| ACM/IEEE Alignment | Not considered | §1.1 · §1.6 · §2.5 · §2.9 · §3.1 applied |

---

## RISK ASSESSMENT

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Incorrect OCR output | Medium | High (academic) | Critique loop + confidence score + HITL approval |
| LLM bias across handwriting styles | Medium | Medium | Acknowledged in Ethics tab · re-run always available |
| Misuse (exams / confidential docs) | Medium | High (legal) | Safety gate screens every image before processing |
| Data privacy breach | Low | High | No persistent storage · service account · Vertex AI |
| Over-automation without oversight | Low | High | Semi-autonomous design — HITL is mandatory |
| API quota exhaustion / abuse | Medium | Medium | Rate limiting (20/session, 10s cooldown), retry logic |
| Credential exposure | Low | High | Service account in Streamlit Secrets, no hardcoded keys |

---

## DEFENCE-IN-DEPTH SAFETY STACK

1. Privacy Consent Gate — informed consent before first access
2. IPR Notice — user acknowledges responsibility before every run
3. Ethical Safety Screening (HITL Gate 1) — AI screens content type
4. Rate Limiting — prevents abuse (20/session, 10s cooldown)
5. Confidence Score — honest uncertainty communication
6. Activity Audit Log — full decision trail per run
7. Ethics & Compliance Tab — per-run ethical summary
8. Output Approval Gate (HITL Gate 2) — human approves before download

---

## CLOs ADDRESSED

| CLO | How Addressed |
|---|---|
| CLO 4 — Ethical decision making, ACM/IEEE | 4-step model applied explicitly · 5 ACM/IEEE principles mapped to features · 1 violation acknowledged · ethical theories applied |
| CLO 5 — Intellectual Property Rights | IPR notice displayed before every run · user agreement via consent gate · open-source licence compliance documented |
| CLO 6 — Legal aspects, data protection | GDPR-aligned zero storage design · PECA 2016 awareness · consent gate as computer contract · computer crimes mitigated |
| CLO 8 — Industry practices, agentic AI | 6-step agentic pipeline · memory architecture · HITL design · transparency features · industry trend awareness |

---

*NoteVision Agent — Phase 2 | Professional Practices in IT*  
*Built with Google Gemini 2.5 Flash · Vertex AI · Streamlit · Python*
