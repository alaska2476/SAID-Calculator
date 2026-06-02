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

Reference["Benefit Type"] = Reference["Benefit"].str.upper().str.strip()
Reference["Tier"] = Reference["Tier"].fillna("ALL").str.upper()
Reference["Amount"] = Reference["Amount"].astype(float)

# =========================
#  UNIVERSAL GROUPING LOGIC
# =========================
def assign_group(b):

        if "LIVING INCOME" in b:
        return "LIVING"
        
         if "SPECIAL CARE" in b:
        return "S/C/H"
     
        if "CLOTHING" in b:
        return "CLOTHING"

        if "LAUNDRY" in b:
        return "LAUNDRY"

        if "PERSONAL CARE" in b:
        return "P/C HOME"

    if "TRUST" in b or "SN/TRUS" in b:
        return "SN/TRUS"

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
        (Reference["Group"] == group) &   # ✅ key change
        ((Reference["Tier"] == tier) | (Reference["Tier"] == "ALL")) &
        ((Reference["Adults"] == adults) | (Reference["Adults"].isna())) &
        (Reference["Children"] == children) &
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
community = c3.selectbox("Community", Community["Community"].unique())

month = c4.selectbox("Benefit Month", [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
])

year = c5.selectbox("Benefit Year", list(range(2020, 2027)))

adults = c6.selectbox("Adults", list(range(1,6)))
children = c7.selectbox("Children", list(range(1,27)))

same = st.checkbox("Same as Declared", value=True)

# =========================
# BENEFIT TABLE
# =========================
def build_table(prefix):
    total = 0

    # ✅ use GROUP instead of Benefit Type
    benefits = sorted(Reference["Group"].unique())

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
