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
st.title("CALCULATIONS FOR COURT PURPOSES")

cols = st.columns(5)

client = cols[0].text_input("Client")
case = cols[1].text_input("Case #")
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

        selected = col1.selectbox("", [""] + benefit_list + ["OTHER"], key=f"{prefix}_b_{i}")

        # ✅ OTHER
        if selected == "OTHER":

            col2.write("")

            for j in range(3):
                col1b, col2b = st.columns([1,1])

                benefit = col1b.text_input("", key=f"{prefix}_custom_{i}_{j}")

                amount_val = col2b.number_input(
                    "Amount ($)",
                    value=None,
                    step=0.01,
                    key=f"{prefix}_manual_other_{i}_{j}",
                    format="%.2f"
                )

                if benefit.strip() != "" and amount_val is not None:
                    total += amount_val

        # ✅ NORMAL BENEFIT
        else:

            benefit = selected
            options = get_amounts(community, benefit, year, month)

            if benefit != "" and len(options) > 0:

                display_vals = [f"${x:,.2f}" for x in options]

                suggestion = col2.selectbox(
                    "Suggested Amount",
                    [""] + display_vals,
                    key=f"{prefix}_suggest_{i}"
                )

                manual_input = col2.number_input(
                    "Amount ($)",
                    value=None,
                    step=0.01,
                    key=f"{prefix}_manual_{i}",
                    format="%.2f"
                )

                if manual_input is not None:
                    amount_val = manual_input
                elif suggestion != "":
                    amount_val = float(suggestion.replace("$","").replace(",",""))
                else:
                    amount_val = 0

            else:
                amount_val = col2.number_input(
                    "Amount ($)",
                    value=None,
                    step=0.01,
                    key=f"{prefix}_manual_{i}_{benefit}",
                    format="%.2f"
                )

            if amount_val is not None:
                total += amount_val

    return total

# =========================
# DECLARED & ACTUAL
# =========================
d1, spacer, d2 = st.columns([1, 0.4, 1])

with d1:
    st.subheader("Declared")
    declared_total = build_table("declared")

with d2:
    st.subheader("Actual")

    if same:
        actual_total = declared_total
    else:
        actual_total = build_table("actual")

# =========================
# TOTALS
# =========================
d1a, spacer2, d2a = st.columns([1, 0.4, 1])

with d1a:
    st.markdown(f"**Total Declared:** ${declared_total:,.2f}")

with d2a:
    st.markdown(f"**Total Actual:** ${actual_total:,.2f}")

st.divider()

# =========================
# INCOME
# =========================
st.subheader("INCOME")

c1, c2, c3 = st.columns(3)

net_income = c1.number_input("Net Income ($)", value=None)
less_exemption = c2.number_input("Less Exemption ($)", value=None)

net_result = (net_income or 0) - (less_exemption or 0)

with c3:
    st.markdown("Net After Exemptions")
    st.text_input("", f"${net_result:,.2f}", disabled=True)

# =========================
# FINAL CALCULATIONS
# =========================
chargeable = net_result

c1, c2, c3 = st.columns(3)

c1.markdown(f"**Chargeable Income:** ${chargeable:,.2f}")

budget = actual_total - chargeable
c2.markdown(f"**Budget deficit/surplus:** ${budget:,.2f}")

benefits_issued = c3.number_input("Benefits Issued ($)", value=None)

overpayment = (benefits_issued or 0) - budget

c1, c2 = st.columns(2)

c1.markdown(f"**OVERPAYMENT:** ${overpayment:,.2f}")
fraud = c2.number_input("Fraud Overpayment ($)", value=None)
