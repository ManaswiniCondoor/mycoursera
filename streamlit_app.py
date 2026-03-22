"""
Trial Buddy — Streamlit Web UI
Deploy free at https://streamlit.io/cloud
"""

import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

SYSTEM_PROMPT = (
    "You are Trial Buddy, a compassionate guide helping patients understand clinical trials. "
    "You translate complex medical eligibility criteria into plain, warm, simple English. "
    "You NEVER tell someone they qualify or don't qualify. "
    "You NEVER give medical advice. "
    "You ALWAYS end responses with: 'Please verify directly with the trial coordinator "
    "before making any decisions. This is not medical advice.' "
    "You ONLY summarize information retrieved from ClinicalTrials.gov. "
    "If data is missing, say so honestly."
)

SIMULATION_TRIALS = [
    {
        "name": "Understanding New Treatments for Type 2 Diabetes",
        "what_tested": "A once-weekly injection that helps control blood sugar by working with your body's natural insulin response.",
        "eligibility": "Adults aged 18–75 with a Type 2 Diabetes diagnosis for at least 6 months. You should not be using insulin currently.",
        "location": "Mayo Clinic, Rochester, MN",
        "nct_id": "NCT05012345",
        "link": "https://clinicaltrials.gov/study/NCT05012345",
        "status": "Recruiting",
    },
    {
        "name": "Comparing Two Blood Pressure Medications in Older Adults",
        "what_tested": "Whether a newer blood pressure pill works better than the standard one for people over 65, with fewer side effects.",
        "eligibility": "Adults 65 and older with high blood pressure (systolic above 140). Must not have had a stroke or heart attack in the past year.",
        "location": "Johns Hopkins Hospital, Baltimore, MD",
        "nct_id": "NCT04987654",
        "link": "https://clinicaltrials.gov/study/NCT04987654",
        "status": "Recruiting",
    },
    {
        "name": "Early Detection Tool for Lung Changes in Former Smokers",
        "what_tested": "A new breathing test that might catch early lung problems sooner than traditional scans.",
        "eligibility": "Former smokers aged 50–80 who smoked for at least 10 years.",
        "location": "University of Pittsburgh Medical Center, Pittsburgh, PA",
        "nct_id": "NCT05098765",
        "link": "https://clinicaltrials.gov/study/NCT05098765",
        "status": "Not yet recruiting",
    },
]


def fetch_trials(condition: str) -> list:
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {"query.cond": condition, "pageSize": 10, "format": "json"}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("studies", [])
    except Exception:
        return []


def fetch_news(condition: str, tavily_key: str) -> str:
    if not tavily_key:
        return ""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
        result = client.search(
            query=f"clinical trials {condition} 2025 2026",
            max_results=3,
            search_depth="basic",
        )
        snippets = [
            f"- {r.get('title', '')}: {r.get('content', '')[:300]}"
            for r in result.get("results", [])
        ]
        return "\n".join(snippets)
    except Exception:
        return ""


def summarize_trial(study: dict) -> dict:
    proto = study.get("protocolSection", {})
    ident = proto.get("identificationModule", {})
    status = proto.get("statusModule", {})
    eligibility = proto.get("eligibilityModule", {})
    contacts = proto.get("contactsLocationsModule", {})
    locations = contacts.get("locations", [])
    loc_str = "Location not listed"
    if locations:
        loc = locations[0]
        loc_str = ", ".join(filter(None, [loc.get("facility", ""), loc.get("city", ""), loc.get("state", "")]))
    return {
        "nct_id": ident.get("nctId", "N/A"),
        "title": ident.get("briefTitle", "Untitled Study"),
        "status": status.get("overallStatus", "Unknown"),
        "eligibility": eligibility.get("eligibilityCriteria", "Not provided")[:800],
        "location": loc_str,
    }


