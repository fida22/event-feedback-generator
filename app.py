import json, os
import requests, streamlit as st

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

def secret(k):
    return os.getenv(k) or st.secrets.get(k, "")

SYSTEM = """You design event feedback forms. Given an event description, return ONLY valid JSON (no markdown):
{"title": str, "description": str, "sections": [{"title": str, "questions": [
 {"text": str, "type": "MULTIPLE_CHOICE"|"CHECKBOX"|"SCALE"|"PARAGRAPH"|"TEXT",
  "options": [str], "required": bool}]}]}
Rules: 4-6 sections tailored to the event's purpose, activities and technical details
(e.g. Overall Experience, each activity/session, Technical/Content Quality, Logistics & Venue,
Suggestions). 10-18 questions total. SCALE = 1-5 rating (no options). Use options only for
MULTIPLE_CHOICE/CHECKBOX. Mix types. Reference the real activities and tools named. End with an
optional open-ended suggestions question."""

def generate(desc):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODEL}:generateContent?key={secret('GEMINI_API_KEY')}")
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"parts": [{"text": desc}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    last = None
    for _ in range(3):  # retry on API error or broken JSON
        r = requests.post(url, json=body, timeout=60)
        if r.status_code != 200:
            last = r.text[:200]
            continue
        try:
            txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(txt)
        except Exception as e:
            last = e
    raise RuntimeError(f"Gemini failed: {last}")

def create_form(spec):
    r = requests.post(secret("APPS_SCRIPT_URL"),
                      data=json.dumps({"token": secret("APPS_SCRIPT_TOKEN"), "form": spec}),
                      timeout=60)
    r.raise_for_status()
    out = r.json()
    if "error" in out:
        raise RuntimeError(out["error"])
    return out

st.set_page_config(page_title="Event Feedback Form Generator", page_icon="📝")
st.title("📝 Event Feedback Form Generator")
st.caption("Describe your event. Get a tailored Google Form in seconds.")

desc = st.text_area("Event description", height=180, placeholder=
    "e.g. 2-day hackathon at IIITDM, 120 participants, theme: AI for healthcare, "
    "workshops on LangChain and Docker, mentor rounds, final demo, free food...")

if st.button("Generate questions", type="primary", disabled=not desc.strip()):
    with st.spinner("Designing your form..."):
        try:
            st.session_state.spec = generate(desc)
            st.session_state.pop("result", None)
        except Exception as e:
            st.error(str(e))

spec = st.session_state.get("spec")
if spec:
    st.subheader(spec["title"])
    st.write(spec.get("description", ""))
    for s in spec["sections"]:
        with st.expander(s["title"], expanded=True):
            for q in s["questions"]:
                st.markdown(f"**{q['text']}** `{q['type']}`" + (" *" if q.get("required") else ""))
                if q.get("options"):
                    st.caption(" • ".join(q["options"]))
    if st.button("Create Google Form ✅"):
        with st.spinner("Creating form..."):
            try:
                st.session_state.result = create_form(spec)
            except Exception as e:
                st.error(str(e))

res = st.session_state.get("result")
if res:
    st.success("Form created!")
    st.markdown(f"**Share with attendees:** {res['url']}")
    st.markdown(f"**Edit form:** {res['editUrl']}")
