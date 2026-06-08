import os
import re
import json
import logging
import concurrent.futures
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AI_INTEGRATIONS_OPENAI_API_KEY = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
AI_INTEGRATIONS_OPENAI_BASE_URL = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")

client = OpenAI(
    api_key=AI_INTEGRATIONS_OPENAI_API_KEY,
    base_url=AI_INTEGRATIONS_OPENAI_BASE_URL
)


def _sanitize_ai_output(text: str) -> str:
    """Replace em/en dashes with a regular hyphen and collapse double-hyphens.

    Safety net: even if the AI ignores the prompt-level instruction, em dashes
    (U+2014 —) and en dashes (U+2013 –) are stripped here before any caller
    sees the text. Double hyphens produced by the substitution (or by the AI
    itself) are then collapsed to a single hyphen.

    Hebrew abbreviations that use a geresh-apostrophe (מנכ"ל, ד"ר …) are not
    affected because they contain no hyphen characters.
    """
    text = text.replace('\u2014', '-').replace('\u2013', '-')
    text = re.sub(r'-{2,}', '-', text)
    return text


def should_retry(exception: BaseException) -> bool:
    error_msg = str(exception)
    return (
        "429" in error_msg
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower()
        or "rate limit" in error_msg.lower()
        or "empty_response" in error_msg
        or (hasattr(exception, "status_code") and exception.status_code == 429)
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception(should_retry),
    reraise=True
)
def call_ai(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_completion_tokens=16384
    )
    choice = response.choices[0]
    content = choice.message.content or ""
    finish_reason = choice.finish_reason

    logger.info(f"AI response: {len(content)} chars, finish_reason={finish_reason}")

    if not content.strip():
        logger.warning(f"Empty AI response (finish_reason={finish_reason}), retrying...")
        raise Exception("empty_response: AI returned empty content")

    if finish_reason == "length":
        logger.warning("Response was truncated due to max_completion_tokens")

    return _sanitize_ai_output(content)


def _safe_json_parse(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fixed = text
    fixed = re.sub(r'(?<=: )"([^"]*)"([^",\n\r\]\}]*)(")', lambda m: ': "' + m.group(1) + '\\"' + m.group(2) + '"', fixed)

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    fixed = text
    in_string = False
    escape_next = False
    result_chars = []
    i = 0
    while i < len(fixed):
        c = fixed[i]
        if escape_next:
            result_chars.append(c)
            escape_next = False
            i += 1
            continue
        if c == '\\':
            result_chars.append(c)
            escape_next = True
            i += 1
            continue
        if c == '"':
            if not in_string:
                in_string = True
                result_chars.append(c)
            else:
                rest = fixed[i+1:].lstrip()
                if rest and rest[0] in (',', '}', ']', ':'):
                    in_string = False
                    result_chars.append(c)
                elif not rest:
                    in_string = False
                    result_chars.append(c)
                else:
                    result_chars.append('\\"')
        else:
            result_chars.append(c)
        i += 1

    repaired = "".join(result_chars)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    repaired2 = re.sub(r'[\x00-\x1f]', lambda m: '\\n' if m.group() == '\n' else '', text)
    try:
        return json.loads(repaired2)
    except json.JSONDecodeError as e:
        logger.error(f"All JSON repair attempts failed: {e}")
        raise


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from an AI JSON response."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _parse_cv_sections(
    cv_text: str,
    target_instruction: str,
    lang_rule: str,
    is_english: bool,
) -> dict:
    """
    Phase 1 — Section discovery & metadata only. NO original text copied.
    Outputs ONLY a list of section title strings + score/tips/keywords.
    Output is ~50-150 tokens regardless of CV length (~5-10 seconds).
    Raises json.JSONDecodeError on parse failure so caller can fall back.
    """
    if is_english:
        system_prompt = f"""You are a CV analysis expert. Your task is to IDENTIFY SECTIONS ONLY — do NOT copy any CV text, do NOT write any improved content.
{target_instruction}

Rules:
{lang_rule}
* List only sections that actually exist in the CV. Do not invent sections.
* The first section covering contact info must be titled exactly "Personal Details".
* If a "Miscellaneous" section exists, include it as its own entry.
* Output section titles as a plain JSON array of strings — no objects, no original text.

Score rubric (0-100, sum exactly):
- Contact details (0-10): name + phone + email = 10, one missing = 5, none = 0
- Professional summary (0-15): present and strong = 15, weak = 8, absent = 0
- Work experience (0-35): 2+ positions with achievements + dates = 35, 2+ without achievements = 20, 1 position = 15, none = 0
- Education (0-15): degree + institution + years = 15, partial = 8, absent = 0
- Skills (0-15): 5+ skills = 15, 1-4 = 8, absent = 0
- Languages (0-5): at least 1 with proficiency level = 5, without level = 3, absent = 0
- Bonus (0-5): LinkedIn / volunteering / projects = 5

Return JSON only (no markdown, no code fences):
{{
  "sections": ["Personal Details", "Professional Summary", "Work Experience"],
  "general_tips": ["tip 1", "tip 2"],
  "keywords_to_add": ["keyword 1"],
  "score": 72
}}"""
        user_prompt = f"""Identify the section names of this CV. Return ONLY the title strings — do not copy any CV text.

---
{cv_text}
---"""
    else:
        system_prompt = f"""אתה מומחה לניתוח קורות חיים. משימתך היא לזהות את שמות הסעיפים בלבד — אל תעתיק טקסט מהקו"ח ואל תכתוב תוכן משופר.
{target_instruction}

כללים:
{lang_rule}
* רשום רק סעיפים שקיימים בפועל בקורות החיים. אל תמציא סעיפים.
* כותרת הסעיף הראשון (פרטי קשר) חייבת להיות בדיוק "פרטים אישיים".
* אם קיים סעיף "שונות" — כלול אותו כפריט נפרד.
* פלט את שמות הסעיפים כמערך JSON של מחרוזות בלבד — ללא אובייקטים, ללא טקסט מקורי.

רובריקת ציון (0-100, חבר במדויק):
- פרטי קשר (0-10): שם + טלפון + אימייל = 10, חסר אחד = 5, אין כלל = 0
- תקציר מקצועי (0-15): קיים ואיכותי עם זהות מקצועית = 15, קיים אך חלש = 8, לא קיים = 0
- ניסיון תעסוקתי (0-35): 2+ תפקידים עם הישגים ותאריכים = 35, 2+ ללא הישגים = 20, תפקיד אחד = 15, אין = 0
- השכלה (0-15): תואר + מוסד + שנים = 15, חלקי = 8, לא קיים = 0
- מיומנויות (0-15): 5+ מיומנויות = 15, 1-4 = 8, לא קיים = 0
- שפות (0-5): שפה אחת לפחות עם רמה = 5, ללא רמה = 3, לא קיים = 0
- בונוס (0-5): לינקדאין / התנדבות / פרויקטים = 5
- אם בקורות החיים אין תואר אקדמי, הוסף ב-general_tips המלצה לציין את המגמה ושם התיכון.
- general_tips: כלול רק מידע חסר שהמשתמש צריך להוסיף בעצמו (לינקדאין, מגמה ותיכון, הסמכות, פרויקטים). אל תכלול עצות ניסוח, עיצוב או פרמוט — אלה אינם רלוונטיים כאן.

החזר JSON בלבד (ללא markdown, ללא סימני קוד):
{{
  "sections": ["פרטים אישיים", "תקציר מקצועי", "ניסיון תעסוקתי"],
  "general_tips": ["טיפ 1", "טיפ 2"],
  "keywords_to_add": ["מילת מפתח 1"],
  "score": 72
}}"""
        user_prompt = f"""זהה את שמות הסעיפים בקורות החיים הבאים. החזר רק את שמות הסעיפים — אל תעתיק טקסט מהקו"ח.

---
{cv_text}
---"""

    raw = call_ai(system_prompt, user_prompt)
    logger.info(f"Phase 1 response: {len(raw)} chars")
    return _safe_json_parse(_strip_code_fences(raw))


