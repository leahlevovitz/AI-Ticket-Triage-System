"""
Ticket Triage System
=====================
AI (Ollama llama3) → Summary + Category
Rules (Regex + Logic) → Urgency + Human Escalation

The AI handles natural language understanding (summarization, intent classification).
The Rules handle deterministic business logic (urgency detection, escalation decisions).
"""

import re
import json
import requests
from prompts import SYSTEM_PROMPT

# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"

# ============================================================
# RULE ENGINE (No AI - fast, free, deterministic)
# ============================================================
# WHY RULES: Urgency and escalation are business decisions based on
# clear keywords. They must be consistent, instant, and free.
# AI would be overkill and non-deterministic for this.

# Typo-tolerant patterns (handles common Hebrew misspellings)
URGENCY_PATTERNS = {
    "critical": [
        r"(דחוף|דכוף|דחו[פף]|חירום|חרום|מיידי|urgent|critical|emergency)",
        r"(נפל|קרס|כרס|לא עובד בכלל|השירות למטה|down|crashed)",
        r"(פריצה|פרצה|אבטחה|דליפת מידע|hack|breach|hacked)",
        r"(אובדן נתונים|מחיקה|נמחק הכל|data.?loss)",
    ],
    "high": [
        r"(לא מצליח להיכנס|לא נכנס|נעול|חסום|blocked|locked|can.?t.?log.?in)",
        r"(חיוב שגוי|חיוב כפול|גנבו|fraud|double.?charge)",
        r"(לא עובד|תקלה|תקל|באג|bug|error|not.?working)",
        r"(ממתין כבר|יומיים|שבוע|לא מגיבים|לא עונים|no.?response)",
    ],
    "medium": [
        r"(איטי|אטי|slow|ביצועים|לוקח זמן|takes.?long)",
        r"(שאלה|אפשר לדעת|מעוניין|רוצה לברר|question)",
        r"(שינוי|עדכון|שדרוג|upgrade|change)",
    ],
    "low": [
        r"(הצעה|פידבק|פידבאק|feedback|suggestion|feature.?request)",
        r"(תודה|מרוצה|שבח|מעולה|compliment|thanks|great.?service)",
        r"(מידע כללי|שאלה כללית|general|info)",
    ],
}

HUMAN_ESCALATION_RULES = {
    "sensitive_categories": ["אבטחה", "חיוב_ותשלומים"],
    "critical_urgencies": ["critical", "high"],
    "escalation_keywords": [
        r"(מנהל|מנהלת|supervisor|manager|אני רוצה לדבר עם)",
        r"(עורך דין|משפטי|legal|תביעה|sue)",
        r"(ביטול|לבטל|סגירת חשבון|לסגור חשבון|cancel|close.?account)",
        r"(החזר כספי|החזר.?כסף|refund|פיצוי|compensation)",
    ],
}


def assess_urgency(text: str) -> str:
    """Rule-based urgency detection using typo-tolerant Regex."""
    text_lower = text.lower()
    for level in ["critical", "high", "medium", "low"]:
        for pattern in URGENCY_PATTERNS[level]:
            if re.search(pattern, text_lower):
                return level
    return "medium"


def requires_human(text: str, category: str, urgency: str) -> bool:
    """Rule-based escalation decision using boolean logic."""
    if category in HUMAN_ESCALATION_RULES["sensitive_categories"]:
        return True
    if urgency in HUMAN_ESCALATION_RULES["critical_urgencies"]:
        return True
    for pattern in HUMAN_ESCALATION_RULES["escalation_keywords"]:
        if re.search(pattern, text.lower()):
            return True
    return False


# ============================================================
# AI ENGINE (Ollama LLM)
# ============================================================
# WHY AI: Summary and categorization require understanding natural
# language, context, intent, and paraphrasing. A customer can express
# the same issue in 100 different ways - only AI can handle this.

VALID_CATEGORIES = ["תמיכה_טכנית", "חיוב_ותשלומים", "מכירות", "שירות_לקוחות", "אבטחה", "כללי"]


