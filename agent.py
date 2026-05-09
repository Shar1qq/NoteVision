"""
NoteVision Agent - Phase 2 Agentic Core
=========================================
Implements the agentic pipeline:
  Perceive → Assess → Plan → Convert → Critique → Refine → Deliver

Architecture:
  - AgentMemory    : short-term session memory + long-term history log
  - AgentTools     : discrete callable tools the agent selects from
  - NoteVisionAgent: orchestrates the full agent loop
"""

import io
import time
import json
import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from PIL import Image
from google import genai
from google.genai import types


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ImageAssessment:
    """Result of the agent's perception/quality check tool."""
    quality: str          # "good" | "poor" | "unclear"
    has_math: bool
    has_diagrams: bool
    handwriting_density: str   # "sparse" | "dense"
    estimated_confidence: float  # 0.0 – 1.0
    notes: str            # free-text reasoning


@dataclass
class SafetyResult:
    """Result of the agent's ethical safety screening gate (Step 0).
    Implements responsible AI per ACM/IEEE Code of Ethics §1.6, §2.9.
    """
    is_safe: bool
    concern_type: str   # "none" | "exam_paper" | "personal_data" | "confidential" | "inappropriate"
    explanation: str
    recommendation: str


@dataclass
class ConversionResult:
    """Full output of a single agent run."""
    timestamp: str
    filename: str
    assessment: ImageAssessment
    strategy_used: str
    markdown: str
    critique: str
    refined_markdown: str
    confidence: float
    agent_log: list[str] = field(default_factory=list)
    safety_result: dict = field(default_factory=lambda: {
        "is_safe": True, "concern_type": "none",
        "explanation": "Not screened.", "recommendation": "Safe to process."
    })


# ─────────────────────────────────────────────────────────────────────────────
# Agent Memory
# ─────────────────────────────────────────────────────────────────────────────

class AgentMemory:
    """
    Short-term  : current session context (last N results).
    Long-term   : persisted JSON log across reruns (Streamlit session_state).
    """

    def __init__(self, session_state, max_short_term: int = 5):
        self._state = session_state
        self._max = max_short_term

        if "agent_history" not in self._state:
            self._state.agent_history = []          # long-term log (dicts)
        if "agent_short_term" not in self._state:
            self._state.agent_short_term = []       # last N ConversionResult dicts

    # Short-term ---------------------------------------------------------------

    def store(self, result: ConversionResult):
        d = asdict(result)
        self._state.agent_short_term.append(d)
        self._state.agent_history.append(d)
        # Keep short-term window
        if len(self._state.agent_short_term) > self._max:
            self._state.agent_short_term.pop(0)

    def get_short_term(self) -> list[dict]:
        return self._state.agent_short_term

    def get_history(self) -> list[dict]:
        return self._state.agent_history

    # Context summary for LLM prompts -----------------------------------------

    def context_summary(self) -> str:
        items = self._state.agent_short_term
        if not items:
            return "No prior conversions in this session."
        lines = ["Recent session conversions:"]
        for r in items[-3:]:
            lines.append(
                f"  • [{r['timestamp']}] {r['filename']} "
                f"— quality={r['assessment']['quality']}, "
                f"strategy={r['strategy_used']}, "
                f"confidence={r['confidence']:.0%}"
            )
        return "\n".join(lines)

    def total_conversions(self) -> int:
        return len(self._state.agent_history)

    def session_conversions(self) -> int:
        return len(self._state.agent_short_term)


# ─────────────────────────────────────────────────────────────────────────────
# Agent Tools
# ─────────────────────────────────────────────────────────────────────────────