def _improve_one_section(
    section_title: str,
    cv_text: str,
    expert_intro: str,
    work_context: str,
    target_instruction: str,
    lang_rule: str,
    content_limits_block: str,
    _pages_tech_note: str,
    is_english: bool,
    keywords_to_add: list = None,
) -> dict:
    """
    Phase 2 — Single-section extract + improve.
    Called concurrently for every section via ThreadPoolExecutor.
    Receives the full CV text and the section title only.
    Finds the section itself, copies the original, then improves it.
    Returns {"original": "...", "improved": "...", "explanation": "..."}.
    """
    _kws = [k for k in (keywords_to_add or []) if k and str(k).strip()]
    if _kws and is_english:
        keywords_block = f"Keywords to weave in naturally (only where relevant to this section): {', '.join(_kws)}\n"
    elif _kws:
        keywords_block = f"מילות מפתח לשילוב טבעי בטקסט (רק אם רלוונטיות לסעיף זה): {', '.join(_kws)}\n"
    else:
        keywords_block = ""

    if is_english:
        system_prompt = f"""{expert_intro}

{work_context}
{target_instruction}

Rules:
{lang_rule}
* Do not invent information not present in the original.
* Include ALL positions that appear in the original — never omit any.
* Professional, direct, clear language without clichés.
* Remove non-professional details (ID, family status, photo).
* {_pages_tech_note}
* Do not add sub-headings like "Key Achievements" — write achievement bullets directly.
* If this is the "Personal Details" section: consolidate all contact info. Title must be exactly "Personal Details".

Work market 2026 principles:
* Define a consistent professional identity.
* Emphasise business impact with quantifiable outcomes.
* Frame responsibilities as results, not task lists.
* Highlight cross-role core skills.
* Use strong action verbs: Led, Built, Launched, Delivered, Optimised, Scaled.

{keywords_block}
{content_limits_block}

Task: work on ONLY the "{section_title}" section from this CV.
1. Locate the section and copy its exact original text into "original".
2. Write the improved version into "improved".
3. Write a brief explanation into "explanation".
Return JSON only (no markdown, no code fences):
{{"original": "exact text from CV", "improved": "improved section text", "explanation": "brief explanation"}}"""

        user_prompt = f"""Work on the "{section_title}" section from this CV.

Full CV:
---
{cv_text}
---"""

    else:
        system_prompt = f"""{expert_intro}

{work_context}
{target_instruction}

כללי עבודה:
{lang_rule}
* אל תמציא נתונים שלא הופיעו במקור.
* כלול את כל התפקידים שהופיעו במקור — אל תשמיט אף תפקיד בשום מקרה ובשום תנאי.
* ניסוח מקצועי, ישיר, בהיר וללא קלישאות.
* הסר רק פרטים שאינם מקצועיים כגון תעודת זהות, מצב משפחתי ותמונה.
* {_pages_tech_note}
* אל תוסיף כותרות משנה חוזרות — פשוט רשום נקודות ישירות.
* אל תשתמש בסוגריים עגולים בטקסט. צמצם משמעותית את השימוש במקפים, העדף פסיק, נקודה, או ניסוח מחדש. אסור להשתמש במקף ארוך (—) או בינוני (–), השתמש רק במקף קצר רגיל (-) של מקלדת ובמשורה. כתוב בסגנון אנושי, לא AI. קיצורים עבריים מוסכמים כגון מנכ"ל, משא"ן, ד"ר, מ"מ וכדומה, שמור אותם כפי שהם.
* אם זהו סעיף "פרטים אישיים" — מזג את כל פרטי הקשר מכל מקומות הופעתם בקו"ח. כותרת הסעיף תהיה בדיוק "פרטים אישיים". "פרופיל לינקדין"/"פרופיל לינקדאין" — חלץ את הערך שאחריהם.
* אם זהו סעיף "שונות" — בשדה improved כתוב משפט הסבר קצר בעברית שמסביר מה פוזר לאן.

עקרונות חובה לשוק העבודה 2026:
* הגדר זהות מקצועית עקבית וברורה.
* הדגש תרומה עסקית והשפעה בכל תפקיד; תרגם להשפעה מספרית אם אפשר.
* נסח אחריות בצורה תוצאתית ולא כרשימת משימות.
* זהה את 5 הכישורים הקריטיים ביותר הרלוונטיים לתפקיד היעד והבלט אותם.
* צור חוט מקצועי מקשר בין התחנות.
* הדגש למידה, הסתגלות טכנולוגית ושיפור תהליכים.
* השתמש בפעלים חזקים ואקטיביים (בצורת שם הפועל): הובלה, ניהול, פיתוח, יזמות, יישום, ייעול, הטמעה, הגדלה.
* אם מופיע ניסיון בעבודה עם כלי בינה מלאכותית, אוטומציה או כלים דיגיטליים מתקדמים, הדגש זאת.
* אין להמציא ניסיון בעולמות AI שלא הופיע במקור.

התאמה ל-ATS:
* שלב מילות מפתח רלוונטיות באופן טבעי.
* הימנע מעיצוב מורכב או ניסוחים עמומים.
* שמור על ניסוח ברור וקצר.
* אל תכתוב את המילה "ATS" בתוך טקסט קורות החיים עצמו — המושג הוא הנחיה פנימית בלבד.

{keywords_block}
{content_limits_block}

משימה: עבוד על הסעיף "{section_title}" בלבד מקורות החיים הבאים.
1. אתר את הסעיף והעתק את טקסטו המקורי המדויק לשדה "original".
2. כתוב גרסה משופרת לשדה "improved".
3. כתוב הסבר קצר לשדה "explanation".
החזר JSON בלבד (ללא markdown, ללא סימני קוד):
{{"original": "הטקסט המקורי המדויק מהקו\"ח", "improved": "הטקסט המשופר", "explanation": "הסבר קצר"}}"""

        user_prompt = f"""עבוד על הסעיף "{section_title}" מקורות החיים הבאים.

קורות החיים המלאים:
---
{cv_text}
---"""

    raw = call_ai(system_prompt, user_prompt)
    return _safe_json_parse(_strip_code_fences(raw))


def _extract_section_from_cv(cv_text: str, section_title: str) -> str:
    """
    Heuristic fallback: locate `section_title` in `cv_text` and return the
    lines that belong to that section (up to the next blank-line-separated
    block that looks like a new section heading).  Returns an empty string
    if nothing can be found.
    """
    lines = cv_text.splitlines()
    # Find the line index where the title appears (case-insensitive)
    title_lower = section_title.strip().lower()
    start_idx = None
    for i, line in enumerate(lines):
        if title_lower in line.strip().lower():
            start_idx = i
            break
    if start_idx is None:
        return ""
    # Collect lines until we hit a blank line followed by a short ALL-CAPS /
    # title-cased line (likely the next section header), or end of text.
    collected = [lines[start_idx]]
    blank_streak = 0
    for line in lines[start_idx + 1:]:
        stripped = line.strip()
        if stripped == "":
            blank_streak += 1
            if blank_streak >= 2:
                break
            collected.append(line)
            continue
        blank_streak = 0
        # Heuristic: a short line (≤ 40 chars) without punctuation is likely a header
        if len(stripped) <= 40 and stripped == stripped.title() and stripped not in collected:
            # Peek — if collected already has content, treat as next section
            if len(collected) > 1:
                break
        collected.append(line)
    return "\n".join(collected).strip()


def _parallel_analyze(
    cv_text: str,
    is_english: bool,
    expert_intro: str,
    work_context: str,
    target_instruction: str,
    lang_rule: str,
    content_limits_block: str,
    _pages_tech_note: str,
) -> dict:
    """
    Two-phase parallel CV analysis orchestrator.
    Phase 1: single fast call — parse sections + metadata (no improvement).
    Phase 2: one AI call per section, all running concurrently via ThreadPoolExecutor.
    Phase 3: merge results into the standard output dict.
    Raises on Phase 1 failure so caller can fall back to monolithic.
    """
    import time as _time

    # ── Phase 1: parse & metadata ──
    logger.info("Parallel Phase 1: parsing CV into sections + metadata")
    _t0 = _time.monotonic()
    phase1 = _parse_cv_sections(cv_text, target_instruction, lang_rule, is_english)
    _t1 = _time.monotonic()
    raw_sections = phase1.get("sections", [])
    # Phase 1 now returns a plain list of title strings; handle all formats robustly
    sections = [
        {"title": t} if isinstance(t, str)
        else {"title": t.get("title", f"section_{i}")} if isinstance(t, dict)
        else {"title": f"section_{i}"}
        for i, t in enumerate(raw_sections)
    ]
    if not sections:
        raise ValueError("Phase 1 returned no sections")
    logger.info(f"Phase 1 complete in {_t1 - _t0:.1f}s: {len(sections)} sections, score={phase1.get('score')}")

    # ── Phase 2: parallel section improvements ──
    _p1_keywords = phase1.get("keywords_to_add", [])
    fallback_msg = (
        "Could not auto-improve this section — edit manually"
        if is_english else
        "לא הצלחנו לשפר סעיף זה אוטומטית — ניתן לערוך ידנית"
    )

    def _improve_task(args: tuple) -> tuple:
        idx, section = args
        title = section.get("title", f"section_{idx}")
        try:
            res = _improve_one_section(
                section_title=title,
                cv_text=cv_text,
                expert_intro=expert_intro,
                work_context=work_context,
                target_instruction=target_instruction,
                lang_rule=lang_rule,
                content_limits_block=content_limits_block,
                _pages_tech_note=_pages_tech_note,
                is_english=is_english,
                keywords_to_add=_p1_keywords,
            )
            original    = (res.get("original") or "").strip()
            improved    = (res.get("improved")  or "").strip() or original
            explanation = res.get("explanation", "")
            logger.info(f"Section '{title}': original={len(original)} chars, improved={len(improved)} chars")
            return idx, original, improved, explanation
        except Exception as exc:
            logger.warning(f"Section '{title}' improvement failed: {exc}")
            extracted = _extract_section_from_cv(cv_text, title)
            return idx, extracted, extracted, fallback_msg

    logger.info(f"Parallel Phase 2: improving {len(sections)} sections concurrently (max_workers=5)")
    _t2 = _time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            (idx, section, executor.submit(_improve_task, (idx, section)))
            for idx, section in enumerate(sections)
        ]

    results = []
    for idx, section, future in futures:
        title = section.get("title", f"section_{idx}")
        try:
            results.append(future.result(timeout=120))
        except concurrent.futures.TimeoutError:
            logger.warning(f"Section '{title}' timed out after 120s")
            extracted = _extract_section_from_cv(cv_text, title)
            results.append((idx, extracted, extracted, fallback_msg))
        except Exception as exc:
            logger.warning(f"Section '{title}' future error: {exc}")
            extracted = _extract_section_from_cv(cv_text, title)
            results.append((idx, extracted, extracted, fallback_msg))

    _t3 = _time.monotonic()
    logger.info(f"Phase 2 complete in {_t3 - _t2:.1f}s — total parallel analysis: {_t3 - _t0:.1f}s")

    # ── Phase 3: merge ──
    for idx, original, improved, explanation in results:
        sections[idx]["original"]    = original
        sections[idx]["improved"]    = improved
        sections[idx]["explanation"] = explanation
        if not sections[idx].get("original", "").strip():
            sections[idx]["original"] = improved

    logger.info("Parallel analysis complete")
    return {
        "sections":        sections,
        "general_tips":    phase1.get("general_tips", []),
        "keywords_to_add": phase1.get("keywords_to_add", []),
        "score":           phase1.get("score", 50),
    }


