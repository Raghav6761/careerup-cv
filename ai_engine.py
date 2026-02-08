import os
import re
import json
import logging
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


def analyze_cv(cv_text: str, target_position: str = "") -> dict:
    ats_instruction = ""
    if target_position.strip():
        ats_instruction = f"""
- התפקיד אליו המועמד מתמודד: "{target_position}"
- שלב מילות מפתח רלוונטיות לתפקיד זה בטקסט המשופר כדי לעבור מערכות סינון ATS
- התאם את התקציר המקצועי, ההישגים והמיומנויות לתפקיד היעד
- בשדה keywords_to_add הוסף מילות מפתח ספציפיות לתפקיד שיסייעו בעבירת מסנני ATS
- אל תשנה עובדות, רק נסח מחדש כדי להדגיש התאמה לתפקיד"""

    system_prompt = f"""אתה מומחה בכתיבת קורות חיים מקצועיים בהתאם לסטנדרטים המקצועיים העדכניים ביותר.
תפקידך לנתח קורות חיים קיימים ולהציע שיפורים מפורטים לכל סעיף בנפרד.

עליך להחזיר תשובה בפורמט JSON בלבד (ללא markdown, ללא סימני קוד).
חשוב: ודא שכל גרש כפול (") בתוך ערכי טקסט מיוחלף ב-\\" כדי שה-JSON יהיה תקין. לדוגמה: דוא\\"ל ולא דוא"ל.

חשוב מאוד:
1. זהה כל סעיף בקורות החיים בנפרד (פרטים אישיים, ניסיון, השכלה, מיומנויות וכו')
2. בשדה "original" - העתק את הטקסט המקורי המדויק מקורות החיים עבור כל סעיף. אל תשאיר שדה זה ריק!
3. בשדה "improved" - כתוב גרסה משופרת של אותו סעיף
4. אם סעיף מסוים לא קיים בקורות החיים אך מומלץ להוסיפו, כתוב "לא קיים במקור" בשדה original

המבנה הנדרש:
{{
    "sections": [
        {{
            "title": "שם הסעיף (לדוגמה: פרטים אישיים)",
            "original": "הטקסט המקורי המדויק מקורות החיים - חובה למלא!",
            "improved": "הגרסה המשופרת של הטקסט",
            "explanation": "הסבר קצר מה שופר ולמה"
        }}
    ],
    "general_tips": ["טיפ 1", "טיפ 2"],
    "keywords_to_add": ["מילת מפתח 1", "מילת מפתח 2"],
    "score": 72
}}

כללים חשובים:
- השתמש בעברית בלבד
- חלק את קורות החיים ל-3 סעיפים לפחות
- שדה "original" חייב להכיל את הטקסט המקורי כפי שהוא מופיע בקורות החיים - זה קריטי!

הנחיות מקצועיות לשיפור קורות חיים:
- תקציר מקצועי (החלק הכי חשוב!): 2-3 משפטים קצרים הכוללים: סך שנות ניסיון מצטבר, ניסיון רלוונטי למשרה, הישגים כמותיים בולטים, וכישורים רכים רלוונטיים (עבודת צוות, מנהיגות, פתרון בעיות)
- השתמש בפעלים חזקים ואקטיביים: ניהלתי, פיתחתי, יזמתי, יישמתי, הובלתי, ייעלתי, הטמעתי, הגדלתי, חסכתי, שיפרתי, הקמתי
- נסח הישגים מדידים במקום מטלות (למשל: "הגדלתי מכירות ב-30% תוך שישה חודשים" במקום "אחראי על מכירות")
- הוסף מדדים כמותיים להישגים: אחוזי שיפור, סכומי חיסכון, מספר אנשים שנוהלו, היקף תקציב
- הישגים: עד 2-3 נקודות לכל תפקיד, 4-5 לתפקיד רלוונטי עיקרי. כל נקודה משפט אחד קצר בלבד
- סדר הצגת תפקידים: תאריך ראשון, אחריו שם החברה והתפקיד. סדר כרונולוגי יורד (מהאחרון לראשון)
- אם המועמד התקדם באותו ארגון, הבלט את ההתקדמות בקריירה

סינון מידע אישי מיותר:
- הסר מצב משפחתי, מספר תעודת זהות, תאריך לידה, ותמונה אם מופיעים
- פרטים אישיים צריכים לכלול רק: שם מלא, טלפון, אימייל, וכתובת לינקדאין (אם יש)
- אפשרי להוסיף מיקום גאוגרפי, לא חובה עיר מגורים מדויקת

כללי עיצוב ומבנה:
- חשוב מאוד: שמור על תמציתיות מקסימלית! קורות חיים חייבים להיכנס לעמוד אחד בלבד
- תאריכים: הצג שנים בלבד (לא חודשים). לדוגמה: "2020-2023" ולא "ינואר 2020 - מרץ 2023"
- זהה והתייחס לפערים תעסוקתיים (חורים בקורות החיים) - המלץ כיצד להתמודד איתם
- אל תוסיף טקסט מיותר, פסקאות ארוכות, או תיאורים מפורטים מדי
- לא להוסיף כותרות כמו "קורות חיים" או "קורות חיים משופרים" - רק תוכן
- הוסף מילות מפתח רלוונטיות לתחום
- ציון (score) בין 0-100 המשקף את איכות קורות החיים המקוריים
- סעיפים מומלצים: פרטים אישיים, תקציר מקצועי, ניסיון תעסוקתי, השכלה, מיומנויות, שפות
- אם יש הצטיינויות (מעבודה, צבא, או לימודים) - הבלט אותן
- אם יש התנדבות או פרויקטים עצמאיים משמעותיים, המלץ להוסיף אותם{ats_instruction}"""

    target_note = ""
    if target_position.strip():
        target_note = f"\n\nהתפקיד אליו המועמד מתמודד: {target_position}\nשלב מילות מפתח רלוונטיות לתפקיד זה בשיפורים."

    user_prompt = f"""נתח את קורות החיים הבאים. חשוב: זהה כל סעיף, העתק את הטקסט המקורי שלו לשדה original, וכתוב גרסה משופרת בשדה improved.

קורות החיים:
---
{cv_text}
---

זכור: שדה original חייב להכיל את הטקסט המקורי מקורות החיים. אל תשאיר אותו ריק.{target_note}"""

    logger.info(f"Analyzing CV with {len(cv_text)} characters")
    result = call_ai(system_prompt, user_prompt)
    logger.info(f"AI response length: {len(result)} characters")

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
        sections = parsed.get("sections", [])
        logger.info(f"Parsed {len(sections)} sections successfully")
        for section in sections:
            orig_len = len(section.get("original", ""))
            impr_len = len(section.get("improved", ""))
            logger.info(f"Section '{section.get('title', '?')}': original={orig_len} chars, improved={impr_len} chars")
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
        "linkedin": "כתובת לינקדאין"
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

