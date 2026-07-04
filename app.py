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

st.set_page_config(page_title="AI Car Lease Assistant", page_icon="🚗", layout="centered")

# ---------- Custom styling ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

/* Hero banner */
.hero-banner {
    background: linear-gradient(135deg, #1B1F1D 0%, #2A2F2C 100%);
    padding: 32px 28px;
    border-radius: 10px;
    margin-bottom: 22px;
    border: 1px solid #3a3f3b;
}
.hero-banner h1 {
    font-family: 'Big Shoulders Display', sans-serif;
    font-weight: 800;
    text-transform: uppercase;
    color: #F1F0EA;
    font-size: 34px;
    letter-spacing: 0.01em;
    margin: 0 0 6px 0;
}
.hero-banner p {
    color: #C9C7BE;
    font-size: 15px;
    margin: 0;
    line-height: 1.5;
}
.hero-badge {
    display: inline-block;
    background: #F5B700;
    color: #1B1F1D;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 4px 10px;
    border-radius: 3px;
    margin-bottom: 12px;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E3E1D8;
    border-radius: 8px;
    padding: 14px 16px 10px 16px;
    box-shadow: 2px 2px 0 #EDEBE1;
}
div[data-testid="stMetricLabel"] {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px !important;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #6B7280 !important;
}
div[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
}

/* Buttons */
div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {
    border-radius: 6px;
    font-weight: 600;
    letter-spacing: 0.02em;
}
div[data-testid="stButton"] button[kind="primary"] {
    background-color: #1B1F1D;
    border: none;
}
div[data-testid="stButton"] button[kind="primary"]:hover {
    background-color: #2A2F2C;
}

/* Section headers */
h2, h3 { font-family: 'Big Shoulders Display', sans-serif; text-transform: uppercase; letter-spacing: 0.01em; }

/* Tabs */
button[data-baseweb="tab"] {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* File uploader */
div[data-testid="stFileUploaderDropzone"] {
    border-radius: 8px;
    border: 2px dashed #C9C6BA;
}

/* Term cards */
.term-card {
    background: #FFFFFF;
    border: 1px solid #E3E1D8;
    border-left: 4px solid #C9C6BA;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 12px;
    box-shadow: 2px 2px 0 #F3F1E9;
}
.term-card.good { border-left-color: #3F7D58; }
.term-card.bad { border-left-color: #C0392B; }
.term-card .tc-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10.5px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #6B7280;
    margin-bottom: 4px;
}
.term-card .tc-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 22px;
    font-weight: 600;
    color: #1B1F1D;
}
.term-card .tc-value.empty { color: #C9C6BA; font-size: 15px; font-weight: 400; }

/* Negotiation cards */
.neg-card {
    background: #FFFDF5;
    border: 1px solid #F0E6C0;
    border-left: 4px solid #F5B700;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 10px;
    font-size: 14.5px;
    line-height: 1.5;
}

/* Vehicle card */
.vehicle-card {
    background: linear-gradient(135deg, #1B1F1D 0%, #2A2F2C 100%);
    color: #F1F0EA;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.vehicle-card .vc-name {
    font-family: 'Big Shoulders Display', sans-serif;
    font-size: 26px;
    text-transform: uppercase;
}
.vehicle-card .vc-vin {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: #9C9A92;
}
</style>
""", unsafe_allow_html=True)

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


def term_flag(field, val, fields):
    """Returns 'good', 'bad', or None (neutral) for coloring a term card."""
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
        value_html = f'<div class="tc-value">{prefix}{val:,.2f}{suffix}</div>' if isinstance(val, float) else f'<div class="tc-value">{prefix}{val:,}{suffix}</div>'
    css_class = f"term-card {flag}" if flag else "term-card"
    st.markdown(f"""
    <div class="{css_class}">
        <div class="tc-label">{icon} {label}</div>
        {value_html}
    </div>
    """, unsafe_allow_html=True)


def render_fairness_gauge(score):
    color = "#3F7D58" if score >= 85 else ("#F5B700" if score >= 65 else "#C0392B")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'suffix': "/100", 'font': {'size': 36, 'family': 'IBM Plex Mono'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': color, 'thickness': 0.3},
            'bgcolor': "white",
            'steps': [
                {'range': [0, 65], 'color': '#FBEDEB'},
                {'range': [65, 85], 'color': '#FEF6E0'},
                {'range': [85, 100], 'color': '#EBF3EE'},
            ],
        }
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

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
    """Calls Gemini, retrying automatically on transient server errors (e.g. 503)."""
    client = genai.Client(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(text=text[:15000])

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
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
    return {
        "make": lookup.get("Make"),
        "model": lookup.get("Model"),
        "year": lookup.get("Model Year"),
    }


def get_recalls(make, model, year):
    """Free NHTSA recalls lookup by make/model/year."""
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


# ---------- Fairness Score ----------
def compute_fairness_score(fields):
    """
    Weighted 0-100 score based on how extracted terms compare to typical
    market ranges. Returns (score, list of (label, points_lost, reason)).
    """
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


# ---------- PDF report ----------
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
            f"{vehicle.get('year','')} {vehicle.get('make','')} {vehicle.get('model','')}  (VIN: {vin or 'n/a'})",
            body))

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
st.markdown("""
<div class="hero-banner">
    <div class="hero-badge">AI Car Lease Assistant</div>
    <h1>🚗 Know the deal before you sign</h1>
    <p>Upload a lease or loan contract PDF. An LLM reads the text, pulls out the key
    financial terms, decodes the vehicle, checks for recalls, scores the deal's
    fairness, and flags anything worth negotiating.</p>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload contract PDF", type=["pdf"])

if uploaded_file and not API_KEY:
    st.warning("Add your Gemini API key in the sidebar to analyze the contract.")

if uploaded_file and API_KEY:
    with st.spinner("Reading PDF..."):
        text = extract_pdf_text(uploaded_file)

    if not text.strip():
        st.error("Couldn't find any text in that PDF — it may be a scanned image without OCR text.")
    else:
        if st.button("Analyze with AI", type="primary"):
            with st.spinner("Asking Gemini to read the contract..."):
                try:
                    result = analyze_with_gemini(API_KEY, text)
                except Exception as e:
                    st.error(f"Couldn't get a response after retrying. Try again in a moment. ({e})")
                    st.stop()

            fields = result.get("fields", {})
            vin = result.get("vin")
            negotiation_points = result.get("negotiation_points", [])

            st.session_state["fields"] = fields
            st.session_state["vin"] = vin
            st.session_state["negotiation_points"] = negotiation_points
            st.session_state["raw_text"] = text
            st.session_state.pop("vehicle", None)
            st.session_state.pop("recalls", None)

if "fields" in st.session_state:
    fields = st.session_state["fields"]
    vin = st.session_state["vin"]
    negotiation_points = st.session_state["negotiation_points"]
    score, checks = compute_fairness_score(fields)
    label, emoji = fairness_label(score)

    st.markdown("<br>", unsafe_allow_html=True)
    tab_overview, tab_vehicle, tab_negotiate, tab_explain = st.tabs(
        ["📊 Overview", "🚙 Vehicle & Recalls", "🤝 Negotiation", "📖 Explained"]
    )

    # ---- Overview tab ----
    with tab_overview:
        gcol1, gcol2 = st.columns([1, 1])
        with gcol1:
            render_fairness_gauge(score)
        with gcol2:
            st.markdown(f"### {emoji} {label}")
            for check_label, pts, reason in checks:
                st.caption(f"**{check_label}** — {reason}")

        st.markdown("#### Financial Terms")
        cols = st.columns(3)
        for i, field in enumerate(NUMERIC_FIELDS):
            with cols[i % 3]:
                render_term_card(field, fields.get(field), fields)

    # ---- Vehicle & Recalls tab ----
    with tab_vehicle:
        manual_vin = st.text_input("VIN (auto-filled if found, editable)", value=vin or "", max_chars=17)
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
            st.caption("Enter a 17-character VIN to decode the vehicle and check recalls.")

    # ---- Negotiation tab ----
    with tab_negotiate:
        st.markdown("#### Negotiation Suggestions")
        if negotiation_points:
            for point in negotiation_points:
                st.markdown(f'<div class="neg-card">💬 {point}</div>', unsafe_allow_html=True)
        else:
            st.caption("No suggestions generated.")

    # ---- Explained tab ----
    with tab_explain:
        st.markdown("#### What Each Term Means")
        for field in FIELDS:
            with st.expander(f"{TERM_ICONS.get(field, '•')} {field.replace('_', ' ').title()}"):
                st.write(EXPLANATIONS.get(field, "No explanation available."))
                val = fields.get(field)
                if val is not None:
                    st.caption(f"Found in contract: {val}")

    st.markdown("---")
    payload = {
        "vin": manual_vin or vin,
        "sla_fields": fields,
        "negotiation_suggestions": negotiation_points,
        "fairness_score": score,
    }

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "⬇️ Download JSON summary",
            data=json.dumps(payload, indent=2),
            file_name="lease_contract_summary.json",
            mime="application/json",
        )
    with dl2:
        pdf_buf = build_pdf_report(fields, payload["vin"], vehicle, negotiation_points, score, checks, recalls)
        st.download_button(
            "⬇️ Download PDF report",
            data=pdf_buf,
            file_name="lease_contract_report.pdf",
            mime="application/pdf",
        )

    with st.expander("View extracted contract text"):
        st.text(st.session_state["raw_text"][:6000])
