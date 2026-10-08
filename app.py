import json, os
import time
import requests, streamlit as st

GEMINI_PREFER = [os.getenv("GEMINI_MODEL", ""), "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash"]
GROQ_PREFER = [os.getenv("GROQ_MODEL", ""), "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]


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

TYPES = {"MULTIPLE_CHOICE", "CHECKBOX", "SCALE", "PARAGRAPH", "TEXT"}


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def clean(spec):
    """Check the model output and fix small problems so Apps Script never gets bad data."""
    if not isinstance(spec, dict) or not isinstance(spec.get("sections"), list):
        raise ValueError("Model output has no sections.")
    sections = []
    for s in spec["sections"]:
        qs = []
        for q in s.get("questions", []):
            text = str(q.get("text", "")).strip()
            if not text:
                continue
            t = str(q.get("type", "PARAGRAPH")).upper()
            if t not in TYPES:
                t = "PARAGRAPH"
            opts = [str(o) for o in q.get("options", [])] if t in ("MULTIPLE_CHOICE", "CHECKBOX") else []
            if t in ("MULTIPLE_CHOICE", "CHECKBOX") and len(opts) < 2:
                t, opts = "PARAGRAPH", []
            qs.append({"text": text, "type": t, "options": opts, "required": bool(q.get("required", False))})
        if qs:
            sections.append({"title": str(s.get("title") or "Questions"), "questions": qs})
    if not sections:
        raise ValueError("Model output has no usable questions.")
    return {
        "title": str(spec.get("title") or "Event Feedback Form"),
        "description": str(spec.get("description") or ""),
        "sections": sections,
    }


def gemini_models(key):
    """Ask Google which models exist right now, so retired names never break the app."""
    r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                     headers={"x-goog-api-key": key}, timeout=20)
    r.raise_for_status()
    names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])
             and "flash" in m["name"]
             and not any(x in m["name"] for x in ("image", "tts", "live", "audio", "embedding"))]
    pref = [m for m in GEMINI_PREFER if m and m in names]
    return pref + [m for m in sorted(names, reverse=True) if m not in pref]


def generate_gemini(desc):
    key = secret("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing in Secrets.")
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"parts": [{"text": desc}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    models = gemini_models(key)
    if not models:
        raise RuntimeError("No Gemini flash models available for this key.")
    last = None
    for attempt in range(2):
        for m in models[:3]:
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                    headers={"x-goog-api-key": key}, json=body, timeout=60)
                if r.status_code != 200:
                    last = f"{m}: HTTP {r.status_code} {r.text[:150]}"
                    continue
                txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return clean(parse_json(txt))
            except Exception as e:
                last = f"{m}: {e}"
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(last)


def groq_models(key):
    r = requests.get("https://api.groq.com/openai/v1/models",
                     headers={"Authorization": f"Bearer {key}"}, timeout=20)
    r.raise_for_status()
    ids = [m["id"] for m in r.json()["data"]
           if not any(x in m["id"] for x in ("whisper", "guard", "tts", "playai", "distil"))]
    pref = [m for m in GROQ_PREFER if m and m in ids]
    return pref + [m for m in ids if m not in pref]


def generate_groq(desc):
    key = secret("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing in Secrets.")
    last = None
    for m in groq_models(key)[:3]:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": m,
                      "response_format": {"type": "json_object"},
                      "messages": [{"role": "system", "content": SYSTEM + "\nReturn JSON only."},
                                   {"role": "user", "content": desc}]},
                timeout=60)
            r.raise_for_status()
            return clean(parse_json(r.json()["choices"][0]["message"]["content"]))
        except Exception as e:
            last = f"{m}: {e}"
    raise RuntimeError(last or "No Groq models available.")


def generate(desc):
    errs = []
    for fn in (generate_gemini, generate_groq):
        try:
            return fn(desc)
        except Exception as e:
            errs.append(f"{fn.__name__}: {e}")
    raise RuntimeError("Gemini and Groq both failed. " + " | ".join(errs))


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
