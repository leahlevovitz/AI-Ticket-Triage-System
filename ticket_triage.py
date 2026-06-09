"""
ticket_triage.py - Core Ticket Triage Logic
=============================================
This file implements the main ticket processing pipeline.

Architecture:
    AI (Ollama LLM) → Summary + Category (requires NLU)
    Rules (Regex + Logic) → Urgency + Human Escalation (deterministic)

Why this split?
    - AI is used where natural language understanding is needed:
      summarizing text and classifying intent from free-form input.
    - Rules are used where deterministic business logic is needed:
      urgency detection (keyword-based) and escalation decisions (boolean logic).
    - This saves cost, improves speed, and ensures consistency for
      business-critical decisions.
"""

import re
import json
import requests
from prompts import SYSTEM_PROMPT

# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"  # Local LLM model - free, runs on CPU

# ============================================================
# RULE ENGINE - No AI (fast, free, deterministic)
# ============================================================
# WHY RULES FOR URGENCY:
# Urgency detection is based on clear signal words ("urgent", "crashed",
# "emergency"). These are finite, predictable, and don't require
# understanding context. Regex is:
# - Instant (microseconds vs seconds for AI)
# - Free (no model computation)
# - Deterministic (same input always gives same output)
# - Typo-tolerant (we include common misspellings)

# Urgency patterns with typo tolerance for Hebrew
# Each level has a list of regex patterns that trigger it
URGENCY_PATTERNS = {
    "critical": [
        # Hebrew urgency words + common misspellings (דכוף instead of דחוף)
        r"(דחוף|דכוף|דחו[פף]|חירום|חרום|מיידי|urgent|critical|emergency)",
        # System down / crashed
        r"(נפל|קרס|כרס|לא עובד בכלל|השירות למטה|down|crashed)",
        # Security breach
        r"(פריצה|פרצה|אבטחה|דליפת מידע|hack|breach|hacked)",
        # Data loss
        r"(אובדן נתונים|מחיקה|נמחק הכל|data.?loss)",
    ],
    "high": [
        # Login issues
        r"(לא מצליח להיכנס|לא נכנס|נעול|חסום|blocked|locked|can.?t.?log.?in)",
        # Billing fraud
        r"(חיוב שגוי|חיוב כפול|גנבו|איבדתי.?כסף|איבדתי.?מלא|fraud|double.?charge|lost.?money)",
        # Something not working
        r"(לא עובד|תקלה|תקל|באג|bug|error|not.?working)",
        # Long wait / no response
        r"(ממתין כבר|יומיים|שבוע|לא מגיבים|לא עונים|no.?response)",
    ],
    "medium": [
        # Slow performance
        r"(איטי|אטי|slow|ביצועים|לוקח זמן|takes.?long)",
        # Questions / inquiries
        r"(שאלה|אפשר לדעת|מעוניין|רוצה לברר|question)",
        # Change requests
        r"(שינוי|עדכון|שדרוג|upgrade|change)",
    ],
    "low": [
        # Feature requests / feedback
        r"(הצעה|פידבק|פידבאק|feedback|suggestion|feature.?request)",
        # Compliments / thanks
        r"(תודה|מרוצה|שבח|מעולה|compliment|thanks|great.?service)",
        # General info
        r"(מידע כללי|שאלה כללית|general|info)",
    ],
}

# WHY RULES FOR HUMAN ESCALATION:
# The decision "does this need a human?" is pure boolean logic:
# IF (sensitive category) OR (high urgency) OR (escalation keyword) → human
# This is a business rule that must be consistent and predictable.
# AI would be non-deterministic and potentially miss critical cases.

HUMAN_ESCALATION_RULES = {
    # Categories that always require human review
    "sensitive_categories": ["אבטחה", "חיוב_ותשלומים"],
    # Urgency levels that require human attention
    "critical_urgencies": ["critical", "high"],
    # Keywords that indicate customer wants human interaction
    "escalation_keywords": [
        r"(מנהל|מנהלת|supervisor|manager|אני רוצה לדבר עם)",
        r"(עורך דין|משפטי|legal|תביעה|sue)",
        r"(ביטול|לבטל|סגירת חשבון|לסגור חשבון|cancel|close.?account)",
        r"(החזר כספי|החזר.?כסף|refund|פיצוי|compensation)",
    ],
}


def assess_urgency(text: str) -> str:
    """
    Rule-based urgency detection using typo-tolerant Regex.
    
    This function does NOT use AI. It scans the text for predefined
    keywords that indicate urgency level. This approach is:
    - Deterministic: same text always gets same urgency
    - Fast: runs in microseconds
    - Free: no API calls needed
    - Typo-tolerant: handles common Hebrew misspellings
    
    Returns: "critical", "high", "medium", or "low"
    """
    text_lower = text.lower()
    for level in ["critical", "high", "medium", "low"]:
        for pattern in URGENCY_PATTERNS[level]:
            if re.search(pattern, text_lower):
                return level
    return "medium"  # Default: medium if no keywords matched