def _build_cv_params(
    cv_text: str,
    target_position: str,
    language: str,
    max_pages: int,
) -> dict:
    """Build all AI prompt parameters for CV analysis (shared by streaming + monolithic paths)."""
    is_english = (language == "en")

    if target_position.strip():
        if is_english:
            target_instruction = f"""

Specific job provided:
"{target_position}"
* If the target position or job description is written in Hebrew — translate it to English and use the English version.
* Tailor the CV specifically to this role.
* Incorporate relevant keywords from the job description naturally.
* Highlight experience, skills and achievements that match the requirements.
* In the keywords_to_add field, add specific keywords from the job description to help pass ATS filters."""
        else:
            target_instruction = f"""

משרה ספציפית שסופקה:
"{target_position}"
* אם שם התפקיד או תיאור המשרה כתובים באנגלית — תרגם אותם לעברית ועבוד על פי הגרסה העברית.
* התאם את המסמך אליה באופן ממוקד.
* שלב מילות מפתח רלוונטיות מתוך תיאור המשרה.
* הדגש ניסיון, מיומנויות והישגים התואמים לדרישות.
* בשדה keywords_to_add הוסף מילות מפתח ספציפיות מתוך תיאור המשרה שיסייעו בעבירת מסנני ATS."""
    else:
        if is_english:
            target_instruction = """

No specific job provided:
* Build a broad but focused professional positioning.
* Highlight core transferable skills.
* Use language adapted to the global job market."""
        else:
            target_instruction = """

לא סופקה משרה ספציפית:
* בנה מיצוב מקצועי רחב אך ממוקד תחום.
* הדגש מיומנויות ליבה חוצות תפקידים.
* שמור על ניסוח מותאם לשוק הישראלי."""

    if is_english:
        lang_rule = ("* Write ONLY in English. All improved CV content must be in English, including section titles, job descriptions, summaries and skills.\n"
                     "* CRITICAL: If a section does not exist in the original CV, do NOT create it. Never write 'Not specified', 'N/A', 'None', 'Not provided' or any placeholder. Simply omit that section from the JSON entirely.")
        expert_intro = "You are an expert CV writer and career positioning specialist for the global job market in 2026, across all professions and industries."
        work_context = "Based on the provided CV, improve the document while preserving all existing information. Do not omit any positions or time periods. Maintain a complete and continuous career picture, articulated to reflect a clear professional identity, business value, achievements and alignment with the modern work world."
    else:
        lang_rule = "* כתוב בעברית בלבד."
        expert_intro = "אתה מומחה לכתיבת קורות חיים ולמיצוב מועמדים לשוק העבודה הישראלי בשנת 2026, עבור כלל המקצועות והתחומים."
        work_context = "בהתבסס על קורות החיים שסופקו, שפר את המסמך תוך שמירה מלאה על כלל המידע הקיים. אין להשמיט תפקידים או תקופות. יש לשמר תמונה מלאה ורציפה של הקריירה, ולנסח אותה כך שתשקף זהות מקצועית ברורה, ערך עסקי, הישגים והתאמה לעולם העבודה החדש."

    if max_pages >= 2:
        content_limits_block = """הנחיות תוכן לשני עמודים:
* כלול את כל התפקידים שהופיעו במקור ללא יוצא מן הכלל — אל תשמיט אף תפקיד.
* תקציר מקצועי: לפחות 5 משפטים עשירים וחדי-משמעות, המציגים זהות מקצועית ברורה. המשפט הראשון: תואר/תפקיד + שנות ניסיון + טכנולוגיות/מודולים מרכזיים. המשפט השני: תחומי ידע עמוקים ומומחיות ייחודית. המשפט השלישי: ערך עסקי ותרומה לארגון. המשפטים הנוספים: מאפיין אישי בולט כגון ניהול יחסי לקוח, פתרון בעיות, או למידה מהירה. כתוב פסקה רציפה אחת, ללא רשימות.
* לכל תפקיד: לפחות 5 נקודות תמציתיות, כל נקודה בשורה אחת. כל נקודה חייבת לכלול: הפעולה שבוצעה + הטכנולוגיה/כלי ספציפי ששימש + ההשפעה התפעולית, עסקית או טכנית. אל תקצץ תכנים חשובים מהמקור.
* הרחב את סעיף המיומנויות לפחות ל-12 פריטים. כלול כישורים סטנדרטיים שאמורים להיות ברשות המועמד לאור ניסיונו — מתודולוגיות, כלים משלימים, תחומי ידע רלוונטיים — גם אם לא צוינו מפורשות. אם הניסיון/תחום מעיד על שימוש בכלי AI, הוסף לסעיף המיומנויות כלי AI רלוונטיים (כגון ChatGPT, Claude, Copilot, Cursor, Midjourney וכדומה) אם לא צוינו כבר.
* השכלה: כלול את כל הרקע האקדמי הרלוונטי.
* קורסים, הסמכות ופרויקטים: כלול את כל הרלוונטי.
* עדיפות: תוכן וערך מקצועי קודמים לחיסכון בעמודים. השתדל לא לחרוג מ-2 עמודים, אך לא על חשבון מידע מהותי.

סדר מחייב של קורות החיים:
1. פרטים אישיים - שם מלא, טלפון, אימייל, לינקדאין, עיר מגורים אופציונלית.
2. תקציר מקצועי - לפחות 5 משפטים: זהות מקצועית, תחום התמחות, ערך מקצועי מרכזי.
3. ניסיון תעסוקתי - כלול את כל התפקידים. לכל תפקיד: שנים → שם חברה → תפקיד → לפחות 5 נקודות תמציתיות, כל נקודה בשורה אחת.
4. שירות צבאי - אם מופיע במקור.
5. השכלה - שנים → מוסד → תואר → תחום לימוד.
6. מיומנויות - כל המיומנויות הטכניות והרכות הרלוונטיות.
7. קורסים, הסמכות ופרויקטים - אם מופיעים במקור."""
    else:
        content_limits_block = """הנחיות תוכן לשאיפה לעמוד אחד:
* כלול את כל התפקידים שהופיעו במקור ללא יוצא מן הכלל — אל תשמיט אף תפקיד.
* תקציר מקצועי: 3 משפטים עשירים וחדי-משמעות. המשפט הראשון: תואר/תפקיד + שנות ניסיון + טכנולוגיות/מודולים מרכזיים + תחום עיסוק. המשפט השני: מומחיות מרכזית וערך עסקי. המשפט השלישי: מאפיין בולט — ניהול לקוחות, פתרון בעיות, למידה מהירה. כתוב פסקה רציפה אחת, ללא רשימות, ללא מיקוף.
* לכל תפקיד: 3-5 נקודות תמציתיות, כל נקודה בשורה אחת. כל נקודה חייבת לכלול: הפעולה שבוצעה + הטכנולוגיה/כלי ספציפי ששימש + ההשפעה התפעולית, עסקית או טכנית.
* הרחב את סעיף המיומנויות לפחות ל-12 פריטים. כלול כישורים סטנדרטיים שאמורים להיות ברשות המועמד לאור ניסיונו — מתודולוגיות, כלים משלימים, תחומי ידע רלוונטיים — גם אם לא צוינו מפורשות. אם הניסיון/תחום מעיד על שימוש בכלי AI, הוסף לסעיף המיומנויות כלי AI רלוונטיים (כגון ChatGPT, Claude, Copilot, Cursor, Midjourney וכדומה) אם לא צוינו כבר.
* ניסח כל נקודה בצורה תמציתית ומדויקת - הימנע ממשפטים ארוכים.
* עדיפות: תוכן וערך מקצועי קודמים לחיסכון בעמודים. שאף להכניס לעמוד אחד, אך אם הניסיון עשיר ואיכותי - עדיף שני עמודים על פני השמטת תוכן חשוב.

סדר מחייב של קורות החיים:
1. פרטים אישיים - שם מלא, טלפון, אימייל, לינקדאין, עיר מגורים אופציונלית.
2. תקציר מקצועי - 3 משפטים: זהות מקצועית, תחום התמחות, ערך מקצועי מרכזי.
3. ניסיון תעסוקתי - כלול את כל התפקידים. לכל תפקיד: שנים → שם חברה → תפקיד → 3-5 נקודות תמציתיות, כל נקודה בשורה אחת.
4. שירות צבאי - אם מופיע במקור.
5. השכלה - שנים → מוסד → תואר → תחום לימוד.
6. מיומנויות - כל המיומנויות הטכניות והרכות הרלוונטיות.
7. קורסים, הסמכות ופרויקטים - אם מופיעים במקור."""

    _pages_tech_note = (
        f"השתדל לא לחרוג מ-{max_pages} עמודים, אך לא על חשבון מידע מהותי — תוכן וערך מקצועי קודמים לחיסכון בעמודים"
        if max_pages >= 2 else
        "שאף להכניס לעמוד אחד. אם הניסיון עשיר - עדיף לגלוש לעמוד שני על פני השמטת תוכן חשוב"
    )

    return {
        "cv_text":             cv_text,
        "is_english":          is_english,
        "expert_intro":        expert_intro,
        "work_context":        work_context,
        "target_instruction":  target_instruction,
        "lang_rule":           lang_rule,
        "content_limits_block": content_limits_block,
        "_pages_tech_note":    _pages_tech_note,
    }


