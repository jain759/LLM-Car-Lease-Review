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
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

:root {
    --neon-cyan: #00F5D4;
    --neon-pink: #FF2E9A;
    --neon-purple: #B026FF;
    --neon-yellow: #F5FF00;
    --neon-red: #FF3B5C;
    --bg-black: #07070B;
    --bg-panel: #0F0F16;
}

.stApp {
    background-color: var(--bg-black);
    color: #E8E8ED;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; color: #E8E8ED; }
h1, h2, h3, h4 { font-family: 'Rajdhani', sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; color: #FFFFFF; }
p, span, label, .stMarkdown { color: #C7C7D1; }

/* Hero */
.hero-wrap {
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 24px;
    padding: 30px 36px;
    border: 1px solid #23232E;
    border-radius: 14px;
    background: radial-gradient(circle at top left, rgba(0,245,212,0.06), transparent 60%),
                radial-gradient(circle at bottom right, rgba(176,38,255,0.08), transparent 60%),
                var(--bg-panel);
    margin-bottom: 28px;
}
.hero-title {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 46px;
    line-height: 1.05;
    text-transform: uppercase;
    color: #FFFFFF;
    text-shadow: 0 0 18px rgba(0,245,212,0.35);
    margin: 0;
}
.hero-title .accent { color: var(--neon-cyan); }
.hero-sub {
    font-size: 15px;
    color: #9A9AA6;
    max-width: 520px;
    margin-top: 10px;
    line-height: 1.5;
}
.hero-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--neon-cyan);
    border: 1px solid var(--neon-cyan);
    border-radius: 20px;
    padding: 5px 14px;
    display: inline-block;
    margin-bottom: 14px;
    box-shadow: 0 0 12px rgba(0,245,212,0.25);
}

/* Generic glow panel */
.glow-panel {
    background: var(--bg-panel);
    border-radius: 14px;
    padding: 22px 24px;
    border: 1px solid #23232E;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    height: 100%;
}
.glow-panel:hover { transform: translateY(-3px) scale(1.012); }

.glow-cyan { border-color: rgba(0,245,212,0.35); box-shadow: 0 0 16px rgba(0,245,212,0.08); }
.glow-cyan:hover { border-color: var(--neon-cyan); box-shadow: 0 0 26px rgba(0,245,212,0.35); }

.glow-purple { border-color: rgba(176,38,255,0.35); box-shadow: 0 0 16px rgba(176,38,255,0.08); }
.glow-purple:hover { border-color: var(--neon-purple); box-shadow: 0 0 26px rgba(176,38,255,0.35); }

.glow-pink { border-color: rgba(255,46,154,0.35); box-shadow: 0 0 16px rgba(255,46,154,0.08); }
.glow-pink:hover { border-color: var(--neon-pink); box-shadow: 0 0 26px rgba(255,46,154,0.35); }

.panel-heading {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 20px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 14px;
}

/* Term cards */
.term-card {
    background: #0B0B12;
    border: 1px solid #24242E;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 12px;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.term-card:hover { transform: scale(1.035); }
.term-card.good { border-color: rgba(0,245,212,0.4); box-shadow: 0 0 10px rgba(0,245,212,0.12); }
.term-card.good:hover { border-color: var(--neon-cyan); box-shadow: 0 0 20px rgba(0,245,212,0.4); }
.term-card.bad { border-color: rgba(255,59,92,0.45); box-shadow: 0 0 10px rgba(255,59,92,0.14); }
.term-card.bad:hover { border-color: var(--neon-red); box-shadow: 0 0 20px rgba(255,59,92,0.45); }
.term-card .tc-label {
    font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; letter-spacing: 0.08em;
    text-transform: uppercase; color: #8C8C99; margin-bottom: 6px;
}
.term-card .tc-value { font-family: 'IBM Plex Mono', monospace; font-size: 21px; font-weight: 600; color: #FFFFFF; }
.term-card .tc-value.empty { color: #4A4A55; font-size: 14px; font-weight: 400; }

/* Negotiation cards */
.neg-card {
    background: #12100A;
    border: 1px solid rgba(245,255,0,0.3);
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 12px;
    font-size: 14.5px;
    line-height: 1.5;
    color: #EDEDD8;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.neg-card:hover { transform: scale(1.015); border-color: var(--neon-yellow); box-shadow: 0 0 18px rgba(245,255,0,0.25); }

/* Vehicle card */
.vehicle-card {
    background: linear-gradient(135deg, #12081D 0%, #1A0F26 100%);
    border: 1px solid rgba(176,38,255,0.4);
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 6px;
    box-shadow: 0 0 16px rgba(176,38,255,0.12);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.vehicle-card:hover { transform: scale(1.015); box-shadow: 0 0 26px rgba(176,38,255,0.35); }
.vehicle-card .vc-name { font-family: 'Rajdhani', sans-serif; font-weight: 700; font-size: 26px; text-transform: uppercase; color: #FFFFFF; }
.vehicle-card .vc-vin { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #B9A6D6; margin-top: 4px; }

/* Streamlit widget overrides */
div[data-testid="stFileUploaderDropzone"] {
    background: var(--bg-panel);
    border-radius: 10px;
    border: 1.5px dashed rgba(0,245,212,0.4);
}
div[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(90deg, #00F5D4, #00C2FF);
    color: #07070B;
    border: none;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    box-shadow: 0 0 16px rgba(0,245,212,0.35);
    transition: box-shadow 0.15s ease, transform 0.15s ease;
}
div[data-testid="stButton"] button[kind="primary"]:hover {
    box-shadow: 0 0 26px rgba(0,245,212,0.6);
    transform: scale(1.02);
}
div[data-testid="stDownloadButton"] button {
    background: var(--bg-panel);
    border: 1px solid rgba(0,245,212,0.4);
    color: #E8E8ED;
    font-weight: 600;
    transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
div[data-testid="stDownloadButton"] button:hover {
    border-color: var(--neon-cyan);
    box-shadow: 0 0 16px rgba(0,245,212,0.3);
}
section[data-testid="stSidebar"] { background-color: #0B0B12; border-right: 1px solid #23232E; }
details { background: #0B0B12; border: 1px solid #24242E; border-radius: 8px; padding: 6px 12px; margin-bottom: 8px; }
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

PROMPT_TEMPLATE = """You are reading a car lease or auto loan contract. Extract the following
fields from the contract text below. If a field is not present, use null.
Also find a 17-character VIN if one appears, and write 2-4 short, concrete
negotiation suggestions comparing the terms to typical market ranges
(APR 3-7%, term 12-60 months, mileage allowance 12,000-15,000 mi/yr).

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
  "negotiation_points": [string, ...]
}}

CONTRACT TEXT:
\"\"\"{text}\"\"\"
"""


def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def analyze_with_gemini(api_key, text, max_retries=3):
    client = genai.Client(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(text=text[:15000])
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            raw = response.text.strip()
            raw = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
            return json.loads(raw)
        except Exception as e:
            last_error = e
            is_transient = "503" in str(e) or "UNAVAILABLE" in str(e) or "overloaded" in str(e).lower()
            if is_transient and attempt < max_retries:
                st.toast(f"Model is busy, retrying... ({attempt}/{max_retries})")
                time.sleep(2 * attempt)
                continue
            raise last_error
    raise last_error


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


def render_fairness_gauge(score):
    color = "#00F5D4" if score >= 85 else ("#F5FF00" if score >= 65 else "#FF3B5C")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'suffix': "/100", 'font': {'size': 34, 'family': 'IBM Plex Mono', 'color': '#FFFFFF'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': '#4A4A55', 'tickfont': {'color': '#8C8C99'}},
            'bar': {'color': color, 'thickness': 0.28},
            'bgcolor': "#0B0B12",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 65], 'color': 'rgba(255,59,92,0.15)'},
                {'range': [65, 85], 'color': 'rgba(245,255,0,0.12)'},
                {'range': [85, 100], 'color': 'rgba(0,245,212,0.15)'},
            ],
        }
    ))
    fig.update_layout(
        height=230, margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font={'color': '#E8E8ED'}
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


# ---------- UI ----------
hero_left, hero_right = st.columns([2, 1])
with hero_left:
    st.markdown("""
    <div class="hero-badge">LLM-Powered Contract Review</div>
    <div class="hero-title">Know the deal<br><span class="accent">before you sign.</span></div>
    <div class="hero-sub">Upload a lease or loan contract PDF. An LLM reads it, scores its fairness,
    decodes the vehicle, checks for open recalls, and tells you exactly what to negotiate.</div>
    """, unsafe_allow_html=True)
with hero_right:
    st.markdown("<br>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload contract PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded_file and API_KEY:
        analyze_clicked = st.button("⚡ Analyze with AI", type="primary", use_container_width=True)
    else:
        analyze_clicked = False
    if uploaded_file and not API_KEY:
        st.warning("Add your Gemini API key in the sidebar first.")

if uploaded_file and API_KEY and analyze_clicked:
    with st.spinner("Reading PDF..."):
        text = extract_pdf_text(uploaded_file)
    if not text.strip():
        st.error("Couldn't find any text in that PDF — it may be a scanned image without OCR text.")
    else:
        with st.spinner("Asking Gemini to read the contract..."):
            try:
                result = analyze_with_gemini(API_KEY, text)
            except Exception as e:
                st.error(f"Couldn't get a response after retrying. Try again in a moment. ({e})")
                st.stop()
        st.session_state["fields"] = result.get("fields", {})
        st.session_state["vin"] = result.get("vin")
        st.session_state["negotiation_points"] = result.get("negotiation_points", [])
        st.session_state["raw_text"] = text

if "fields" in st.session_state:
    fields = st.session_state["fields"]
    vin = st.session_state["vin"]
    negotiation_points = st.session_state["negotiation_points"]
    score, checks = compute_fairness_score(fields)
    label, emoji = fairness_label(score)

    st.markdown("<br>", unsafe_allow_html=True)

    row1_left, row1_mid, row1_right = st.columns([1.1, 1.7, 1.1])

    # ---- Fairness gauge (cyan) ----
    with row1_left:
        st.markdown('<div class="glow-panel glow-cyan">', unsafe_allow_html=True)
        st.markdown(f'<div class="panel-heading">{emoji} Fairness Score</div>', unsafe_allow_html=True)
        render_fairness_gauge(score)
        st.markdown(f"**{label}**")
        for check_label, pts, reason in checks[:4]:
            st.caption(f"**{check_label}** — {reason}")
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- Financial terms grid (cyan/red per field) ----
    with row1_mid:
        st.markdown('<div class="glow-panel glow-cyan">', unsafe_allow_html=True)
        st.markdown('<div class="panel-heading">💵 Financial Terms</div>', unsafe_allow_html=True)
        tcols = st.columns(3)
        for i, field in enumerate(NUMERIC_FIELDS):
            with tcols[i % 3]:
                render_term_card(field, fields.get(field), fields)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- Vehicle & recalls (purple) ----
    with row1_right:
        st.markdown('<div class="glow-panel glow-purple">', unsafe_allow_html=True)
        st.markdown('<div class="panel-heading">🚙 Vehicle & Recalls</div>', unsafe_allow_html=True)
        manual_vin = st.text_input("VIN", value=vin or "", max_chars=17, label_visibility="collapsed",
                                    placeholder="Enter 17-character VIN")
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
                with st.spinner("Checking recalls..."):
                    recalls = get_recalls(vehicle.get("make"), vehicle.get("model"), vehicle.get("year"))
                if recalls:
                    st.warning(f"⚠️ {len(recalls)} open recall(s) found.")
                    for r in recalls[:3]:
                        with st.expander(r.get("Component", "Recall")):
                            st.write(r.get("Summary", "No details available."))
                else:
                    st.success("No open recalls found.")
            except Exception:
                st.caption("Couldn't decode that VIN.")
        else:
            st.caption("Enter a 17-character VIN to decode the vehicle.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    row2_left, row2_right = st.columns([1.5, 1])

    # ---- Negotiation (yellow) ----
    with row2_left:
        st.markdown('<div class="glow-panel" style="border-color: rgba(245,255,0,0.3); box-shadow: 0 0 16px rgba(245,255,0,0.08);">', unsafe_allow_html=True)
        st.markdown('<div class="panel-heading">🤝 Negotiation Suggestions</div>', unsafe_allow_html=True)
        if negotiation_points:
            for point in negotiation_points:
                st.markdown(f'<div class="neg-card">💬 {point}</div>', unsafe_allow_html=True)
        else:
            st.caption("No suggestions generated.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- Explanations (pink) ----
    with row2_right:
        st.markdown('<div class="glow-panel glow-pink">', unsafe_allow_html=True)
        st.markdown('<div class="panel-heading">📖 What Terms Mean</div>', unsafe_allow_html=True)
        for field in FIELDS:
            with st.expander(f"{TERM_ICONS.get(field, '•')} {field.replace('_', ' ').title()}"):
                st.write(EXPLANATIONS.get(field, "No explanation available."))
                val = fields.get(field)
                if val is not None:
                    st.caption(f"Found in contract: {val}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    payload = {
        "vin": manual_vin or vin,
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