הנחיות מקצועיות:
- תקציר מקצועי (החלק הכי חשוב!): 2-3 משפטים הכוללים סך שנות ניסיון, הישגים כמותיים, וכישורים רכים רלוונטיים
- השתמש בפעלים חזקים ואקטיביים: ניהלתי, פיתחתי, יזמתי, יישמתי, הובלתי, ייעלתי, הטמעתי, הגדלתי
- נסח הישגים מדידים עם מדדים כמותיים (אחוזים, סכומים, מספר אנשים)
- הישגים: עד 2-3 נקודות לכל תפקיד, 4-5 לתפקיד רלוונטי עיקרי
- סדר כרונולוגי יורד. תאריכים בשנים בלבד (לא חודשים)
- אם המועמד התקדם באותו ארגון, הבלט את ההתקדמות
- הבלט הצטיינויות מעבודה, צבא או לימודים
- פרטים אישיים: שם, טלפון, אימייל, לינקדאין בלבד. לא לכלול מצב משפחתי, ת.ז., תאריך לידה
- אם חסר מידע, השאר את השדה ריק
- שמור על תמציתיות מקסימלית - עמוד אחד בלבד
- אל תוסיף כותרות כמו "קורות חיים" - רק התוכן עצמו
- אם יש התנדבות או פרויקטים עצמאיים, כלול אותם. אם אין - השאר מערך ריק"""

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
            "contact": {"phone": "", "email": "", "city": ""},
            "professional_summary": result[:300],
            "experience": [],
            "education": [],
            "skills": {"technical": [], "soft": []},
            "languages": [],
            "additional": []
        }


def generate_cv_from_form(form_data: dict, target_position: str = "") -> dict:
    ats_instruction = ""
    if target_position.strip():
        ats_instruction = f"""
- התפקיד אליו המועמד מתמודד: "{target_position}"
- שלב מילות מפתח רלוונטיות לתפקיד זה בתקציר המקצועי, בהישגים ובמיומנויות כדי לעבור מערכות סינון ATS
- התאם את הניסוח כך שידגיש התאמה לתפקיד היעד
- אל תמציא מידע שלא קיים בטופס, רק נסח מחדש כדי להדגיש התאמה"""

    system_prompt = f"""אתה מומחה בכתיבת קורות חיים מקצועיים בהתאם לסטנדרטים המקצועיים העדכניים ביותר.
