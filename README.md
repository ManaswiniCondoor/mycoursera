# Trial Buddy — Clinical Trial Finder

A stateless Python CLI agent that helps patients find clinical trials in plain English. You enter a condition and zip code; Trial Buddy searches ClinicalTrials.gov, pulls recent news, and explains matching trials in simple, compassionate language powered by Groq AI.

---

## What It Does

1. Asks you for a medical condition and your zip code
2. Searches the [ClinicalTrials.gov](https://clinicaltrials.gov) public API (no key needed)
3. Optionally pulls recent news about trials via Tavily
4. Sends results to Groq (Llama 3.3 70B) to translate medical jargon into plain English
5. Shows you up to 3 matching trials with:
   - Plain-English trial name and description
   - Simplified eligibility criteria
   - Nearest location
   - NCT number + direct link
   - Recruitment status
6. Always includes a clear medical disclaimer
7. Runs in **simulation mode** if no API keys are present — great for demos

---

## How to Get Free API Keys

No credit card is required for either service.

| Service | Sign up at | Free tier |
|---------|-----------|-----------|
| **Groq** | [console.groq.com](https://console.groq.com) | Free, generous rate limits |
| **Tavily** | [app.tavily.com](https://app.tavily.com) | 1,000 free searches/month |

---

## How to Run Locally

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd mycoursera

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up your API keys
cp .env.example .env
# Edit .env and paste your Groq and Tavily keys

# 4. Run Trial Buddy
python trialbuddy.py
```

If you skip step 3, the app runs in **simulation mode** with realistic example data.

---

## How to Deploy to Streamlit (Free)

Trial Buddy is a CLI app, but you can wrap it in Streamlit for a browser UI:

1. Create a free account at [streamlit.io](https://streamlit.io)
2. Create a new file `streamlit_app.py` that calls the Trial Buddy functions
3. Push to GitHub and connect the repo in the Streamlit dashboard
4. Add your API keys in **Streamlit → Settings → Secrets**

---

## Privacy Statement

**Trial Buddy is fully stateless and privacy-first:**

- No database — nothing is stored
- No logging of user input (condition or zip code)
- No analytics or tracking of any kind
- Every session is completely independent
- Nothing is written to disk except the code itself
- Your search data goes directly to the APIs and is never retained by this app

---

## Disclaimer

> ⚠️ Trial Buddy is not a medical service. We do not store your information.
> Always consult your doctor and speak directly with trial coordinators before
> making any health decisions.

Trial Buddy never tells you whether you qualify for a trial. It only summarizes publicly available information from ClinicalTrials.gov. Always verify details directly with the trial coordinator.

---

## Tech Stack

- **Python 3** — no frameworks required
- **Groq API** (`llama-3.3-70b-versatile`) — plain-language AI translation
- **Tavily API** — recent news search
- **ClinicalTrials.gov API v2** — public, no key required
- **python-dotenv** — environment variable management