def analyze_cv(cv_text: str, target_position: str = "", language: str = "he", max_pages: int = 1) -> dict:
    # ── Try streaming parallel approach ──
    try:
        result = None
        for event in analyze_cv_streaming(cv_text, target_position, language, max_pages):
            if event["type"] == "done":
                result = event["result"]
        if result is not None:
            return result
    except Exception as parallel_err:
        logger.warning(f"Parallel analysis failed ({parallel_err}), falling back to monolithic call")

    # ── Monolithic fallback: unpack params ──
    _p                   = _build_cv_params(cv_text, target_position, language, max_pages)
    is_english           = _p["is_english"]
    expert_intro         = _p["expert_intro"]
    work_context         = _p["work_context"]
    target_instruction   = _p["target_instruction"]
    lang_rule            = _p["lang_rule"]
    content_limits_block = _p["content_limits_block"]
    _pages_tech_note     = _p["_pages_tech_note"]

    # ── Monolithic fallback (original single-call approach) ──
    system_prompt = f"""{expert_intro}

{work_context}
{target_instruction}

כללי עבודה:
{lang_rule}
* אל תמחק מידע קיים.
* אל תמציא נתונים שלא הופיעו במקור.
* שמור על רצף כרונולוגי יורד לפי שנים בלבד.
* הסר רק פרטים שאינם מקצועיים כגון תעודת זהות, מצב משפחתי ותמונה.
* ניסוח מקצועי, ישיר, בהיר וללא קלישאות.
* כלול את כל התפקידים שהופיעו במקור — אל תשמיט אף תפקיד בשום מקרה ובשום תנאי, גם לא בשל מגבלת עמודים.
* כלול את כל ההשכלה, ההסמכות, הקורסים וההכשרות שהופיעו במקור — אל תשמיט אף פריט, גם לא בשל מגבלת עמודים.
* במקרה של סתירה בין פירוט לבין מגבלת עמודים — שמור על איכות התוכן וההשפעה העסקית על פני קיצור כפוי, אך הימנע מחזרתיות.
* מיזוג פרטי קשר: אם טלפון, אימייל, לינקדאין, עיר מגורים או שם מופיעים במספר מקומות שונים במסמך המקורי (למשל גם בראש העמוד וגם בעמודה צדדית), מזג את כולם לסעיף "פרטים אישיים" אחד בלבד בראש המסמך. שים לב: "פרופיל לינקדין" ו-"פרופיל לינקדאין" הם שדה לינקדאין — חלץ את הערך שאחריהם (שם או URL) לשדה linkedin. אל תיצור שני סעיפים נפרדים לפרטי קשר. חובה: כותרת הסעיף הראשון תמיד תהיה בדיוק "פרטים אישיים" — אל תשתמש ב"פרטי קשר", "נתונים אישיים" או כל שם אחר.
* טיפול בסעיף "שונות": אם קיים סעיף "שונות" או "כישורים נוספים", פרק אותו לפי סוג התוכן ושלב כל פריט בסעיף המתאים לו:
  - שפות (עברית, אנגלית, רוסית וכו') → סעיף "שפות" עם רמת שפה לכל שפה
  - כלי תוכנה, יישומים, Office, כלים דיגיטליים → סעיף "מיומנויות" או "כלים וטכנולוגיות"
  - סיווג ביטחוני, רישיון נהיגה, נכונות לשעות נוספות → שלב בסעיף "פרטים אישיים" בשורה נפרדת
  - לאחר הפירוק, כלול את סעיף "שונות" ב-JSON רק לצורך תצוגה בשלב הסקירה. בשדה improved כתוב משפט הסבר קצר וקריא בעברית שמסביר מה פוזר לאן, לדוגמה: "השפות הועברו לסעיף שפות, שליטה ב-Office הועברה למיומנויות, וסיווג ביטחוני נוסף לפרטים אישיים." — אל תכתוב JSON, אל תכתוב קוד, רק טקסט רגיל

עקרונות חובה לשוק העבודה 2026:
* הגדר זהות מקצועית עקבית וברורה כבר בתחילת המסמך.
* הדגש תרומה עסקית והשפעה בכל תפקיד; במידת האפשר, תרגם 'השפעה' לנתונים מספריים, אחוזים או יעדים שהושגו.
* נסח אחריות בצורה תוצאתית ולא כרשימת משימות בלבד.
* הצג הישגים מדידים אם קיימים במקור.
* הדגש מיומנויות ליבה חוצות תפקידים.
* זהה את 5 הכישורים הקריטיים ביותר הרלוונטיים לתפקיד היעד והבלט אותם לאורך המסמך - בתקציר המקצועי, בתיאורי התפקידים ובסעיף המיומנויות. אם אין תפקיד יעד, התאם 5 כישורים קריטיים לתפקידים שבוצעו עם דגש על התפקיד האחרון כרונולוגית.
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
* אל תכתוב את המילה "ATS" בתוך טקסט קורות החיים עצמו — המושג הוא הנחיה פנימית בלבד.

{content_limits_block}

עליך להחזיר תשובה בפורמט JSON בלבד (ללא markdown, ללא סימני קוד).
חשוב: ודא שכל גרש כפול בתוך ערכי טקסט מיוחלף ב-\\" כדי שה-JSON יהיה תקין.

חשוב מאוד:
1. זהה כל סעיף בקורות החיים בנפרד
2. בשדה "original" - העתק את הטקסט המקורי המדויק מקורות החיים עבור כל סעיף. אל תשאיר שדה זה ריק!
3. בשדה "improved" - כתוב גרסה משופרת של אותו סעיף
4. אם סעיף מסוים לא קיים בקורות החיים - אל תיצור אותו כלל! לא ליצור סעיפים עם טקסט כמו "לא צוין" או "לא סופק". פשוט השמט את הסעיף לחלוטין
5. בשדה "explanation" - הסבר קצר מה חיזק השיפור מבחינת זהות מקצועית, ערך עסקי, הסתגלות טכנולוגית והתאמה לשוק

המבנה הנדרש:
{{
    "sections": [
        {{
            "title": "שם הסעיף",
            "original": "הטקסט המקורי המדויק מקורות החיים - חובה למלא!",
            "improved": "הגרסה המשופרת של הטקסט",
            "explanation": "הסבר קצר מה חיזק השיפור"
        }}
    ],
    "general_tips": ["טיפ 1", "טיפ 2"],
    "keywords_to_add": ["מילת מפתח 1", "מילת מפתח 2"],
    "score": 72
}}

כללים טכניים:
- חלק את קורות החיים ל-3 סעיפים לפחות
- שדה "original" חייב להכיל את הטקסט המקורי כפי שהוא מופיע בקורות החיים - זה קריטי!
- אל תשתמש בסוגריים עגולים בטקסט. צמצם משמעותית את השימוש במקפים, העדף פסיק, נקודה, או ניסוח מחדש. אסור להשתמש במקף ארוך (—) או בינוני (–), השתמש רק במקף קצר רגיל (-) של מקלדת ובמשורה. כתוב בסגנון אנושי, לא AI. קיצורים עבריים מוסכמים כגון מנכ"ל, משא"ן, ד"ר, מ"מ וכדומה, שמור אותם כפי שהם
- {_pages_tech_note}
- לא להוסיף כותרות כמו "קורות חיים" או "קורות חיים משופרים" - רק תוכן
- אל תוסיף כותרות משנה חוזרות בתוך סעיפים כמו "הישגים נבחרים" או "תיאור התפקיד" - פשוט רשום את ההישגים כנקודות ישירות
- חשב את ציון score בין 0-100 לפי הרובריקה הבאה בלבד. חבר את הנקודות במדויק:
  פרטי קשר (0-10): שם + טלפון + אימייל = 10, חסר אחד = 5, אין כלל = 0
  תקציר מקצועי (0-15): קיים ואיכותי עם זהות מקצועית = 15, קיים אך חלש = 8, לא קיים = 0
  ניסיון תעסוקתי (0-35): 2+ תפקידים עם הישגים ותאריכים = 35, 2+ תפקידים ללא הישגים = 20, תפקיד אחד בלבד = 15, אין = 0
  השכלה (0-15): תואר + מוסד + שנים = 15, חלקי = 8, לא קיים = 0
  מיומנויות (0-15): 5+ מיומנויות = 15, 1-4 = 8, לא קיים = 0
  שפות (0-5): שפה אחת לפחות עם רמה = 5, ללא רמה = 3, לא קיים = 0
  בונוס (0-5): לינקדאין / התנדבות / פרויקטים = 5
  החזר את סכום הנקודות בלבד כמספר שלם
- אם יש הצטיינויות מעבודה, צבא או לימודים - הבלט אותן
- אם יש התנדבות או פרויקטים עצמאיים משמעותיים, המלץ להוסיף אותם
- אם בקורות החיים אין תואר אקדמי (תואר ראשון, שני או שלישי), הוסף ב-general_tips המלצה ספציפית לציין את המגמה בה למד המועמד בתיכון ושם בית הספר - זה מחזק את הפרופיל ומוסיף הקשר חשוב
- general_tips: כלול אך ורק מידע חסר שהמשתמש צריך להוסיף בעצמו — לינקדאין חסר, מגמה ותיכון, הסמכות, פרויקטים. אסור לכלול עצות ניסוח, כתיבה, עיצוב או פרמוט — הניסוח כבר מטופל בשדות improved
- חשוב ביותר: אם סעיף לא קיים במקור - אל תיצור אותו! לא לכתוב "לא צוין", "לא סופק", "לא מולא" או כל טקסט ממלא מקום. פשוט אל תכלול את הסעיף ב-JSON

ודא שהתוצאה הסופית משקפת קורות חיים מלאים, מקצועיים, מדויקים ותואמים לסטנדרטים העדכניים ביותר של שוק העבודה הישראלי ושל מערכות סינון מועמדים."""

    user_prompt = f"""נתח את קורות החיים הבאים. חשוב: זהה כל סעיף, העתק את הטקסט המקורי שלו לשדה original, וכתוב גרסה משופרת בשדה improved.

קורות החיים:
---
{cv_text}
---

זכור: שדה original חייב להכיל את הטקסט המקורי מקורות החיים. אל תשאיר אותו ריק."""

    logger.info(f"Monolithic fallback: analyzing CV with {len(cv_text)} characters")
    result = call_ai(system_prompt, user_prompt)
    logger.info(f"Monolithic response: {len(result)} characters")

    result = _strip_code_fences(result)

    try:
        parsed = _safe_json_parse(result)
        sections = parsed.get("sections", [])
        logger.info(f"Monolithic: parsed {len(sections)} sections")
        for section in sections:
            if not section.get("original", "").strip():
                section["original"] = section.get("improved", "לא זמין")
                logger.warning(f"Section '{section.get('title', '?')}' had empty original, copied from improved")
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Raw AI response (first 500 chars): {result[:500]}")
        lines = cv_text.strip().split("\n")
        chunks = []
        current_chunk = []
        for line in lines:
            if line.strip() == "" and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
            else:
                current_chunk.append(line)
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        fallback_sections = []
        for idx, chunk in enumerate(chunks[:6]):
            fallback_sections.append({
                "title": f"סעיף {idx + 1}",
                "original": chunk.strip(),
                "improved": chunk.strip(),
                "explanation": "לא הצלחנו לנתח סעיף זה אוטומטית - ניתן לערוך ידנית"
            })

        if not fallback_sections:
            fallback_sections.append({
                "title": "קורות חיים",
                "original": cv_text[:800],
                "improved": cv_text[:800],
                "explanation": "לא הצלחנו לנתח - ניתן לערוך ידנית"
            })

        return {
            "sections": fallback_sections,
            "general_tips": ["מומלץ לחלק את קורות החיים לסעיפים ברורים", "הוסף תקציר מקצועי בתחילת המסמך"],
            "keywords_to_add": [],
            "score": 50
        }


