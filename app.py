import streamlit as st
import pandas as pd
import os
import io

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide")

st.markdown("""
<style>
.block-container {padding-top:0.8rem; padding-bottom: 0.5rem;}
div.row-widget.stHorizontal {gap: 0.3rem;}
h1 {text-align: center;}
</style>
""", unsafe_allow_html=True)

# =========================
# SAFE LOAD
# =========================
def load_excel_safe(path):
    if os.path.exists(path):
        return pd.read_excel(path)
    else:
        st.error(f"Missing file: {path}")
        st.stop()

# =========================
# LOAD DATA
# =========================
Reference = load_excel_safe("Reference.xlsx")
Community = load_excel_safe("Community.xlsx")
file_path = "monthly_records.xlsx"

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

client = cols[0].text_input("Client", key="client")
case = cols[1].text_input("Case #", key="case")
community = cols[2].selectbox("Community", Community["Community"].unique())

month_names = [
"January","February","March","April","May","June",
"July","August","September","October","November","December"
]

month = cols[3].selectbox("Benefit Month", month_names)
year = cols[4].selectbox("Benefit Year", sorted(Reference["Start Date"].dt.year.unique()))

same = st.checkbox("Same as Declared", value=True)

# =========================
# TABLE FUNCTION
# =========================
def build_table(prefix):
    rows = 6
    total = 0
    benefit_list = sorted(Reference["Benefit Type"].unique())

    st.markdown("**Benefit | Amount**")

    for i in range(rows):

        col1, col2 = st.columns([1,1])

        selected = col1.selectbox(
            "",
            [""] + benefit_list + ["OTHER"],
            key=f"{prefix}_b_{i}"
        )

        if selected == "OTHER":

            col2.write("")

            for j in range(10):
                col1b, col2b = st.columns([1,1])

                benefit = col1b.text_input(
                    "",
                    key=f"{prefix}_custom_{i}_{j}",
                    placeholder=f"Enter new benefit {j+1}"
                ).upper()

                amount_val = col2b.number_input(
                    "Amount ($)",
                    value=0.00,
                    step=0.01,
                    key=f"{prefix}_manual_other_{i}_{j}",
                    format="%.2f"
                )

                if benefit.strip() != "":
                    total += amount_val

        else:
            benefit = selected
            options = get_amounts(community, benefit, year, month)

            if benefit != "" and len(options) > 0:
                display_vals = [f"${x:,.2f}" for x in options]

                selected_amt = col2.selectbox(
                    "",
                    display_vals,
                    key=f"{prefix}_a_{i}"
                )

                amount_val = float(selected_amt.replace("$","").replace(",",""))

            else:
                amount_val = col2.number_input(
                    "Amount ($)",
                    value=0.00,
                    step=0.01,
                    key=f"{prefix}_manual_{i}_{benefit}",
                    format="%.2f"
                )

            total += amount_val

    return total

# =========================
# DECLARED / ACTUAL
# =========================
d1, _, d2 = st.columns([1, 0.4, 1])

with d1:
    st.subheader("Declared")
    declared_total = build_table("declared")

with d2:
    st.subheader("Actual")

    if same:
        actual_total = declared_total
        st.info("Actual total is using Declared total")
    else:
        actual_total = build_table("actual")

# =========================
# TOTALS
# =========================
d1a, _, d2a = st.columns([1, 0.4, 1])

with d1a:
    st.markdown(f"**Total Declared:** ${declared_total:,.2f}")

with d2a:
    st.markdown(f"**Total Actual:** ${actual_total:,.2f}")

st.divider()

# =========================
# INCOME
# =========================
st.subheader("INCOME")

col1_inc, _, col2_inc = st.columns([1, 0.3, 1])

with col1_inc:
    st.markdown("**Declared Income**")
    d_net = st.number_input("Net Income ($)", 0.00, key="d_net")
    d_less = st.number_input("Less Exemption ($)", 0.00, key="d_less")
    declared_net_result = d_net - d_less
    st.markdown(f"**Net:** ${declared_net_result:,.2f}")

with col2_inc:
    st.markdown("**Actual Income**")

    if same:
        actual_net_result = declared_net_result
        st.info("Using Declared Income")
    else:
        a_net = st.number_input("Net Income ($)", 0.00, key="a_net")
        a_less = st.number_input("Less Exemption ($)", 0.00, key="a_less")
        actual_net_result = a_net - a_less
        st.markdown(f"**Net:** ${actual_net_result:,.2f}")

# =========================
# OTHER INCOME
# =========================
st.subheader("OTHER INCOME")

col1_o, spacer_o, col2_o = st.columns([1, 0.3, 1])

# =========================
# DECLARED OTHER INCOME
# =========================
with col1_o:
    st.markdown("**Declared Other Income**")

    d_surplus = st.number_input("Surplus ($)", 0.00, key="d_surplus")
    d_interest = st.number_input("Interest income ($)", 0.00, key="d_interest")
    d_less_other = st.number_input("Less Exemption ($)", 0.00, key="d_less_other")

    declared_other_total = d_surplus + d_interest - d_less_other

    st.markdown(f"**Total Other Income:** ${declared_other_total:,.2f}")

# =========================
# ACTUAL OTHER INCOME
# =========================
with col2_o:
    st.markdown("**Actual Other Income**")

    if same:
        actual_other_total = declared_other_total
        st.info("Using Declared Other Income")
    else:
        a_surplus = st.number_input("Surplus ($)", 0.00, key="a_surplus")
        a_interest = st.number_input("Interest income ($)", 0.00, key="a_interest")
        a_less_other = st.number_input("Less Exemption ($)", 0.00, key="a_less_other")

        actual_other_total = a_surplus + a_interest - a_less_other

        st.markdown(f"**Total Other Income:** ${actual_other_total:,.2f}")
# =========================
# TOTAL INCOME (UNDER EACH SIDE)
# =========================
st.subheader("TOTAL INCOME")

col1_ti, _, col2_ti = st.columns([1, 0.3, 1])

# ✅ Declared side
with col1_ti:
    declared_total_income = declared_net_result + declared_other_total

    st.markdown("**Declared Total Income**")
    st.markdown(f"Net: ${declared_net_result:,.2f}")
    st.markdown(f"Other Income: ${declared_other_total:,.2f}")
    st.markdown(f"✅ **Total Income:** ${declared_total_income:,.2f}")

# ✅ Actual side
with col2_ti:
    actual_total_income = actual_net_result + actual_other_total

    st.markdown("**Actual Total Income**")
    st.markdown(f"Net: ${actual_net_result:,.2f}")
    st.markdown(f"Other Income: ${actual_other_total:,.2f}")
    st.markdown(f"✅ **Total Income:** ${actual_total_income:,.2f}")
# =========================
# FINAL CALCULATIONS
# =========================
chargeable = actual_net_result + actual_other_total

c1, c2, c3 = st.columns(3)

c1.markdown(f"**Chargeable Income:** ${chargeable:,.2f}")

budget = actual_total - chargeable
c2.markdown(f"**Budget deficit/surplus:** ${budget:,.2f}")

benefits_issued = c3.number_input("Benefits Issued ($)", 0.00)

overpayment = benefits_issued - budget

c1, c2 = st.columns(2)

c1.markdown(f"**OVERPAYMENT:** ${overpayment:,.2f}")
fraud = c2.number_input("Fraud Overpayment ($)", 0.00)
