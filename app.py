import streamlit as st
import pandas as pd
import os

st.set_page_config(layout="wide")

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

Reference["Benefit"] = Reference["Benefit"].str.upper().str.strip()
Reference["Tier"] = Reference["Tier"].fillna("ALL").str.upper()

# =========================
# CREATE BENEFIT GROUP (UI)
# =========================
def get_group(b):
    if "PUBLIC CONSULTATION HOME" in b:
        return "P/C HOME"
    return b

Reference["Group"] = Reference["Benefit"].apply(get_group)

# =========================
# FUNCTIONS
# =========================
def get_tier(comm):
    t = Community.loc[Community["Community"] == comm, "Tier"]
    return t.values[0] if len(t) > 0 else "D"

def get_benefit_options(group):
    return sorted(Reference.loc[Reference["Group"] == group, "Benefit"].unique())

def get_amounts(comm, benefit, adults, children, year, month):

    if benefit == "":
        return []

    tier = get_tier(comm)
    date = pd.to_datetime(f"{year}-{month:02d}-01")

    df = Reference[
        (Reference["Benefit"] == benefit) &
        ((Reference["Tier"] == tier) | (Reference["Tier"] == "ALL")) &
        (Reference["Children"] == children) &
        ((Reference["Adults"].isna()) | (Reference["Adults"] == adults)) &
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

community = c3.selectbox("Community", sorted(Community["Community"]))

# ✅ KEY FILTERS
adults = c4.selectbox("Adults", list(range(0,6)))
children = c5.selectbox("Children", list(range(0,27)))

month_lookup = {
    "January":1,"February":2,"March":3,"April":4,"May":5,"June":6,
    "July":7,"August":8,"September":9,"October":10,"November":11,"December":12
}

month_name = c6.selectbox("Month", list(month_lookup.keys()))
month = month_lookup[month_name]

year = c7.selectbox("Year", sorted(Reference["Start_Date"].dt.year.unique()))

same = st.checkbox("Same as Declared", value=True)

# =========================
# BENEFIT TABLE
# =========================
def build_table(prefix):
    total = 0
    groups = sorted(Reference["Group"].unique())

    for i in range(6):
        c1,c2,c3 = st.columns([1,1,1])

        group = c1.selectbox("Benefit Group", [""] + groups + ["OTHER"], key=f"{prefix}_g_{i}")

        # OTHER OPTION
        if group == "OTHER":
            val = c2.number_input("Amount", 0.0, key=f"{prefix}_other_{i}")
            total += val
            continue

        # SHOW SUB-TYPES (e.g. HOME 1–5)
        options = get_benefit_options(group) if group else []

        benefit = ""
        if options:
            benefit = c2.selectbox("Type", options, key=f"{prefix}_b_{i}")

        amounts = get_amounts(community, benefit, adults, children, year, month)

        if amounts:
            val = c3.selectbox("Amount", amounts, key=f"{prefix}_amt_{i}")
        else:
            val = c3.number_input("Amount", 0.0, key=f"{prefix}_num_{i}")

        total += float(val)

    return total

# =========================
# BENEFITS
# =========================
col1, _, col2 = st.columns([1,0.3,1])

with col1:
    st.subheader("Declared")
    declared_total = build_table("d")
    st.markdown(f"### Total Declared: ${declared_total:,.2f}")

with col2:
    st.subheader("Actual")

    if same:
        actual_total = declared_total
        st.info("Using declared values")
    else:
        actual_total = build_table("a")

    st.markdown(f"### Total Actual: ${actual_total:,.2f}")

# =========================
# INCOME
# =========================
st.divider()
st.subheader("INCOME")

declared_net_total = 0

for i in range(4):
    c1,c2 = st.columns(2)
    net = c1.number_input(f"Net Income {i+1}", 0.0, key=f"net_{i}")
    less = c2.number_input(f"Less {i+1}", 0.0, key=f"less_{i}")
    declared_net_total += (net - less)

st.markdown(f"**Net Income: ${declared_net_total:,.2f}**")

# =========================
# FINAL CALCULATION
# =========================
declared_benefit = declared_total - declared_net_total

st.markdown(f"### Final Benefit: ${declared_benefit:,.2f}")

# =========================
# OVERPAYMENT
# =========================
st.divider()

issued = st.number_input("Benefits Issued", 0.0)
overpayment = issued - declared_benefit

st.markdown(f"### Overpayment: ${overpayment:,.2f}")
