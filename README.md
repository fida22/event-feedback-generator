# Event Feedback Form Generator (Everyday Use track)

Paste an event description, get a customized Google Form for feedback.

## What it does
Takes a free-text event description and generates a feedback form tailored to the event's
purpose, activities and technical details. Shows a question preview, then creates a real
Google Form and returns the shareable link.

## How it works
1. **Streamlit UI** collects the event description.
2. **Claude API** returns a structured JSON form (sections, question types, options). Invalid JSON is retried up to 3 times.
3. User reviews the preview.
4. JSON is POSTed to a **Google Apps Script web app** (`Code.gs`) that builds the Form via `FormApp` and returns the live + edit URLs.

## Tools
Python, Streamlit, Anthropic Claude API, Google Apps Script, Streamlit Community Cloud.

## Run / deploy
1. Create a Google Apps Script project, paste `Code.gs`, set `TOKEN`, deploy as Web app (Execute as: Me, Access: Anyone). Copy the URL.
2. Add secrets (Streamlit Cloud > Settings > Secrets):
```
ANTHROPIC_API_KEY = "..."
APPS_SCRIPT_URL = "https://script.google.com/macros/s/.../exec"
APPS_SCRIPT_TOKEN = "same as TOKEN in Code.gs"
```
3. `pip install -r requirements.txt && streamlit run app.py`
