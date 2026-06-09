import streamlit as st
import pandas as pd
import os
import io

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

st.markdown("""
<style>
.block-container {padding-top:0.8rem;}
h1 {text-align:center;}
</style>
""", unsafe_allow_html=True)

# =========================
# LOAD DATA
# =========================
def load_excel_safe(path):
    if os.path.exists(path):
        return pd.read_excel(path, engine="openpyxl")
    else:
        st.error(f"Missing file: {path}")
        st.stop()

Reference = load_excel_safe("Reference.xlsx")
Community = load_excel_safe("Community.xlsx")

# =========================
# CLEAN DATA
# =========================
Reference["Start_Date"] = pd.to_datetime(Reference["Start_Date"])
Reference["End_Date"] = pd.to_datetime(Reference["End_Date"])
Reference["Benefit Type"] = Reference["Benefit"].str.upper().str.strip()
Reference["Tier"] = Reference["Tier"].fillna("ALL").str.upper()
Reference["Amount"] = Reference["Amount"].astype(float)

# =========================
# GROUPING
# =========================
def assign_group(b):
    if "LIVING" in b: return "LIVING"
    if "APPROVED HOME" in b: return "APPROVED HOME"
    if "ROOM" in b: return "BOARD & ROOM"
    return b

Reference["Group"] = Reference["Benefit Type"].apply(assign_group)

# =========================
# FUNCTIONS
# =========================
def get_tier(comm):
    t = Community.loc[Community["Community"] == comm, "Tier"]
    return t.values[0] if len(t) > 0 else "D"

def get_amounts(comm, group, year, month):
    if group in ["", "OTHER"]:
        return []

    tier = get_tier(comm)
    date = pd.to_datetime(f"{year} {month} 01")

    df = Reference[
        (Reference["Group"] == group) &
        ((Reference["Tier"] == tier) | (Reference["Tier"] == "ALL")) &
        ((Reference["Adults"] == adults) | (Reference["Adults"].isna())) &
        (Reference["Children"] == children) &
        (Reference["Start_Date"] <= date) &
        (Reference["End_Date"] >= date)
    ]
    return sorted(df["Amount"].dropna().unique())

# =========================
# HEADER
# =========================
st.title("SAID TRANSITION CALCULATOR")

c1,c2,c3,c4,c5,c6,c7 = st.columns(7)

client = c1.text_input("Client")
case = c2.text_input("Case #")
community = c3.selectbox("Community", Community["Community"].unique())

month = c4.selectbox("Benefit Month", [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
])

year = c5.selectbox("Benefit Year", list(range(2020, 2027)))
adults = c6.selectbox("Adults", list(range(1,6)))
children = c7.selectbox("Children", list(range(0,27)))

# =========================
# TABLE BUILDER
# =========================
def build_table(prefix):
    total = 0
    benefits = sorted(Reference["Group"].unique())

    for i in range(6):
        c1,c2 = st.columns(2)
        b = c1.selectbox("", [""] + benefits + ["OTHER"], key=f"{prefix}_b_{i}")

        if b == "OTHER":
            for j in range(10):
                c3,c4 = st.columns(2)
                name = c3.text_input("", key=f"{prefix}_custom_{i}_{j}")
                val = c4.number_input("Amount ($)", 0.0, key=f"{prefix}_other_{i}_{j}")
                if name.strip():
                    total += val
        else:
            opts = get_amounts(community, b, year, month)
            val = c2.selectbox("", opts, key=f"{prefix}_amt_{i}") if opts else c2.number_input("Amount ($)", 0.0, key=f"{prefix}_num_{i}")
            total += float(val)

    return total

# =========================
# ✅ BENEFITS
# =========================

h1, _, h2 = st.columns([1,0.3,1])
with h1: st.subheader("Declared")
with h2: st.subheader("Actual")

_, _, cb = st.columns([1,0.3,1])
with cb:
    same_actual = st.checkbox("Same as Declared", True)

col1,_,col2 = st.columns([1,0.3,1])

with col1:
    declared_total = build_table("d")
    st.markdown(f"### Total Declared: ${declared_total:,.2f}")

with col2:
    actual_total = declared_total if same_actual else build_table("a")
    if same_actual:
        st.info("Using declared values")
    st.markdown(f"### Total Actual: ${actual_total:,.2f}")

# =========================
# ✅ INCOME
# =========================
st.subheader("INCOME")

h1, _, h2 = st.columns([1,0.3,1])
with h1: st.markdown("**Declared Income**")
with h2: st.markdown("**Other Income**")

_, _, cb2 = st.columns([1,0.3,1])
with cb2:
    same_income = st.checkbox("Same as Declared Income", True)

col1_inc,_,col2_inc = st.columns([1,0.3,1])

with col1_inc:
    declared_net_total = 0
    for i in range(4):
        c1,c2 = st.columns(2)
        declared_net_total += (
            c1.number_input(f"Net Income {i+1}",0.0,key=f"d_net_{i}") -
            c2.number_input("Less",0.0,key=f"d_less_{i}")
        )
    st.markdown(f"**Net Income: ${declared_net_total:,.2f}**")

with col2_inc:
    if same_income:
        other_income_total = 0
        st.info("No additional income")
    else:
        total = 0

        c1,c2 = st.columns(2)
        total += c1.number_input("Surplus",0.0) - c2.number_input("Less",0.0)

        c3,c4 = st.columns(2)
        total += c3.number_input("Interest",0.0) - c4.number_input("Less ",0.0)

        for i in range(2):
            c5,c6 = st.columns(2)
            total += c5.number_input(f"Other {i+1}",0.0,key=f"o{i}") - c6.number_input("Less",0.0,key=f"ol{i}")

        other_income_total = total
        st.markdown(f"**Total Other Income: ${other_income_total:,.2f}**")

# =========================
# FINAL
# =========================
declared_total_income = declared_net_total + (0 if same_income else other_income_total)
actual_budget = actual_total - declared_total_income

st.markdown(f"### Benefit: ${(declared_total - declared_net_total):,.2f}")

# =========================
# OVERPAYMENT
# =========================
issued = st.number_input("Benefits Issued ($)",0.0)
overpayment = issued - actual_budget
st.markdown(f"### OVERPAYMENT: ${overpayment:,.2f}")

# =========================
# ✅ SAVE FIX (NO KEYERROR)
# =========================
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=[
        "Client","Case","Month","Year","Overpayment"
    ])

if st.button("Save Month Calculation"):

    new_row = pd.DataFrame([{
        "Client": client,
        "Case": case,
        "Month": month,
        "Year": year,
        "Overpayment": overpayment
    }])

    hist = st.session_state.history

    if not hist.empty:
        mask = (
            (hist["Client"] == client) &
            (hist["Case"] == case) &
            (hist["Month"] == month) &
            (hist["Year"] == year)
        )
        hist = hist[~mask]

    st.session_state.history = pd.concat([hist, new_row], ignore_index=True)

# =========================
# DISPLAY + DOWNLOAD
# =========================
if len(st.session_state.history) > 0:

    st.dataframe(st.session_state.history)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state.history.to_excel(writer, index=False)

    st.download_button("Download Summary", output.getvalue(), "SAID_Summary.xlsx")
