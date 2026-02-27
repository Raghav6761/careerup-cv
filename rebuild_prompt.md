# CV-Master AI - Full Rebuild Prompt for Replit

## Copy everything below this line and paste into a new Replit project:

---

Build a Hebrew (RTL) Streamlit web application called "Career Up | CV Master AI" for creating and improving professional resumes/CVs using AI. The entire interface must be in Hebrew with full RTL support.

## Branding & Meta
- Page title: "Career Up | CV Master AI"
- Page icon: 📄
- Add `<meta name="robots" content="noindex, nofollow">` to prevent indexing
- Logo text: "📄 CV-Master AI" with subtitle "כלי חכם ליצירה ושיפור קורות חיים מקצועיים"

## Tech Stack
- **Framework**: Streamlit (Python), run with `streamlit run app.py --server.port 5000`
- **AI**: OpenAI GPT-5 via Replit AI Integrations (`python_openai_ai_integrations`). Use environment variables `AI_INTEGRATIONS_OPENAI_API_KEY` and `AI_INTEGRATIONS_OPENAI_BASE_URL` for the OpenAI client. No separate API key needed
- **File Processing**: pdfplumber (PDF extraction), python-docx (DOCX extraction), native Python (TXT)
- **PDF Export**: ReportLab with custom Hebrew font "Assistant" (Google Font, download Regular and Bold TTF files to `fonts/` directory)
- **DOCX Export**: python-docx with RTL XML manipulation
- **Hebrew BiDi in PDFs**: Use `python-bidi` (`get_display`) for visual reordering. Apply `get_display()` per line with `TA_RIGHT` alignment and NO `wordWrap='RTL'`. For long paragraphs, pre-wrap manually using `stringWidth()` before applying `get_display()` to each line
- **Retry Logic**: Use `tenacity` library with exponential backoff for AI calls (retry on 429/rate limit errors, up to 5 attempts)
- **Storage**: Streamlit session state only (no database)

## UI Design (IMPORTANT - Use Competitor-Style Clean UI)

The UI must look clean and professional, similar to modern Israeli CV builder sites. Key design principles:

### Color Scheme
- **Background**: Pure white (#ffffff)
- **Primary accent**: Bright blue (#0066FF) for primary buttons and interactive elements
- **Secondary**: Light blue borders (#7fb3d8) for card outlines on hover
- **Text**: Dark (#2c3e50) for headings, gray (#6b7c93) for secondary text
- **Borders**: Light gray (#e2e8f0) for card borders and separators
- **Section backgrounds**: Very light gray (#f8f9fa) for form section cards

### Home Page - Two Big Action Cards
The home page should display TWO large side-by-side cards (not buttons):
- **Right card (primary, blue background #0066FF, white text)**: "כתיבת קורות חיים" - for building CV from scratch
- **Left card (white background, blue border)**: "העלאת קו״ח קיימים" - for improving existing CV
- Cards should be large (180px+ height), with rounded corners (16px), and have hover effects

### Form Design (Build from Scratch)
The form should be organized in **white card sections with subtle shadows**, each containing:
- A section header on the right side with the section name in bold (e.g., "פרטים אישיים", "תקציר", "ניסיון תעסוקתי", "השכלה")
- Clean input fields with proper labels
- "פרטים נוספים" expandable section under personal details for optional fields
- Blue "+ הוסף..." links/buttons for adding more entries (experience, education, etc.)
- Proper spacing and visual hierarchy between sections

### General UI Rules
- All text right-aligned (RTL)
- Font: "Assistant" from Google Fonts (weights 300-800)
- Mobile-first responsive design (stack columns on mobile, full-width buttons)
- Step indicators (dots) showing progress in the improve flow (3 steps)
- Use `st.expander` for tips and collapsible sections
- Score display: large number with color (green >= 70, orange >= 50, red < 50)
- Download buttons styled with the accent blue color
- No emojis in section headers inside the exported CV documents (emojis are OK in the UI)

## Two Main User Flows

### Flow 1: Improve Existing CV (שיפור קורות חיים קיימים)

**Page 1 - Upload (`improve_upload`)**:
- Step indicator: dot 1 active
- File uploader accepting PDF, DOCX, TXT
- **Target position/job description field** (optional text area): Label "תפקיד יעד (אופציונלי)" with explanation: "ציין את שם התפקיד או הדבק את תיאור המשרה המלא - הבינה המלאכותית תחלץ מילות מפתח ותשלב אותן בקורות החיים כדי לעבור מערכות סינון ATS"
- Placeholder: "למשל: מנהל משאבי אנוש, מפתח Full Stack...\nאו הדבק כאן את תיאור המשרה המלא מהמודעה"
- "נתח את קורות החיים" primary button
- Processing status with progress messages

**Page 2 - Review (`improve_review`)**:
- Step indicator: dot 2 active
- Score display (0-100) at top
- Expandable tips section
- Expandable recommended keywords section
- **For each section**: Side-by-side comparison (original vs. improved) with explanation
- Radio buttons per section: "השתמש בגרסה המשופרת" / "השאר מקור" / "ערוך ידנית"
- Manual edit text area when "ערוך ידנית" is selected
- "צור קורות חיים סופיים" primary button

**Page 3 - Export (`improve_export`)**:
- Step indicator: dot 3 active
- Editable final preview: each section with editable title and content
- Delete section button (trash icon) per section
- "הוסף סעיף חדש" button
- **Hebrew download**: PDF and DOCX buttons
- **English translation section**: "תרגם לאנגלית" button, then English PDF and DOCX download buttons
- "חזרה לדף הבית" button

### Flow 2: Build from Scratch (כתיבת קורות חיים מאפס)

**Page 1 - Smart Form (`build_form`)**:
- **Target position field** (same as improve flow, at the top)
- **Personal Details section (פרטים אישיים)**:
  - Full name (שם מלא)
  - Phone (טלפון), Email (אימייל), City (עיר) - in 3 columns
  - LinkedIn URL (optional)
- **Professional Summary (תקציר מקצועי)**: Text area with hint "כתוב בקצרה על הרקע המקצועי שלך, או השאר ריק והבינה המלאכותית תכתוב עבורך"
- **Work Experience (ניסיון תעסוקתי)**: Dynamic list, each entry has:
  - Job title (תפקיד), Company (חברה), Period (תקופה) - in 3 columns
  - Achievements text area (הישגים)
  - Honors/distinctions field (הצטיינות - optional)
  - Delete button, "הוסף תפקיד נוסף" button
- **Education (השכלה)**: Dynamic list, each entry has:
  - Degree (תואר/תעודה), Institution (מוסד), Year (שנת סיום) - in 3 columns
  - Honors field (optional)
  - Delete button, "הוסף השכלה נוספת" button
- **Skills (מיומנויות)**: Technical skills + Soft skills text inputs
- **Languages (שפות)**: Dynamic list with language name + level, default: Hebrew (שפת אם) + English
- **Volunteering (התנדבות בקהילה)**: Optional text area
- **Independent Projects (פרויקטים עצמאיים)**: Optional text area
- **Additional Info (מידע נוסף)**: Text area for courses, certifications, military service
- "צור קורות חיים מקצועיים" primary button
- Validation: require at least full name + one substantive field

**Page 2 - Preview & Edit (`build_preview`)**:
- All fields editable (structured form, not raw text)
- Same sections as the form but populated with AI-enhanced data
- Achievements displayed as text area (one per line)
- Volunteering, Projects, Additional as text areas
- **Hebrew download**: PDF and DOCX
- **English translation**: Translate button, then English PDF and DOCX
- "חזרה לדף הבית" button

## AI Engine - CRITICAL PROMPTS

### Main CV Improvement/Generation Prompt (for BOTH flows)

Use the following prompt as the system prompt for the AI, adapted for each flow. This is the core prompt:

```
אתה מומחה לכתיבת קורות חיים ולמיצוב מועמדים לשוק העבודה הישראלי בשנת 2026, עבור כלל המקצועות והתחומים.

בהתבסס על קורות החיים שסופקו, שפר את המסמך תוך שמירה מלאה על כלל המידע הקיים. אין להשמיט תפקידים או תקופות. יש לשמר תמונה מלאה ורציפה של הקריירה, ולנסח אותה כך שתשקף זהות מקצועית ברורה, ערך עסקי, הישגים והתאמה לעולם העבודה החדש.

אם סופקה משרה ספציפית:
* התאם את המסמך אליה באופן ממוקד.
* שלב מילות מפתח רלוונטיות מתוך תיאור המשרה.
* הדגש ניסיון, מיומנויות והישגים התואמים לדרישות.

אם לא סופקה משרה:
* בנה מיצוב מקצועי רחב אך ממוקד תחום.
* הדגש מיומנויות ליבה חוצות תפקידים.
* שמור על ניסוח מותאם לשוק הישראלי.

כללי עבודה:
* כתוב בעברית בלבד.
* אל תמחק מידע קיים.
* אל תמציא נתונים שלא הופיעו במקור.
* שמור על רצף כרונולוגי יורד לפי שנים בלבד.
* הסר רק פרטים שאינם מקצועיים כגון תעודת זהות, מצב משפחתי ותמונה.
* ניסוח מקצועי, ישיר, בהיר וללא קלישאות.

עקרונות חובה לשוק העבודה 2026:
* הגדר זהות מקצועית עקבית וברורה כבר בתחילת המסמך.
* הדגש תרומה עסקית והשפעה בכל תפקיד.
* נסח אחריות בצורה תוצאתית ולא כרשימת משימות בלבד.
* הצג הישגים מדידים אם קיימים במקור.
* הדגש מיומנויות ליבה חוצות תפקידים.
* צור חוט מקצועי מקשר בין התחנות.
* הדגש למידה, הסתגלות טכנולוגית ושיפור תהליכים אם קיימים.
* אם מופיע ניסיון בעבודה עם כלי בינה מלאכותית, אוטומציה או כלים דיגיטליים מתקדמים, הדגש זאת והצג את ההשפעה המקצועית או העסקית.
* אם לא מופיע שימוש ישיר בכלי AI, אך קיימת אינדיקציה ללמידה עצמאית, חדשנות או אוריינות דיגיטלית, נסח זאת כחוזקה מקצועית.
* אין להמציא ניסיון בעולמות AI שלא הופיע במקור.
* ודא שהמסמך תומך גם בקריאה אנושית וגם במערכות סינון אוטומטיות.

התאמה ל-ATS:
* שלב מילות מפתח רלוונטיות באופן טבעי בתוך תיאורי התפקידים ולא רק ברשימת מיומנויות.
* השתמש בכותרות ברורות וסטנדרטיות.
* הימנע מעיצוב מורכב או ניסוחים עמומים.
* ודא שמיומנויות מרכזיות מופיעות לפחות פעמיים במסמך בהקשר מקצועי אמיתי.
* שלב מונחים רלוונטיים הקשורים לחדשנות, דיגיטציה ו-AI אם הופיעו במקור.
* שמור על ניסוח ברור וקצר כדי לאפשר סריקה מהירה.

סדר מחייב של קורות החיים:
1. פרטים אישיים - שם מלא, טלפון, אימייל, לינקדאין, עיר מגורים אופציונלית.
2. תקציר מקצועי - 2-4 משפטים הכוללים: זהות מקצועית, תחום התמחות, היקף ניסיון, ערך מקצועי מרכזי, מיומנויות ליבה מרכזיות.
3. ניסיון תעסוקתי - לכל תפקיד: שנים → שם חברה → תפקיד → 2-4 נקודות תמציתיות המדגישות אחריות, ערך והשפעה.
4. שירות צבאי - אם מופיע במקור.
5. השכלה - שנים → מוסד → תואר → תחום לימוד.
6. מיומנויות - מחולקות לקבוצות ברורות כגון מיומנויות מקצועיות, כלים וטכנולוגיות, שפות ויכולות בין-אישיות.
7. קורסים, הסמכות ופרויקטים - אם מופיעים במקור.
```

### Adaptation for "Improve Existing CV" Flow (analyze_cv)

Wrap the above prompt with these additional instructions:

- Tell the AI to return JSON format with this structure:
```json
{
    "sections": [
        {
            "title": "שם הסעיף",
            "original": "הטקסט המקורי המדויק מקורות החיים",
            "improved": "הגרסה המשופרת",
            "explanation": "הסבר קצר מה חיזק השיפור מבחינת זהות מקצועית, ערך עסקי, הסתגלות טכנולוגית והתאמה לשוק"
        }
    ],
    "general_tips": ["טיפ 1", "טיפ 2"],
    "keywords_to_add": ["מילת מפתח 1", "מילת מפתח 2"],
    "score": 72
}
```
- Stress that the "original" field MUST contain the exact original text from the CV - never leave it empty
- If a section doesn't exist but is recommended, write "לא קיים במקור" in the original field
- Minimum 3 sections
- Score 0-100 reflecting original CV quality
- If a target position/job description is provided, add specific ATS instructions to extract keywords from the job description and weave them naturally into the improved text
- IMPORTANT JSON safety rule: Tell the AI not to use parentheses () or double quotes "" inside Hebrew text values (use dashes or commas instead) to avoid JSON parsing errors
- Implement robust JSON parsing with multiple fallback repair attempts (regex fixes, character-by-character repair, control character removal)

### Adaptation for "Build from Scratch" Flow (generate_cv_from_form)

Use the same core prompt principles but adapt for structured form data input:
- Tell the AI to return JSON with this structure:
```json
{
    "full_name": "שם מלא",
    "contact": {"phone": "טלפון", "email": "אימייל", "city": "עיר", "linkedin": "לינקדאין"},
    "professional_summary": "תקציר מקצועי של 2-4 משפטים",
    "experience": [
        {"title": "תפקיד", "company": "חברה", "period": "תקופה", "achievements": ["הישג 1", "הישג 2"], "honors": "הצטיינות אם יש"}
    ],
    "education": [{"degree": "תואר", "institution": "מוסד", "year": "שנה", "honors": "הצטיינות אם יש"}],
    "skills": {"technical": ["מיומנות"], "soft": ["מיומנות"]},
    "languages": [{"language": "שפה", "level": "רמה"}],
    "volunteering": ["פעילות התנדבותית"],
    "projects": ["פרויקט עצמאי"],
    "additional": ["פריט נוסף"]
}
```
- Preserve original factual data (name, phone, email, dates, institutions)
- Only improve phrasing of achievements, summary, and skills
- Never invent information not in the form
- Write professional summary if user left it blank
- If target position/job description is provided, extract keywords and integrate them naturally

### Section Edit Prompt (improve_section_text)
For inline editing of individual sections:
- System prompt instructing to improve text professionally
- Use strong action verbs
- Add quantitative metrics where possible
- Dates in years only
- Return only improved text, no explanations
- Same parentheses/quotes safety rule

### Translation Prompts

**For free-text CV (improve flow) - translate_cv_to_english:**
- Maintain exact structure and formatting
- Keep section markers like `=== Section Name ===` but translate section names
- Transliterate or translate Hebrew company names to English (NEVER output reversed Hebrew)
- Keep emails, phone numbers, URLs unchanged
- Translate degrees to standard English equivalents
- Don't add repetitive sub-headers like "Selected Achievements" under each job
- Military service: translate as descriptive text, not job entries

**For structured data (build flow) - translate_cv_data_to_english:**
- Return same JSON structure but in English
- Same transliteration rules for company names
- Professional CV language and action verbs

## Export System - Critical Technical Details

### PDF Export (Hebrew)
- **Page**: A4, margins 18mm left/right, 12mm top/bottom
- **Font**: Register "Assistant-Regular.ttf" and "Assistant-Bold.ttf" from `fonts/` directory using `pdfmetrics.registerFont`
- **Hebrew BiDi rendering** (most critical technical challenge):
  - Use `python-bidi` library's `get_display()` function to visually reorder Hebrew text
  - Apply `get_display()` to each INDIVIDUAL LINE, not paragraphs
  - Use `TA_RIGHT` alignment for all Hebrew text
  - Do NOT use `wordWrap='RTL'` - it conflicts with `get_display()` causing double-reversal
  - For long text that needs wrapping: calculate line width using `stringWidth()`, split into lines manually at word boundaries, then apply `get_display()` to each line separately
  - Use a width buffer (e.g., 170mm instead of full 174mm available) to prevent ReportLab from re-wrapping already-wrapped lines
- **Personal details formatting**: Name = bold, 20pt, centered, dark color (#2c3e50). Contact info (phone | email | city | linkedin) = 9pt, gray (#555555), centered, pipe-separated. NO section header "פרטים אישיים". Add 2pt horizontal line separator below contact info
- **Section headers**: Bold, colored, with bottom border line (1pt, #7fb3d8)
- **Job entries**: Period | Title | Company format, bold. Light separator between different roles
- **Bullet points**: Prefixed with bullet, proper RTL indentation
- **Clean text function**: Remove hidden Unicode LTR/RTL marks, standardize quotes and parentheses

### PDF Export (English)
- Same layout but LTR: `TA_LEFT` alignment, no BiDi reshaping
- Same personal details formatting (name bold+centered, contact gray+centered)
- Deduplicate consecutive identical section headers (track `last_header`)

### DOCX Export (Hebrew)
- Font: Assistant, 10pt
- Margins: 1.8cm left/right, 1.2cm top/bottom
- **RTL in DOCX**: Manipulate XML using `OxmlElement` to add `<w:bidi>` to paragraph properties and `<w:rtl>` + `<w:cs>` to run properties
- Personal details: Name = bold, 16pt, centered. Contact = 9pt, gray, centered. No section header
- Job headers detected by regex matching year patterns `(19|20)\d{2}` with dashes/pipes (NOT matching phone numbers)

### DOCX Export (English)
- Same structure but LTR (no RTL XML manipulation)
- Same deduplication of consecutive headers

### Job Header Detection
Use regex to identify job/role header lines (for bold formatting):
- Match year patterns `(19|20)\d{2}` (NOT `\d{4}` which catches phone numbers)
- Look for separator characters (dash, pipe) between year and text
- Also match keywords like "present", "היום", "נוכחי"
- Phone numbers like "050-333-6915" must NOT be falsely detected as job headers

## File Structure
```
app.py              - Main Streamlit app with page routing and all page render functions
ai_engine.py        - AI logic (CV analysis, generation, translation, section improvement)
file_processor.py   - File upload processing and text extraction (PDF/DOCX/TXT)
export_utils.py     - All PDF and DOCX export functions (Hebrew + English, structured + free-text)
styles.py           - Custom CSS injection function for RTL Hebrew layout and theming
fonts/              - Assistant-Regular.ttf and Assistant-Bold.ttf font files
.streamlit/config.toml - Streamlit server configuration
```

## Important Implementation Notes

1. **AI API calls**: Use `max_completion_tokens=16384` for CV analysis/generation. Implement retry with tenacity (5 attempts, exponential backoff 2-60 seconds)
2. **JSON safety**: The AI sometimes returns malformed JSON with Hebrew text. Implement a multi-stage JSON repair function: First try direct `json.loads`, then regex-based quote escaping, then character-by-character repair (track string state, escape internal quotes), then remove control characters
3. **Session state**: Use Streamlit session state for ALL data persistence between pages. Initialize all state variables at app startup
4. **Page routing**: Use a `page` session state variable with a dictionary mapping page names to render functions
5. **CVs must fit on ONE PAGE**: Instruct the AI to keep content concise. Output must fit a single A4 page
6. **No "קורות חיים" title**: Never add headers like "קורות חיים" or "קורות חיים משופרים" to the document - just the content sections

## Dependencies (Python packages needed)
- streamlit
- openai
- pdfplumber
- python-docx
- reportlab
- python-bidi
- tenacity
