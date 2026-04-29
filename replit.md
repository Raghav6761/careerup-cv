# CV-Master AI

## Overview
CV-Master AI is a Hebrew (RTL) Streamlit application for creating and improving professional resumes/CVs using AI (OpenAI via Replit AI Integrations).

## Architecture
- **Framework**: Streamlit (Python)
- **AI**: OpenAI GPT-5 via Replit AI Integrations (no API key needed)
- **File Processing**: pdfplumber (PDF), python-docx (DOCX), native Python (TXT)
- **Export**: ReportLab (PDF), python-docx (DOCX)
- **Section Reorder**: streamlit-sortables (drag-and-drop in improve_export)
- **Styling**: Custom CSS injected via Streamlit markdown (RTL, Assistant font, pastel blue theme)
- **Storage**: Streamlit session state + browser localStorage (streamlit-js-eval)
- **Persistence**: persistence.py — auto-saves all form data and AI results to localStorage; restored on page refresh or session timeout

## Project Structure
```
app.py              - Main Streamlit app with page routing
ai_engine.py        - AI logic (CV analysis, interview chat, CV generation)
file_processor.py   - File upload and text extraction
export_utils.py     - PDF and DOCX export functions
persistence.py      - Browser localStorage persistence (init/save/clear)
styles.py           - Custom CSS for RTL Hebrew layout and theming
fonts/              - Assistant font files for PDF export
.streamlit/         - Streamlit configuration
```

## Key Features
1. **Improve Existing CV**: Upload PDF/DOCX/TXT → AI analysis → side-by-side comparison → approve/edit per section → export
2. **Build from Scratch**: Smart form with structured fields → AI polishes content → preview/edit → export
3. **Language Selector (Improve flow)**: Radio button on upload page lets user choose Hebrew or English for the improved CV; English mode bypasses the separate translation step and exports directly via English export functions
4. **English Translation Export**: Both flows support AI-powered translation to English with PDF/DOCX export in LTR format
5. **Empty section filtering**: All export functions use `_is_empty_content()` and `_filter_list()` to skip placeholder/empty sections universally; `_EMPTY_PLACEHOLDERS` includes plural "לא צויינו" in addition to "לא צויין"; `render_improve_reorder` pre-filters export_sections using `_is_empty_content` before building the cache key
6. **CV document title**: Optional "כותרת קורות החיים" field in the reorder/export step; appears as a centered bold 14pt heading at the top of all exported PDF/DOCX files; all 4 improve-flow export functions accept `cv_title: str = ""` parameter
7. **Build→Improve handoff**: On the build_preview page, a secondary recommendation button "🔍 בדוק את הניסוח דרך כלי השיפור" appears below the DOCX download button. Clicking it converts the generated_cv dict to plain text via `_cv_dict_to_text()`, stores it in `staged_cv_text` + `staged_from_build=True` session keys, and navigates to improve_upload. On improve_upload, when `staged_from_build` is set: a green success banner appears ("✅ קורות החיים שיצרת מוכנים לבדיקה..."), the Analyze button enables without requiring a file upload, staged text is used as CV input instead of file extraction, and the staged state is cleared after analysis or when the user clicks "× בטל". Uploaded files take precedence over staged text. Staged keys are not persisted to localStorage and are cleared in `reset_improve()`.
8. **Per-section consultation chat (Build flow)**: Each content section in the build-from-scratch form has a "💬 התייעץ" button that opens an INLINE chat panel beneath that section's inputs (inside the same card) with an OpenAI GPT-5 career advisor focused on that specific section (target/personal/summary/experience/education/skills/military/volunteering/projects/additional). Only one panel is open at a time — opening another section closes the previous one (`st.session_state.active_consultation` holds the open section's key). Button label toggles between "💬 התייעץ" and "✖ סגור התייעצות". Chat history kept per-section in `st.session_state.consultation_chats` and persisted to browser localStorage (last 30 messages per section) via `persistence.py`. Backend: `section_consultation_reply()` and `section_consultation_greeting()` in `ai_engine.py` (with `_SECTION_LABELS` and `_SECTION_GUIDANCE` dicts). UI helpers in `app.py`: `_render_consult_button(section_key)` (toggle in section header) and `_render_consult_panel(section_key)` (renders inline chat box + clear button + chat input only when that section is active; called at the bottom of each section's container).

## User Flow Pages
- `home` - Two path selection cards
- `improve_upload` - File upload page
- `improve_review` - Side-by-side comparison with approve/edit
- `improve_export` - Step 3: content editing only (title, text, add/delete sections)
- `improve_reorder` - Step 4: drag-and-drop section reorder (navy blue ⠿ handles) + export/download
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

## AI Content Enrichment (per-job detail)
- Each job bullet must include: action + specific technology/tool + operational/business impact
- One-page mode: 3-5 bullets per job (was 2-4)
- Two-page mode: 4-6 bullets per job (was up to 5)
- Skills section: minimum 12 items, including standard industry skills inferred from experience
- If no academic degree detected: general_tips includes a recommendation to add high-school major and school name
- general_tips expander is open by default (expanded=True)
- Professional summary (1-page): 2-3 rich sentences: title+years+tech → expertise+value → standout trait; continuous paragraph, no lists/dashes
- Professional summary (2-page): 3-4 sentences; same structure with optional 4th sentence on personal strength

## One-Page / Two-Page PDF Selector
- Both flows (improve_upload + build_form) show a "📄 כמה עמודים תרצו?" radio card: "נסה להכניס לעמוד אחד (מומלץ)" (default) or "עד שני עמודים"
- Session keys: `improve_max_pages` (int 1 or 2), `build_max_pages` (int 1 or 2)
- `reset_improve()` clears `improve_max_pages` and its widget key `improve_pages_radio`
- All 4 PDF export functions accept `max_pages: int = 1`; compression loop stops when `_count_pdf_pages() <= max_pages`
- "עמוד אחד" is an aspiration, not a hard limit — AI writes all content and PDF compression tries to fit; if it can't, 2 pages is acceptable
- "עד שני עמודים" is a hard maximum — AI must not exceed 2 pages
- `_PDF_COMPRESSION_LEVELS` has 3 levels (10pt → 9pt → 8pt minimum); margins reduced: 15mm → 13mm → 11mm (was 18mm → 16mm → 14mm) to better fill the page
- DOCX exports are unchanged (no page-count enforcement)

## AI Content Guidelines
### One-page mode (aspiration, not hard limit)
- Include ALL relevant experience — no job or achievement should be omitted
- Summary: 2-3 focused sentences
- Per job: 2-4 concise bullet points, one line each
- AI instructed: "prefer 2 pages over cutting important content"

### Two-page mode (hard maximum)
- Include ALL relevant experience
- Summary: 3-4 sentences
- Per job: up to 5 concise bullet points
- Hard limit: must not exceed 2 pages

## Design
- Hebrew RTL interface
- White background (#ffffff), logo blue (#2b56e0) accent, dark navy (#022559) secondary
- Homepage: CareerUp logo image in header, two CTA cards (blue filled + white/blue outlined)
- Favicon: logo_icon.png (blue rounded square with trend arrow), logo_full.png in header
- Button text: "בנה קו״ח חדשים" (primary/blue), "שפר קו״ח קיימים" (secondary/white+blue border)
- Assistant Google Font, logo 56px height in header, 18px buttons
- Modern rounded corners (14px), subtle shadows
- Mobile-first responsive design
