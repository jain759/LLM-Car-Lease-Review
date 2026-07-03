import io
import json
import re
import time

import requests
import streamlit as st
from PyPDF2 import PdfReader
from google import genai
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

st.set_page_config(page_title="AI Car Lease Assistant", page_icon="🚗", layout="centered")

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
st.title("🚗 AI Car Lease Assistant")
st.write(
    "Upload a lease or loan contract PDF. An LLM reads the text, pulls out the key "
    "financial terms, decodes the vehicle, checks for recalls, scores the deal's "
    "fairness, and flags anything worth negotiating."
)

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

    st.markdown("---")

    # Fairness score
    score, checks = compute_fairness_score(fields)
    label, emoji = fairness_label(score)
    st.subheader("Contract Fairness Score")
    c1, c2 = st.columns([1, 3])
    with c1:
        st.metric("Score", f"{score}/100")
    with c2:
        st.write(f"### {emoji} {label}")
    for check_label, pts, reason in checks:
        st.caption(f"**{check_label}** — {reason}")

    st.markdown("---")
    st.subheader("Vehicle")
    manual_vin = st.text_input("VIN (auto-filled if found, editable)", value=vin or "", max_chars=17)
    vehicle = None
    recalls = []
    if manual_vin and len(manual_vin) == 17:
        try:
            vehicle = decode_vin(manual_vin)
            st.write(f"**{vehicle.get('year','')} {vehicle.get('make','')} {vehicle.get('model','')}**")
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

    st.subheader("Financial Terms")
    cols = st.columns(3)
    for i, field in enumerate(NUMERIC_FIELDS):
        val = fields.get(field)
        with cols[i % 3]:
            st.metric(field.replace("_", " ").title(), val if val is not None else "not found")

    st.subheader("Negotiation Suggestions")
    if negotiation_points:
        for point in negotiation_points:
            st.write(f"• {point}")
    else:
        st.caption("No suggestions generated.")

    st.subheader("What Each Term Means")
    for field in FIELDS:
        with st.expander(field.replace("_", " ").title()):
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
            "Download JSON summary",
            data=json.dumps(payload, indent=2),
            file_name="lease_contract_summary.json",
            mime="application/json",
        )
    with dl2:
        pdf_buf = build_pdf_report(fields, manual_vin or vin, vehicle, negotiation_points, score, checks, recalls)
        st.download_button(
            "Download PDF report",
            data=pdf_buf,
            file_name="lease_contract_report.pdf",
            mime="application/pdf",
        )

    with st.expander("View extracted contract text"):
        st.text(st.session_state["raw_text"][:6000])