def ask_groq(trials: list, news: str, condition: str, zipcode: str, groq_key: str) -> str:
    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        summaries = [summarize_trial(s) for s in trials[:6]]
        user_msg = (
            f"Here are raw clinical trial results for condition '{condition}' "
            f"near zip code '{zipcode}':\n\n{json.dumps(summaries, indent=2)}\n\n"
        )
        if news:
            user_msg += f"Recent news:\n{news}\n\n"
        user_msg += (
            "Please explain up to 3 of these trials in simple, warm language for a patient. "
            "For each trial include:\n"
            "1. A plain-English name\n2. What they are testing\n"
            "3. Who they are looking for (simplified eligibility)\n"
            "4. The location listed\n"
            "5. The NCT number and link: https://clinicaltrials.gov/study/<NCTID>\n"
            "6. The recruitment status\nFormat each trial clearly with numbered sections."
        )
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
            max_tokens=1200,
        )
        return chat.choices[0].message.content
    except Exception as e:
        return f"Groq error: {e}\n\nPlease verify directly with the trial coordinator before making any decisions. This is not medical advice."


def render_simulation():
    for i, t in enumerate(SIMULATION_TRIALS, 1):
        status_color = "🟢" if t["status"] == "Recruiting" else "🟡"
        with st.expander(f"Trial {i}: {t['name']}", expanded=True):
            st.markdown(f"**What they're testing:** {t['what_tested']}")
            st.markdown(f"**Who they're looking for:** {t['eligibility']}")
            st.markdown(f"**Location:** {t['location']}")
            st.markdown(f"**Status:** {status_color} {t['status']}")
            st.markdown(f"**NCT Number:** [{t['nct_id']}]({t['link']})")


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Trial Buddy",
    page_icon="🔬",
    layout="centered",
)

st.title("🔬 Trial Buddy")
st.caption("Find clinical trials in plain English")

st.warning(
    "⚠️ **Trial Buddy is not a medical service.** We do not store your information. "
    "Always consult your doctor and speak directly with trial coordinators before "
    "making any health decisions.",
    icon="⚠️",
)

# ── Sidebar: API keys (override env) ─────────────────────────────────────────
with st.sidebar:
    st.header("API Keys (optional)")
    st.caption("Leave blank to run in simulation mode.")
    groq_key = st.text_input("Groq API Key", value=GROQ_API_KEY, type="password",
                              help="Free at console.groq.com")
    tavily_key = st.text_input("Tavily API Key", value=TAVILY_API_KEY, type="password",
                                help="Free at app.tavily.com")

    mode_label = "Simulation mode" if not groq_key else "Live mode (Groq AI)"
    st.info(f"Current mode: **{mode_label}**")

    st.divider()
    st.caption("Privacy: nothing you enter is stored or logged.")

# ── Main form ─────────────────────────────────────────────────────────────────
with st.form("search_form"):
    condition = st.text_input("What condition are you searching for?",
                               placeholder="e.g. Type 2 Diabetes, breast cancer, Parkinson's")
    zipcode = st.text_input("What is your zip code?", placeholder="e.g. 90210")
    submitted = st.form_submit_button("Find Trials", type="primary", use_container_width=True)

if submitted:
    if not condition.strip():
        st.error("Please enter a condition.")
    elif not zipcode.strip():
        st.error("Please enter a zip code.")
    else:
        simulation_mode = not groq_key

        if simulation_mode:
            st.info("Running in simulation mode — showing example trials.")
            render_simulation()
        else:
            with st.spinner("Searching ClinicalTrials.gov..."):
                trials = fetch_trials(condition)

            news = ""
            if tavily_key:
                with st.spinner("Fetching recent news..."):
                    news = fetch_news(condition, tavily_key)

            if not trials:
                st.warning("No trials found on ClinicalTrials.gov. Showing simulation data.")
                render_simulation()
            else:
                with st.spinner(f"Found {len(trials)} trial(s). Asking Groq AI to explain them..."):
                    result = ask_groq(trials, news, condition, zipcode, groq_key)

                st.subheader(f"Trials for: {condition}")
                st.markdown(result)

        st.divider()
        st.caption(
            "⚠️ Please verify directly with the trial coordinator before making any decisions. "
            "This is not medical advice."
        )
