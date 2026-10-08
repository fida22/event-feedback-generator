# Event Feedback Form Generator (Everyday Use track)

Paste an event description, get a customized Google Form for feedback.

**Live app:** <add your Streamlit link here>

## What it does
Takes a free-text event description and generates a feedback form tailored to the event's
purpose, activities and technical details. Shows a question preview, then creates a real
Google Form and returns the shareable link.

## How it works
Event description -> Gemini (structured JSON) -> preview -> Apps Script -> Google Form link

1. **Streamlit UI** collects the event description.
2. **Google Gemini API** returns a structured JSON form (sections, question types, options). API errors and invalid JSON are retried up to 3 times.
3. The user reviews the question preview.
4. The JSON is POSTed to a **Google Apps Script web app** (`Code.gs`), protected by a shared secret token. It builds the Form with `FormApp` and returns the live and edit URLs.

## Tools used
Python, Streamlit, Google Gemini API, Google Apps Script, GitHub, Streamlit Community Cloud.

## Run / deploy
1. Create an Apps Script project, paste `Code.gs`, set `TOKEN`, deploy as Web app (Execute as: Me, Access: Anyone). Copy the `/exec` URL.
2. Get a free Gemini API key from aistudio.google.com.
3. Add secrets (Streamlit Cloud > Settings > Secrets):
```
GEMINI_API_KEY = "..."
APPS_SCRIPT_URL = "https://script.google.com/macros/s/.../exec"
APPS_SCRIPT_TOKEN = "same as TOKEN in Code.gs"
```
4. Run locally: `pip install -r requirements.txt && streamlit run app.py`
