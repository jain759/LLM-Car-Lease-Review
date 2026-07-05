import io
import json
import re
import time

import requests
import streamlit as st
import plotly.graph_objects as go
from PyPDF2 import PdfReader
from google import genai
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

st.set_page_config(page_title="Lease Assistant", page_icon="⚡", layout="wide")

# ---------- Neon dashboard styling ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&display=swap');

:root {
    --accent-purple: #8B5CF6;
    --accent-blue: #3B82F6;
    --accent-emerald: #34D399;
    --accent-amber: #FBBF24;
    --accent-red: #F87171;
    --accent-pink: #F472B6;
    --bg-black: #0A0A10;
    --glass: rgba(255,255,255,0.04);
    --glass-border: rgba(255,255,255,0.09);
}

.stApp {
    background: var(--bg-black);
    color: #E5E5EA;
    position: relative;
    overflow-x: hidden;
}
.stApp::before {
    content: ''; position: fixed; top: -220px; left: -180px; width: 620px; height: 620px;
    background: radial-gradient(circle, rgba(139,92,246,0.30), transparent 70%);
    filter: blur(90px); z-index: 0; pointer-events: none;
}
.stApp::after {
    content: ''; position: fixed; bottom: -260px; right: -180px; width: 700px; height: 700px;
    background: radial-gradient(circle, rgba(59,130,246,0.25), transparent 70%);
    filter: blur(100px); z-index: 0; pointer-events: none;
}
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1500px; position: relative; z-index: 1; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #E5E5EA; }
h1, h2, h3, h4 { font-family: 'Inter', sans-serif; font-weight: 700; letter-spacing: -0.02em; color: #F5F5F7; }
p, span, label, .stMarkdown { color: #A8A8B3; }

/* Hero */
.hero-badge {
    font-family: 'Inter', sans-serif; font-size: 12.5px; font-weight: 600; letter-spacing: 0.01em;
    color: #C4B5FD; background: rgba(139,92,246,0.12); border: 1px solid rgba(139,92,246,0.3);
    border-radius: 20px; padding: 6px 16px; display: inline-block; margin-bottom: 16px;
}
.hero-title {
    font-family: 'Inter', sans-serif; font-weight: 800; font-size: 44px; line-height: 1.1;
    letter-spacing: -0.03em; color: #F5F5F7; margin: 0;
}
.hero-title .accent {
    background: linear-gradient(90deg, #A78BFA, #60A5FA);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero-sub { font-size: 15px; color: #9A9AA6; max-width: 520px; margin-top: 14px; line-height: 1.6; }

.upload-heading {
    font-family: 'Inter', sans-serif; font-weight: 600; font-size: 14px;
    letter-spacing: 0.01em; color: #C4B5FD; margin-bottom: 10px;
}

/* Tabs — clean minimal underline */
button[data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
    color: #8C8C99 !important;
    padding: 10px 4px !important;
}
button[data-baseweb="tab"][aria-selected="true"] { color: #F5F5F7 !important; }
div[data-baseweb="tab-highlight"] { background: linear-gradient(90deg, #A78BFA, #60A5FA) !important; box-shadow: none; }
div[data-baseweb="tab-border"] { background-color: rgba(255,255,255,0.08) !important; }

/* Glass panels (real Streamlit containers) */
div[class*="st-key-panel-"] {
    border-radius: 20px !important;
    padding: 10px 8px !important;
    background: var(--glass) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    border: 1px solid var(--glass-border) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.28) !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
div[class*="st-key-panel-"]:hover {
    transform: translateY(-3px);
    border-color: rgba(255,255,255,0.18) !important;
    box-shadow: 0 14px 40px rgba(0,0,0,0.4) !important;
}

.panel-heading {
    font-family: 'Inter', sans-serif; font-weight: 700; font-size: 20px;
    letter-spacing: -0.01em; margin: 10px 0 16px 4px;
}
.panel-sub { font-family: 'Inter', sans-serif; font-size: 12.5px; color: #7A7A87;
    margin: -10px 0 16px 4px; }

/* Term cards — glass */
.term-card {
    background: rgba(255,255,255,0.035); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.09); border-radius: 14px;
    padding: 16px 18px; margin-bottom: 14px;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.term-card:hover { transform: translateY(-3px); border-color: rgba(255,255,255,0.2); box-shadow: 0 10px 28px rgba(0,0,0,0.3); }
.term-card.good { border-color: rgba(52,211,153,0.4); }
.term-card.good:hover { border-color: var(--accent-emerald); box-shadow: 0 10px 28px rgba(52,211,153,0.18); }
.term-card.bad { border-color: rgba(248,113,113,0.4); }
.term-card.bad:hover { border-color: var(--accent-red); box-shadow: 0 10px 28px rgba(248,113,113,0.18); }
.term-card .tc-label {
    font-family: 'Inter', sans-serif; font-size: 11px; letter-spacing: 0.03em;
    text-transform: uppercase; color: #8C8C99; margin-bottom: 8px; font-weight: 500;
}
.term-card .tc-value { font-family: 'IBM Plex Mono', monospace; font-size: 23px; font-weight: 600; color: #F5F5F7; }
.term-card .tc-value.empty { color: #55555F; font-size: 14px; font-weight: 400; }

/* Negotiation cards */
.neg-card {
    background: rgba(251,191,36,0.06); backdrop-filter: blur(14px);
    border: 1px solid rgba(251,191,36,0.25); border-radius: 14px;
    padding: 16px 20px; margin-bottom: 14px; font-size: 15px; line-height: 1.6; color: #EDE6D3;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.neg-card:hover { transform: translateY(-2px); border-color: var(--accent-amber); box-shadow: 0 10px 26px rgba(251,191,36,0.15); }

/* Vehicle card */
.vehicle-card {
    background: rgba(139,92,246,0.07); backdrop-filter: blur(20px);
    border: 1px solid rgba(139,92,246,0.3); border-radius: 18px; padding: 24px 26px; margin-bottom: 18px;
    box-shadow: 0 8px 28px rgba(139,92,246,0.1); transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.vehicle-card:hover { transform: translateY(-2px); box-shadow: 0 14px 36px rgba(139,92,246,0.22); }
.vehicle-card .vc-name { font-family: 'Inter', sans-serif; font-weight: 700; font-size: 28px; letter-spacing: -0.01em; color: #F5F5F7; }
.vehicle-card .vc-vin { font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; color: #C4B5FD; margin-top: 6px; }

/* Price estimate card */
.price-card {
    background: rgba(52,211,153,0.06); backdrop-filter: blur(20px);
    border: 1px solid rgba(52,211,153,0.3); border-radius: 18px; padding: 22px 26px; margin-bottom: 14px;
    box-shadow: 0 8px 28px rgba(52,211,153,0.08);
}
.price-card .pc-range { font-family: 'IBM Plex Mono', monospace; font-size: 27px; font-weight: 600; color: var(--accent-emerald); }
.price-card .pc-note { font-size: 13.5px; color: #9A9AA6; margin-top: 8px; line-height: 1.5; }

/* Upload dropzone — glass */
div[data-testid="stFileUploaderDropzone"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 16px !important;
    border: 1.5px dashed rgba(139,92,246,0.45) !important;
    padding: 26px 18px !important;
    backdrop-filter: blur(14px) !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
div[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #A78BFA !important;
    box-shadow: 0 8px 30px rgba(139,92,246,0.18) !important;
}
div[data-testid="stFileUploaderDropzoneInstructions"] span { font-size: 15.5px !important; color: #E5E5EA !important; }
div[data-testid="stFileUploaderDropzoneInstructions"] small { font-size: 12.5px !important; color: #8C8C99 !important; }
div[data-testid="stFileUploaderDropzone"] svg { width: 30px !important; height: 30px !important; color: #A78BFA !important; fill: #A78BFA !important; }
div[data-testid="stFileUploaderDropzone"] button {
    border: 1px solid rgba(139,92,246,0.4) !important; background: rgba(139,92,246,0.08) !important;
    color: #E5E5EA !important; font-weight: 500 !important; border-radius: 10px !important;
}

/* Buttons */
div[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(90deg, #8B5CF6, #3B82F6);
    color: #FFFFFF !important; border: none; border-radius: 12px;
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important; font-size: 16px !important;
    letter-spacing: 0; padding: 14px 20px !important; height: auto !important;
    box-shadow: 0 8px 24px rgba(139,92,246,0.35);
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}
div[data-testid="stButton"] button[kind="primary"] p { color: #FFFFFF !important; font-size: 16px !important; font-weight: 600 !important; }
div[data-testid="stButton"] button[kind="primary"]:hover { box-shadow: 0 12px 32px rgba(139,92,246,0.5); transform: translateY(-2px); }

div[data-testid="stDownloadButton"] button {
    background: rgba(255,255,255,0.04); backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.14); color: #E5E5EA; font-weight: 500; border-radius: 10px;
    transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}
div[data-testid="stDownloadButton"] button:hover {
    border-color: rgba(139,92,246,0.5); box-shadow: 0 8px 24px rgba(139,92,246,0.2); transform: translateY(-2px);
}

section[data-testid="stSidebar"] { background-color: rgba(255,255,255,0.02); border-right: 1px solid rgba(255,255,255,0.08); backdrop-filter: blur(20px); }
details { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 8px 14px; margin-bottom: 10px; }
summary { color: #E5E5EA !important; }

/* Chat bubbles */
div[data-testid="stChatMessage"] { background: rgba(255,255,255,0.035); backdrop-filter: blur(14px); border: 1px solid rgba(255,255,255,0.09); border-radius: 14px; }
</style>
""", unsafe_allow_html=True)

# ---------- API key handling ----------
def get_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return st.session_state.get("manual_api_key", "")

with st.sidebar:
    st.header("Setup")
    if "GEMINI_API_KEY" not in st.secrets:
        st.session_state["manual_api_key"] = st.text_input(
            "Gemini API key", type="password",
            help="Get a free key at aistudio.google.com/apikey"
        )
        st.caption("For local testing only. Once deployed, add this as a Streamlit secret instead.")
    else:
        st.success("API key loaded from secrets ✅")
    st.markdown("---")
    st.caption("Model: gemini-2.5-flash (free tier)")

API_KEY = get_api_key()

# ---------- Field schema ----------
FIELDS = [
    "apr_percent", "term_months", "monthly_payment", "down_payment",
    "residual_value", "mileage_allowance", "mileage_overage_fee",
    "early_termination_fee", "purchase_option_price",
    "insurance_requirements", "maintenance_responsibilities",
    "warranty_summary", "late_fee_policy",
]

NUMERIC_FIELDS = [
    "apr_percent", "term_months", "monthly_payment", "down_payment",
    "residual_value", "mileage_allowance", "mileage_overage_fee",
    "early_termination_fee", "purchase_option_price",
]

EXPLANATIONS = {
    "apr_percent": "APR (Annual Percentage Rate) is the yearly interest charged on the loan or lease.",
    "term_months": "Term is the length of the loan or lease, in months.",
    "monthly_payment": "Monthly Payment is the fixed amount you pay each month.",
    "down_payment": "Down Payment is the upfront amount you pay at signing.",
    "residual_value": "Residual Value is the car's estimated worth at the end of the lease.",
    "mileage_allowance": "Mileage Allowance is how many miles per year you're allotted before overage fees kick in.",
    "mileage_overage_fee": "Mileage Overage Fee is what you pay per mile over your allowance.",
    "early_termination_fee": "Early Termination Fee is the penalty for ending the lease before the term is up.",
    "purchase_option_price": "Purchase Option Price is what you'd pay to buy the car at lease end.",
    "insurance_requirements": "Insurance Requirements specify what coverage you must maintain.",
    "maintenance_responsibilities": "Maintenance Responsibilities explain who handles servicing and repairs.",
    "warranty_summary": "Warranty Summary describes what parts or services are covered by warranty.",
    "late_fee_policy": "Late Fee Policy is the penalty if you miss or delay a payment.",
}

TERM_ICONS = {
    "apr_percent": "📈", "term_months": "📅", "monthly_payment": "💳",
    "down_payment": "💰", "residual_value": "🏷️", "mileage_allowance": "🛣️",
    "mileage_overage_fee": "⚠️", "early_termination_fee": "🚪", "purchase_option_price": "🔑",
}

TERM_UNITS = {
    "apr_percent": "%", "term_months": " mo", "monthly_payment": "$",
    "down_payment": "$", "residual_value": "$", "mileage_allowance": " mi/yr",
    "mileage_overage_fee": "$/mi", "early_termination_fee": "$", "purchase_option_price": "$",
}

# Contracts can safely be much longer than 15k chars — gemini-2.5-flash has a huge
# context window. This just guards against truly extreme edge cases.
MAX_CONTRACT_CHARS = 100000

PROMPT_TEMPLATE = """You are reading a car lease or auto loan contract. Extract the following
fields from the contract text below. If a field is not present, use null.
Also find a 17-character VIN if one appears, and write 2-4 short, concrete
negotiation suggestions comparing the terms to typical market ranges
(APR 3-7%, term 12-60 months, mileage allowance 12,000-15,000 mi/yr).

Also write a "specific_explanations" object: for each numeric field that was found,
write ONE short sentence explaining what that specific number means for THIS
contract in plain English (e.g. "Your $3,200 termination fee equals about 8 months
of payments if you end the lease early."). Skip fields that are null.

Respond with ONLY valid JSON, no markdown fences, no commentary, in this exact shape:
{{
  "fields": {{
    "apr_percent": number or null,
    "term_months": number or null,
    "monthly_payment": number or null,
    "down_payment": number or null,
    "residual_value": number or null,
    "mileage_allowance": number or null,
    "mileage_overage_fee": number or null,
    "early_termination_fee": number or null,
    "purchase_option_price": number or null,
    "insurance_requirements": string or null,
    "maintenance_responsibilities": string or null,
    "warranty_summary": string or null,
    "late_fee_policy": string or null
  }},
  "vin": string or null,
  "negotiation_points": [string, ...],
  "specific_explanations": {{ "field_name": "sentence", ... }}
}}

CONTRACT TEXT:
\"\"\"{text}\"\"\"
"""

PRICE_PROMPT_TEMPLATE = """You are a car pricing expert. Based on your general knowledge of the
used/new car market (not live data), estimate a fair price range in USD for this vehicle:

Year: {year}
Make: {make}
Model: {model}

Respond with ONLY valid JSON, no markdown fences, no commentary:
{{
  "price_low": number,
  "price_high": number,
  "summary": "one short sentence explaining the estimate and what could shift it (mileage, trim, condition)"
}}
"""

CHAT_SYSTEM_PREAMBLE = """You are a helpful, concise assistant helping someone understand their car
lease/loan contract. Answer only using the contract details below plus general consumer-finance
knowledge. If something isn't in the contract, say so clearly instead of guessing specifics.
Keep answers short (2-5 sentences) unless asked for more detail.

EXTRACTED CONTRACT FIELDS:
{fields_json}

VEHICLE:
{vehicle_json}

RAW CONTRACT TEXT (may be partial):
\"\"\"{raw_text}\"\"\"
"""


def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def call_gemini(api_key, prompt, max_retries=3):
    """Generic Gemini call with retry on transient server errors (e.g. 503)."""
    client = genai.Client(api_key=api_key)
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            return response.text.strip()
        except Exception as e:
            last_error = e
            is_transient = "503" in str(e) or "UNAVAILABLE" in str(e) or "overloaded" in str(e).lower()
            if is_transient and attempt < max_retries:
                st.toast(f"Model is busy, retrying... ({attempt}/{max_retries})")
                time.sleep(2 * attempt)
                continue
            raise last_error
    raise last_error


def parse_json_response(raw):
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)


def analyze_with_gemini(api_key, text):
    truncated = text[:MAX_CONTRACT_CHARS]
    prompt = PROMPT_TEMPLATE.format(text=truncated)
    raw = call_gemini(api_key, prompt)
    return parse_json_response(raw), len(text) > MAX_CONTRACT_CHARS


def estimate_price_range(api_key, vehicle):
    prompt = PRICE_PROMPT_TEMPLATE.format(
        year=vehicle.get("year", "unknown"),
        make=vehicle.get("make", "unknown"),
        model=vehicle.get("model", "unknown"),
    )
    raw = call_gemini(api_key, prompt)
    return parse_json_response(raw)


def chat_reply(api_key, fields, vehicle, raw_text, history, user_message):
    preamble = CHAT_SYSTEM_PREAMBLE.format(
        fields_json=json.dumps(fields, indent=2),
        vehicle_json=json.dumps(vehicle or {}, indent=2),
        raw_text=raw_text[:MAX_CONTRACT_CHARS],
    )
    convo = ""
    for turn in history:
        role = "User" if turn["role"] == "user" else "Assistant"
        convo += f"\n{role}: {turn['content']}"
    convo += f"\nUser: {user_message}\nAssistant:"
    full_prompt = preamble + "\n\nCONVERSATION SO FAR:" + convo
    return call_gemini(api_key, full_prompt)


def decode_vin(vin):
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("Results", [])
    lookup = {item["Variable"]: item["Value"] for item in results}
    return {"make": lookup.get("Make"), "model": lookup.get("Model"), "year": lookup.get("Model Year")}


def get_recalls(make, model, year):
    if not (make and model and year):
        return []
    url = "https://api.nhtsa.gov/recalls/recallsByVehicle"
    params = {"make": make, "model": model, "modelYear": year}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception:
        return []


def compute_fairness_score(fields):
    checks = []
    score = 100
    apr = fields.get("apr_percent")
    if apr is not None:
        if apr <= 7:
            checks.append(("APR", 0, f"{apr}% is within the typical 3-7% range."))
        elif apr <= 10:
            checks.append(("APR", 10, f"{apr}% is somewhat above typical (3-7%)."))
            score -= 10
        else:
            checks.append(("APR", 20, f"{apr}% is well above typical (3-7%)."))
            score -= 20
    term = fields.get("term_months")
    if term is not None:
        if 12 <= term <= 60:
            checks.append(("Term", 0, f"{term} months is a standard length."))
        else:
            checks.append(("Term", 8, f"{term} months is outside the common 12-60 month range."))
            score -= 8
    mileage = fields.get("mileage_allowance")
    if mileage is not None:
        if mileage >= 12000:
            checks.append(("Mileage Allowance", 0, f"{mileage:,} mi/yr meets or exceeds the typical minimum."))
        else:
            checks.append(("Mileage Allowance", 12, f"{mileage:,} mi/yr is below the typical 12,000-15,000 mi/yr."))
            score -= 12
    overage = fields.get("mileage_overage_fee")
    if overage is not None:
        if overage <= 0.25:
            checks.append(("Mileage Overage Fee", 0, f"${overage}/mile is within typical range."))
        else:
            checks.append(("Mileage Overage Fee", 8, f"${overage}/mile is higher than typical (~$0.15-0.25)."))
            score -= 8
    term_fee = fields.get("early_termination_fee")
    monthly = fields.get("monthly_payment")
    if term_fee is not None and monthly:
        if term_fee <= monthly * 6:
            checks.append(("Early Termination Fee", 0, "Roughly in line with typical lease penalties."))
        else:
            checks.append(("Early Termination Fee", 12, "Notably higher than typical (>6 months of payments)."))
            score -= 12
    score = max(0, min(100, score))
    return score, checks


def fairness_label(score):
    if score >= 85:
        return "Good Deal", "🟢"
    elif score >= 65:
        return "Fair, Some Concerns", "🟡"
    else:
        return "Needs Negotiation", "🔴"


def term_flag(field, val, fields):
    if val is None:
        return None
    if field == "apr_percent":
        return "good" if val <= 7 else "bad"
    if field == "term_months":
        return "good" if 12 <= val <= 60 else "bad"
    if field == "mileage_allowance":
        return "good" if val >= 12000 else "bad"
    if field == "mileage_overage_fee":
        return "good" if val <= 0.25 else "bad"
    if field == "early_termination_fee":
        monthly = fields.get("monthly_payment")
        if monthly:
            return "good" if val <= monthly * 6 else "bad"
    return None


def render_term_card(field, val, fields):
    flag = term_flag(field, val, fields)
    icon = TERM_ICONS.get(field, "•")
    label = field.replace("_", " ").title()
    unit = TERM_UNITS.get(field, "")
    if val is None:
        value_html = '<div class="tc-value empty">not found</div>'
    else:
        prefix = "$" if unit == "$" else ""
        suffix = "" if unit == "$" else unit
        value_html = (f'<div class="tc-value">{prefix}{val:,.2f}{suffix}</div>'
                      if isinstance(val, float) else f'<div class="tc-value">{prefix}{val:,}{suffix}</div>')
    css_class = f"term-card {flag}" if flag else "term-card"
    st.markdown(f"""
    <div class="{css_class}">
        <div class="tc-label">{icon} {label}</div>
        {value_html}
    </div>
    """, unsafe_allow_html=True)


def render_fairness_gauge(score, height=280):
    color = "#34D399" if score >= 85 else ("#FBBF24" if score >= 65 else "#F87171")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'suffix': "/100", 'font': {'size': 36, 'family': 'IBM Plex Mono', 'color': '#F5F5F7'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': '#4A4A55', 'tickfont': {'color': '#8C8C99'}},
            'bar': {'color': color, 'thickness': 0.28},
            'bgcolor': "rgba(255,255,255,0.03)",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 65], 'color': 'rgba(248,113,113,0.12)'},
                {'range': [65, 85], 'color': 'rgba(251,191,36,0.10)'},
                {'range': [85, 100], 'color': 'rgba(52,211,153,0.12)'},
            ],
        }
    ))
    fig.update_layout(
        height=height, margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font={'color': '#E5E5EA'}
    )
    st.plotly_chart(fig, use_container_width=True)


def build_pdf_report(fields, vin, vehicle, negotiation_points, score, checks, recalls):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.6*inch, bottomMargin=0.6*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleX', parent=styles['Title'], fontSize=16)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=12, spaceBefore=12, spaceAfter=6)
    body = styles['Normal']
    story = []
    story.append(Paragraph("Car Lease Contract Summary", title_style))
    story.append(Spacer(1, 6))
    label, _ = fairness_label(score)
    story.append(Paragraph(f"<b>Fairness Score: {score}/100 — {label}</b>", body))
    story.append(Spacer(1, 10))
    if vehicle and (vehicle.get("make") or vehicle.get("model")):
        story.append(Paragraph("Vehicle", h2))
        story.append(Paragraph(
            f"{vehicle.get('year','')} {vehicle.get('make','')} {vehicle.get('model','')}  (VIN: {vin or 'n/a'})", body))
    story.append(Paragraph("Financial Terms", h2))
    rows = [["Field", "Value"]]
    for f in NUMERIC_FIELDS:
        val = fields.get(f)
        rows.append([f.replace("_", " ").title(), str(val) if val is not None else "not found"])
    t = Table(rows, colWidths=[3*inch, 2.7*inch])
    t.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    story.append(t)
    story.append(Paragraph("Fairness Breakdown", h2))
    for label_, pts, reason in checks:
        story.append(Paragraph(f"• <b>{label_}</b>: {reason}", body))
    story.append(Paragraph("Negotiation Suggestions", h2))
    for p in negotiation_points:
        story.append(Paragraph(f"• {p}", body))
    if recalls:
        story.append(Paragraph("Open Recalls", h2))
        for r in recalls[:5]:
            story.append(Paragraph(f"• {r.get('Component','')}: {r.get('Summary','')[:200]}", body))
    doc.build(story)
    buf.seek(0)
    return buf


def process_contract(api_key, uploaded_file):
    """Runs the full pipeline for one uploaded contract, returns a result dict."""
    text = extract_pdf_text(uploaded_file)
    if not text.strip():
        return None, "Couldn't find any text in that PDF — it may be a scanned image without OCR text."
    result, was_truncated = analyze_with_gemini(api_key, text)
    return {
        "fields": result.get("fields", {}),
        "vin": result.get("vin"),
        "negotiation_points": result.get("negotiation_points", []),
        "specific_explanations": result.get("specific_explanations", {}),
        "raw_text": text,
        "was_truncated": was_truncated,
        "filename": uploaded_file.name,
    }, None


# ---------- UI ----------
hero_left, hero_right = st.columns([2, 1])
with hero_left:
    st.markdown("""
    <div class="hero-badge">LLM-POWERED CONTRACT REVIEW</div>
    <div class="hero-title">Know the deal<br><span class="accent">before you sign.</span></div>
    <div class="hero-sub">Upload a lease or loan contract PDF. An LLM reads it, scores its fairness,
    decodes the vehicle, checks for open recalls, estimates a fair price, and tells you exactly
    what to negotiate — plus you can chat with it about your specific contract.</div>
    """, unsafe_allow_html=True)
with hero_right:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="upload-heading">📄 Upload Your Contract</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload contract PDF", type=["pdf"], label_visibility="collapsed", key="uploader_main"
    )
    if uploaded_file and not API_KEY:
        st.warning("Add your Gemini API key in the sidebar first.")

analyze_clicked = False
if uploaded_file and API_KEY:
    st.markdown("<br>", unsafe_allow_html=True)
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        analyze_clicked = st.button("⚡ ANALYZE WITH AI", type="primary", use_container_width=True)

if uploaded_file and API_KEY and analyze_clicked:
    with st.spinner("Reading PDF and asking Gemini to analyze it..."):
        result, error = process_contract(API_KEY, uploaded_file)
    if error:
        st.error(error)
    else:
        st.session_state["fields"] = result["fields"]
        st.session_state["vin"] = result["vin"]
        st.session_state["negotiation_points"] = result["negotiation_points"]
        st.session_state["specific_explanations"] = result["specific_explanations"]
        st.session_state["raw_text"] = result["raw_text"]
        st.session_state["was_truncated"] = result["was_truncated"]
        st.session_state["chat_history"] = []
        st.session_state.pop("compare_result_b", None)

if "fields" in st.session_state:
    fields = st.session_state["fields"]
    vin = st.session_state["vin"]
    negotiation_points = st.session_state["negotiation_points"]
    specific_explanations = st.session_state.get("specific_explanations", {})
    score, checks = compute_fairness_score(fields)
    label, emoji = fairness_label(score)

    if st.session_state.get("was_truncated"):
        st.info(f"This contract was long, so only the first {MAX_CONTRACT_CHARS:,} characters were analyzed. "
                "Key terms are usually near the top, but double check the full document for anything missed.")

    st.markdown("<br>", unsafe_allow_html=True)

    tab_overview, tab_terms, tab_vehicle, tab_neg, tab_chat, tab_compare, tab_explain = st.tabs([
        "📊 OVERVIEW", "💵 FINANCIAL TERMS", "🚙 VEHICLE & RECALLS",
        "🤝 NEGOTIATION", "💬 ASK AI", "📑 COMPARE", "📖 EXPLAINED"
    ])

    with tab_overview:
        with st.container(border=True, key="panel-fairness"):
            st.markdown('<div class="panel-heading">Contract Fairness Score</div>', unsafe_allow_html=True)
            gcol1, gcol2 = st.columns([1, 1.3])
            with gcol1:
                render_fairness_gauge(score)
            with gcol2:
                st.markdown(f"### {emoji} {label}")
                st.markdown("<br>", unsafe_allow_html=True)
                for check_label, pts, reason in checks:
                    st.markdown(f"**{check_label}** — {reason}")

    with tab_terms:
        with st.container(border=True, key="panel-terms"):
            st.markdown('<div class="panel-heading">Financial Terms</div>', unsafe_allow_html=True)
            st.markdown('<div class="panel-sub">Green = within typical market range · Red = worth negotiating</div>', unsafe_allow_html=True)
            tcols = st.columns(3)
            for i, field in enumerate(NUMERIC_FIELDS):
                with tcols[i % 3]:
                    render_term_card(field, fields.get(field), fields)

    with tab_vehicle:
        with st.container(border=True, key="panel-vehicle"):
            st.markdown('<div class="panel-heading">Vehicle & Recalls</div>', unsafe_allow_html=True)
            manual_vin = st.text_input("VIN", value=vin or "", max_chars=17,
                                        placeholder="Enter 17-character VIN", label_visibility="collapsed")
            vehicle = None
            recalls = []
            if manual_vin and len(manual_vin) == 17:
                try:
                    vehicle = decode_vin(manual_vin)
                    st.markdown(f"""
                    <div class="vehicle-card">
                        <div class="vc-name">{vehicle.get('year','')} {vehicle.get('make','')} {vehicle.get('model','')}</div>
                        <div class="vc-vin">VIN {manual_vin}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("##### 💲 AI Estimated Fair Price Range")
                    price_key = f"price_{manual_vin}"
                    if price_key not in st.session_state:
                        with st.spinner("Estimating fair price range..."):
                            try:
                                st.session_state[price_key] = estimate_price_range(API_KEY, vehicle)
                            except Exception:
                                st.session_state[price_key] = None
                    price_info = st.session_state.get(price_key)
                    if price_info:
                        st.markdown(f"""
                        <div class="price-card">
                            <div class="pc-range">${price_info.get('price_low', 0):,.0f} – ${price_info.get('price_high', 0):,.0f}</div>
                            <div class="pc-note">{price_info.get('summary', '')}</div>
                            <div class="pc-note">⚠️ AI estimate based on general knowledge — not live market data.</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.caption("Couldn't generate a price estimate right now.")

                    with st.spinner("Checking for open recalls..."):
                        recalls = get_recalls(vehicle.get("make"), vehicle.get("model"), vehicle.get("year"))
                    if recalls:
                        st.warning(f"⚠️ {len(recalls)} open recall(s) found for this vehicle.")
                        for r in recalls[:5]:
                            with st.expander(r.get("Component", "Recall")):
                                st.write(r.get("Summary", "No details available."))
                                st.caption(f"Reported: {r.get('ReportReceivedDate', 'n/a')}")
                    else:
                        st.success("No open recalls found for this make/model/year.")
                except Exception:
                    st.caption("Couldn't decode that VIN.")
            else:
                st.caption("Enter a 17-character VIN to decode the vehicle, get a price estimate, and check recalls.")

    with tab_neg:
        with st.container(border=True, key="panel-negotiation"):
            st.markdown('<div class="panel-heading">Negotiation Suggestions</div>', unsafe_allow_html=True)
            if negotiation_points:
                for point in negotiation_points:
                    st.markdown(f'<div class="neg-card">💬 {point}</div>', unsafe_allow_html=True)
            else:
                st.caption("No suggestions generated.")

    with tab_chat:
        with st.container(border=True, key="panel-negotiation"):
            st.markdown('<div class="panel-heading">Ask AI About Your Contract</div>', unsafe_allow_html=True)
            st.caption("Ask anything specific — \"what happens if I go over mileage?\", \"is this APR normal?\", etc.")

            if "chat_history" not in st.session_state:
                st.session_state["chat_history"] = []

            for turn in st.session_state["chat_history"]:
                with st.chat_message(turn["role"]):
                    st.write(turn["content"])

            user_q = st.chat_input("Ask a question about this contract...")
            if user_q:
                st.session_state["chat_history"].append({"role": "user", "content": user_q})
                with st.spinner("Thinking..."):
                    try:
                        answer = chat_reply(
                            API_KEY, fields,
                            st.session_state.get("last_vehicle"),
                            st.session_state["raw_text"],
                            st.session_state["chat_history"][:-1],
                            user_q,
                        )
                    except Exception as e:
                        answer = f"Sorry, couldn't get a response right now. ({e})"
                st.session_state["chat_history"].append({"role": "assistant", "content": answer})
                st.rerun()

    with tab_compare:
        with st.container(border=True, key="panel-terms"):
            st.markdown('<div class="panel-heading">Compare Two Contracts</div>', unsafe_allow_html=True)
            st.caption("Upload a second contract to compare it side-by-side with the one above.")
            second_file = st.file_uploader("Upload second contract PDF", type=["pdf"], key="uploader_compare")
            if second_file and st.button("Analyze Second Contract", key="analyze_b"):
                with st.spinner("Reading and analyzing second contract..."):
                    result_b, error_b = process_contract(API_KEY, second_file)
                if error_b:
                    st.error(error_b)
                else:
                    st.session_state["compare_result_b"] = result_b

            if "compare_result_b" in st.session_state:
                fields_b = st.session_state["compare_result_b"]["fields"]
                score_b, _ = compute_fairness_score(fields_b)
                label_b, emoji_b = fairness_label(score_b)

                ccol1, ccol2 = st.columns(2)
                with ccol1:
                    st.markdown(f"**Contract A** — {emoji} {label} ({score}/100)")
                with ccol2:
                    st.markdown(f"**Contract B: {st.session_state['compare_result_b']['filename']}** — {emoji_b} {label_b} ({score_b}/100)")

                rows = []
                for f in NUMERIC_FIELDS:
                    val_a = fields.get(f)
                    val_b = fields_b.get(f)
                    rows.append({
                        "Field": f.replace("_", " ").title(),
                        "Contract A": val_a if val_a is not None else "—",
                        "Contract B": val_b if val_b is not None else "—",
                    })
                st.table(rows)

    with tab_explain:
        with st.container(border=True, key="panel-explain"):
            st.markdown('<div class="panel-heading">What Each Term Means</div>', unsafe_allow_html=True)
            for field in FIELDS:
                with st.expander(f"{TERM_ICONS.get(field, '•')} {field.replace('_', ' ').title()}"):
                    st.write(EXPLANATIONS.get(field, "No explanation available."))
                    specific = specific_explanations.get(field)
                    if specific:
                        st.markdown(f"**For your contract:** {specific}")
                    val = fields.get(field)
                    if val is not None:
                        st.caption(f"Found in contract: {val}")

    st.markdown("<br>", unsafe_allow_html=True)
    payload = {
        "vin": (manual_vin if manual_vin else vin) or vin,
        "sla_fields": fields,
        "negotiation_suggestions": negotiation_points,
        "fairness_score": score,
    }
    dl1, dl2, dl3 = st.columns([1, 1, 2])
    with dl1:
        st.download_button("⬇️ JSON", data=json.dumps(payload, indent=2),
                            file_name="lease_contract_summary.json", mime="application/json",
                            use_container_width=True)
    with dl2:
        pdf_buf = build_pdf_report(fields, payload["vin"], vehicle, negotiation_points, score, checks, recalls)
        st.download_button("⬇️ PDF Report", data=pdf_buf, file_name="lease_contract_report.pdf",
                            mime="application/pdf", use_container_width=True)

    with st.expander("View extracted contract text"):
        st.text(st.session_state["raw_text"][:6000])