def analyze_cv_streaming(
    cv_text: str,
    target_position: str = "",
    language: str = "he",
    max_pages: int = 1,
):
    """
    Generator: yields analysis progress events as sections are completed in parallel.

    Event types (in order):
      {"type": "metadata", "score": int, "general_tips": [...],
       "keywords_to_add": [...], "sections_count": int}

      {"type": "section", "idx": int, "title": str,
       "original": str, "improved": str, "explanation": str}
       — yielded for each section AS SOON AS it finishes (fastest-first order)

      {"type": "done", "result": full_result_dict}

    Raises ValueError / any exception on Phase 1 failure so analyze_cv()
    can fall back to the monolithic path.
    """
    import time as _time

    p = _build_cv_params(cv_text, target_position, language, max_pages)
    is_english           = p["is_english"]
    expert_intro         = p["expert_intro"]
    work_context         = p["work_context"]
    target_instruction   = p["target_instruction"]
    lang_rule            = p["lang_rule"]
    content_limits_block = p["content_limits_block"]
    _pages_tech_note     = p["_pages_tech_note"]

    # ── Phase 1: section discovery ──
    _t0 = _time.monotonic()
    logger.info("Streaming Phase 1: discovering sections")
    phase1 = _parse_cv_sections(cv_text, target_instruction, lang_rule, is_english)
    _t1 = _time.monotonic()

    raw_sections = phase1.get("sections", [])
    sections = [
        {"title": t} if isinstance(t, str)
        else {"title": t.get("title", f"section_{i}")} if isinstance(t, dict)
        else {"title": f"section_{i}"}
        for i, t in enumerate(raw_sections)
    ]
    if not sections:
        raise ValueError("Phase 1 returned no sections")

    logger.info(f"Streaming Phase 1 done in {_t1 - _t0:.1f}s: {len(sections)} sections, score={phase1.get('score')}")

    yield {
        "type":            "metadata",
        "score":           phase1.get("score", 50),
        "general_tips":    phase1.get("general_tips", []),
        "keywords_to_add": phase1.get("keywords_to_add", []),
        "sections_count":  len(sections),
    }

    # ── Phase 2: parallel improvement, yield each section as it completes ──
    _p1_keywords = phase1.get("keywords_to_add", [])
    fallback_msg = (
        "Could not auto-improve this section — edit manually"
        if is_english else
        "לא הצלחנו לשפר סעיף זה אוטומטית — ניתן לערוך ידנית"
    )

    def _make_task(idx: int, section: dict) -> tuple:
        title = section.get("title", f"section_{idx}")
        try:
            res = _improve_one_section(
                section_title=title,
                cv_text=cv_text,
                expert_intro=expert_intro,
                work_context=work_context,
                target_instruction=target_instruction,
                lang_rule=lang_rule,
                content_limits_block=content_limits_block,
                _pages_tech_note=_pages_tech_note,
                is_english=is_english,
                keywords_to_add=_p1_keywords,
            )
            original    = (res.get("original") or "").strip()
            improved    = (res.get("improved")  or "").strip() or original
            explanation = res.get("explanation", "")
            return idx, original, improved, explanation
        except Exception as exc:
            logger.warning(f"Section '{title}' failed in streaming: {exc}")
            extracted = _extract_section_from_cv(cv_text, title)
            return idx, extracted, extracted, fallback_msg

    _t2 = _time.monotonic()
    logger.info(f"Streaming Phase 2: {len(sections)} sections, max_workers=5, using as_completed")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {
            executor.submit(_make_task, idx, section): (idx, section)
            for idx, section in enumerate(sections)
        }
        for future in concurrent.futures.as_completed(future_map):
            idx_key, section = future_map[future]
            title = section.get("title", f"section_{idx_key}")
            try:
                res_idx, original, improved, explanation = future.result(timeout=120)
            except concurrent.futures.TimeoutError:
                logger.warning(f"Streaming: section '{title}' timed out")
                extracted = _extract_section_from_cv(cv_text, title)
                res_idx, original, improved, explanation = idx_key, extracted, extracted, fallback_msg
            except Exception as exc:
                logger.warning(f"Streaming: section '{title}' future error: {exc}")
                extracted = _extract_section_from_cv(cv_text, title)
                res_idx, original, improved, explanation = idx_key, extracted, extracted, fallback_msg

            sections[res_idx]["original"]    = original
            sections[res_idx]["improved"]    = improved
            sections[res_idx]["explanation"] = explanation
            if not sections[res_idx].get("original", "").strip():
                sections[res_idx]["original"] = improved

            logger.info(f"Streaming: '{title}' done — {len(improved)} chars improved")
            yield {
                "type":        "section",
                "idx":         res_idx,
                "title":       sections[res_idx]["title"],
                "original":    original,
                "improved":    improved,
                "explanation": explanation,
            }

    _t3 = _time.monotonic()
    logger.info(f"Streaming Phase 2 done in {_t3 - _t2:.1f}s — total: {_t3 - _t0:.1f}s")

    yield {
        "type": "done",
        "result": {
            "sections":        sections,
            "general_tips":    phase1.get("general_tips", []),
            "keywords_to_add": phase1.get("keywords_to_add", []),
            "score":           phase1.get("score", 50),
        },
    }


def get_interview_question(conversation_history: list, step: int) -> str:
    system_prompt = """אתה מומחה בכתיבת קורות חיים. אתה מנהל ראיון עם המשתמש כדי לאסוף מידע ליצירת קורות חיים מקצועיים.

שלבי הראיון:
1. פרטים אישיים (שם, טלפון, אימייל, עיר מגורים)
2. תקציר מקצועי / מטרת קריירה
3. ניסיון תעסוקתי (תפקידים, חברות, תקופות, הישגים)
4. השכלה (תארים, מוסדות, שנים)
5. מיומנויות (טכניות ורכות)
6. שפות
7. מידע נוסף (התנדבות, קורסים, הסמכות)

כללים:
- שאל שאלה אחת בכל פעם
- היה ידידותי ומעודד
- אם המשתמש נתן תשובה קצרה, בקש פרטים נוספים
- שאל בעברית בלבד
- אל תציג את מספר השלב"""

    messages = [{"role": "system", "content": system_prompt}]

    if not conversation_history:
        messages.append({
            "role": "user",
            "content": "שלום, אני רוצה ליצור קורות חיים חדשים. בוא נתחיל."
        })
    else:
        for msg in conversation_history:
            messages.append(msg)

    # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
    # do not change this unless explicitly requested by the user
    response = client.chat.completions.create(
        model="gpt-5",
        messages=messages,
        max_completion_tokens=1024
    )
    return _sanitize_ai_output(response.choices[0].message.content or "")


def generate_cv_from_interview(conversation_history: list) -> dict:
    system_prompt = """אתה מומחה בכתיבת קורות חיים מקצועיים בהתאם לסטנדרטים המקצועיים העדכניים ביותר.
על סמך השיחה עם המשתמש, צור קורות חיים מלאים ומקצועיים.

החזר את התוצאה בפורמט JSON בלבד (ללא markdown, ללא ```):
{
    "full_name": "שם מלא",
    "contact": {
        "phone": "טלפון",
        "email": "אימייל",
        "city": "עיר",
        "linkedin": "לינקדאין - URL מלא או שם פרופיל (לדוגמה אם במקור כתוב 'פרופיל לינקדין Keren Belinson' → שמור 'Keren Belinson')"
    },
    "professional_summary": "תקציר מקצועי של 2-3 משפטים",
    "experience": [
        {
            "title": "תפקיד",
            "company": "חברה",
            "period": "תקופה",
            "achievements": ["הישג 1", "הישג 2"],
            "honors": "הצטיינות אם יש"
        }
    ],
    "education": [
        {
            "degree": "תואר",
            "institution": "מוסד",
            "year": "שנה",
            "honors": "הצטיינות אם יש"
        }
    ],
    "skills": {
        "technical": ["מיומנות 1"],
        "soft": ["מיומנות 1"]
    },
    "languages": [{"language": "שפה", "level": "רמה"}],
    "volunteering": ["פעילות התנדבותית"],
    "projects": ["פרויקט עצמאי"],
    "additional": ["פריט נוסף"]
}

מגבלות תוכן מחייבות לעמוד אחד - חובה לקיים בדיוק:
- תקציר מקצועי: עד 3 משפטים בלבד, לא יותר מ-50 מילים בסך הכל
- ניסיון תעסוקתי: עד 4 תפקידים בלבד. לכל תפקיד: עד 3 נקודות תמציתיות לכל היותר, כל נקודה עד 12 מילים
- השכלה: עד 3 ערכים בלבד
- מיומנויות: עד 8 מיומנויות טכניות ועד 5 מיומנויות רכות

הנחיות מקצועיות:
- תקציר מקצועי (החלק הכי חשוב!): עד 3 משפטים (לא יותר מ-50 מילים) הכוללים סך שנות ניסיון, הישגים כמותיים, וכישורים רכים רלוונטיים
- השתמש בפעלים חזקים ואקטיביים (בצורת שם הפועל): הובלה, ניהול, פיתוח, יזמות, יישום, ייעול, הטמעה, הגדלה
- נסח הישגים מדידים עם מדדים כמותיים. במידת האפשר (לא חובה), הוסף מספרים כגון אחוזי שיפור (10-30%), טווחי זמן, היקף תקציב, מספר אנשים. אם אין מידע כמותי מפורש, אפשר להעריך טווחים סבירים
- הישגים: עד 3 נקודות לכל תפקיד, כל נקודה עד 12 מילים בלבד
- סדר כרונולוגי יורד. תאריכים בשנים בלבד (לא חודשים)
- אם המועמד התקדם באותו ארגון, הבלט את ההתקדמות
- הבלט הצטיינויות מעבודה, צבא או לימודים
- פרטים אישיים: שם, טלפון, אימייל, לינקדאין בלבד. לא לכלול מצב משפחתי, ת.ז., תאריך לידה
- אם חסר מידע, השאר את השדה ריק
- שמור על תמציתיות מקסימלית - עמוד אחד בלבד
- אל תוסיף כותרות כמו "קורות חיים" - רק התוכן עצמו
- אם יש התנדבות או פרויקטים עצמאיים, כלול אותם. אם אין - השאר מערך ריק
- אל תשתמש בסוגריים עגולים () בטקסט. צמצם משמעותית את השימוש במקפים, העדף פסיק, נקודה, או ניסוח מחדש. אסור להשתמש במקף ארוך (—) או בינוני (–), השתמש רק במקף קצר רגיל (-) של מקלדת ובמשורה. כתוב בסגנון אנושי, לא AI. קיצורים עבריים מוסכמים כגון מנכ"ל, משא"ן, ד"ר, מ"מ וכדומה, שמור אותם כפי שהם"""

    conv_text = "\n".join([
        f"{'משתמש' if m['role'] == 'user' else 'מערכת'}: {m['content']}"
        for m in conversation_history
    ])

    user_prompt = f"""על סמך השיחה הבאה, צור קורות חיים מקצועיים:

{conv_text}"""

    result = call_ai(system_prompt, user_prompt)

    result = result.strip()
    if result.startswith("```json"):
        result = result[7:]
    if result.startswith("```"):
        result = result[3:]
    if result.endswith("```"):
        result = result[:-3]
    result = result.strip()

    try:
        return _safe_json_parse(result)
    except (json.JSONDecodeError, Exception):
        return {
            "full_name": "",
            "contact": {"phone": "", "email": "", "city": "", "linkedin": ""},
            "professional_summary": result[:300],
            "experience": [],
            "education": [],
            "skills": {"technical": [], "soft": []},
            "languages": [],
            "military": [],
            "volunteering": [],
            "projects": [],
            "additional": []
        }


