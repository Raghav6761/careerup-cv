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

    return content


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
    Phase 1 — Parse & Metadata.
    Single fast AI call: extracts section titles + original text, calculates
    score, generates general_tips and keywords_to_add.
    Does NOT write any improved content — output is small (~300-600 tokens).
    Raises json.JSONDecodeError on parse failure so caller can fall back.
    """
    if is_english:
        system_prompt = f"""You are a CV analysis expert. Your task in this step is to PARSE ONLY — do NOT write any improved content.
{target_instruction}

Rules:
{lang_rule}
* Do NOT create sections that do not exist in the CV.
* Never write 'Not specified', 'N/A', 'None', 'Not provided' or any placeholder.
* Copy the EXACT original text for each section — do not paraphrase or improve.
* Merge all contact information (name, phone, email, LinkedIn, city) into a single "Personal Details" section.
* Identify ALL distinct sections present in the CV.

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
  "sections": [
    {{"title": "Section Name", "original": "Exact original text from the CV"}}
  ],
  "general_tips": ["tip 1", "tip 2"],
  "keywords_to_add": ["keyword 1"],
  "score": 72
}}"""
        user_prompt = f"""Parse this CV into its sections. Copy the exact original text for each.

---
{cv_text}
---"""
    else:
        system_prompt = f"""אתה מומחה לניתוח קורות חיים. משימתך בשלב זה היא לפרק בלבד — אל תכתוב תוכן משופר.
{target_instruction}

כללים:
{lang_rule}
* אל תיצור סעיפים שאינם קיימים בקורות החיים.
* לא לכתוב "לא צוין", "לא סופק" או כל טקסט ממלא מקום.
* העתק את הטקסט המקורי המדויק לכל סעיף — אל תנסח מחדש.
* כותרת הסעיף הראשון תמיד תהיה בדיוק "פרטים אישיים" — מזג לתוכו את כל פרטי הקשר.
* זהה את כל הסעיפים הנפרדים הקיימים בקורות החיים.
* אם קיים סעיף "שונות" — כלול אותו כסעיף בפני עצמו.

רובריקת ציון (0-100, חבר במדויק):
- פרטי קשר (0-10): שם + טלפון + אימייל = 10, חסר אחד = 5, אין כלל = 0
- תקציר מקצועי (0-15): קיים ואיכותי עם זהות מקצועית = 15, קיים אך חלש = 8, לא קיים = 0
- ניסיון תעסוקתי (0-35): 2+ תפקידים עם הישגים ותאריכים = 35, 2+ ללא הישגים = 20, תפקיד אחד = 15, אין = 0
- השכלה (0-15): תואר + מוסד + שנים = 15, חלקי = 8, לא קיים = 0
- מיומנויות (0-15): 5+ מיומנויות = 15, 1-4 = 8, לא קיים = 0
- שפות (0-5): שפה אחת לפחות עם רמה = 5, ללא רמה = 3, לא קיים = 0
- בונוס (0-5): לינקדאין / התנדבות / פרויקטים = 5
- אם בקורות החיים אין תואר אקדמי, הוסף ב-general_tips המלצה לציין את המגמה ושם התיכון.

החזר JSON בלבד (ללא markdown, ללא סימני קוד):
{{
  "sections": [
    {{"title": "שם הסעיף", "original": "הטקסט המקורי המדויק"}}
  ],
  "general_tips": ["טיפ 1", "טיפ 2"],
  "keywords_to_add": ["מילת מפתח 1"],
  "score": 72
}}"""
        user_prompt = f"""פרק את קורות החיים הבאים לסעיפיהם. העתק את הטקסט המקורי המדויק לכל סעיף.

