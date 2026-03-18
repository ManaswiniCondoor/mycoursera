#!/usr/bin/env python3
"""
Trial Buddy — Clinical Trial Finder Agent
Stateless CLI agent that helps patients find clinical trials in plain English.
"""

import os
import json
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

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

DISCLAIMER = (
    "\n⚠️  Trial Buddy is not a medical service. We do not store your information. "
    "Always consult your doctor and speak directly with trial coordinators before "
    "making any health decisions.\n"
)

SIMULATION_TRIALS = [
    {
        "name": "Understanding New Treatments for Type 2 Diabetes",
        "what_tested": "A once-weekly injection that helps control blood sugar by working with your body's natural insulin response.",
        "eligibility": "Adults aged 18–75 with a Type 2 Diabetes diagnosis for at least 6 months. You should not be using insulin currently.",
        "location": "Mayo Clinic, Rochester, MN (approx. 45 miles from your zip code)",
        "nct_id": "NCT05012345",
        "link": "https://clinicaltrials.gov/study/NCT05012345",
        "status": "Recruiting",
    },
    {
        "name": "Comparing Two Blood Pressure Medications in Older Adults",
        "what_tested": "Whether a newer blood pressure pill works better than the standard one for people over 65, with fewer side effects.",
        "eligibility": "Adults 65 and older with high blood pressure (systolic above 140). Must not have had a stroke or heart attack in the past year.",
        "location": "Johns Hopkins Hospital, Baltimore, MD (approx. 12 miles from your zip code)",
        "nct_id": "NCT04987654",
        "link": "https://clinicaltrials.gov/study/NCT04987654",
        "status": "Recruiting",
    },
    {
        "name": "Early Detection Tool for Lung Changes in Former Smokers",
        "what_tested": "A new breathing test (spirometry plus a biomarker breath sample) that might catch early lung problems sooner than traditional scans.",
        "eligibility": "Former smokers aged 50–80 who smoked for at least 10 years. Non-smokers and current smokers are not eligible.",
        "location": "University of Pittsburgh Medical Center, Pittsburgh, PA (approx. 30 miles from your zip code)",
        "nct_id": "NCT05098765",
        "link": "https://clinicaltrials.gov/study/NCT05098765",
        "status": "Not yet recruiting",
    },
]


def fetch_trials(condition: str) -> list:
    """Fetch trials from ClinicalTrials.gov public API. Returns list of study dicts."""
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        "query.cond": condition,
        "pageSize": 10,
        "format": "json",
        "fields": "NCTId,BriefTitle,OverallStatus,EligibilityCriteria,LocationFacility,LocationCity,LocationState",
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("studies", [])
    except Exception as e:
        print(f"  [Note: Could not reach ClinicalTrials.gov — {e}]")
        return []


def fetch_news(condition: str) -> str:
    """Fetch recent news via Tavily. Returns plain-text snippets or empty string."""
    if not TAVILY_API_KEY:
        return ""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        result = client.search(
            query=f"clinical trials {condition} 2025 2026",
            max_results=3,
            search_depth="basic",
        )
        snippets = []
        for r in result.get("results", []):
            title = r.get("title", "")
            content = r.get("content", "")
            if title or content:
                snippets.append(f"- {title}: {content[:300]}")
        return "\n".join(snippets)
    except Exception as e:
        return f"[News search unavailable: {e}]"


def summarize_trial_for_prompt(study: dict) -> dict:
    """Extract relevant fields from a ClinicalTrials.gov study object."""
    proto = study.get("protocolSection", {})
    ident = proto.get("identificationModule", {})
    status = proto.get("statusModule", {})
    eligibility = proto.get("eligibilityModule", {})
    contacts = proto.get("contactsLocationsModule", {})

    locations = contacts.get("locations", [])
    location_str = "Location not listed"
    if locations:
        loc = locations[0]
        city = loc.get("city", "")
        state = loc.get("state", "")
        facility = loc.get("facility", "")
        location_str = ", ".join(filter(None, [facility, city, state]))

    return {
        "nct_id": ident.get("nctId", "N/A"),
        "title": ident.get("briefTitle", "Untitled Study"),
        "status": status.get("overallStatus", "Unknown"),
        "eligibility": eligibility.get("eligibilityCriteria", "Not provided")[:800],
        "location": location_str,
    }