def requires_human(text: str, category: str, urgency: str) -> bool:
    """
    Rule-based escalation decision using boolean logic.
    
    This function does NOT use AI. It applies business rules:
    1. Sensitive categories (security, billing) → always human
    2. Critical/high urgency → always human
    3. Escalation keywords (manager, cancel, refund) → human
    
    Returns: True if human handling required, False if can be automated
    """
    # Rule 1: Sensitive categories always need human review
    if category in HUMAN_ESCALATION_RULES["sensitive_categories"]:
        return True
    # Rule 2: High urgency needs human attention
    if urgency in HUMAN_ESCALATION_RULES["critical_urgencies"]:
        return True
    # Rule 3: Customer explicitly requesting escalation
    for pattern in HUMAN_ESCALATION_RULES["escalation_keywords"]:
        if re.search(pattern, text.lower()):
            return True
    return False


# ============================================================
# AI ENGINE - Ollama LLM
# ============================================================
# WHY AI FOR SUMMARY + CATEGORY:
# These tasks require natural language understanding:
# - Summarization: condensing free-form text into 1-2 sentences
# - Categorization: understanding customer INTENT, not just keywords
#   Example: "I've been trying to get in for 2 days" → login issue
#   This can't be done with regex - too many possible phrasings.

VALID_CATEGORIES = [
    "תמיכה_טכנית", "חיוב_ותשלומים", "מכירות",
    "שירות_לקוחות", "אבטחה", "כללי"
]


def ai_analyze(text: str) -> dict:
    """
    Use Ollama LLM for summarization and categorization.
    
    This function USES AI because:
    - Summarization requires paraphrasing (language generation)
    - Categorization requires intent understanding
    - Same issue can be expressed in infinite ways
    
    Returns: {"summary": "...", "category": "..."}
    """
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": f"{SYSTEM_PROMPT}\n\nפנייה:\n{text}",
            "stream": False,
            "options": {
                "temperature": 0.0,      # Deterministic output
                "num_predict": 100,      # Limit response length
                "num_ctx": 1024,         # Context window size
            },
            "format": "json",  # Force JSON output
        }, timeout=120)

        print(f"[DEBUG] Status: {response.status_code}")
        if response.status_code != 200:
            return _fallback(text)

        raw = response.json().get("response", "{}")
        result = json.loads(raw)

        # Extract and validate results
        summary = result.get("summary", "")
        category = result.get("category", "כללי")
        urgency = result.get("urgency", "medium")

        # Validation: if summary is empty or looks like a category name, use fallback
        if not summary or len(summary) < 5 or category in summary.replace(" ", ""):
            summary = text[:70] + "..." if len(text) > 70 else text

        # Validation: ensure category is from our valid list
        if category not in VALID_CATEGORIES:
            for valid in VALID_CATEGORIES:
                if valid in category or category in valid:
                    category = valid
                    break
            else:
                category = "כללי"

        # Validation: ensure urgency is valid
        valid_urgencies = ["critical", "high", "medium", "low"]
        if urgency not in valid_urgencies:
            urgency = "medium"

        return {"summary": summary, "category": category, "urgency": urgency}

    except (json.JSONDecodeError, requests.RequestException, KeyError):
        return _fallback(text)


def _fallback(text: str) -> dict:
    """Fallback when AI is unavailable - use original text as summary."""
    return {
        "summary": text[:70] + "..." if len(text) > 70 else text,
        "category": "כללי"
    }


# ============================================================
# MAIN PIPELINE - Combines AI + Rules
# ============================================================


def process_ticket(text: str) -> dict:
    """
    Process a single ticket through the full pipeline.
    
    Pipeline:
    1. AI analyzes content → summary + category + urgency
    2. Rules detect urgency from keywords (regex)
    3. Final urgency = the HIGHER of AI vs Rules (combined approach)
    4. Rules decide escalation → boolean logic on category + urgency
    
    Returns complete ticket analysis dict.
    """
    # Step 1: AI - summarization, categorization, and urgency (requires NLU)
    ai_result = ai_analyze(text)

    # Step 2: Rules - urgency detection from keywords (instant, deterministic)
    rule_urgency = assess_urgency(text)

    # Step 3: Combine - take the HIGHER urgency between AI and Rules
    # This ensures we never miss explicit keywords like "urgent"/"דחוף"
    # while also catching context-based urgency from AI
    urgency_levels = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    ai_urgency = ai_result.get("urgency", "medium")
    if ai_urgency not in urgency_levels:
        ai_urgency = "medium"
    final_urgency = ai_urgency if urgency_levels.get(ai_urgency, 2) >= urgency_levels.get(rule_urgency, 2) else rule_urgency

    # Step 4: Rules - human escalation decision (boolean logic, deterministic)
    category = ai_result["category"]
    human_needed = requires_human(text, category, final_urgency)

    return {
        "text": text,
        "summary": ai_result["summary"],
        "category": category,
        "urgency": final_urgency,
        "human_required": human_needed,
    }


def process_tickets_batch(tickets: list) -> list:
    """Process multiple tickets in parallel for better throughput."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(process_ticket, tickets))
    return results


# ============================================================
# SAMPLE TICKETS - 12 diverse examples for demonstration
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


# ============================================================
# CLI Mode - Run from command line for testing
# ============================================================

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
        print(f"  #{i} {result['text'][:60]}...")
        print(f"  Summary:  {result['summary']}")
        print(f"  Category: {result['category']}")
        print(f"  Urgency:  {result['urgency']}")
        print(f"  Human:    {'Yes' if result['human_required'] else 'No'}")