---
{cv_text}
---"""

    raw = call_ai(system_prompt, user_prompt)
    logger.info(f"Phase 1 response: {len(raw)} chars")
    return _safe_json_parse(_strip_code_fences(raw))


def _improve_one_section(
    section_title: str,
    section_original: str,
    cv_text: str,
    expert_intro: str,
    work_context: str,
    target_instruction: str,
    lang_rule: str,
    content_limits_block: str,
    _pages_tech_note: str,
    is_english: bool,
) -> dict:
    """
    Phase 2 — Single-section improvement.
    Called concurrently for every section via ThreadPoolExecutor.
    Returns {"improved": "...", "explanation": "..."}.
    """
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

{content_limits_block}

Task: improve ONLY the "{section_title}" section. The full CV is provided as context for coherence.
Return JSON only (no markdown, no code fences):
{{"improved": "improved section text", "explanation": "brief explanation"}}"""

        user_prompt = f"""Improve the "{section_title}" section.

Original section text:
---
{section_original}
---

Full CV context (do not rewrite other sections):
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
* אל תשתמש בסוגריים עגולים בטקסט העברי — השתמש במקף או בפסיק. קיצורים עבריים מוסכמים כגון מנכ"ל, משא"ן, ד"ר — שמור אותם כפי שהם.
* אם זהו סעיף "פרטים אישיים" — מזג את כל פרטי הקשר. כותרת הסעיף תהיה בדיוק "פרטים אישיים". "פרופיל לינקדין"/"פרופיל לינקדאין" — חלץ את הערך שאחריהם.
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

{content_limits_block}

משימה: שפר את הסעיף "{section_title}" בלבד. קורות החיים המלאים מסופקים כהקשר לעקביות.
החזר JSON בלבד (ללא markdown, ללא סימני קוד):
{{"improved": "הטקסט המשופר של הסעיף", "explanation": "הסבר קצר"}}"""

        user_prompt = f"""שפר את הסעיף "{section_title}".

הטקסט המקורי של הסעיף:
---
{section_original}
---

הקשר - קורות החיים המלאים (אל תשכתב סעיפים אחרים):
---
{cv_text}
---"""

    raw = call_ai(system_prompt, user_prompt)
    return _safe_json_parse(_strip_code_fences(raw))


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
    # ── Phase 1: parse & metadata ──
    logger.info("Parallel Phase 1: parsing CV into sections + metadata")
    phase1 = _parse_cv_sections(cv_text, target_instruction, lang_rule, is_english)
    sections = phase1.get("sections", [])
    if not sections:
        raise ValueError("Phase 1 returned no sections")
    logger.info(f"Phase 1 complete: {len(sections)} sections, score={phase1.get('score')}")

    # ── Phase 2: parallel section improvements ──
    fallback_msg = (
        "Could not auto-improve this section — edit manually"
        if is_english else
        "לא הצלחנו לשפר סעיף זה אוטומטית — ניתן לערוך ידנית"
    )

    def _improve_task(args: tuple) -> tuple:
        idx, section = args
        title    = section.get("title", f"section_{idx}")
        original = section.get("original", "")
        try:
            res = _improve_one_section(
                section_title=title,
                section_original=original,
                cv_text=cv_text,
                expert_intro=expert_intro,
                work_context=work_context,
                target_instruction=target_instruction,
                lang_rule=lang_rule,
                content_limits_block=content_limits_block,
                _pages_tech_note=_pages_tech_note,
                is_english=is_english,
            )
            improved    = (res.get("improved") or "").strip() or original
            explanation = res.get("explanation", "")
            logger.info(f"Section '{title}': improved ({len(improved)} chars)")
            return idx, improved, explanation
        except Exception as exc:
            logger.warning(f"Section '{title}' improvement failed: {exc} — keeping original")
            return idx, original, fallback_msg

    logger.info(f"Parallel Phase 2: improving {len(sections)} sections concurrently (max_workers=5)")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(_improve_task, enumerate(sections)))

    # ── Phase 3: merge ──
    for idx, improved, explanation in results:
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


