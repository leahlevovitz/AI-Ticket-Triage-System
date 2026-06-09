# Ticket Triage System - Smart Customer Support Routing

## Overview
A system that processes customer support tickets and returns for each:
- **Summary** (AI-generated)
- **Category / Team** (AI-generated)
- **Urgency Level** (Rule-based)
- **Human Escalation Decision** (Rule-based)

## Installation & Running

### Step 1: Install Ollama (once)
Download from: https://ollama.com/download

### Step 2: Download model (once, ~2.5GB)
```bash
ollama pull gemma3:4b
```

### Step 3: Install Python dependencies (once)
```bash
python -m pip install requests flask
```

### Step 4: Run the system
```bash
# Windows PowerShell:
$env:NO_PROXY="localhost,127.0.0.1"
python app.py

# Windows CMD:
set NO_PROXY=localhost,127.0.0.1 && python app.py
```

### Step 5: Open browser
```
http://localhost:8080
```

## Architecture: AI vs Rules

| Feature | Method | Why |
|---------|--------|-----|
| Summary |  AI (Ollama LLM) | Requires natural language understanding, paraphrasing |
| Category |  AI (Ollama LLM) | Requires intent recognition - same issue can be phrased 100 ways |
| Urgency |  Rules (Regex) | Clear keywords ("urgent", "crashed") - deterministic, instant, free |
| Human Needed |  Rules (Logic) | Boolean business decision: IF critical OR sensitive category → human |

### Why this split?
1. **Cost** - Rules save 50% of AI calls (urgency + escalation are free)
2. **Speed** - Regex runs in microseconds, AI takes seconds
3. **Reliability** - Business rules must be deterministic (same input → same output always)
4. **Accuracy** - AI excels at language understanding, Rules excel at clear logic

## Tools Used
| Tool | Purpose |
|------|---------|
| Python 3 | Main programming language |
| Ollama (gemma3:4b) | Local LLM for summarization + categorization |
| Flask | Web UI framework |
| Regex | Urgency detection with typo tolerance |
| Boolean Logic | Human escalation decisions |

## Installation & Running

### Step 1: Install Ollama (once)
Download from: https://ollama.com/download

### Step 2: Download model (once, ~2.5GB)
```bash
ollama pull gemma3:4b
```

### Step 3: Install Python dependencies (once)
```bash
python -m pip install requests flask
```

### Step 4: Run the system
```bash
# Windows PowerShell:
$env:NO_PROXY="localhost,127.0.0.1"
python app.py

# Windows CMD:
set NO_PROXY=localhost,127.0.0.1 && python app.py
```

### Step 5: Open browser
```
http://localhost:8080
```

## File Structure
```
├── prompts.py          ← AI System Prompt (English, optimized for LLM)
├── ticket_triage.py    ← Core logic (AI + Rules + Pipeline)
├── app.py              ← Web UI (Flask + HTML/JS)
├── requirements.txt    ← Python dependencies
└── README.md           ← This file
```

## Limitations
1. **Model accuracy** - Local models (4B parameters) have limited Hebrew understanding. Summaries are sometimes imprecise. With larger models (GPT-4, Claude, 70B+) results would be significantly better.
2. **Speed** - Without GPU, each ticket takes 10-30 seconds to process. With GPU: 2-3 seconds.
3. **Typo tolerance** - The Regex rules handle common Hebrew misspellings (דכוף→דחוף, כרס→קרס) but cannot cover all possible typos.
4. **Language mixing** - The model occasionally mixes Hebrew and English in summaries.

## Sample Output
```
Ticket: "אני לא מצליח להיכנס לחשבון שלי כבר יומיים. דחוף!"
├── Summary (AI):    "לקוח לא מצליח להתחבר לחשבון שלו כבר יומיים"
├── Category (AI):   תמיכה_טכנית
├── Urgency (Rule):  critical (matched: "דחוף")
└── Human (Rule):    Yes (urgency is critical)
```
