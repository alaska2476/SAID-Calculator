import streamlit as st
import pandas as pd
import os

# =========================
# PAGE CONFIG
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
    return t.values[0] if len(t) > 0 else "D")

def get_amounts(comm, benefit, year, month):
    if benefit in ["", "OTHER"]:
        return []

    tier = get_tier(comm)
    input_date = pd.to_datetime(f"{year} {month} 01")

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

community = cols[0].selectbox("Community", Community["Community"].unique())
month = cols[1].selectbox("Month", ["January","February","March","April","May","June",
                                   "July","August","September","October","November","December"])
year = cols[2].selectbox("Year", sorted(Reference["Start Date"].dt.year.unique()))
same = cols[3].checkbox("Same as Declared", value=True)

# =========================
# BENEFIT TABLE
# =========================
def build_table(prefix):
    total = 0
    benefits = sorted(Reference["Benefit Type"].unique())

    for i in range(6):

        c1, c2 = st.columns(2)

        b = c1.selectbox("", [""] + benefits + ["OTHER"], key=f"{prefix}_b_{i}")

        if b == "OTHER":
            for j in range(10):
                c3, c4 = st.columns(2)
                
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

col1, _, col2 = st.columns([1,0.3,1])

with col1:
    st.subheader("Declared")
    declared_total = build_table("d")

with col2:
    st.subheader("Actual")
    if same:
        actual_total = declared_total
        st.info("Actual total is using Declared total")
    else:
        actual_total = build_table("a")

# =========================
# INCOME
# =========================
st.subheader("INCOME")

c1, _, c2 = st.columns([1,0.3,1])

with c1:
    d_net = st.number_input("Net Income ($)", 0.0, key="d_net")
    d_less = st.number_input("Less Exemption ($)", 0.0, key="d_less")
    declared_net = d_net - d_less
    st.write(f"Net: ${declared_net:,.2f}")

with c2:
    if same:
        a_net = st.number_input("Net Income ($)", value=d_net, key="a_net", disabled=True)
        a_less = st.number_input("Less Exemption ($)", value=d_less, key="a_less", disabled=True)
    else:
        a_net = st.number_input("Net Income ($)", 0.0, key="a_net")
        a_less = st.number_input("Less Exemption ($)", 0.0, key="a_less")

    actual_net = a_net - a_less
    st.write(f"Net: ${actual_net:,.2f}")

# =========================
# OTHER INCOME
# =========================
st.subheader("OTHER INCOME")

c1, _, c2 = st.columns([1,0.3,1])

with c1:
    d_s = st.number_input("Surplus ($)", 0.0, key="d_s")
    d_i = st.number_input("Interest ($)", 0.0, key="d_i")
    d_l = st.number_input("Less ($)", 0.0, key="d_l")

    declared_other = d_s + d_i - d_l
    st.write(f"Total: ${declared_other:,.2f}")

with c2:
    if same:
        a_s = st.number_input("Surplus ($)", value=d_s, key="a_s", disabled=True)
        a_i = st.number_input("Interest ($)", value=d_i, key="a_i", disabled=True)
        a_l = st.number_input("Less ($)", value=d_l, key="a_l", disabled=True)
    else:
        a_s = st.number_input("Surplus ($)", 0.0, key="a_s")
        a_i = st.number_input("Interest ($)", 0.0, key="a_i")
        a_l = st.number_input("Less ($)", 0.0, key="a_l")

    actual_other = a_s + a_i - a_l
    st.write(f"Total: ${actual_other:,.2f}")

# =========================
# TOTAL INCOME + BENEFIT
# =========================
st.subheader("TOTAL INCOME")

c1, _, c2 = st.columns([1,0.3,1])

with c1:
    declared_total_income = declared_net + declared_other
    declared_benefit = declared_total - declared_total_income

    st.write(f"Total Income: ${declared_total_income:,.2f}")
    st.write(f"Benefit: ${declared_benefit:,.2f}")

with c2:
    actual_total_income = actual_net + actual_other
    actual_benefit = actual_total - actual_total_income

    st.write(f"Total Income: ${actual_total_income:,.2f}")
    st.write(f"Benefit: ${actual_benefit:,.2f}")

# =========================
# FINAL
# =========================
st.divider()

issued = st.number_input("Benefits Issued ($)", 0.0)
overpayment = issued - actual_benefit

st.write(f"OVERPAYMENT: ${overpayment:,.2f}")
