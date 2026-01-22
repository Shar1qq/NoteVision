import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import io
import time

# Page configuration
st.set_page_config(
    page_title="NoteVision - AI Notes Converter",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern, professional UI
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background-color: #1a202c;
    }
    
    /* Card-like containers */
    .stApp {
        background: #1a202c;
    }
    
    /* Header styling */
    h1 {
        color: #f7fafc;
        font-weight: 800;
        font-size: 2.2rem !important; /* Reduced from 3rem */
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    h2 {
        color: #e2e8f0;
        font-weight: 600;
        font-size: 1.3rem !important; /* Reduced from 1.5rem */
        margin-top: 1.2rem;
    }
    
    h3 {
        color: #cbd5e0;
        font-weight: 600;
        font-size: 1.1rem !important; /* Reduced from 1.2rem */
    }
    
    /* Subtitle styling */
    .subtitle {
        color: #a0aec0;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* File uploader styling */
    .stFileUploader {
        background: #2d3748;
        border: 2px dashed #4a5568;
        border-radius: 12px;
        padding: 2rem;
        transition: all 0.3s ease;
    }
    
    .stFileUploader:hover {
        border-color: #667eea;
        background: #2d3748;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Download button styling */
    .stDownloadButton > button {
        background: #2d3748;
        color: #667eea;
        border: 2px solid #667eea;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stDownloadButton > button:hover {
        background: #667eea;
        color: white;
        transform: translateY(-2px);
    }
    
    /* Sidebar styling */
    .css-1d391kg, [data-testid="stSidebar"] {
        background-color: #2d3748;
        border-right: 1px solid #4a5568;
    }
    
    /* Info box styling */
    .stInfo {
        background: #2c3e50;
        border-left: 4px solid #667eea;
        border-radius: 8px;
        padding: 1rem;
        color: #e2e8f0;
    }
    
    /* Success message styling */
    .stSuccess {
        background: #1e3a27;
        border-left: 4px solid #28a745;
        border-radius: 8px;
        color: #e2e8f0;
    }
    
    /* Warning message styling */
    .stWarning {
        background: #4a3b1a;
        border-left: 4px solid #ffc107;
        border-radius: 8px;
        color: #e2e8f0;
    }
    
    /* Error message styling */
    .stError {
        background: #4a1c1c;
        border-left: 4px solid #dc3545;
        border-radius: 8px;
        color: #e2e8f0;
    }
    
    /* Image container */
    .stImage {
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    /* Markdown output container */
    .markdown-output {
        background: #2d3748;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #4a5568;
        max-height: 600px;
        overflow-y: auto;
        color: #e2e8f0;
    }
    
    /* Spinner styling */
    .stSpinner > div {
        border-color: #667eea !important;
    }
    
    /* Divider */
    hr {
        margin: 2rem 0;
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #4a5568, transparent);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for rate limiting
if 'conversion_count' not in st.session_state:
    st.session_state.conversion_count = 0
if 'last_conversion_time' not in st.session_state:
    st.session_state.last_conversion_time = 0

# Rate limiting configuration
MAX_CONVERSIONS_PER_SESSION = 20
COOLDOWN_SECONDS = 10

# Configure Gemini API
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error("⚠️ API Key not configured. Please set up GEMINI_API_KEY in Streamlit secrets.")
    st.stop()

# System prompt for Gemini
SYSTEM_PROMPT = """You are an OCR and document-structuring assistant.

Convert this handwritten university note image into a clean, well-structured Markdown document.

Rules:
- Preserve headings, subheadings, and bullet points
- Preserve arrows, boxes, and emphasis
- Convert all mathematical expressions into valid LaTeX (use $ for inline math and $$ for block math)
- Do NOT summarize or paraphrase
- Maintain original academic wording
- If something is unclear, make a best-effort guess and mark it with (?)

Output only Markdown."""

def convert_markdown_to_docx(markdown_text):
    """Convert markdown text to a DOCX file"""
    doc = Document()
    
    # Add title
    title = doc.add_paragraph("Converted Notes")
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    title_format = title.runs[0]
    title_format.font.size = Pt(18)
    title_format.font.bold = True
    
    doc.add_paragraph()  # Spacing
    
    # Add the content
    # Simple processing - split by lines and handle basic markdown
    lines = markdown_text.split('\n')
    
    for line in lines:
        if line.strip():
            # Handle headings
            if line.startswith('# '):
                p = doc.add_paragraph(line.replace('# ', ''))
                p.runs[0].font.size = Pt(16)
                p.runs[0].font.bold = True
            elif line.startswith('## '):
                p = doc.add_paragraph(line.replace('## ', ''))
                p.runs[0].font.size = Pt(14)
                p.runs[0].font.bold = True
            elif line.startswith('### '):
                p = doc.add_paragraph(line.replace('### ', ''))
                p.runs[0].font.size = Pt(12)
                p.runs[0].font.bold = True
            # Handle bullet points
            elif line.strip().startswith('-') or line.strip().startswith('*'):
                p = doc.add_paragraph(line.strip()[1:].strip(), style='List Bullet')
            else:
                # Regular paragraph
                p = doc.add_paragraph(line)
    
    return doc

def process_image_with_gemini(image):
    """Process image using Gemini Vision API with retry logic"""
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Generate content using new API
            response = client.models.generate_content(
                model='models/gemini-2.0-flash',
                contents=[
                    SYSTEM_PROMPT,
                    types.Part.from_bytes(
                        data=img_byte_arr.read(),
                        mime_type='image/png'
                    )
                ]
            )
            
            text = response.text
            
            # Clean up markdown code blocks if present
            if text.startswith("```"):
                lines = text.split('\n')
                # Remove first line if it starts with ```
                if lines[0].startswith("```"):
                    lines = lines[1:]
                # Remove last line if it starts with ```
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines)
            
            return text
        
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a rate limit error
            if '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    st.warning(f"⏳ Rate limit reached. Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    st.error("⚠️ **API Rate Limit Exceeded**\n\nPlease wait 1-2 minutes and try again. The free tier has limited requests per minute.")
                    return None
            
            # Check if it's an overload error
            elif '503' in error_msg or 'UNAVAILABLE' in error_msg:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    st.warning(f"⏳ Model is busy. Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    st.error("The AI model is currently overloaded. Please try again in a minute.")
                    return None
            
            # Other errors
            else:
                st.error(f"Error processing image: {error_msg}")
                return None
    
    return None

# Main UI
st.markdown("<h1>📝 NoteVision</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Transform handwritten notes into editable documents with AI</p>", unsafe_allow_html=True)

st.markdown("""
<div style='background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%); 
            border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem;'>
    <p style='margin: 0; color: #4a5568; font-size: 1rem;'>
        ✨ Upload your handwritten university notes (including mathematical formulas) and convert them 
        into clean, structured, editable documents powered by NoteVision AI.
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar with enhanced stats
st.sidebar.markdown("### 📊 Session Stats")
st.sidebar.markdown(f"""
<div style='background: white; padding: 1rem; border-radius: 10px; border: 2px solid #e2e8f0;'>
    <p style='margin: 0; font-size: 0.9rem; color: #718096;'>Conversions Used</p>
    <p style='margin: 0; font-size: 2rem; font-weight: bold; color: #667eea;'>
        {st.session_state.conversion_count}/{MAX_CONVERSIONS_PER_SESSION}
    </p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ How It Works")
st.sidebar.markdown("""
1. **Upload** your handwritten note image
2. **Convert** using AI vision processing
3. **Review** the extracted markdown content
4. **Download** as DOCX or Markdown
""")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Features")
st.sidebar.markdown("""
- ✅ Handwritten text recognition
- ✅ Mathematical formulas → LaTeX
- ✅ Structure preservation
- ✅ Export to DOCX/Markdown
- ✅ Rate limiting protection
""")

# Check rate limit
if st.session_state.conversion_count >= MAX_CONVERSIONS_PER_SESSION:
    st.error(f"⚠️ You've reached the maximum of {MAX_CONVERSIONS_PER_SESSION} conversions per session. Please refresh the page to start a new session.")
    st.stop()

# File uploader
uploaded_file = st.file_uploader(
    "Upload your handwritten notes",
    type=['jpg', 'jpeg', 'png'],
    help="Upload an image of your handwritten notes"
)

if uploaded_file is not None:
    # Load image
    image = Image.open(uploaded_file)
    
    # Display image in expander (hidden by default to save space)
    with st.expander("📸 View Original Image", expanded=False):
        st.image(image, use_column_width=True)
    
    # Convert button area
    col_btn, col_blank = st.columns([1, 2])
    with col_btn:
        convert_button = st.button("🔄 Convert to Editable Text", type="primary", use_container_width=True)
    
    if convert_button:
        # Check cooldown
        time_since_last = time.time() - st.session_state.last_conversion_time
        if time_since_last < COOLDOWN_SECONDS:
            st.warning(f"⏳ Please wait {int(COOLDOWN_SECONDS - time_since_last)} seconds before converting again.")
        else:
            with st.spinner("🔍 Analyzing your handwritten notes with AI..."):
                # Process the image
                markdown_output = process_image_with_gemini(image)
                
                if markdown_output:
                    # Store in session state
                    st.session_state.markdown_output = markdown_output
                    st.session_state.conversion_count += 1
                    st.session_state.last_conversion_time = time.time()
                    
                    st.success("✅ Conversion complete!")
                    st.rerun()

    # Display output if available (Full Width)
    if 'markdown_output' in st.session_state:
        st.markdown("### 📄 Extracted Content")
        
        # Create a styled container for markdown output
        st.markdown("""
        <div style='background: #2d3748; border-radius: 12px; padding: 2rem; 
                    border: 2px solid #4a5568;' class='markdown-output'>
        """, unsafe_allow_html=True)
        
        st.markdown(st.session_state.markdown_output)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("")  # Spacing
        
        # Download section with improved styling
        st.markdown("### 💾 Download Options")
        
        col_docx, col_md, col_empty = st.columns([1, 1, 2])
        
        with col_docx:
            # Generate DOCX
            doc = convert_markdown_to_docx(st.session_state.markdown_output)
            
            # Save to bytes
            docx_buffer = io.BytesIO()
            doc.save(docx_buffer)
            docx_buffer.seek(0)
            
            # Download button
            st.download_button(
                label="📥 DOCX File",
                data=docx_buffer,
                file_name="converted_notes.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        
        with col_md:
            # Markdown download
            st.download_button(
                label="📥 Markdown File",
                data=st.session_state.markdown_output,
                file_name="converted_notes.md",
                mime="text/markdown",
                use_container_width=True
            )

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 2rem 0;'>
    <p style='color: #a0aec0; font-size: 0.9rem; margin: 0;'>
        Powered by NoteVision AI | Built with Streamlit ❤️
    </p>
    <p style='color: #cbd5e0; font-size: 0.8rem; margin-top: 0.5rem;'>
        © 2026 NoteVision - Transform Handwriting into Digital Text
    </p>
</div>
""", unsafe_allow_html=True)
