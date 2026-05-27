import streamlit as st
import pandas as pd
import os

st.set_page_config(layout="wide")

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

cols = st.columns(4)

community = cols[0].selectbox("Community", Community["Community"].unique())
month = cols[1].selectbox("Month", [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
])
year = cols[2].selectbox("Year", sorted(Reference["Start Date"].dt.year.unique()))
same = cols[3].checkbox("Same as Declared", True)

# =========================
# TABLE FUNCTION (KEY FIX)
# =========================
def build_table(prefix):

    rows = 6
    total = 0
    benefit_list = sorted(Reference["Benefit Type"].unique())

    st.markdown("**Benefit | Amount**")

    for i in range(rows):

        col1, col2 = st.columns([1,2])

        benefit = col1.selectbox(
            "",
            [""] + benefit_list,
            key=f"{prefix}_b_{i}"
        )

        options = get_amounts(community, benefit, year, month)

        # ✅ SINGLE INPUT FIELD (MAIN)
        amount_key = f"{prefix}_amount_{i}"

        amount_val = col2.text_input(
            "",
            value=st.session_state.get(amount_key, ""),
            key=amount_key
        )

        # ✅ DROPDOWN AS BUTTONS (fills SAME FIELD)
        if len(options) > 0:
            btn_cols = col2.columns(len(options))

            for idx, val in enumerate(options):
                if btn_cols[idx].button(f"{val:.2f}", key=f"{prefix}_btn_{i}_{idx}"):
                    st.session_state[amount_key] = str(val)

        # ✅ convert to float
        try:
            total += float(amount_val)
        except:
            pass

    return total

# =========================
# DISPLAY
# =========================
d1, d2 = st.columns(2)

with d1:
    st.subheader("Declared")
    declared_total = build_table("declared")

with d2:
    st.subheader("Actual")
    actual_total = build_table("actual")

st.markdown(f"### Total Declared: ${declared_total:,.2f}")
st.markdown(f"### Total Actual: ${actual_total:,.2f}")
