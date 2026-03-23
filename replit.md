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
3. **Language Selector (Improve flow)**: Radio button on upload page lets user choose Hebrew or English for the improved CV; English mode bypasses the separate translation step and exports directly via English export functions
4. **English Translation Export**: Both flows support AI-powered translation to English with PDF/DOCX export in LTR format
5. **Empty section filtering**: All export functions use `_is_empty_content()` and `_filter_list()` to skip placeholder/empty sections universally

## User Flow Pages
- `home` - Two path selection cards
- `improve_upload` - File upload page
- `improve_review` - Side-by-side comparison with approve/edit
- `improve_export` - Final preview and download
- `build_form` - Smart form for filling CV fields (personal details, experience, education, skills, languages, military service, volunteering, projects, additional info)
- `build_preview` - Generated CV preview and download

## Running
```
streamlit run app.py --server.port 5000
```

## Export Formatting
- PDF and DOCX exports use identical visual properties across all flows (build/improve, Hebrew/English)
- Shared DOCX helper functions: `_add_docx_body_paragraph`, `_add_docx_bullet_paragraph`, `_add_docx_job_header`, `_add_docx_separator_line`
- Font sizes: name=20pt, section header=12pt, body/job/bullet=9pt, contact=9pt
- Line spacing: body/job leading=13pt, bullet leading=12pt, name leading=24pt, contact leading=12pt
- Section headers use a separate blue (#7fb3d8) separator line underneath
- Personal details: name bold centered + contact pipe-separated centered + dark HR separator
- Contact labels (טלפון, אימייל, etc.) are stripped via `_extract_contact_value()` (case-insensitive)
- Bullet paragraphs have 8pt indent (rightIndent for RTL, leftIndent for LTR)
- Military service rendered as separate section "שירות צבאי / לאומי" (optional), ordered: languages → military → volunteering → projects → additional
- Military lines filtered from personal/contact section in improve exports via `_is_military_line()` helper
- Optional sections (military, volunteering, projects, additional) only appear if user provided content

## Design
- Hebrew RTL interface
- White background (#ffffff), vibrant blue (#0066FF) accent, dark text (#1a1a2e)
- Homepage: "CV-Master" (dark) + "AI" (blue) header, two CTA buttons (filled blue + outlined)
- Button text: "כתיבת קורות חיים" (primary/filled), "העלאת קו״ח קיימים" (secondary/outlined)
- Assistant Google Font, 38px header, 18px buttons
- Modern rounded corners (14px), subtle shadows
- Mobile-first responsive design
