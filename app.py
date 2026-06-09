import streamlit as st
import pandas as pd
import os
import io

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
# GROUPING
# =========================
def assign_group(b):
    if "LIVING" in b: return "LIVING"
    if "APPROVED HOME" in b: return "APPROVED HOME"
    if "CLOTHING" in b: return "CLOTHING"
    if "SPECIAL CARE" in b: return "S/C/H"
    if "ROOM" in b: return "BOARD & ROOM"
    if "TRUST" in b or "SN/TRUS" in b: return "SN/TRUS"
    if "CHILD BENEFIT" in b: return "CHILD BENEFIT"
    if "DISABILITY ALLOWANCE" in b: return "DIS/ALL"
    if "FAMILY HOMES" in b: return "FAMILY HOMES"
    if "EDUCATION" in b: return "EDUCATION"
    if "HOUSEHOLD ALLOWANCE" in b: return "HOUSEHOLD ALLOWANCE"
    if "LAUNDRY" in b: return "LAUNDRY"
    if "MEALS" in b: return "MEALS"
    if "PERSONAL CARE" in b: return "PC/HOME"
    if "SALVATION ARMY" in b: return "SALVATION ARMY"
    if "SINGLE PARENT HOME" in b: return "SINGLE PARENT HOME"
    if "TRAINING" in b: return "TRAINING"
    if "YWCA" in b: return "YWCA"
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

# =========================
# HEADER
# =========================
st.title("SAID TRANSITION CALCULATOR")

c1,c2,c3,c4,c5,c6,c7 = st.columns(7)

client = c1.text_input("Client")
case = c2.text_input("Case #")
community = c3.selectbox("Community", Community["Community"].unique())
month = c4.selectbox("Benefit Month", ["January","February","March","April","May","June","July","August","September","October","November","December"])
year = c5.selectbox("Benefit Year", list(range(2020, 2027)))
adults = c6.selectbox("Adults", list(range(1,6)))
children = c7.selectbox("Children", list(range(0,27)))

# =========================
# TABLE BUILDER
# =========================
def build_table(prefix):
    total = 0
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
            val = c2.selectbox("", opts, key=f"{prefix}_amt_{i}") if opts else c2.number_input("Amount ($)", 0.0, key=f"{prefix}_num_{i}")
            total += float(val)

    return total

# =========================
# ✅ BENEFITS (FINAL ALIGNMENT)
# =========================

# Headers
h1, _, h2 = st.columns([1,0.3,1])
with h1: st.subheader("Declared")
with h2: st.subheader("Actual")

# Checkbox ABOVE ACTUAL ONLY
_, _, cb_col = st.columns([1,0.3,1])
with cb_col:
    same_actual = st.checkbox("Same as Declared", True)

# Data
col1,_,col2 = st.columns([1,0.3,1])
with col1:
    declared_total = build_table("d")
    st.markdown(f"### Total Declared: ${declared_total:,.2f}")
with col2:
    actual_total = declared_total if same_actual else build_table("a")
    if same_actual:
        st.info("Using declared values")
    st.markdown(f"### Total Actual: ${actual_total:,.2f}")

st.divider()

# =========================
# INCOME
# =========================
st.subheader("INCOME")

col1_inc,_,col2_inc = st.columns([1,0.3,1])

with col1_inc:
    st.markdown("**Declared Income**")
    declared_net_total = sum(
        st.columns(2)[0].number_input(f"Net {i}",0.0,key=f"net{i}") -
        st.columns(2)[1].number_input("Less",0.0,key=f"less{i}")
        for i in range(4)
    )

# ✅ OTHER INCOME MATCHED STYLE
h1, h2 = st.columns([1,1])
with h2: st.markdown("**Other Income**")

_, cb2 = st.columns([1,1])
with cb2:
    same_income = st.checkbox("Same as Declared Income", True)

col1_inc,_,col2_inc = st.columns([1,0.3,1])

with col2_inc:
    if same_income:
        other_income_total = 0
        st.info("No additional income")
    else:
        c1,c2 = st.columns(2)
        surplus = c1.number_input("Surplus",0.0)
        less1 = c2.number_input("Less",0.0)
        total = surplus - less1

        c3,c4 = st.columns(2)
        interest = c3.number_input("Interest",0.0)
        less2 = c4.number_input("Less ",0.0)
        total += interest - less2

        for i in range(2):
            c5,c6 = st.columns(2)
            v = c5.number_input(f"Other {i+1}",0.0,key=f"o{i}")
            l = c6.number_input("Less",0.0,key=f"ol{i}")
            total += v - l

        other_income_total = total
        st.markdown(f"**Total Other Income: ${other_income_total:,.2f}**")

# =========================
# FINAL
# =========================
declared_total_income = declared_net_total + (0 if same_income else other_income_total)
actual_budget = actual_total - declared_total_income

st.markdown(f"### Benefit: ${(declared_total - declared_net_total):,.2f}")

# OVERPAYMENT
issued = st.number_input("Benefits Issued ($)",0.0)
overpayment = issued - actual_budget
st.markdown(f"### OVERPAYMENT: ${overpayment:,.2f}")

# SAVE + DOWNLOAD
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame()

if st.button("Save"):
    new = pd.DataFrame([{"Client":client,"Month":month,"Year":year,"Overpayment":overpayment}])
    st.session_state.history = pd.concat([st.session_state.history,new],ignore_index=True)

if len(st.session_state.history)>0:
    st.dataframe(st.session_state.history)

    output = io.BytesIO()
    with pd.ExcelWriter(output,engine='openpyxl') as writer:
        st.session_state.history.to_excel(writer,index=False)

    st.download_button("Download",output.getvalue(),"summary.xlsx")
