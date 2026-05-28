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
        (Reference["Tier"] == tier) &
        (Reference["Start Date"] <= date) &
        (Reference["End Date"] >= date)
    ]

    return sorted(df["Amount"].unique())

# =========================
# HEADER ROW 
# =========================
c1,c2,c3,c4,c5 = st.columns(5)

client = c1.text_input("Client")
case = c2.text_input("Case #")
community = c3.selectbox("Community", Community["Community"].unique())
month = c4.selectbox("Benefit Month", [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
])
year = c5.selectbox("Benefit Year", sorted(Reference["Start Date"].dt.year.unique()))

same = st.checkbox("Same as Declared", value=True)

# =========================
# TABLE FUNCTION
# =========================
def build_table(prefix):
    total = 0
    benefits = sorted(Reference["Benefit Type"].unique())

    for i in range(6):
        c1,c2 = st.columns(2)

        b = c1.selectbox("", [""] + benefits + ["OTHER"], key=f"{prefix}_b_{i}")

        if b == "OTHER":
            for j in range(5):
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
# BENEFITS SECTION
# =========================
col1,_,col2 = st.columns([1,0.3,1])

with col1:
    st.subheader("Declared")
    st.markdown("**Benefit | Amount**")
    declared_total = build_table("d")
    st.markdown(f"### Total Declared: ${declared_total:,.2f}")

with col2:
    st.subheader("Actual")

    if same:
        actual_total = declared_total
        st.info("Actual total is using Declared total")
    else:
        st.markdown("**Benefit | Amount**")
        actual_total = build_table("a")

    st.markdown(f"### Total Actual: ${actual_total:,.2f}")

st.divider()

# =========================
# INCOME
# =========================
st.subheader("INCOME")

c1,_,c2 = st.columns([1,0.3,1])

with c1:
    d_net = st.number_input("Net Income ($)", 0.0, key="d_net")
    d_less = st.number_input("Less Exemption ($)", 0.0, key="d_less")
    declared_net = d_net - d_less
    st.markdown(f"Net: ${declared_net:,.2f}")

with c2:
    a_net = st.number_input("Net Income ($)", 0.0, key="a_net")
    a_less = st.number_input("Less Exemption ($)", 0.0, key="a_less")
    actual_net = a_net - a_less
    st.markdown(f"Net: ${actual_net:,.2f}")

# =========================
# OTHER INCOME
# =========================
st.subheader("OTHER INCOME")

c1,_,c2 = st.columns([1,0.3,1])

with c1:
    d_s = st.number_input("Surplus ($)", 0.0, key="d_s")
    d_i = st.number_input("Interest", 0.0, key="d_i")
    d_l = st.number_input("Less", 0.0, key="d_l")
    declared_other = d_s + d_i - d_l
    st.markdown(f"Total: ${declared_other:,.2f}")

with c2:
    a_s = st.number_input("Surplus ($)", 0.0, key="a_s")
    a_i = st.number_input("Interest", 0.0, key="a_i")
    a_l = st.number_input("Less", 0.0, key="a_l")
    actual_other = a_s + a_i - a_l
    st.markdown(f"Total: ${actual_other:,.2f}")
# =========================
# TOTAL INCOME 
# =========================

declared_total_income = declared_net + declared_other
actual_total_income = actual_net + actual_other
# =========================
# FINAL CALCULATIONS (CLEAN STYLE)
# =========================

c1, _, c2 = st.columns([1, 0.3, 1])

with c1:
    declared_budget = declared_total - declared_total_income
    declared_chargeable = declared_total_income

    st.markdown(f"**Chargeable Income: ${declared_chargeable:,.2f}**")
    st.markdown(f"**Benefit: ${declared_budget:,.2f}**")

with c2:
    actual_budget = actual_total - actual_total_income
    actual_chargeable = actual_total_income

    st.markdown(f"**Chargeable Income: ${actual_chargeable:,.2f}**")
    st.markdown(f"**Budget deficit/surplus: ${actual_budget:,.2f}**")


# =========================
# =========================
# OVERPAYMENT (COMPACT INPUT ✅)
# =========================
st.divider()

st.markdown("**Benefits Issued ($)**")

# ✅ create centered narrow column
_, c1, _ = st.columns([1, 1, 3])   # adjust ratio here

issued = c1.number_input("", 0.0, key="benefits_issued")

overpayment = issued - actual_budget

st.markdown(f"### OVERPAYMENT: ${overpayment:,.2f}")