def generate_cv_from_form(form_data: dict, target_position: str = "", max_pages: int = 1) -> dict:
    target_instruction = ""
    if target_position.strip():
        target_instruction = f"""

משרה ספציפית שסופקה:
"{target_position}"
* התאם את המסמך אליה באופן ממוקד.
* שלב מילות מפתח רלוונטיות מתוך תיאור המשרה.
* הדגש ניסיון, מיומנויות והישגים התואמים לדרישות.
* אל תמציא מידע שלא קיים בטופס, רק נסח מחדש כדי להדגיש התאמה."""
    else:
        target_instruction = """

לא סופקה משרה ספציפית:
* בנה מיצוב מקצועי רחב אך ממוקד תחום.
* הדגש מיומנויות ליבה חוצות תפקידים.
* שמור על ניסוח מותאם לשוק הישראלי."""

    if max_pages >= 2:
        _build_content_limits_block = """הנחיות תוכן לשני עמודים:
* כלול את כל הניסיון הרלוונטי מהנתונים - אל תשמיט תפקידים או הישגים חשובים.
* תקציר מקצועי: 3-4 משפטים, ממוקד וברור.
* לכל תפקיד: עד 5 נקודות תמציתיות, כל נקודה בשורה אחת קצרה.
* השכלה: כלול את כל הרקע האקדמי הרלוונטי.
* מיומנויות: כלול את כל המיומנויות הרלוונטיות לתפקיד. אם הניסיון/תחום מעיד על שימוש בכלי AI, הוסף לסעיף המיומנויות כלי AI רלוונטיים (כגון ChatGPT, Claude, Copilot, Cursor, Midjourney וכדומה) אם לא צוינו כבר.
* קורסים, הסמכות ופרויקטים: כלול את כל הרלוונטי.
* חובה: קורות החיים לא יעלו על 2 עמודים.

סדר מחייב של קורות החיים:
1. פרטים אישיים - שם מלא, טלפון, אימייל, לינקדאין, עיר מגורים אופציונלית.
2. תקציר מקצועי - 3-4 משפטים: זהות מקצועית, תחום התמחות, ערך מקצועי מרכזי.
3. ניסיון תעסוקתי - כלול את כל התפקידים הרלוונטיים. לכל תפקיד: שנים → שם חברה → תפקיד → עד 5 נקודות תמציתיות, כל נקודה בשורה אחת.
4. שירות צבאי - אם מופיע בנתונים.
5. השכלה - שנים → מוסד → תואר → תחום לימוד.
6. מיומנויות - כל המיומנויות הטכניות והרכות הרלוונטיות.
7. קורסים, הסמכות ופרויקטים - אם מופיעים בנתונים."""
    else:
        _build_content_limits_block = """הנחיות תוכן לשאיפה לעמוד אחד:
* כלול את כל הניסיון הרלוונטי מהנתונים - אל תשמיט תפקידים או הישגים חשובים.
* תקציר מקצועי: 2-3 משפטים ממוקדים.
* לכל תפקיד: 2-4 נקודות תמציתיות, כל נקודה בשורה אחת קצרה.
* ניסח כל נקודה בצורה תמציתית ומדויקת - הימנע ממשפטים ארוכים.
* שאף להכניס לעמוד אחד, אך אם הניסיון עשיר ואיכותי - עדיף שני עמודים על פני השמטת תוכן חשוב.
* מיומנויות: אם הניסיון/תחום מעיד על שימוש בכלי AI, הוסף לסעיף המיומנויות כלי AI רלוונטיים (כגון ChatGPT, Claude, Copilot, Cursor, Midjourney וכדומה) אם לא צוינו כבר.

סדר מחייב של קורות החיים:
1. פרטים אישיים - שם מלא, טלפון, אימייל, לינקדאין, עיר מגורים אופציונלית.
2. תקציר מקצועי - 2-3 משפטים: זהות מקצועית, תחום התמחות, ערך מקצועי מרכזי.
3. ניסיון תעסוקתי - כלול את כל התפקידים הרלוונטיים. לכל תפקיד: שנים → שם חברה → תפקיד → 2-4 נקודות תמציתיות, כל נקודה בשורה אחת.
4. שירות צבאי - אם מופיע בנתונים.
5. השכלה - שנים → מוסד → תואר → תחום לימוד.
6. מיומנויות - כל המיומנויות הטכניות והרכות הרלוונטיות.
7. קורסים, הסמכות ופרויקטים - אם מופיעים בנתונים."""

    system_prompt = f"""אתה מומחה לכתיבת קורות חיים ולמיצוב מועמדים לשוק העבודה הישראלי בשנת 2026, עבור כלל המקצועות והתחומים.

קיבלת נתוני טופס מהמשתמש. בהתבסס על הנתונים שסופקו, בנה קורות חיים מקצועיים תוך שמירה מלאה על כלל המידע הקיים. נסח את התוכן כך שישקף זהות מקצועית ברורה, ערך עסקי, הישגים והתאמה לעולם העבודה החדש.
{target_instruction}

כללי עבודה:
* כתוב בעברית בלבד.
* שמור על הנתונים המקוריים - שם, טלפון, אימייל, תקופות, מוסדות.
* שפר רק את הניסוח של הישגים, תקציר, ומיומנויות.
* אל תמציא נתונים שלא הופיעו בטופס.
* שמור על רצף כרונולוגי יורד לפי שנים בלבד.
* ניסוח מקצועי, ישיר, בהיר וללא קלישאות.
* אם המשתמש לא כתב תקציר מקצועי, כתוב אחד עבורו בהתבסס על הנתונים.

עקרונות חובה לשוק העבודה 2026:
* הגדר זהות מקצועית עקבית וברורה בתקציר המקצועי.
* הדגש תרומה עסקית והשפעה בכל תפקיד.
* נסח אחריות בצורה תוצאתית ולא כרשימת משימות בלבד.
* הצג הישגים מדידים אם קיימים בנתונים.
* הדגש מיומנויות ליבה חוצות תפקידים.
* זהה את 5 הכישורים הקריטיים ביותר הרלוונטיים לתפקיד היעד והבלט אותם לאורך המסמך - בתקציר המקצועי, בתיאורי התפקידים ובסעיף המיומנויות.
* צור חוט מקצועי מקשר בין התחנות.
* הדגש למידה, הסתגלות טכנולוגית ושיפור תהליכים אם קיימים.
* אם מופיע ניסיון בעבודה עם כלי בינה מלאכותית, אוטומציה או כלים דיגיטליים מתקדמים, הדגש זאת והצג את ההשפעה המקצועית או העסקית.
* אם לא מופיע שימוש ישיר בכלי AI, אך קיימת אינדיקציה ללמידה עצמאית, חדשנות או אוריינות דיגיטלית, נסח זאת כחוזקה מקצועית.
* אין להמציא ניסיון בעולמות AI שלא הופיע בנתונים.
* ודא שהמסמך תומך גם בקריאה אנושית וגם במערכות סינון אוטומטיות.

התאמה ל-ATS:
* שלב מילות מפתח רלוונטיות באופן טבעי בתוך תיאורי התפקידים ולא רק ברשימת מיומנויות.
* השתמש בכותרות ברורות וסטנדרטיות.
* הימנע מעיצוב מורכב או ניסוחים עמומים.
* ודא שמיומנויות מרכזיות מופיעות לפחות פעמיים במסמך בהקשר מקצועי אמיתי.
* שלב מונחים רלוונטיים הקשורים לחדשנות, דיגיטציה ו-AI אם הופיעו בנתונים.
* שמור על ניסוח ברור וקצר כדי לאפשר סריקה מהירה.
* אל תכתוב את המילה "ATS" בתוך טקסט קורות החיים עצמו — המושג הוא הנחיה פנימית בלבד.

{_build_content_limits_block}

החזר את התוצאה בפורמט JSON בלבד (ללא markdown, ללא ```):
{{
    "full_name": "שם מלא",
    "contact": {{"phone": "טלפון", "email": "אימייל", "city": "עיר", "linkedin": "לינקדאין - URL מלא או שם פרופיל (אם במקור 'פרופיל לינקדין [שם]' → שמור את השם)", "portfolio": ""}},
    "professional_summary": "תקציר מקצועי של 2-3 משפטים בלבד",
    "experience": [
        {{"title": "תפקיד", "company": "חברה", "period": "תקופה", "achievements": ["הישג 1", "הישג 2"], "honors": "הצטיינות אם יש"}}
    ],
    "education": [{{"degree": "תואר", "institution": "מוסד", "year": "תקופה למשל 2018-2022 או 2022-היום", "honors": "הצטיינות אם יש"}}],
    "skills": {{"technical": ["מיומנות"], "soft": ["מיומנות"]}},
    "languages": [{{"language": "שפה", "level": "רמה"}}],
    "military": ["שירות צבאי / לאומי"],
    "volunteering": ["פעילות התנדבותית"],
    "projects": ["פרויקט עצמאי"],
    "additional": ["פריט נוסף"]
}}

כללים טכניים:
- שמור על תמציתיות - קורות חיים חייבים להיכנס ל-{max_pages} עמוד{"ים" if max_pages >= 2 else ""} לכל היותר
- אל תוסיף כותרות כמו "קורות חיים" - רק התוכן עצמו
- אם יש שירות צבאי/לאומי, התנדבות או פרויקטים עצמאיים, כלול אותם בשדות המתאימים. אם אין - השאר מערך ריק []
- אם יש הצטיינויות מעבודה, צבא או לימודים - הבלט אותן
- אל תשתמש בסוגריים עגולים בטקסט. צמצם משמעותית את השימוש במקפים, העדף פסיק, נקודה, או ניסוח מחדש. אסור להשתמש במקף ארוך (—) או בינוני (–), השתמש רק במקף קצר רגיל (-) של מקלדת ובמשורה. כתוב בסגנון אנושי, לא AI. קיצורים עבריים מוסכמים כגון מנכ"ל, משא"ן, ד"ר, מ"מ וכדומה, שמור אותם כפי שהם
- חשוב ביותר: אם שדה לא סופק בנתוני הטופס - השאר אותו כמחרוזת ריקה "" או מערך ריק []. לא לכתוב "לא צוין", "לא סופק", "לא מולא" או כל טקסט ממלא מקום! אם אין מידע - פשוט השאר ריק
- אם שדה honors ריק או לא רלוונטי - השאר מחרוזת ריקה ""

ודא שהתוצאה הסופית משקפת קורות חיים מלאים, מקצועיים, מדויקים ותואמים לסטנדרטים העדכניים ביותר של שוק העבודה הישראלי ושל מערכות סינון מועמדים."""

    form_text = f"""שם: {form_data.get('full_name', '')}
טלפון: {form_data.get('phone', '')}
אימייל: {form_data.get('email', '')}
עיר: {form_data.get('city', '')}
לינקדאין: {form_data.get('linkedin', '')}
פורטפוליו/קישור נוסף: {form_data.get('portfolio', '')}

תקציר מקצועי: {form_data.get('professional_summary', '')}

ניסיון תעסוקתי:
"""
    for exp in form_data.get("experience", []):
        title = exp.get("title", "")
        company = exp.get("company", "")
        period = exp.get("period", "")
        achievements = exp.get("achievements", "")
        honors = exp.get("honors", "")
        if title or company:
            form_text += f"- תפקיד: {title}, חברה: {company}, תקופה: {period}\n"
            if achievements:
                form_text += f"  הישגים: {achievements}\n"
            if honors:
                form_text += f"  הצטיינות: {honors}\n"

    form_text += "\nהשכלה:\n"
    for edu in form_data.get("education", []):
        degree = edu.get("degree", "")
        institution = edu.get("institution", "")
        year = edu.get("year", "")
        honors = edu.get("honors", "")
        if degree or institution:
            form_text += f"- {degree}, {institution}, {year}\n"
            if honors:
                form_text += f"  הצטיינות: {honors}\n"

    form_text += f"\nמיומנויות טכניות: {form_data.get('technical_skills', '')}\n"
    form_text += f"מיומנויות רכות: {form_data.get('soft_skills', '')}\n"

    form_text += "\nשפות:\n"
    for lang in form_data.get("languages", []):
        lang_name = lang.get("language", "")
        level = lang.get("level", "")
        if lang_name:
            form_text += f"- {lang_name}: {level}\n"

    military = form_data.get("military", "")
    if military:
        form_text += f"\nשירות צבאי / לאומי: {military}\n"

    volunteering = form_data.get("volunteering", "")
    if volunteering:
        form_text += f"\nהתנדבות: {volunteering}\n"

    projects = form_data.get("projects", "")
    if projects:
        form_text += f"\nפרויקטים עצמאיים: {projects}\n"

    additional = form_data.get("additional", "")
    if additional:
        form_text += f"\nמידע נוסף: {additional}\n"

    user_prompt = f"""צור קורות חיים מקצועיים על סמך נתוני הטופס הבאים:

{form_text}"""

    result = call_ai(system_prompt, user_prompt)

    result = result.strip()
    if result.startswith("```json"):
        result = result[7:]
    if result.startswith("```"):
        result = result[3:]
    if result.endswith("```"):
        result = result[:-3]
    result = result.strip()

    try:
        parsed = _safe_json_parse(result)
        if isinstance(parsed.get("contact"), dict):
            parsed["contact"]["portfolio"] = form_data.get("portfolio", "")
        return parsed
    except (json.JSONDecodeError, Exception):
        return {
            "full_name": form_data.get("full_name", ""),
            "contact": {
                "phone": form_data.get("phone", ""),
                "email": form_data.get("email", ""),
                "city": form_data.get("city", ""),
                "linkedin": form_data.get("linkedin", ""),
                "portfolio": form_data.get("portfolio", "")
            },
            "professional_summary": form_data.get("professional_summary", ""),
            "experience": [],
            "education": [],
            "skills": {"technical": [], "soft": []},
            "languages": [],
            "military": [],
            "volunteering": [],
            "projects": [],
            "additional": []
        }


