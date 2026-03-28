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

## One-Page PDF Enforcement
- All 4 PDF export functions use a 5-level compression retry loop (`_PDF_COMPRESSION_LEVELS`)
- After building each PDF, `_count_pdf_pages()` checks page count via pdfplumber
- If >1 page, the next compression level is applied and the PDF is rebuilt
- Compression levels reduce: side margins (18mm→12mm), section spacing, leading, font size (9→8pt at level 3+)
- Font-only reduction happens at levels 3 and 4 to preserve readability as long as possible
- DOCX exports use tighter margins (1.5cm sides, 1.0cm top/bottom) and tighter spacing (space_after=1pt, section header space_before=5pt)

## AI Content Limits
- Summary: max 2-3 sentences
- Experience: max 4 most recent jobs, max 2-3 bullet points per job
- Skills: max 8 technical + 4 soft skills
- Optional sections (courses, projects): max 3 items each

## Design
- Hebrew RTL interface
- White background (#ffffff), logo blue (#2b56e0) accent, dark navy (#022559) secondary
- Homepage: CareerUp logo image in header, two CTA cards (blue filled + white/blue outlined)
- Favicon: logo_icon.png (blue rounded square with trend arrow), logo_full.png in header
- Button text: "בנה קו״ח חדשים" (primary/blue), "שפר קו״ח קיימים" (secondary/white+blue border)
- Assistant Google Font, logo 56px height in header, 18px buttons
- Modern rounded corners (14px), subtle shadows
- Mobile-first responsive design
