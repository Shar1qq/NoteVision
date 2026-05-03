"""
NoteVision – Phase 2 Agentic Application
==========================================
Transforms Phase 1 (static convert-on-click tool) into a fully agentic system:
  Perceive → Assess → Plan → Convert → Critique → Refine → Deliver

UI layers:
  - Agent Activity Log   : real-time step-by-step transparency
  - Assessment Panel     : what the agent perceived
  - Strategy Badge       : which tool the agent chose and why
  - Critique Panel       : self-review output
  - Confidence Meter     : agent certainty score
  - Human-in-the-Loop    : user can accept, reject, or request another pass
  - Memory Dashboard     : session + history stats
"""

import streamlit as st
from google import genai
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import io

from agent import AgentMemory, NoteVisionAgent
from PIL import Image

# ─────────────────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="NoteVision Agent – Phase 2",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Styling
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .stApp { background: #0f1117; }

  /* ── Header ── */
  .nv-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
  }
  .nv-header h1 {
    color: white !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
    margin: 0 !important;
    -webkit-text-fill-color: white !important;
  }
  .nv-header p { color: rgba(255,255,255,0.85); margin: 0.4rem 0 0 0; font-size: 1rem; }

  /* ── Cards ── */
  .nv-card {
    background: #1e2130;
    border: 1px solid #2d3250;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
  }
  .nv-card-title {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #667eea;
    margin-bottom: 0.6rem;
  }

  /* ── Agent log ── */
  .agent-log {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    color: #8b949e;
    max-height: 220px;
    overflow-y: auto;
    line-height: 1.7;
  }
  .agent-log .step { color: #58a6ff; }
  .agent-log .ok   { color: #3fb950; }
  .agent-log .warn { color: #d29922; }

  /* ── Strategy badge ── */
  .strategy-badge {
    display: inline-block;
    background: linear-gradient(135deg, #667eea22, #764ba222);
    border: 1px solid #667eea55;
    color: #a5b4fc;
    border-radius: 20px;
    padding: 0.3rem 1rem;
    font-size: 0.85rem;
    font-weight: 600;
  }

  /* ── Confidence meter ── */
  .conf-bar-wrap {
    background: #0d1117;
    border-radius: 8px;
    height: 10px;
    overflow: hidden;
    margin-top: 0.5rem;
  }
  .conf-bar-fill {
    height: 100%;
    border-radius: 8px;
    background: linear-gradient(90deg, #667eea, #764ba2);
    transition: width 0.4s ease;
  }

  /* ── Buttons ── */
  .stButton > button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.6rem 1.5rem;
    font-weight: 600;
    font-size: 0.95rem;
    transition: all 0.2s ease;
    box-shadow: 0 4px 14px rgba(102, 126, 234, 0.35);
  }
  .stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.55);
  }
  .stDownloadButton > button {
    background: #1e2130;
    color: #667eea;
    border: 1.5px solid #667eea;
    border-radius: 10px;
    font-weight: 600;
    transition: all 0.2s;
  }
  .stDownloadButton > button:hover {
    background: #667eea;
    color: white;
  }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] { background: #161b27; border-right: 1px solid #2d3250; }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
    background: #1e2130;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    color: #8892b0;
    font-weight: 500;
    font-size: 0.85rem;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: white !important;
  }

  /* ── Assessment grid ── */
  .assess-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    margin-top: 0.5rem;
  }
  .assess-item {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 0.6rem 0.9rem;
    text-align: center;
  }
  .assess-label { font-size: 0.7rem; color: #6e7b8b; text-transform: uppercase; letter-spacing: 0.06em; }
  .assess-value { font-size: 1rem; font-weight: 700; color: #e2e8f0; margin-top: 2px; }

  /* ── History item ── */
  .hist-item {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    margin-bottom: 0.4rem;
    font-size: 0.82rem;
    color: #8b949e;
  }

  /* ── HITL controls ── */
  .hitl-banner {
    background: linear-gradient(135deg, #1a2a1a, #1e2a1e);
    border: 1.5px solid #2ea04388;
    border-radius: 10px;
    padding: 1rem 1.3rem;
    margin: 0.75rem 0;
  }
  .hitl-title { color: #3fb950; font-weight: 700; font-size: 0.9rem; margin-bottom: 0.3rem; }
  .hitl-desc  { color: #8b949e; font-size: 0.82rem; }

  hr { border: none; border-top: 1px solid #2d3250; margin: 1.2rem 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Rate Limiting
# ─────────────────────────────────────────────────────────────────────────────

MAX_PER_SESSION = 20
COOLDOWN = 10

if "conversion_count" not in st.session_state:
    st.session_state.conversion_count = 0
if "last_time" not in st.session_state:
    st.session_state.last_time = 0
if "agent_result" not in st.session_state:
    st.session_state.agent_result = None
if "hitl_accepted" not in st.session_state:
    st.session_state.hitl_accepted = None   # None | True | False

# ─────────────────────────────────────────────────────────────────────────────
# API + Agent init
# ─────────────────────────────────────────────────────────────────────────────

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception:
    st.error("⚠️ API Key not configured. Add GEMINI_API_KEY to Streamlit secrets.")
    st.stop()

memory = AgentMemory(st.session_state)
agent = NoteVisionAgent(gemini_client, memory)

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="nv-header">
  <h1>🤖 NoteVision Agent</h1>
  <p>Phase 2 &nbsp;·&nbsp; Agentic Handwriting Converter &nbsp;·&nbsp;
     Perceive → Assess → Plan → Convert → Critique → Refine → Deliver</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar – Memory Dashboard
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🧠 Agent Memory")
    st.markdown(f"""
<div class="nv-card">
  <div class="nv-card-title">Session Memory</div>
  <div style="font-size:2rem;font-weight:800;color:#667eea;">
    {memory.session_conversions()}
    <span style="font-size:1rem;color:#6e7b8b;">/ {MAX_PER_SESSION}</span>
  </div>
  <div style="font-size:0.8rem;color:#6e7b8b;margin-top:4px;">conversions this session</div>
</div>
<div class="nv-card">
  <div class="nv-card-title">Long-term Memory</div>
  <div style="font-size:1.6rem;font-weight:700;color:#a5b4fc;">
    {memory.total_conversions()}
  </div>
  <div style="font-size:0.8rem;color:#6e7b8b;margin-top:4px;">total conversions ever</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ⚙️ Agent Architecture")
    st.markdown("""
<div style="font-size:0.82rem;color:#8b949e;line-height:1.9;">
🔵 <b style="color:#c9d1d9;">Perceive</b> – quality assessment tool<br>
🔵 <b style="color:#c9d1d9;">Decide</b> &nbsp;– strategy selector (rule-based)<br>
🔵 <b style="color:#c9d1d9;">Act</b> &nbsp;&nbsp;&nbsp;&nbsp;– Gemini Vision conversion<br>
🔵 <b style="color:#c9d1d9;">Critique</b> – self-review tool<br>
🔵 <b style="color:#c9d1d9;">Refine</b> &nbsp;– feedback-based correction<br>
🟢 <b style="color:#3fb950;">HITL</b> &nbsp;&nbsp;&nbsp;– human approval gate
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    # Recent history
    history = memory.get_history()[-5:]
    if history:
        st.markdown("### 📂 Recent History")
        for h in reversed(history):
            q = h["assessment"]["quality"]
            colour = {"good": "#3fb950", "poor": "#f85149", "unclear": "#d29922"}.get(q, "#8b949e")
            st.markdown(f"""
<div class="hist-item">
  <b style="color:#c9d1d9;">{h['filename'][:22]}</b><br>
  <span style="color:{colour};">●</span> {q} &nbsp;·&nbsp; {h['strategy_used']} &nbsp;·&nbsp;
  {h['confidence']:.0%} conf<br>
  <span style="color:#4a5568;">{h['timestamp']}</span>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Main – File Upload
# ─────────────────────────────────────────────────────────────────────────────

uploaded = st.file_uploader(
    "Upload handwritten notes (JPG / PNG / JPEG)",
    type=["jpg", "jpeg", "png"],
    help="The agent will automatically assess quality and choose the best strategy.",
)

if uploaded is not None:
    image = Image.open(uploaded)

    col_img, col_info = st.columns([1, 1])
    with col_img:
        with st.expander("📸 Original Image", expanded=True):
            st.image(image, use_column_width=True)

    with col_info:
        st.markdown("""
<div class="nv-card">
  <div class="nv-card-title">How the Agent Works</div>
  <div style="font-size:0.85rem;color:#8b949e;line-height:1.9;">
    1️⃣ <b style="color:#c9d1d9;">Perceive</b> — analyses image quality & content<br>
    2️⃣ <b style="color:#c9d1d9;">Decide</b> — picks the best conversion strategy<br>
    3️⃣ <b style="color:#c9d1d9;">Act</b> — converts with strategy-specific prompt<br>
    4️⃣ <b style="color:#c9d1d9;">Critique</b> — self-reviews its own output<br>
    5️⃣ <b style="color:#c9d1d9;">Refine</b> — fixes issues found in critique<br>
    6️⃣ <b style="color:#c9d1d9;">HITL gate</b> — you approve before download
  </div>
</div>
""", unsafe_allow_html=True)

    # ─ Rate-limit check ───────────────────────────────────────────────────────
    import time as _time
    if st.session_state.conversion_count >= MAX_PER_SESSION:
        st.error(f"Session limit reached ({MAX_PER_SESSION} conversions). Refresh to start a new session.")
        st.stop()

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        run_agent = st.button("🚀 Run Agent", type="primary", use_container_width=True)

    if run_agent:
        elapsed = _time.time() - st.session_state.last_time
        if elapsed < COOLDOWN:
            st.warning(f"⏳ Cooldown: please wait {int(COOLDOWN - elapsed)}s before the next run.")
        else:
            # Reset HITL state for new run
            st.session_state.hitl_accepted = None
            st.session_state.agent_result = None

            log_lines = []

            # Live agent log container
            st.markdown("#### 🔄 Agent Activity")
            log_placeholder = st.empty()

            def _update_log(msg: str):
                log_lines.append(msg)
                coloured = []
                for line in log_lines:
                    cls = "ok" if "✅" in line else "warn" if "⏳" in line or "⚠️" in line else "step"
                    coloured.append(f'<span class="{cls}">{line}</span>')
                log_placeholder.markdown(
                    f'<div class="agent-log">{"<br>".join(coloured)}</div>',
                    unsafe_allow_html=True,
                )

            with st.spinner("Agent running…"):
                try:
                    result = agent.run(image, uploaded.name, log_callback=_update_log)
                    st.session_state.agent_result = result
                    st.session_state.conversion_count += 1
                    st.session_state.last_time = _time.time()
                    st.rerun()
                except Exception as e:
                    st.error(f"Agent failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Results Panel (after agent run)
# ─────────────────────────────────────────────────────────────────────────────

result = st.session_state.get("agent_result")
if result is not None:

    st.markdown("---")
    st.markdown("## 📊 Agent Report")

    # ── Row 1: Assessment + Strategy + Confidence ─────────────────────────────
    c1, c2, c3 = st.columns([2, 1.5, 1.5])

    with c1:
        q = result.assessment.quality
        q_colour = {"good": "#3fb950", "poor": "#f85149", "unclear": "#d29922"}.get(q, "#8b949e")
        st.markdown(f"""
<div class="nv-card">
  <div class="nv-card-title">🔍 Perception — Image Assessment</div>
  <div class="assess-grid">
    <div class="assess-item">
      <div class="assess-label">Quality</div>
      <div class="assess-value" style="color:{q_colour};">{q.upper()}</div>
    </div>
    <div class="assess-item">
      <div class="assess-label">Has Math</div>
      <div class="assess-value">{"✓" if result.assessment.has_math else "✗"}</div>
    </div>
    <div class="assess-item">
      <div class="assess-label">Diagrams</div>
      <div class="assess-value">{"✓" if result.assessment.has_diagrams else "✗"}</div>
    </div>
    <div class="assess-item">
      <div class="assess-label">Density</div>
      <div class="assess-value" style="font-size:0.85rem;">{result.assessment.handwriting_density}</div>
    </div>
    <div class="assess-item" style="grid-column:span 2;">
      <div class="assess-label">Agent Notes</div>
      <div style="font-size:0.78rem;color:#8b949e;margin-top:4px;">{result.assessment.notes}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    with c2:
        strategy_labels = {
            "math_focused":         "📐 Math Focused",
            "careful_reconstruction": "🔬 Careful Reconstruction",
            "structure_aware":      "🗂 Structure Aware",
            "detail_preserving":    "🔎 Detail Preserving",
            "standard":             "⚡ Standard",
        }
        badge = strategy_labels.get(result.strategy_used, result.strategy_used)
        st.markdown(f"""
<div class="nv-card" style="height:100%;">
  <div class="nv-card-title">🧠 Decision — Strategy</div>
  <div style="margin-top:0.8rem;">
    <div class="strategy-badge">{badge}</div>
  </div>
  <div style="font-size:0.78rem;color:#6e7b8b;margin-top:0.8rem;">
    Selected automatically based on image perception.
  </div>
</div>
""", unsafe_allow_html=True)

    with c3:
        conf_pct = int(result.confidence * 100)
        conf_colour = "#3fb950" if conf_pct >= 75 else "#d29922" if conf_pct >= 50 else "#f85149"
        st.markdown(f"""
<div class="nv-card" style="height:100%;">
  <div class="nv-card-title">📈 Agent Confidence</div>
  <div style="font-size:2.4rem;font-weight:800;color:{conf_colour};margin-top:0.4rem;">
    {conf_pct}%
  </div>
  <div class="conf-bar-wrap">
    <div class="conf-bar-fill" style="width:{conf_pct}%;background:{'linear-gradient(90deg,#3fb950,#2ea043)' if conf_pct>=75 else 'linear-gradient(90deg,#d29922,#9e6a03)' if conf_pct>=50 else 'linear-gradient(90deg,#f85149,#da3633)'};"></div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Tabs: Output / Critique / Log ─────────────────────────────────────────
    st.markdown("### 📄 Agent Output")
    tab_out, tab_crit, tab_log = st.tabs(["✅ Refined Output", "🔎 Self-Critique", "🔄 Activity Log"])

    with tab_out:
        st.markdown(result.refined_markdown)

    with tab_crit:
        refined_used = ("looks complete and accurate" not in result.critique.lower())
        st.markdown(f"""
<div class="nv-card">
  <div class="nv-card-title">Critique Result</div>
  <div style="font-size:0.88rem;color:#c9d1d9;line-height:1.7;">{result.critique}</div>
  <div style="margin-top:0.8rem;font-size:0.78rem;color:#6e7b8b;">
    {'⚙️ Refinement pass was applied based on this critique.' if refined_used else '✅ No refinement needed — output passed review.'}
  </div>
</div>
""", unsafe_allow_html=True)

    with tab_log:
        log_html = "<br>".join(result.agent_log)
        st.markdown(f'<div class="agent-log">{log_html}</div>', unsafe_allow_html=True)

    # ── Human-in-the-Loop Gate ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
<div class="hitl-banner">
  <div class="hitl-title">🟢 Human-in-the-Loop Control</div>
  <div class="hitl-desc">
    Review the agent's output above. You control what happens next — approve to download,
    reject to discard, or re-run for another agent pass.
  </div>
</div>
""", unsafe_allow_html=True)

    col_a, col_r, col_rr = st.columns([1, 1, 1])
    with col_a:
        if st.button("✅ Accept Output", use_container_width=True):
            st.session_state.hitl_accepted = True
            st.rerun()
    with col_r:
        if st.button("❌ Reject Output", use_container_width=True):
            st.session_state.hitl_accepted = False
            st.session_state.agent_result = None
            st.rerun()
    with col_rr:
        if st.button("🔁 Re-run Agent", use_container_width=True):
            st.session_state.agent_result = None
            st.session_state.hitl_accepted = None
            st.rerun()

    # ── Download Section (only if accepted) ───────────────────────────────────
    if st.session_state.hitl_accepted is True:
        st.success("✅ Output accepted! Downloads are now available.")
        st.markdown("### 💾 Download")

        final_md = result.refined_markdown

        def _make_docx(md_text: str) -> bytes:
            doc = Document()
            t = doc.add_paragraph("Converted Notes")
            t.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            t.runs[0].font.size = Pt(18)
            t.runs[0].font.bold = True
            doc.add_paragraph()
            for line in md_text.split("\n"):
                if line.strip():
                    if line.startswith("# "):
                        p = doc.add_paragraph(line[2:])
                        p.runs[0].font.size = Pt(16)
                        p.runs[0].font.bold = True
                    elif line.startswith("## "):
                        p = doc.add_paragraph(line[3:])
                        p.runs[0].font.size = Pt(14)
                        p.runs[0].font.bold = True
                    elif line.startswith("### "):
                        p = doc.add_paragraph(line[4:])
                        p.runs[0].font.size = Pt(12)
                        p.runs[0].font.bold = True
                    elif line.strip().startswith(("-", "*")):
                        doc.add_paragraph(line.strip()[1:].strip(), style="List Bullet")
                    else:
                        doc.add_paragraph(line)
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)
            return buf.read()

        col_d1, col_d2, _ = st.columns([1, 1, 2])
        with col_d1:
            st.download_button(
                "📥 DOCX File",
                data=_make_docx(final_md),
                file_name="notevision_output.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        with col_d2:
            st.download_button(
                "📥 Markdown File",
                data=final_md,
                file_name="notevision_output.md",
                mime="text/markdown",
                use_container_width=True,
            )

    elif st.session_state.hitl_accepted is False:
        st.warning("Output rejected. Upload a new image or re-run the agent.")

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("""
<div style="text-align:center;padding:1.5rem 0;">
  <p style="color:#4a5568;font-size:0.85rem;margin:0;">
    NoteVision Agent &nbsp;·&nbsp; Phase 2 Agentic System &nbsp;·&nbsp;
    Perceive → Assess → Plan → Convert → Critique → Refine → Deliver
  </p>
  <p style="color:#3d4559;font-size:0.75rem;margin-top:6px;">
    Powered by Google Gemini 2.0 Flash &nbsp;|&nbsp; Built with Streamlit
  </p>
</div>
""", unsafe_allow_html=True)
