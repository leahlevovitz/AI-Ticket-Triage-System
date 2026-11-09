# 🎫 AI Ticket Triage System

> Smart routing for customer-support tickets: **an LLM where language understanding is needed, deterministic rules where predictability matters.**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web_UI-000000?logo=flask&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Gemma_3_4B-111111)
![LLM](https://img.shields.io/badge/AI-Local_LLM-2DD4BF)

Every incoming ticket is turned into a structured, routable record:

| Field | How it's produced | Why |
|---|---|---|
| **Summary** | 🤖 Local LLM (Ollama, Gemma 3 4B) | Needs real language understanding and paraphrasing |
| **Category / team** | 🤖 Local LLM | The same issue can be phrased a hundred ways, so intent matters |
| **Urgency** | 📏 Rules (regex keywords) | Deterministic, instant and free; never misses "urgent" / "דחוף" |
| **Needs a human?** | 📏 Business logic | Escalation (manager, refund, cancel) must be predictable and auditable |

## ✨ Highlights
- **Hybrid AI + rules architecture.** The model handles meaning; the rules handle decisions that must never be wrong.
- **Runs 100% locally.** No API keys, no cost, no customer data leaving the machine.
- **Hebrew-first prompts** with few-shot examples and strict JSON output.
- **Graceful fallback.** If the model fails or returns invalid JSON, the ticket is still triaged by the rules and flagged for a human.
- **Batch mode.** Process a single ticket or a whole list of sample tickets from the web UI.

## 🏗️ How it works
```
Ticket text
   │
   ├──► 🤖 Ollama LLM ──► summary + category (JSON)
   │
   ├──► 📏 Regex rules ──► urgency: high / medium / low
   │
   └──► 📏 Escalation logic ──► human_required: true / false
                │
                ▼
        Structured ticket → routed to the right team
```

## 📁 Project structure
```
app.py            # Flask web app and API endpoints (/process, /process_samples, ...)
ticket_triage.py  # Core pipeline: AI analysis, urgency rules, escalation logic, fallback
prompts.py        # System prompt with categories and few-shot examples
requirements.txt
```

## 🚀 Getting started
```bash
# 1. Install Ollama: https://ollama.com/download, then pull the model (~2.5 GB)
ollama pull gemma3:4b

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app (Windows PowerShell)
$env:NO_PROXY="localhost,127.0.0.1"
python app.py
```
Then open **http://localhost:8080**.

## 💡 What I learned
Good AI engineering isn't "use the model for everything". It's choosing **where** a model adds value and where a simple rule is faster, cheaper and safer.

---
👩‍💻 Built by **Leah Levovitz** · [LinkedIn](https://www.linkedin.com/in/leahlevovitz) · [GitHub](https://github.com/leahlevovitz)
