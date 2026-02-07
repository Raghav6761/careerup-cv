# CV-Master AI

## Overview
CV-Master AI is a Hebrew (RTL) Streamlit application for creating and improving professional resumes/CVs using AI (OpenAI via Replit AI Integrations).

## Architecture
- **Framework**: Streamlit (Python)
- **AI**: OpenAI GPT-5 via Replit AI Integrations (no API key needed)
- **File Processing**: pdfplumber (PDF), python-docx (DOCX), native Python (TXT)
- **Export**: ReportLab (PDF), python-docx (DOCX)
- **Styling**: Custom CSS injected via Streamlit markdown (RTL, Assistant font, pastel blue theme)
- **Storage**: Streamlit session state (no database)

## Project Structure
```
app.py              - Main Streamlit app with page routing
ai_engine.py        - AI logic (CV analysis, interview chat, CV generation)
file_processor.py   - File upload and text extraction
export_utils.py     - PDF and DOCX export functions
styles.py           - Custom CSS for RTL Hebrew layout and theming
fonts/              - Assistant font files for PDF export
.streamlit/         - Streamlit configuration
```

## Key Features
1. **Improve Existing CV**: Upload PDF/DOCX/TXT → AI analysis → side-by-side comparison → approve/edit per section → export
2. **Build from Scratch**: Smart form with structured fields → AI polishes content → preview/edit → export
3. **English Translation Export**: Both flows support AI-powered translation to English with PDF/DOCX export in LTR format

## User Flow Pages
- `home` - Two path selection cards
- `improve_upload` - File upload page
- `improve_review` - Side-by-side comparison with approve/edit
- `improve_export` - Final preview and download
- `build_form` - Smart form for filling CV fields (personal details, experience, education, skills, languages)
- `build_preview` - Generated CV preview and download

## Running
```
streamlit run app.py --server.port 5000
```

## Design
- Hebrew RTL interface
- White background, pastel blue (#7fb3d8) accent, light gray borders
- Assistant Google Font
- Mobile-first responsive design
