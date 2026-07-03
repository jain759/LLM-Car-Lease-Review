import json
import os
import re

import requests
import streamlit as st
from PyPDF2 import PdfReader
from google import genai

st.set_page_config(page_title="AI Car Lease Assistant", page_icon="🚗", layout="centered")

# ---------- API key handling ----------
# Looks for the key in Streamlit secrets first (used once deployed),
# falls back to a manual input box (handy for local testing).
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

# ---------- Field schema (same fields as the original notebook) ----------
FIELDS = [
    "apr_percent", "term_months", "monthly_payment", "down_payment",
    "residual_value", "mileage_allowance", "mileage_overage_fee",
    "early_termination_fee", "purchase_option_price",
    "insurance_requirements", "maintenance_responsibilities",
    "warranty_summary", "late_fee_policy",
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


def analyze_with_gemini(api_key, text):
    client = genai.Client(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(text=text[:15000])  # keep prompt a reasonable size
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    raw = response.text.strip()
    raw = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    return json.loads(raw)


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


# ---------- UI ----------
st.title("🚗 AI Car Lease Assistant")
st.write(
    "Upload a lease or loan contract PDF. An LLM reads the text, pulls out the key "
    "financial terms, decodes the vehicle, and flags anything worth negotiating."
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
                    st.error(f"Couldn't parse the AI's response. Try again. ({e})")
                    st.stop()

            fields = result.get("fields", {})
            vin = result.get("vin")
            negotiation_points = result.get("negotiation_points", [])

            st.session_state["fields"] = fields
            st.session_state["vin"] = vin
            st.session_state["negotiation_points"] = negotiation_points
            st.session_state["raw_text"] = text

if "fields" in st.session_state:
    fields = st.session_state["fields"]
    vin = st.session_state["vin"]
    negotiation_points = st.session_state["negotiation_points"]

    st.markdown("---")
    st.subheader("Vehicle")
    manual_vin = st.text_input("VIN (auto-filled if found, editable)", value=vin or "", max_chars=17)
    if manual_vin and len(manual_vin) == 17:
        try:
            vehicle = decode_vin(manual_vin)
            st.write(f"**{vehicle.get('year','')} {vehicle.get('make','')} {vehicle.get('model','')}**")
        except Exception:
            st.caption("Couldn't decode that VIN.")
    else:
        st.caption("Enter a 17-character VIN to decode the vehicle.")

    st.subheader("Financial Terms")
    cols = st.columns(3)
    numeric_fields = [f for f in FIELDS if f in (
        "apr_percent", "term_months", "monthly_payment", "down_payment",
        "residual_value", "mileage_allowance", "mileage_overage_fee",
        "early_termination_fee", "purchase_option_price"
    )]
    for i, field in enumerate(numeric_fields):
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
    }
    st.download_button(
        "Download JSON summary",
        data=json.dumps(payload, indent=2),
        file_name="lease_contract_summary.json",
        mime="application/json",
    )

    with st.expander("View extracted contract text"):
        st.text(st.session_state["raw_text"][:6000])