def translate_cv_to_english(cv_text: str) -> str:
    system_prompt = """You are a professional CV/resume translator specializing in Hebrew to English translation.
Translate the following CV content from Hebrew to English professionally.

Rules:
- Maintain the exact same structure and formatting (sections, bullet points, separators)
- IMPORTANT: Keep section markers like === Section Name === exactly as they appear, but translate the section name inside them to English
- Translate job titles, skills, and descriptions professionally
- CRITICAL: For Hebrew company/organization names that appear in quotes (e.g., "אנוש כח אדם", "המרכז בריאותי לכף רגל"), either transliterate them to English (e.g., "Enosh Koach Adam") or translate their meaning (e.g., "Human Resources Inc."). NEVER output reversed Hebrew characters. The output must be fully readable in English left-to-right.
- Keep email addresses, phone numbers, and URLs unchanged
- Translate degree names to their standard English equivalents (e.g., תואר ראשון = B.A./B.Sc.)
- Use professional CV language and action verbs
- Keep dates and numbers as-is
- Preserve line breaks and bullet points (• or -)
- Do NOT add repetitive sub-headers like "Selected Achievements", "Key Achievements", or "Role Description" under each job. Just list the achievements directly as bullet points under the job title/company/period line. The section header "Professional Experience" or "Work Experience" should appear only once at the top
- For military service lines, translate them as regular text (not as job positions). Mark them clearly, e.g., "Military Service: Israeli Air Force, Intelligence – Clerk (full service)"
- CRITICAL: Military service information must NEVER appear in the personal details/contact section at the top of the CV. It should only appear in its own separate section (e.g., "Military Service") or under "Additional Information". The contact/personal section should only contain: name, phone, email, city, LinkedIn
- Do NOT add any explanations, just return the translated text"""

    return call_ai(system_prompt, f"Translate this CV to English:\n\n{cv_text}")


def translate_cv_data_to_english(cv_data: dict) -> dict:
    system_prompt = """You are a professional CV/resume translator specializing in Hebrew to English translation.
Translate the CV data from Hebrew to English professionally.

Return the result in JSON format only (no markdown, no ```):
{
    "full_name": "Full Name",
    "contact": {"phone": "phone", "email": "email", "city": "City", "linkedin": "LinkedIn URL"},
    "professional_summary": "Professional summary in 2-3 sentences",
    "experience": [
        {"title": "Job Title", "company": "Company", "period": "Period", "achievements": ["Achievement 1"], "honors": "Honors if any"}
    ],
    "education": [{"degree": "Degree", "institution": "Institution", "year": "Year", "honors": "Honors if any"}],
    "skills": {"technical": ["Skill"], "soft": ["Skill"]},
    "languages": [{"language": "Language", "level": "Level"}],
    "volunteering": ["Volunteering activity"],
    "projects": ["Personal project"],
    "additional": ["Additional item"]
}

Rules:
- Translate all Hebrew text to professional English
- CRITICAL: For Hebrew company/organization names, either transliterate them to English or translate their meaning. NEVER output reversed Hebrew characters. The output must be fully readable in English left-to-right.
- Keep emails, phone numbers unchanged
- Translate degree names to standard English equivalents
- Use professional CV language and action verbs
- Keep dates and numbers as-is
- Do NOT add explanations, only return valid JSON"""

    user_prompt = f"Translate this CV data to English:\n\n{json.dumps(cv_data, ensure_ascii=False)}"
    result = call_ai(system_prompt, user_prompt)

    result = result.strip()
    if result.startswith("```json"):
        result = result[7:]
    if result.startswith("```"):
        result = result[3:]
    if result.endswith("```"):
        result = result[:-3]
    result = result.strip()

    try:
        return _safe_json_parse(result)
    except (json.JSONDecodeError, Exception):
        return cv_data


def improve_section_text(original: str, context: str = "") -> str:
    system_prompt = """אתה מומחה לכתיבת קורות חיים ולמיצוב מועמדים לשוק העבודה הישראלי בשנת 2026.
החזר רק את הטקסט המשופר, ללא הסברים נוספים.
- נסח אחריות בצורה תוצאתית ולא כרשימת משימות בלבד
- הדגש תרומה עסקית והשפעה
- הצג הישגים מדידים אם קיימים במקור
- הדגש מיומנויות ליבה חוצות תפקידים
- אל תמציא נתונים שלא הופיעו במקור
- תאריכים בשנים בלבד - לא חודשים
- כתוב בעברית, ניסוח מקצועי, ישיר, בהיר וללא קלישאות
- אל תשתמש בסוגריים עגולים בטקסט. צמצם משמעותית את השימוש במקפים, העדף פסיק, נקודה, או ניסוח מחדש. אסור להשתמש במקף ארוך (—) או בינוני (–), השתמש רק במקף קצר רגיל (-) של מקלדת ובמשורה. כתוב בסגנון אנושי, לא AI. קיצורים עבריים מוסכמים כגון מנכ"ל, משא"ן, ד"ר, מ"מ וכדומה, שמור אותם כפי שהם"""

    return call_ai(system_prompt, f"טקסט לשיפור:\n{original}\n\nהקשר:\n{context}")


# ============================================================================
# Per-section consultation chat (Build CV form)
# ============================================================================

_SECTION_LABELS = {
    "target": "תפקיד יעד",
    "personal": "פרטים אישיים",
    "summary": "תקציר מקצועי",
    "experience": "ניסיון תעסוקתי",
    "education": "השכלה אקדמית / מקצועית",
    "skills": "מיומנויות",
    "military": "שירות צבאי / לאומי",
    "volunteering": "התנדבות בקהילה",
    "projects": "פרויקטים עצמאיים",
    "additional": "מידע נוסף",
}