קיבלת נתוני טופס מהמשתמש. תפקידך:
1. לשפר ולנסח מחדש את התוכן בצורה מקצועית
2. לכתוב תקציר מקצועי אם המשתמש לא כתב אחד
3. לנסח הישגים באופן מדיד ומקצועי
4. להוסיף מילות מפתח רלוונטיות

החזר את התוצאה בפורמט JSON בלבד (ללא markdown, ללא ```):
{{
    "full_name": "שם מלא",
    "contact": {{"phone": "טלפון", "email": "אימייל", "city": "עיר", "linkedin": "כתובת לינקדאין"}},
    "professional_summary": "תקציר מקצועי של 2-3 משפטים",
    "experience": [
        {{"title": "תפקיד", "company": "חברה", "period": "תקופה", "achievements": ["הישג 1", "הישג 2"], "honors": "הצטיינות אם יש"}}
    ],
    "education": [{{"degree": "תואר", "institution": "מוסד", "year": "שנה", "honors": "הצטיינות אם יש"}}],
    "skills": {{"technical": ["מיומנות"], "soft": ["מיומנות"]}},
    "languages": [{{"language": "שפה", "level": "רמה"}}],
    "volunteering": ["פעילות התנדבותית"],
    "projects": ["פרויקט עצמאי"],
    "additional": ["פריט נוסף"]
}}

כללים:
- שמור על הנתונים המקוריים (שם, טלפון, אימייל, תקופות, מוסדות)
- שפר רק את הניסוח של הישגים, תקציר, ומיומנויות
- אל תמציא מידע שלא קיים בטופס
- כתוב בעברית בלבד

הנחיות מקצועיות:
- תקציר מקצועי (החלק הכי חשוב!): 2-3 משפטים הכוללים סך שנות ניסיון, הישגים כמותיים בולטים, וכישורים רכים רלוונטיים
- השתמש בפעלים חזקים ואקטיביים: ניהלתי, פיתחתי, יזמתי, יישמתי, הובלתי, ייעלתי, הטמעתי, הגדלתי, חסכתי, שיפרתי
- נסח הישגים מדידים עם מדדים כמותיים (אחוזים, סכומים, מספר אנשים)
- הישגים: עד 2-3 נקודות לכל תפקיד, 4-5 לתפקיד רלוונטי עיקרי
- סדר כרונולוגי יורד. תאריכים בשנים בלבד (לא חודשים)
- אם המועמד התקדם באותו ארגון, הבלט את ההתקדמות
- הבלט הצטיינויות מעבודה, צבא או לימודים
- שמור על תמציתיות מקסימלית - עמוד אחד בלבד
- אל תוסיף כותרות כמו "קורות חיים" - רק התוכן עצמו
- אם יש התנדבות או פרויקטים עצמאיים, כלול אותם בשדות המתאימים. אם אין - השאר מערך ריק{ats_instruction}"""

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

    volunteering = form_data.get("volunteering", "")
    if volunteering:
        form_text += f"\nהתנדבות: {volunteering}\n"

    projects = form_data.get("projects", "")
    if projects:
        form_text += f"\nפרויקטים עצמאיים: {projects}\n"

    additional = form_data.get("additional", "")
    if additional:
        form_text += f"\nמידע נוסף: {additional}\n"

    target_note = ""
    if target_position.strip():
        target_note = f"\n\nהתפקיד אליו המועמד מתמודד: {target_position}\nשלב מילות מפתח רלוונטיות לתפקיד זה."

    user_prompt = f"""צור קורות חיים מקצועיים על סמך נתוני הטופס הבאים:

{form_text}{target_note}"""

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
                "city": form_data.get("city", "")
            },
            "professional_summary": form_data.get("professional_summary", ""),
            "experience": [],
            "education": [],
            "skills": {"technical": [], "soft": []},
            "languages": [],
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
- For military service lines, translate them as regular text (not as job positions). Mark them clearly, e.g., "Military Service: Israeli Air Force, Intelligence – Clerk (full service)"
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
    system_prompt = """אתה מומחה בכתיבת קורות חיים. שפר את הטקסט הבא כך שיהיה מקצועי יותר.
החזר רק את הטקסט המשופר, ללא הסברים נוספים.
- נסח הישגים מדידים במקום מטלות (למשל: "הגדלתי מכירות ב-30%" במקום "אחראי על מכירות")
- השתמש בפעלים חזקים ואקטיביים: ניהלתי, פיתחתי, יזמתי, יישמתי, הובלתי, ייעלתי
- הוסף מדדים כמותיים אם אפשר: אחוזים, סכומים, מספר אנשים
- תאריכים בשנים בלבד (לא חודשים)
- כתוב בעברית"""

    return call_ai(system_prompt, f"טקסט לשיפור:\n{original}\n\nהקשר:\n{context}")
