import streamlit as st
import pandas as pd
import os

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide")

st.markdown("""
<style>
.block-container {padding-top:0.8rem; padding-bottom: 0.5rem;}
h1 {text-align: center;}
</style>
""", unsafe_allow_html=True)

# =========================
# LOAD DATA
# =========================
def load_excel_safe(path):
    if os.path.exists(path):
        return pd.read_excel(path)
    else:
        st.error(f"Missing file: {path}")
        st.stop()

Reference = load_excel_safe("Reference.xlsx")
Community = load_excel_safe("Community.xlsx")

Reference.columns = ["Benefit Type","Start Date","End Date","Tier","Amount"]

Reference["Start Date"] = pd.to_datetime(Reference["Start Date"])
Reference["End Date"] = pd.to_datetime(Reference["End Date"])
Reference["Benefit Type"] = Reference["Benefit Type"].str.upper().str.strip()
Reference["Tier"] = Reference["Tier"].str.upper().str.strip()
Reference["Amount"] = Reference["Amount"].replace(r'[\$,]', '', regex=True).astype(float)

Community["Tier"] = Community["Tier"].str.upper().str.strip()

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
    input_date = pd.to_datetime(f"{year} {month} 01", format="%Y %B %d")

    df = Reference[
        (Reference["Benefit Type"] == benefit) &
        (Reference["Tier"] == tier) &
        (Reference["Start Date"] <= input_date) &
        (Reference["End Date"] >= input_date)
    ]

    return sorted(df["Amount"].unique())

# =========================
# HEADER
# =========================
st.title("SAID TRANSITION CALCULATOR")

cols = st.columns(5)

client = cols[0].text_input("Client")
case = cols[1].text_input("Case #")
community = cols[2].selectbox("Community", Community["Community"].unique())

months = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]

month = cols[3].selectbox("Benefit Month", months)
year = cols[4].selectbox("Benefit Year", sorted(Reference["Start Date"].dt.year.unique()))

same = st.checkbox("Same as Declared", value=True)

# =========================
# TABLE FUNCTION
# =========================
def build_table(prefix):
    rows = 6
    total = 0
    benefit_list = sorted(Reference["Benefit Type"].unique())

    for i in range(rows):

        col1, col2 = st.columns(2)

        selected = col1.selectbox("", [""] + benefit_list + ["OTHER"], key=f"{prefix}_b_{i}")

        if selected == "OTHER":
            col2.write("")

            for j in range(10):
                c1, c2 = st.columns(2)

                benefit = c1.text_input("", key=f"{prefix}_other_{i}_{j}")
                val = c2.number_input("Amount ($)", 0.0, key=f"{prefix}_other_amt_{i}_{j}", format="%.2f")

                if benefit.strip():
                    total += val

        else:
            options = get_amounts(community, selected, year, month)

            if selected and options:
                val = col2.selectbox("", options, key=f"{prefix}_amt_{i}")
            else:
                val = col2.number_input("Amount ($)", 0.0, key=f"{prefix}_manual_{i}")

            total += float(val)

    return total

# =========================
# DECLARED / ACTUAL BENEFITS
# =========================
col1, _, col2 = st.columns([1,0.3,1])

with col1:
    st.subheader("Declared")
    declared_total = build_table("declared")

with col2:
    st.subheader("Actual")
    actual_total = declared_total if same else build_table("actual")

# =========================
# INCOME
# =========================
st.subheader("INCOME")

col1_inc, _, col2_inc = st.columns([1,0.3,1])

with col1_inc:
    d_net = st.number_input("Net Income ($)", 0.0)
    d_less = st.number_input("Less Exemption ($)", 0.0)
    declared_net = d_net - d_less
    st.markdown(f"Net: ${declared_net:,.2f}")

with col2_inc:
    if same:
        actual_net = declared_net
    else:
        a_net = st.number_input("Net Income ($)", 0.0)
        a_less = st.number_input("Less Exemption ($)", 0.0)
        actual_net = a_net - a_less
    st.markdown(f"Net: ${actual_net:,.2f}")

# =========================
# OTHER INCOME
# =========================
st.subheader("OTHER INCOME")

col1_o, _, col2_o = st.columns([1,0.3,1])

with col1_o:
    d_s = st.number_input("Surplus ($)", 0.0)
    d_i = st.number_input("Interest income ($)", 0.0)
    d_l = st.number_input("Less Exemption ($)", 0.0)
    declared_other = d_s + d_i - d_l
    st.markdown(f"Total: ${declared_other:,.2f}")

with col2_o:
    if same:
        actual_other = declared_other
    else:
        a_s = st.number_input("Surplus ($)", 0.0)
        a_i = st.number_input("Interest income ($)", 0.0)
        a_l = st.number_input("Less Exemption ($)", 0.0)
        actual_other = a_s + a_i - a_l
    st.markdown(f"Total: ${actual_other:,.2f}")

# =========================
# ✅ TOTAL INCOME (YOUR REQUIREMENT)
# =========================
st.subheader("TOTAL INCOME")

col1_ti, _, col2_ti = st.columns([1,0.3,1])

with col1_ti:
    declared_total_income = declared_net + declared_other
    st.markdown(f"Declared Net: ${declared_net:,.2f}")
    st.markdown(f"Declared Other: ${declared_other:,.2f}")
    st.markdown(f"✅ Total Income: ${declared_total_income:,.2f}")

with col2_ti:
    actual_total_income = actual_net + actual_other
    st.markdown(f"Actual Net: ${actual_net:,.2f}")
    st.markdown(f"Actual Other: ${actual_other:,.2f}")
    st.markdown(f"✅ Total Income: ${actual_total_income:,.2f}")

# =========================
# FINAL CALCULATIONS
# =========================
st.subheader("FINAL CALCULATIONS")

col1_calc, _, col2_calc = st.columns([1,0.3,1])

with col1_calc:
    declared_chargeable = declared_total_income
    declared_budget = declared_total - declared_chargeable
    st.markdown(f"Chargeable: ${declared_chargeable:,.2f}")
    st.markdown(f"Budget: ${declared_budget:,.2f}")

with col2_calc:
    actual_chargeable = actual_total_income
    actual_budget = actual_total - actual_chargeable
    st.markdown(f"Chargeable: ${actual_chargeable:,.2f}")
    st.markdown(f"Budget: ${actual_budget:,.2f}")

# =========================
# OVERPAYMENT
# =========================
st.divider()

issued = st.number_input("Benefits Issued ($)", 0.0)
overpayment = issued - actual_budget

st.markdown(f"OVERPAYMENT: ${overpayment:,.2f}")
fraud = st.number_input("Fraud Overpayment ($)", 0.0)