class AgentTools:
    """
    Discrete, independently callable tools.
    Each tool returns a typed result the agent loop uses for decision-making.
    """

    def __init__(self, client: genai.Client):
        self.client = client
        self._model = "gemini-2.5-flash"

    # ── Tool 1: Image Quality Assessment ─────────────────────────────────────

    def assess_image(self, image: Image.Image) -> ImageAssessment:
        """
        TOOL: assess_image
        Analyses the uploaded image BEFORE conversion to decide strategy.
        The agent uses this output to pick the right prompt.
        """
        img_bytes = self._to_bytes(image)

        prompt = """You are an image quality analyst for a handwriting OCR system.

Analyse this image and respond with ONLY valid JSON (no markdown, no explanation):
{
  "quality": "good" | "poor" | "unclear",
  "has_math": true | false,
  "has_diagrams": true | false,
  "handwriting_density": "sparse" | "dense",
  "estimated_confidence": <float 0.0-1.0>,
  "notes": "<brief sentence explaining your assessment>"
}"""

        try:
            response = self.client.models.generate_content(
                model=self._model,
                contents=[prompt, types.Part.from_bytes(data=img_bytes, mime_type="image/png")]
            )
            raw = response.text.strip()
            # Strip any accidental markdown fences
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:])
            if raw.endswith("```"):
                raw = "\n".join(raw.split("\n")[:-1])
            data = json.loads(raw)
            return ImageAssessment(**data)
        except Exception:
            # Fallback assessment
            return ImageAssessment(
                quality="unclear",
                has_math=False,
                has_diagrams=False,
                handwriting_density="dense",
                estimated_confidence=0.5,
                notes="Assessment failed; using default strategy."
            )

    # ── Tool 1b: Ethical Safety Screening ──────────────────────────────────────

    def safety_check(self, image: Image.Image) -> SafetyResult:
        """
        TOOL: safety_check  (Ethical Gate — ACM/IEEE §1.6 Respect Privacy, §2.9 Design Inclusive)
        Screens content for sensitive, confidential or inappropriate material
        BEFORE any processing occurs. This is a Human-in-the-Loop checkpoint.
        """
        img_bytes = self._to_bytes(image)
        prompt = """You are an ethical content screener for an AI document processing system.

Analyse this image and respond with ONLY valid JSON (no markdown):
{
  "is_safe": true | false,
  "concern_type": "none" | "exam_paper" | "personal_data" | "confidential" | "inappropriate",
  "explanation": "<one sentence, or 'No concerns detected.'>",
  "recommendation": "<one sentence advice, or 'Safe to process.'>"
}

Flag is_safe as false ONLY if the image clearly shows:
- An active exam or test paper with visible questions/answers (academic integrity)
- Personal medical or legal records (data privacy)
- Documents explicitly labelled CONFIDENTIAL or RESTRICTED
- Clearly inappropriate or harmful content"""
        try:
            response = self.client.models.generate_content(
                model=self._model,
                contents=[prompt, types.Part.from_bytes(data=img_bytes, mime_type="image/png")]
            )
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:])
            if raw.endswith("```"):
                raw = "\n".join(raw.split("\n")[:-1])
            data = json.loads(raw)
            return SafetyResult(**data)
        except Exception:
            return SafetyResult(
                is_safe=True,
                concern_type="none",
                explanation="Safety screening unavailable; proceeding with standard caution.",
                recommendation="Safe to process."
            )

    # ── Tool 2: Strategy Selector ─────────────────────────────────────────────

    def select_strategy(self, assessment: ImageAssessment,
                          diagram_mode: bool = True) -> tuple[str, str]:
        """
        TOOL: select_strategy
        Maps assessment → (strategy_name, system_prompt).
        diagram_mode=True  → generate Mermaid xychart-beta blocks.
        diagram_mode=False → describe graphs/diagrams in plain prose.
        This is the agent's DECISION step – no LLM required, rule-based.
        """
        if assessment.has_diagrams and assessment.has_math:
            strategy = "math_and_diagrams"
            if diagram_mode:
                prompt = _build_prompt(
                    focus="The notes contain BOTH mathematical content AND scientific graphs or diagrams. "
                          "Render ALL math as LaTeX (inline $ or block $$). "
                          "For EVERY graph or plot, generate a ```mermaid\nxychart-beta``` block using EXACTLY this format:\n"
                          "xychart-beta\ntitle \"Graph Name\"\nx-axis [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]\ny-axis \"y-label\" 0 --> 100\nline [0, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11]\n"
                          "RULES: ALWAYS start from origin (x=0, y=0). Use 12 points for smooth curves. "
                          "x-axis must be plain integers only. No subscripts (write T1 not T\u2081), no Greek letters, no special chars in labels. "
                          "For two curves on the same graph, add a second 'line' entry with its own 12 values starting from 0.",
                    extra="After each mermaid block write one italic sentence starting with 'This graph shows...' explaining what the graph represents scientifically and its key takeaway. Double-check all LaTeX syntax.",
                    diagram_mode=True
                )
            else:
                prompt = _build_prompt(
                    focus="The notes contain BOTH mathematical content AND scientific graphs or diagrams. "
                          "Render ALL math as LaTeX (inline $ or block $$). "
                          "For EVERY graph or diagram, use a bold heading for its title, then write a prose description covering: "
                          "what the graph represents, what the axes show, the shape/trend of each curve, key data points, and the scientific conclusion.",
                    extra="Double-check all LaTeX syntax.",
                    diagram_mode=False
                )
        elif assessment.has_math and assessment.quality == "good":
            strategy = "math_focused"
            prompt = _build_prompt(
                focus="Pay special attention to every mathematical formula, equation, "
                      "and symbol. Render ALL math as LaTeX (inline $ or block $$). "
                      "Be extremely precise with superscripts, subscripts, Greek letters.",
                extra="Double-check all LaTeX syntax for correctness.",
                diagram_mode=diagram_mode
            )
        elif assessment.quality == "poor" or assessment.estimated_confidence < 0.4:
            strategy = "careful_reconstruction"
            prompt = _build_prompt(
                focus="The image quality is low. Do your best to infer unclear text "
                      "from context. Mark any uncertain word with (?). Prefer accuracy "
                      "over completeness.",
                extra="Insert [ILLEGIBLE] for sections you cannot interpret at all.",
                diagram_mode=diagram_mode
            )
        elif assessment.has_diagrams:
            strategy = "structure_aware"
            if diagram_mode:
                prompt = _build_prompt(
                    focus="The notes contain diagrams, graphs, or flowcharts. "
                          "For flowcharts and mind-maps use ```mermaid\nflowchart TD``` blocks. "
                          "For x-y scientific plots use ```mermaid\nxychart-beta``` with format:\n"
                          "xychart-beta\ntitle \"Name\"\nx-axis [0,1,2,3,4,5,6,7,8,9,10,11]\ny-axis \"label\" 0 --> 100\nline [0,v1,v2,v3,v4,v5,v6,v7,v8,v9,v10,v11]\n"
                          "RULES: ALWAYS start from origin (x=0, y=0). Use 12 points for smooth curves. x-axis integers only, no subscripts or special chars.",
                    extra="After each mermaid block write one italic sentence starting with 'This graph shows...' explaining what the graph represents and its key takeaway. Every diagram MUST be a mermaid block.",
                    diagram_mode=True
                )
            else:
                prompt = _build_prompt(
                    focus="The notes contain diagrams, graphs, or flowcharts. "
                          "For each diagram or graph, use a bold heading for its title, then write a prose description covering: "
                          "what it represents, what the axes/components show, the shape/trend/relationships, key data points or nodes, and what it illustrates.",
                    extra="",
                    diagram_mode=False
                )
        elif assessment.handwriting_density == "sparse":
            strategy = "detail_preserving"
            prompt = _build_prompt(
                focus="The notes are sparse — every word likely matters. Preserve ALL "
                      "content including margin annotations, underlines, and emphasis.",
                extra="Wrap emphasis in **bold** and use > blockquotes for margin notes.",
                diagram_mode=diagram_mode
            )
        else:
            strategy = "standard"
            prompt = _build_prompt(focus="", extra="", diagram_mode=diagram_mode)

        return strategy, prompt

    # ── Tool 3: Convert ───────────────────────────────────────────────────────

    def convert(self, image: Image.Image, system_prompt: str,
                context: str = "") -> Optional[str]:
        """
        TOOL: convert
        Calls Gemini Vision with retry logic and injects memory context.
        """
        img_bytes = self._to_bytes(image)
        full_prompt = system_prompt
        if context:
            full_prompt = f"{system_prompt}\n\n[Session context]\n{context}"

        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self._model,
                    contents=[
                        full_prompt,
                        types.Part.from_bytes(data=img_bytes, mime_type="image/png")
                    ]
                )
                text = response.text.strip()
                # Strip accidental fences
                if text.startswith("```"):
                    lines = text.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip().startswith("```"):
                        lines = lines[:-1]
                    text = "\n".join(lines)
                return text
            except Exception as e:
                last_error = e
                err = str(e)
                if ("429" in err or "RESOURCE_EXHAUSTED" in err or
                        "503" in err or "UNAVAILABLE" in err):
                    if attempt < 2:
                        time.sleep(2 ** attempt * 2)
                        continue
                raise RuntimeError(f"Gemini API error: {e}") from e
        raise RuntimeError(f"Conversion failed after retries: {last_error}")

    # ── Tool 4: Self-Critique ─────────────────────────────────────────────────

    def critique(self, markdown: str, assessment: ImageAssessment) -> str:
        """
        TOOL: critique
        The agent reviews its own output and identifies gaps.
        This is the LEARNING / feedback step.
        """
        prompt = f"""You are a quality-control reviewer for an OCR system.

Here is the converted markdown from a handwritten note:

---
{markdown[:3000]}
---

Image assessment context:
- Quality: {assessment.quality}
- Contains math: {assessment.has_math}
- Contains diagrams: {assessment.has_diagrams}

Identify 1–3 specific issues (if any) such as:
- Missing or broken LaTeX
- Unclear or missing sections
- Structural problems

Respond concisely in plain text (no bullet headers, just sentences).
If the output looks good, say "Output looks complete and accurate."
"""
        try:
            response = self.client.models.generate_content(
                model=self._model, contents=[prompt]
            )
            return response.text.strip()
        except Exception:
            return "Critique unavailable."

    # ── Tool 5: Refinement ────────────────────────────────────────────────────

    def refine(self, markdown: str, critique: str,
               image: Image.Image) -> Optional[str]:
        """
        TOOL: refine
        Only called if critique identifies real issues.
        Passes critique feedback + original image back to Gemini.
        """
        if "looks complete and accurate" in critique.lower():
            return markdown   # No refinement needed

        img_bytes = self._to_bytes(image)
        prompt = f"""You previously converted a handwritten note to markdown. A quality reviewer found these issues:

{critique}

Here is the original markdown output:
---
{markdown[:4000]}
---

Please produce a corrected version of the markdown fixing the identified issues.
Output ONLY the corrected markdown."""

        try:
            response = self.client.models.generate_content(
                model=self._model,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png")
                ]
            )
            text = response.text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines)
            return text
        except Exception:
            return markdown  # Return original if refinement fails

    # ── Helper ────────────────────────────────────────────────────────────────

    def _to_bytes(self, image: Image.Image) -> bytes:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return buf.read()


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(focus: str, extra: str, diagram_mode: bool = True) -> str:
    if diagram_mode:
        graph_rule = (
            "- For any x-y graph or scientific plot, generate a ```mermaid\\nxychart-beta``` block. "
            "Use ONLY this exact format (no subscripts, no special chars, plain ASCII labels):\n"
            "  xychart-beta\\n  title \"Graph Title\"\\n  x-axis [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]"
            "\\n  y-axis \"y-label\" 0 --> 100\\n  line [0, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11]\\n"
            "  IMPORTANT: always start from x=0 y=0 (origin). Use 12 points for smooth curves."
        )
    else:
        graph_rule = (
            "- GRAPH/DIAGRAM RULE (TEXT MODE — STRICTLY ENFORCED):\n"
            "  * Do NOT draw, sketch, or attempt to represent any graph, chart, or diagram visually.\n"
            "  * Do NOT produce any code blocks (``` ... ```) for graphs or diagrams — not mermaid, not ASCII art, not any other format.\n"
            "  * Instead, describe each graph/diagram in plain prose under a bold heading.\n"
            "  * Your description must cover: (1) what the graph represents, (2) what the axes show, "
            "(3) the shape/trend of each curve, (4) key data points or intersections, "
            "(5) the scientific meaning or conclusion.\n"
            "  * Any attempt to produce an ASCII sketch or code block for a graph is a VIOLATION of these instructions."
        )

    base = f"""You are an OCR and document-structuring assistant.

Convert this handwritten university note image into a clean, well-structured Markdown document.

Rules:
- Preserve headings, subheadings, and bullet points
- Preserve arrows, boxes, and emphasis
- Convert all mathematical expressions into valid LaTeX ($ inline, $$ block)
- Do NOT summarize or paraphrase
- Maintain original academic wording
- Mark unclear content with (?)
{graph_rule}

Output only Markdown."""
    if focus:
        base += f"\n\nSpecial instructions for this image:\n{focus}"
    if extra:
        base += f"\n\nAdditional requirement:\n{extra}"
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Main Agent
# ─────────────────────────────────────────────────────────────────────────────