def analyze_cv(cv_text: str, target_position: str = "", language: str = "he", max_pages: int = 1) -> dict:
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
* הרחב את סעיף המיומנויות לפחות ל-12 פריטים. כלול כישורים סטנדרטיים שאמורים להיות ברשות המועמד לאור ניסיונו — מתודולוגיות, כלים משלימים, תחומי ידע רלוונטיים — גם אם לא צוינו מפורשות.
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
* הרחב את סעיף המיומנויות לפחות ל-12 פריטים. כלול כישורים סטנדרטיים שאמורים להיות ברשות המועמד לאור ניסיונו — מתודולוגיות, כלים משלימים, תחומי ידע רלוונטיים — גם אם לא צוינו מפורשות.
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

    # ── Try parallel two-phase approach ──
    try:
        return _parallel_analyze(
            cv_text=cv_text,
            is_english=is_english,
            expert_intro=expert_intro,
            work_context=work_context,
            target_instruction=target_instruction,
            lang_rule=lang_rule,
            content_limits_block=content_limits_block,
            _pages_tech_note=_pages_tech_note,
        )
    except Exception as parallel_err:
        logger.warning(f"Parallel analysis failed ({parallel_err}), falling back to monolithic call")

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
- אל תשתמש בסוגריים עגולים בטקסט העברי - במקום סוגריים השתמש במקף - או בפסיק. קיצורים עבריים מוסכמים כגון מנכ"ל, משא"ן, ד"ר, מ"מ וכדומה - שמור אותם בדיוק כפי שהם
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
    return response.choices[0].message.content or ""


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
- אל תשתמש בסוגריים עגולים () בטקסט העברי - במקום סוגריים השתמש במקף - או בפסיק. קיצורים עבריים מוסכמים כגון מנכ"ל, משא"ן, ד"ר, מ"מ וכדומה - שמור אותם בדיוק כפי שהם"""

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
* מיומנויות: כלול את כל המיומנויות הרלוונטיות לתפקיד.
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

{_build_content_limits_block}

החזר את התוצאה בפורמט JSON בלבד (ללא markdown, ללא ```):
{{
    "full_name": "שם מלא",
    "contact": {{"phone": "טלפון", "email": "אימייל", "city": "עיר", "linkedin": "לינקדאין - URL מלא או שם פרופיל (אם במקור 'פרופיל לינקדין [שם]' → שמור את השם)"}},
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
- אל תשתמש בסוגריים עגולים בטקסט העברי - במקום סוגריים השתמש במקף - או בפסיק. קיצורים עבריים מוסכמים כגון מנכ"ל, משא"ן, ד"ר, מ"מ וכדומה - שמור אותם בדיוק כפי שהם
- חשוב ביותר: אם שדה לא סופק בנתוני הטופס - השאר אותו כמחרוזת ריקה "" או מערך ריק []. לא לכתוב "לא צוין", "לא סופק", "לא מולא" או כל טקסט ממלא מקום! אם אין מידע - פשוט השאר ריק
- אם שדה honors ריק או לא רלוונטי - השאר מחרוזת ריקה ""

ודא שהתוצאה הסופית משקפת קורות חיים מלאים, מקצועיים, מדויקים ותואמים לסטנדרטים העדכניים ביותר של שוק העבודה הישראלי ושל מערכות סינון מועמדים."""

    form_text = f"""שם: {form_data.get('full_name', '')}
טלפון: {form_data.get('phone', '')}
אימייל: {form_data.get('email', '')}
עיר: {form_data.get('city', '')}
לינקדאין: {form_data.get('linkedin', '')}

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
        return _safe_json_parse(result)
    except (json.JSONDecodeError, Exception):
        return {
            "full_name": form_data.get("full_name", ""),
            "contact": {
                "phone": form_data.get("phone", ""),
                "email": form_data.get("email", ""),
                "city": form_data.get("city", ""),
                "linkedin": form_data.get("linkedin", "")
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
- אל תשתמש בסוגריים עגולים בטקסט - במקום סוגריים השתמש במקף - או בפסיק. קיצורים עבריים מוסכמים כגון מנכ"ל, משא"ן, ד"ר, מ"מ וכדומה - שמור אותם בדיוק כפי שהם"""

    return call_ai(system_prompt, f"טקסט לשיפור:\n{original}\n\nהקשר:\n{context}")
