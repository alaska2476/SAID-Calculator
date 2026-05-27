import streamlit as st
import pandas as pd
import os

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide")

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
# TABLE FUNCTION (FINAL FIX)
# =========================
def build_table(prefix):

    rows = 6
    total = 0
    benefit_list = sorted(Reference["Benefit Type"].unique())

    st.markdown("**Benefit | Amount**")

    for i in range(rows):

        col1, col2 = st.columns([1,1])

        benefit = col1.selectbox(
            "",
            [""] + benefit_list + ["OTHER"],
            key=f"{prefix}_benefit_{i}"
        )

        # ✅ HANDLE OTHER
        if benefit == "OTHER":
            val = col2.number_input(
                "Amount ($)",
                value=0.0,
                key=f"{prefix}_other_{i}"
            )
            total += val
            continue

        options = get_amounts(community, benefit, year, month)

        amount_key = f"{prefix}_amount_{i}"

        # ✅ Initialize state
        if amount_key not in st.session_state:
            st.session_state[amount_key] = 0.0

        # ✅ DROPDOWN (selection only)
        selected = col2.selectbox(
            "",
            [""] + [f"{x:.2f}" for x in options],
            key=f"{prefix}_dropdown_{i}"
        )

        # ✅ APPLY dropdown BEFORE input logic
        if selected != "":
            st.session_state[amount_key] = float(selected)

        # ✅ SINGLE INPUT FIELD (MAIN FIELD)
        val = col2.number_input(
            "",
            step=0.01,
            key=amount_key
        )

        total += val

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

net_income = c1.number_input("Net Income ($)", 0.00)
less_exemption = c2.number_input("Less Exemption ($)", 0.00)

net_result = net_income - less_exemption
c3.markdown(f"**Net After Exemptions:** ${net_result:,.2f}")

# =========================
# OTHER INCOME
# =========================
st.subheader("Other Income")

c1, c2, c3 = st.columns(3)

surplus = c1.number_input("Surplus ($)", 0.00)
interest = c2.number_input("Interest income ($)", 0.00)
other_less = c3.number_input("Less Exemption ($)", 0.00)

total_other = surplus + interest - other_less
st.markdown(f"**Total Other Income:** ${total_other:,.2f}")

# =========================
# FINAL CALC
# =========================
chargeable = net_result + total_other

c1, c2, c3 = st.columns(3)

c1.markdown(f"**Chargeable Income:** ${chargeable:,.2f}")

budget = actual_total - chargeable
c2.markdown(f"**Budget deficit/surplus:** ${budget:,.2f}")

benefits_issued = c3.number_input("Benefits Issued ($)", 0.00)

overpayment = benefits_issued - budget

c1, c2 = st.columns(2)

c1.markdown(f"**OVERPAYMENT:** ${overpayment:,.2f}")
fraud = c2.number_input("Fraud Overpayment ($)", 0.00)
