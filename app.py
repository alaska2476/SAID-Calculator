import streamlit as st
import pandas as pd
import os

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
# FUNCTIONS
# =========================
def get_tier(comm):
    t = Community.loc[Community["Community"] == comm, "Tier"]
    return t.values[0] if len(t) > 0 else "D"

def get_amounts(comm, benefit, year, month):
    if benefit in ["", "OTHER"]:
        return []

    tier = get_tier(comm)
    date = pd.to_datetime(f"{year} {month} 01")

    df = Reference[
        (Reference["Benefit Type"] == benefit) &
        ((Reference["Tier"] == tier) | (Reference["Tier"] == "ALL")) &
        ((Reference["Adults"] == adults) | (Reference["Adults"].isna())) &
        (Reference["Children"] == children) &
        (Reference["Start_Date"] <= date) &
        (Reference["End_Date"] >= date)
    ]

    return sorted(df["Amount"].dropna().unique())

# =========================
# HEADER (ALL IN ONE LINE ✅)
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

year = c5.selectbox("Benefit Year", sorted(Reference["Start_Date"].dt.year.unique()))

# ✅ NOW PERFECTLY ALIGNED
adults = c6.selectbox("Adults", list(range(0,6)))
children = c7.selectbox("Children", list(range(0,27)))

same = st.checkbox("Same as Declared", value=True)

# =========================
# BENEFIT TABLE
# =========================
def build_table(prefix):
    total = 0
    benefits = sorted(Reference["Benefit Type"].unique())

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

            if opts:
                val = c2.selectbox("", opts, key=f"{prefix}_amt_{i}")
            else:
                val = c2.number_input("Amount ($)", 0.0, key=f"{prefix}_num_{i}")

            total += float(val)

    return total

# =========================
# BENEFITS
# =========================
col1,_,col2 = st.columns([1,0.3,1])

with col1:
    st.subheader("Declared")
    declared_total = build_table("d")
    st.markdown(f"### Total Declared: ${declared_total:,.2f}")

with col2:
    st.subheader("Actual")

    if same:
        actual_total = declared_total
        st.info("Actual total is using Declared total")
    else:
        actual_total = build_table("a")

    st.markdown(f"### Total Actual: ${actual_total:,.2f}")

st.divider()

# =========================
# INCOME
# =========================
st.subheader("INCOME")

income_same = st.checkbox("Same as Declared Income", value=True)

col1_inc, _, col2_inc = st.columns([1, 0.3, 1])

with col1_inc:
    st.markdown("**Declared Income**")
    declared_net_total = 0

    for i in range(4):
        c1,c2 = st.columns(2)

        net_val = c1.number_input(f"Net Income {i+1} ($)", 0.0, key=f"d_net_{i}")
        less_val = c2.number_input(f"Less Exemption {i+1} ($)", 0.0, key=f"d_less_{i}")

        declared_net_total += (net_val - less_val)

    st.markdown(f"**Net Income: ${declared_net_total:,.2f}**")

with col2_inc:
    st.markdown("**Other Income**")

    if income_same:
        other_income_total = 0
        st.info("Other Income matches declared")
    else:
        o_s = st.number_input("Surplus ($)", 0.0, key="o_s")
        o_i = st.number_input("Interest", 0.0, key="o_i")
        o_l = st.number_input("Less", 0.0, key="o_l")

        other_income_total = o_s + o_i - o_l
        st.markdown(f"**Total Other Income: ${other_income_total:,.2f}**")

# =========================
# TOTAL INCOME
# =========================
declared_total_income = declared_net_total + (0 if income_same else other_income_total)
actual_total_income = declared_total_income

# =========================
# FINAL
# =========================
c1, _, c2 = st.columns([1, 0.3, 1])

with c1:
    declared_benefit = declared_total - declared_net_total
    st.markdown(f"**Benefit: ${declared_benefit:,.2f}**")

with c2:
    actual_budget = actual_total - actual_total_income
    st.markdown(f"**Chargeable Income: ${actual_total_income:,.2f}**")
    st.markdown(f"**Budget deficit/surplus: ${actual_budget:,.2f}**")

# =========================
# OVERPAYMENT
# =========================
st.divider()

st.markdown("**Benefits Issued ($)**")
issued = st.number_input("", 0.0, key="issued_input")

overpayment = issued - actual_budget
st.markdown(f"### OVERPAYMENT: ${overpayment:,.2f}")