def ask_groq(trials_data: list, news_data: str, condition: str, zipcode: str) -> str:
    """Send trial data to Groq and return plain-English summary."""
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)

        summaries = [summarize_trial_for_prompt(s) for s in trials_data[:6]]
        trials_json = json.dumps(summaries, indent=2)

        user_message = (
            f"Here are raw clinical trial results for condition '{condition}' "
            f"near zip code '{zipcode}':\n\n"
            f"{trials_json}\n\n"
        )
        if news_data:
            user_message += f"Recent news about these trials:\n{news_data}\n\n"

        user_message += (
            "Please explain up to 3 of these trials in simple, warm language for a patient. "
            "For each trial include:\n"
            "1. A plain-English name for the trial\n"
            "2. What they are testing\n"
            "3. Who they are looking for (simplified eligibility)\n"
            "4. The location listed\n"
            "5. The NCT number and a direct link: https://clinicaltrials.gov/study/<NCTID>\n"
            "6. The recruitment status\n"
            "Format each trial clearly with numbered sections."
        )

        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.4,
            max_tokens=1200,
        )
        return chat.choices[0].message.content

    except Exception as e:
        return f"[Groq error: {e}]\n\nPlease verify directly with the trial coordinator before making any decisions. This is not medical advice."


def simulate_response(condition: str, zipcode: str) -> str:
    """Return formatted fake trial data for demo/simulation mode."""
    lines = [
        f"\n[SIMULATION MODE] Showing example trials for: {condition} near {zipcode}\n",
        "=" * 60,
    ]
    for i, trial in enumerate(SIMULATION_TRIALS, 1):
        lines.append(f"\nTrial {i}: {trial['name']}")
        lines.append(f"  What they're testing: {trial['what_tested']}")
        lines.append(f"  Who they're looking for: {trial['eligibility']}")
        lines.append(f"  Nearest location: {trial['location']}")
        lines.append(f"  NCT Number: {trial['nct_id']}")
        lines.append(f"  Link: {trial['link']}")
        lines.append(f"  Status: {trial['status']}")
        lines.append("")

    lines.append("=" * 60)
    lines.append(
        "\nPlease verify directly with the trial coordinator before making any decisions. "
        "This is not medical advice."
    )
    return "\n".join(lines)


def print_banner():
    print("\n" + "=" * 60)
    print("  🔬 Trial Buddy — Clinical Trial Finder")
    print("=" * 60)
    print(DISCLAIMER)

    mode_parts = []
    if GROQ_API_KEY:
        mode_parts.append("Groq AI ✓")
    else:
        mode_parts.append("Groq AI ✗ (simulation)")
    if TAVILY_API_KEY:
        mode_parts.append("Tavily News ✓")
    else:
        mode_parts.append("Tavily News ✗ (skipped)")

    print(f"  Mode: {' | '.join(mode_parts)}\n")


def run_search():
    """Run a single search session and return the result string."""
    condition = input("What condition are you searching for? ").strip()
    if not condition:
        print("  Please enter a condition to search.")
        return

    zipcode = input("What is your zip code? ").strip()
    if not zipcode:
        print("  Please enter a zip code.")
        return

    print(f"\n  Searching for '{condition}' trials near {zipcode}...\n")

    simulation_mode = not GROQ_API_KEY

    if simulation_mode:
        result = simulate_response(condition, zipcode)
    else:
        print("  Fetching trials from ClinicalTrials.gov...")
        trials = fetch_trials(condition)

        news = ""
        if TAVILY_API_KEY:
            print("  Fetching recent news via Tavily...")
            news = fetch_news(condition)

        if not trials:
            print("  No trials found on ClinicalTrials.gov. Using simulation data instead.\n")
            result = simulate_response(condition, zipcode)
        else:
            print(f"  Found {len(trials)} trial(s). Asking Groq to explain them...\n")
            result = ask_groq(trials, news, condition, zipcode)

    print(result)
    print(DISCLAIMER)


def main():
    print_banner()

    while True:
        try:
            run_search()
        except KeyboardInterrupt:
            print("\n\n  Goodbye! Stay well. 💙\n")
            sys.exit(0)

        print()
        again = input("Search for another condition? (y/n): ").strip().lower()
        if again != "y":
            print("\n  Goodbye! Stay well. 💙\n")
            break


if __name__ == "__main__":
    main()