def ai_analyze(text: str) -> dict:
    """Use Ollama LLM for summarization and categorization."""
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": f"{SYSTEM_PROMPT}\n\nפנייה:\n{text}",
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 100, "num_ctx": 1024},
            "format": "json",
        }, timeout=120)

        print(f"[DEBUG] Status: {response.status_code}")
        if response.status_code != 200:
            return _fallback(text)

        raw = response.json().get("response", "{}")
        result = json.loads(raw)

        summary = result.get("summary", "")
        category = result.get("category", "כללי")

        # Validate summary
        if not summary or len(summary) < 5 or category in summary.replace(" ", ""):
            summary = text[:70] + "..." if len(text) > 70 else text

        # Validate category
        if category not in VALID_CATEGORIES:
            for valid in VALID_CATEGORIES:
                if valid in category or category in valid:
                    category = valid
                    break
            else:
                category = "כללי"

        return {"summary": summary, "category": category}

    except (json.JSONDecodeError, requests.RequestException, KeyError):
        return _fallback(text)


def _fallback(text: str) -> dict:
    """Fallback when AI is unavailable - use text as summary."""
    return {
        "summary": text[:70] + "..." if len(text) > 70 else text,
        "category": "כללי"
    }


# ============================================================
# MAIN PIPELINE
# ============================================================


def process_ticket(text: str) -> dict:
    """Process a single ticket combining AI + Rules."""
    # Step 1: AI analyzes content (summary + category)
    ai_result = ai_analyze(text)

    # Step 2: Rules determine urgency (regex on keywords)
    urgency = assess_urgency(text)

    # Step 3: Rules determine if human needed (logic on category + urgency + keywords)
    category = ai_result["category"]
    human_needed = requires_human(text, category, urgency)

    return {
        "text": text,
        "summary": ai_result["summary"],
        "category": category,
        "urgency": urgency,
        "human_required": human_needed,
    }


def process_tickets_batch(tickets: list) -> list:
    """Process multiple tickets in parallel for speed."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(process_ticket, tickets))
    return results


# ============================================================
# SAMPLE TICKETS
# ============================================================

SAMPLE_TICKETS = [
    "שלום, אני לא מצליח להיכנס לחשבון שלי כבר יומיים. ניסיתי לאפס סיסמה ולא מגיע מייל. דחוף!",
    "קיבלתי חיוב כפול בכרטיס האשראי על אותה עסקה. סכום של 500 ש״ח חויב פעמיים. אבקש החזר כספי.",
    "היי, רציתי לשאול אם יש מבצע על החבילה השנתית? מעוניין לשדרג את התוכנית שלי.",
    "השירות קרס לגמרי! אף דבר לא עובד, לא אתר ולא אפליקציה. יש לנו אירוע בעוד שעה וזה חירום!",
    "אני חושב שמישהו פרץ לחשבון שלי. ראיתי פעולות שלא ביצעתי ושינויים בהגדרות. אבטחה!",
    "תודה רבה על השירות המעולה שקיבלתי מנציג בשם יוסי. ממש עזר לי ופתר את הבעיה במהירות.",
    "Hi, your website has been extremely slow for the past few days. Pages take 10 seconds to load. This is affecting my work.",
    "אני רוצה לדבר עם מנהל. הנציג לא עוזר לי ואני מתעסק עם הבעיה הזו כבר שבוע. לא מגיבים!",
    "What are your customer service hours? And where is the nearest branch in Tel Aviv?",
    "אני רוצה לבטל את המנוי שלי. לא מרוצה מהשירות ורוצה סגירת חשבון מיידית וגם החזר על החודש האחרון.",
    "There's a bug in the app - when I click the save button nothing happens. This is on version 3.2.1 Android.",
    "הצעה לשיפור: הייתי שמח אם הייתם מוסיפים מצב כהה (dark mode) לאפליקציה. פידבק כללי.",
]


if __name__ == "__main__":
    import os
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"

    print("=" * 70)
    print("  Ticket Triage System")
    print(f"  Model: {OLLAMA_MODEL} | Rules: Regex + Logic")
    print("=" * 70)

    for i, ticket in enumerate(SAMPLE_TICKETS, 1):
        print(f"\n{'─' * 70}")
        result = process_ticket(ticket)
        print(f"  #{i} {result['text']}")
        print(f"  Summary:  {result['summary']}")
        print(f"  Category: {result['category']}")
        print(f"  Urgency:  {result['urgency']}")
        print(f"  Human:    {'Yes' if result['human_required'] else 'No'}")