_SECTION_GUIDANCE = {
    "target": (
        "המשתמש כותב את שדה 'תפקיד יעד'. "
        "עזור לו לנסח שם תפקיד ברור או להבין מה כדאי להעתיק מתיאור משרה. "
        "הסבר שכאשר מדביקים תיאור משרה מלא, המערכת מתאימה את קורות החיים למילות המפתח. "
        "אל תכתוב עבורו את התפקיד - תן לו עקרונות ודוגמאות קצרות."
    ),
    "personal": (
        "המשתמש כותב את 'פרטים אישיים' (שם, עיר, טלפון, אימייל, לינקדאין). "
        "הסבר אילו פרטים חובה ואילו אופציונליים, איך לכתוב מספר טלפון בצורה תקנית, "
        "מתי כדאי להוסיף לינקדאין, ומה לא כדאי לכתוב (גיל, מצב משפחתי, תמונה אם לא רלוונטי לתפקיד). "
        "הסבר בקצרה מדוע."
    ),
    "summary": (
        "המשתמש כותב 'תקציר מקצועי' - 2-4 משפטים בראש קורות החיים. "
        "הסבר את המבנה הרצוי: תפקיד+שנות ניסיון+תחום, אחר כך התמחות וערך מוסף, "
        "ולסיום תכונה מבדלת. תן דוגמה קצרה אחת אם זה עוזר. "
        "אם המשתמש בלי ניסיון - הסבר איך לכתוב תקציר של בוגר/סטודנט/מחליף קריירה."
    ),
    "experience": (
        "המשתמש כותב 'ניסיון תעסוקתי'. "
        "עזור לו להחליט אילו תפקידים לכלול, איך לתאר הישגים (פעולה + כלי/טכנולוגיה + השפעה עסקית), "
        "ומה לעשות אם אין לו ניסיון רשמי (התמחות, פרויקטים בלימודים, עבודות קיץ, התנדבות שמתפקדת כניסיון). "
        "הזכר שעדיף לכתוב 2-4 בולטים מנוסחים היטב מאשר רשימה ארוכה של משימות. "
        "תן דוגמה קצרה למעבר מ'אחראי על X' ל'הובלתי X והשגתי Y'."
    ),
    "education": (
        "המשתמש כותב 'השכלה אקדמית / מקצועית'. "
        "הסבר אילו תארים/קורסים שווה לכלול ומה הסדר (מהחדש לישן). "
        "אם אין לו תואר אקדמי - הסבר שאפשר וכדאי לכתוב מגמה בתיכון, בית ספר, "
        "קורסים מקצועיים, הסמכות, סדנאות. "
        "הזכר מתי כדאי לציין ממוצע ציונים (רק אם גבוה ורלוונטי) ומתי לציין הצטיינות."
    ),
    "skills": (
        "המשתמש כותב 'מיומנויות' (טכניות ורכות). "
        "עזור לו להבחין בין מיומנויות טכניות (כלים, תוכנות, שפות תכנות, מתודולוגיות) "
        "למיומנויות רכות (תקשורת, מנהיגות, פתרון בעיות). "
        "הזכר שכדאי לכלול לפחות 10-15 מיומנויות טכניות אם רלוונטי לתחום, "
        "ושמיומנויות רכות כדאי לבחור לפי הרלוונטיות לתפקיד. "
        "אם המשתמש לא בטוח - הצע לו לחשוב על כלים שהוא משתמש בהם בעבודה היומיומית. "
        "חשוב במיוחד: אם המשתמש לא ציין כלי AI (כגון ChatGPT, Claude, Copilot, Cursor, Midjourney וכדומה) — "
        "שאל אותו אם הוא משתמש בהם ומלץ לכלול לפחות 2-3 כלי AI פופולריים בתחומו, "
        "כי כלי AI הם מיומנות מבוקשת מאוד בשוק העבודה של 2026."
    ),
    "military": (
        "המשתמש כותב על 'שירות צבאי / לאומי'. "
        "עזור לו להחליט אם לכלול ומה לכתוב: יחידה (אם אין סיווג), תפקיד, דרגה, תקופה, "
        "ובמיוחד הישגים והאחריות שהיו לו. "
        "הסבר שמעסיקים מעריכים מאוד תפקידים פיקודיים, טכניים או יחידות מיוחדות. "
        "אם הוא לא שירת - אפשר לכתוב 'שירות לאומי' או פטור מסיבות בריאותיות, או פשוט להשמיט. "
        "אל תיכנס לעניינים פוליטיים."
    ),
    "volunteering": (
        "המשתמש כותב 'התנדבות בקהילה'. "
        "הסבר שהתנדבות מחזקת קורות חיים במיוחד אצל אנשים בלי הרבה ניסיון תעסוקתי. "
        "עזור לו לתאר את ההתנדבות במונחים מקצועיים: מה עשה, איזו השפעה הביא, "
        "ואילו מיומנויות פיתח שרלוונטיות לתפקיד. "
        "תן דוגמה קצרה של ניסוח טוב לעומת ניסוח חלש."
    ),
    "projects": (
        "המשתמש כותב 'פרויקטים עצמאיים'. "
        "הסבר שזה חלק חשוב במיוחד למפתחים, מעצבים, יוצרי תוכן, יזמים ובוגרים. "
        "עזור לו לתאר כל פרויקט: מטרה, טכנולוגיות/כלים, התוצאה, וקישור אם רלוונטי (GitHub, אתר). "
        "אם הוא לא בטוח אם משהו 'נחשב' פרויקט - הסבר שגם פרויקט סיום, אפליקציה אישית, אתר, או יוזמה בעבודה הקודמת יכולים להיכלל."
    ),
    "additional": (
        "המשתמש כותב 'מידע נוסף' - הסעיף הגמיש של קורות החיים. "
        "עזור לו להחליט מה שווה לכלול: קורסים והסמכות, פרסומים, הרצאות, חברות בארגונים מקצועיים, "
        "תחביבים שמראים תכונות רלוונטיות (ספורט תחרותי, תפקידי הובלה בקהילה). "
        "הסבר מה לא כדאי לכלול (תחביבים גנריים, דעות פוליטיות/דתיות, פרטים אישיים)."
    ),
}


def _build_consultation_system_prompt(section_key: str) -> str:
    label = _SECTION_LABELS.get(section_key, section_key)
    guidance = _SECTION_GUIDANCE.get(section_key, "")
    return (
        f"אתה יועץ קריירה ותיק וחברותי שעוזר למועמדים לכתוב קורות חיים מקצועיים בעברית. "
        f"המשתמש נמצא כרגע בסעיף '{label}' בטופס בניית קורות החיים, ומבקש ממך עצה.\n\n"
        f"הקשר לסעיף הספציפי הזה:\n{guidance}\n\n"
        "כללי תשובה:\n"
        "- ענה בעברית בלבד, בשפה פשוטה ויומיומית - ללא מונחים מקצועיים מיותרים.\n"
        "- תשובה קצרה בלבד: עד 4 שורות קצרות. משפט-שניים ממוקדים עדיפים על פסקה ארוכה.\n"
        "- רשימה רק אם היא באמת מועילה - עד 3 פריטים קצרים בלבד. כברירת מחדל - כתוב פסקה זורמת.\n"
        "- אל תמלא במשפטי מילוי, הסברים מיותרים או כתבי ויתור. ענה ישירות.\n"
        "- אל תכתוב עבור המשתמש את התוכן המלא של קורות החיים שלו - תן עקרונות, דוגמה קצרה בלבד.\n"
        "- אם המשתמש מבקש שתכתוב לו במקומו, הסבר בקצרה שעדיף שיכתוב בעצמו ותן שלד קצר.\n"
        "- אם אתה צריך מידע - שאל שאלה אחת ממוקדת בלבד.\n"
        "- אסור להשתמש במקף ארוך (—) או בינוני (–). השתמש רק במקף קצר רגיל (-) ובמשורה. העדף פסיק, נקודה, או ניסוח מחדש.\n"
        "- אל תזכיר שאתה AI או מודל שפה. אתה פשוט יועץ הקריירה של המשתמש.\n"
        "- אל תזכיר סעיפים אחרים בקורות החיים אלא אם המשתמש שאל עליהם במפורש - התמקד בסעיף הנוכחי בלבד.\n"
    )


def section_consultation_reply(section_key: str, conversation_history: list) -> str:
    """Generate an advisor reply for a per-section consultation chat.

    Args:
        section_key: One of the keys in _SECTION_LABELS (e.g. "summary").
        conversation_history: List of {"role": "user"|"assistant", "content": str}.
            The last message must be from the user.

    Returns:
        The assistant's reply (already sanitized via _sanitize_ai_output).
    """
    if not conversation_history:
        return ""

    system_prompt = _build_consultation_system_prompt(section_key)

    transcript_lines = []
    for msg in conversation_history:
        role = msg.get("role", "user")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        speaker = "המשתמש" if role == "user" else "היועץ"
        transcript_lines.append(f"{speaker}: {content}")
    transcript_lines.append("היועץ:")
    user_prompt = (
        "ענה קצר ולעניין, עד 4 שורות.\n\n"
        "להלן השיחה עד כה. המשך את השיחה בתור היועץ, וענה ישירות להודעה האחרונה של המשתמש. "
        "אל תחזור על מה שכבר נאמר בשיחה הקודמת.\n\n"
        + "\n\n".join(transcript_lines)
    )

    return call_ai(system_prompt, user_prompt)


def section_consultation_greeting(section_key: str) -> str:
    """Return a short, deterministic Hebrew greeting for a section's first open."""
    if section_key == "skills":
        return (
            "שלום! אני כאן לעזור לך עם סעיף המיומנויות. "
            "שים לב — כלי AI כמו ChatGPT, Claude, Copilot ו-Cursor הם מיומנות מבוקשת מאוד ב-2026. "
            "האם כללת אותם ברשימה שלך? "
            "ספר לי אילו כלים אתה משתמש בהם בעבודה, ואני אעזור לך לנסח את המיומנויות בצורה הטובה ביותר."
        )
    label = _SECTION_LABELS.get(section_key, section_key)
    return (
        f"שלום! אני כאן לעזור לך עם הסעיף '{label}'. "
        f"ספר לי מה הקושי או מה אתה רוצה לכתוב, ואני אעזור לך לנסח את זה כמו שצריך."
    )
