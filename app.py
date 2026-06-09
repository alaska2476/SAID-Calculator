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
        (Reference["Start_Date"] <= date) &
        (Reference["End_Date"] >= date)
    ]

    return sorted(df["Amount"].dropna().unique())

# =========================
# HEADER
# =========================
st.title("SAID TRANSITION CALCULATOR")

c1,c2,c3,c4,c5 = st.columns(5)

client = c1.text_input("Client")
case = c2.text_input("Case #")
community = c3.selectbox("Community", Community["Community"].unique())
month = c4.selectbox("Month", ["January","February","March","April"])
year = c5.selectbox("Year", [2024,2025,2026])

# =========================
# BENEFITS ✅ FIXED
# =========================

# ✅ Checkbox ABOVE both
same_actual = st.checkbox("Same as Declared", True)

# ✅ Headers aligned
h1, h2 = st.columns(2)

with h1:
    st.markdown("### Declared")

with h2:
    st.markdown("### Actual")

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
                name = c3.text_input("", key=f"{prefix}_name_{i}_{j}")
                val = c4.number_input("Amount", 0.0, key=f"{prefix}_val_{i}_{j}")
                if name.strip():
                    total += val
        else:
            opts = get_amounts(community, b, year, month)

            if opts:
                val = c2.selectbox("", opts, key=f"{prefix}_amt_{i}")
            else:
                val = c2.number_input("Amount", 0.0, key=f"{prefix}_num_{i}")

            total += float(val)

    return total

# =========================
# DATA ROW
# =========================
col1, col2 = st.columns(2)

with col1:
    declared_total = build_table("d")
    st.markdown(f"### Total Declared: ${declared_total:,.2f}")

with col2:
    if same_actual:
        actual_total = declared_total
        st.info("Using declared values")
    else:
        actual_total = build_table("a")

    st.markdown(f"### Total Actual: ${actual_total:,.2f}")

st.divider()

# =========================
# INCOME
# =========================
st.subheader("INCOME")

col1_inc,_,col2_inc = st.columns([1,0.3,1])

# Declared Income
with col1_inc:
    declared_net_total = 0

    for i in range(4):
        c1,c2 = st.columns(2)
        net = c1.number_input(f"Net {i+1}", 0.0, key=f"net{i}")
        less = c2.number_input("Less", 0.0, key=f"less{i}")
        declared_net_total += (net - less)

    st.markdown(f"**Net Income: ${declared_net_total:,.2f}**")

# ✅ Other Income (checkbox ABOVE ✅)
with col2_inc:

    same_income = st.checkbox("Same as Declared Income", True)

    st.markdown("**Other Income**")

    if same_income:
        other_income_total = 0
        st.info("No additional income")
    else:
        other_income_total = 0

        # Surplus
        c1, c2 = st.columns(2)
        s = c1.number_input("Surplus", 0.0)
        l = c2.number_input("Less", 0.0)
        other_income_total += (s - l)

        # Interest
        c3, c4 = st.columns(2)
        i = c3.number_input("Interest", 0.0)
        l2 = c4.number_input("Less", 0.0)
        other_income_total += (i - l2)

        # Others with LESS ✅
        for i in range(2):
            c5, c6 = st.columns(2)
            v = c5.number_input(f"Other {i+1}", 0.0, key=f"o{i}")
            l = c6.number_input("Less", 0.0, key=f"ol{i}")
            other_income_total += (v - l)

        st.markdown(f"**Total Other Income: ${other_income_total:,.2f}**")

# =========================
# FINAL
# =========================
declared_total_income = declared_net_total + (0 if same_income else other_income_total)
declared_benefit = declared_total - declared_net_total
actual_budget = actual_total - declared_total_income

st.markdown(f"### Benefit: ${declared_benefit:,.2f}")

# =========================
# OVERPAYMENT
# =========================
st.markdown("**Benefits Issued ($)**")
issued = st.number_input("", 0.0)

overpayment = issued - actual_budget
st.markdown(f"### OVERPAYMENT: ${overpayment:,.2f}")

# =========================
# SAVE + OVERWRITE + DOWNLOAD
# =========================
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame()

if st.button("Save Month Calculation"):

    new_row = pd.DataFrame([{
        "Client": client,
        "Case": case,
        "Month": month,
        "Year": year,
        "Declared_Total_Needs": declared_total,
        "Declared_Net_Income": declared_net_total,
        "Declared_Other_Income": (0 if same_income else other_income_total),
        "Declared_Total_Income": declared_total_income,
        "Declared_Benefit": declared_benefit,
        "Actual_Total_Needs": actual_total,
        "Budget_Deficit_Surplus": actual_budget,
        "Benefits_Issued": issued,
        "Overpayment": overpayment
    }])

    hist = st.session_state.history

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

    st.markdown(f"**Total Overpayment: ${st.session_state.history['Overpayment'].sum():,.2f}**")

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state.history.to_excel(writer, index=False)

    st.download_button("Download Summary", output.getvalue(), "SAID_Summary.xlsx")
