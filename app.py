import streamlit as st
import pandas as pd
import os
import io 

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
# GROUPING
# =========================
def assign_group(b):
    if "ADULTS VISITING" in b: return "F/ADULT"
    if "APPROVED HOME" in b: return "AP/HOME"
    if "BASIC ALLOWANCE" in b: return "BASC/AL"
    if "BOARD & ROOM" in b: return "B+C/+CC"   
    if "EXCESS" in b: return "C.T.R."
    if "CHILD BENEFIT" in b: return "SN/CHILD"
    if "CLOTHING" in b: return "CLOTHING"
    if "DISABILITY ALLOWANCE" in b: return "DIS/ALL"     
    if "LIVING" in b: return "LIVING"
    if "HOME HEATING/ENERGY" in b: return "ENERGY"
    if "EDUCATION AND TRAINING" in b: return "EDUC-TI"
    if "EDUCATION EXPENSES AGE" in b: return "SN/EDUC"    
    if "FAMILY HOMES" in b: return "FA HOME"
    if "EDUCATION" in b: return "EDUCATION"
    if "LAUNDRY" in b: return "SN/LAUD"
    if "MEALS AT HOME" in b: return "MEAL/HO" 
    if "MEALS AWAY" in b: return "MEAL/AW"
    if "PERSONAL CARE" in b: return "P/C HOME" 
    if "SALVATION" in b: return "S/A-A/R"
    if "SANCTUARY" in b: return "B&R/SH"  
    if "SHELTER" in b: return "SHELTER"    
    if "SPECIAL CARE" in b: return "S/C/H"
    if "SINGLE PARENT HOME" in b: return "SP/RES"
    if "TRAINING" in b: return "SN/TRAL"
    if "YWCA" in b: return "YWCA PA" 
    return b

Reference["Group"] = Reference["Benefit Type"].apply(assign_group)

# =========================
# FUNCTIONS
# =========================
def get_tier(comm):
    t = Community.loc[Community["Community"] == comm, "Tier"]
    return t.values[0] if len(t) > 0 else "D"

def get_amounts(comm, group, year, month):
    tier = get_tier(comm)
    date = pd.to_datetime(f"{year} {month} 01")

    df = Reference[
        (Reference["Group"] == group) &
        ((Reference["Tier"] == tier) | (Reference["Tier"] == "ALL")) &
        (Reference["Start_Date"] <= date) &
        (Reference["End_Date"] >= date)
    ]

    return sorted(df["Amount"].dropna().unique())

# ✅ FINAL FIXED FILTER FUNCTION
def get_filtered_benefits(comm, year, month):
    tier = get_tier(comm)
    date = pd.to_datetime(f"{year} {month} 01")

    df = Reference[
        ((Reference["Tier"] == tier) | (Reference["Tier"] == "ALL")) &
        (Reference["Start_Date"] <= date) &
        (Reference["End_Date"] >= date)
    ]

    # ✅ ONLY keep groups that actually exist AFTER filtering AND have amounts
    valid_groups = []

    for grp in df["Group"].dropna().unique():
        sub = df[df["Group"] == grp]
        if not sub["Amount"].dropna().empty:
            valid_groups.append(grp)

    return sorted(valid_groups)

# =========================
# HEADER
# =========================
st.title("SAID TRANSITION CALCULATOR")

cols = st.columns(7)
client = cols[0].text_input("Client")
case = cols[1].text_input("Case #")
community = cols[2].selectbox("Community", Community["Community"].unique())
month = cols[3].selectbox("Month", ["January","February","March","April","May","June","July","August","September","October","November","December"])
year = cols[4].selectbox("Year", list(range(2020, 2027)))
adults = cols[5].selectbox("Adults", list(range(1,6)))
children = cols[6].selectbox("Children", list(range(0,27)))

# =========================
# TABLE BUILDER (CORRECTED)
# =========================
def build_table(prefix):
    total = 0

    # ✅ FILTERED BENEFITS BASED ON COMMUNITY + MONTH + YEAR
    benefits = get_filtered_benefits(community, year, month)

    for i in range(6):
        c1, c2 = st.columns(2)

        b = c1.selectbox(
            "",
            [""] + benefits + ["OTHER"],
            key=f"{prefix}_b_{i}",
            index=0
        )

        # ✅ Prevent stale selections
        if b not in benefits + ["", "OTHER"]:
            b = ""

        if b == "OTHER":
            for j in range(5):
                c3, c4 = st.columns(2)
                name = c3.text_input("", key=f"{prefix}_name_{i}_{j}")
                val = c4.number_input("Amount", 0.0, key=f"{prefix}_val_{i}_{j}")
                if name.strip():
                    total += val
        else:
            opts = get_amounts(community, b, year, month)

            if opts:
                val = c2.selectbox("", opts, key=f"{prefix}_amt_{i}", index=0)
            else:
                val = c2.number_input("Amount", 0.0, key=f"{prefix}_num_{i}")

            total += float(val)

    return total

# =========================
# BENEFITS
# =========================
h1, _, h2 = st.columns([1,0.3,1])
with h1: st.subheader("Declared")
with h2: st.subheader("Actual")

_, _, cb = st.columns([1,0.3,1])
with cb:
    same_actual = st.checkbox("Same as Declared", True)

col1,_,col2 = st.columns([1,0.3,1])

with col1:
    declared_total = build_table("d")
    st.markdown(f"### Total Declared: ${declared_total:,.2f}")

with col2:
    actual_total = declared_total if same_actual else build_table("a")
    if same_actual:
        st.info("Using declared values")
    st.markdown(f"### Total Actual: ${actual_total:,.2f}")
