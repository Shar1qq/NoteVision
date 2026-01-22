# NoteVision 📝

Convert handwritten university notes (including mathematical formulas) into clean, editable documents using Google Gemini Vision AI.

## Features

- ✨ Upload images of handwritten notes (JPG, PNG, JPEG)
- 🤖 AI-powered text extraction using Google Gemini Vision
- 📐 Automatic LaTeX conversion for mathematical formulas
- 📄 Export to DOCX (Microsoft Word compatible)
- 🔒 Built-in rate limiting to prevent API abuse
- 🌐 Deployable to Streamlit Cloud with shareable link

## Rate Limiting

To prevent API abuse without password protection:
- **20 conversions per session** (refresh page to reset)
- **10-second cooldown** between conversions
- **Google Cloud quotas** (set in GCP Console)

## Quick Start (Local)

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone/Download this repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key:**
   
   Create `.streamlit/secrets.toml` file:
   ```bash
   # Copy the example file
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   
   Edit `.streamlit/secrets.toml` and add your API key:
   ```toml
   GEMINI_API_KEY = "your-actual-api-key-here"
   ```

4. **Run the app:**
   ```bash
   streamlit run app.py
   ```

5. **Open your browser** at `http://localhost:8501`

## Deployment to Streamlit Cloud

### Step 1: Prepare Repository

1. Push your code to GitHub (make sure `.streamlit/secrets.toml` is NOT committed)
2. Your repository should contain:
   - `app.py`
   - `requirements.txt`
   - `.streamlit/secrets.toml.example` (template only)

### Step 2: Deploy

1. Go to [share.streamlit.io](https://share.streamlit.io/)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository and branch
5. Set main file path: `app.py`
6. Click "Deploy"

### Step 3: Configure Secrets

1. In your deployed app, click "⋮" → "Settings"
2. Go to "Secrets" section
3. Add your API key:
   ```toml
   GEMINI_API_KEY = "your-actual-api-key-here"
   ```
4. Save and the app will restart

### Step 4: Share

Copy the app URL (e.g., `https://notevision.streamlit.app`) and share with your instructor!

## Setting Google Cloud Quotas

To add an extra layer of protection:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" → "Credentials"
3. Find your API key and click "Edit"
4. Under "API restrictions", select "Restrict key"
5. Enable only "Generative Language API"
6. Set quotas:
   - Click "Quotas" in the left menu
   - Search for "Generative Language API"
   - Set daily request limit (e.g., 100 requests/day)
7. Set up billing alerts to monitor costs

## Usage

1. **Upload Image**: Click "Browse files" and select your handwritten notes
2. **Convert**: Click "Convert to Text" button
3. **Review**: Check the extracted Markdown content
4. **Download**: Click "Download as DOCX" or "Download as Markdown"

## Technology Stack

- **Frontend/Backend**: Streamlit (Python)
- **AI Model**: Google Gemini Vision (`gemini-1.5-flash`)
- **Image Processing**: Pillow
- **Document Export**: python-docx
- **Deployment**: Streamlit Cloud

## Project Structure

```
NoteVision/
├── app.py                          # Main application
├── requirements.txt                # Python dependencies
├── .gitignore                      # Git ignore rules
├── .streamlit/
│   └── secrets.toml.example       # API key template
└── README.md                       # This file
```

## Troubleshooting

### "API Key not configured" Error
- Make sure you created `.streamlit/secrets.toml` (local) or added secrets in Streamlit Cloud
- Verify your API key is valid

### "Rate limit exceeded" in GCP
- Check your API quota in Google Cloud Console
- Increase limits or wait for quota reset

### DOCX formatting issues
- The app uses basic Markdown-to-DOCX conversion
- For complex formulas, consider using the Markdown export and a dedicated converter

## License

This project is for educational purposes.

## Support

For issues or questions, please contact the developer.

---

**Built with ❤️ using Streamlit and Google Gemini Vision**