class NoteVisionAgent:
    """
    Orchestrates the full agentic loop:
      Perceive → Assess → Plan → Convert → Critique → Refine → Deliver

    Follows the Observe → Interpret → Decide → Act → Learn cycle.
    Human-in-the-loop: user can approve/reject output before download.
    """

    def __init__(self, client: genai.Client, memory: AgentMemory):
        self.memory = memory
        self.tools = AgentTools(client)

    def run(self, image: Image.Image, filename: str,
            log_callback=None, safety_result: dict = None,
            diagram_mode: bool = True) -> ConversionResult:
        """
        Execute the agent loop. log_callback(str) receives real-time status
        messages for display in the UI.
        """
        log = []

        def _log(msg: str):
            log.append(msg)
            if log_callback:
                log_callback(msg)

        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ── Step 1: PERCEIVE – assess image quality ───────────────────────────
        _log("🔍 [Agent] Perceiving image — running quality assessment…")
        assessment = self.tools.assess_image(image)
        _log(
            f"📊 [Agent] Assessment complete → "
            f"quality={assessment.quality}, "
            f"has_math={assessment.has_math}, "
            f"confidence={assessment.estimated_confidence:.0%}"
        )

        # ── Step 2: DECIDE – choose strategy ─────────────────────────────────
        _log("🧠 [Agent] Deciding conversion strategy…")
        strategy, system_prompt = self.tools.select_strategy(assessment, diagram_mode)
        _log(f"🎯 [Agent] Strategy selected → '{strategy}'")

        # Inject memory context (short-term)
        context = self.memory.context_summary()

        # ── Step 3: ACT – convert ─────────────────────────────────────────────
        _log("⚙️ [Agent] Converting image to Markdown…")
        markdown = self.tools.convert(image, system_prompt, context)
        if not markdown:
            raise RuntimeError("Conversion returned empty response.")

        # ── Step 4: CRITIQUE – self-review ───────────────────────────────────
        _log("🔎 [Agent] Running self-critique on output…")
        critique = self.tools.critique(markdown, assessment)
        _log(f"💬 [Agent] Critique: {critique[:120]}…" if len(critique) > 120 else f"💬 [Agent] Critique: {critique}")

        # ── Step 5: LEARN – refine if needed ─────────────────────────────────
        _log("✨ [Agent] Applying refinements based on critique…")
        refined = self.tools.refine(markdown, critique, image)

        # Compute final confidence (blend assessment + critique signal)
        critique_ok = "looks complete and accurate" in critique.lower()
        confidence = assessment.estimated_confidence * (1.1 if critique_ok else 0.9)
        confidence = min(1.0, confidence)

        result = ConversionResult(
            timestamp=ts,
            filename=filename,
            assessment=assessment,
            strategy_used=strategy,
            markdown=markdown,
            critique=critique,
            refined_markdown=refined,
            confidence=confidence,
            agent_log=log,
            safety_result=safety_result or {
                "is_safe": True, "concern_type": "none",
                "explanation": "Pre-screened externally.", "recommendation": "Safe to process."
            },
        )

        # Store in memory
        self.memory.store(result)
        _log(f"✅ [Agent] Done. Confidence: {confidence:.0%} | Strategy: {strategy}")

        return result
