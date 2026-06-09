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
    if "ROOM" in b: return "BOARD & ROOM"
    return b

Reference["Group"] = Reference["Benefit Type"].apply(assign_group)

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

c1,c2,c3,c4,c5 = st.columns(5)
client = c1.text_input("Client")
case = c2.text_input("Case #")
community = c3.selectbox("Community", Community["Community"].unique())
month = c4.selectbox("Month", ["January","February","March","April"])
year = c5.selectbox("Year", [2024,2025,2026])

# =========================
# BENEFITS
# =========================
def build_table(prefix):
    total = 0
    benefits = sorted(Reference["Group"].unique())

    for i in range(6):
        c1,c2 = st.columns(2)
        b = c1.selectbox("", [""]+benefits, key=f"{prefix}_{i}")

        if b:
            opts = get_amounts(community,b,year,month)
            val = c2.selectbox("",opts,key=f"{prefix}_amt_{i}") if opts else 0
            total += float(val)

    return total

col1,_,col2 = st.columns([1,0.3,1])

with col1:
    st.subheader("Declared")
    declared_total = build_table("d")

with col2:
    st.subheader("Actual")
    same_actual = st.checkbox("Same as Declared")

    if same_actual:
        actual_total = declared_total
    else:
        actual_total = build_table("a")

st.divider()

# =========================
# ✅ INCOME HEADER + TOGGLE INLINE
# =========================
c1,c2 = st.columns([0.7,0.3])

with c1:
    st.subheader("INCOME")

with c2:
    same_actual = st.checkbox("Same as Declared", value=True, key="top_same")

col1_inc,_,col2_inc = st.columns([1,0.3,1])

# Declared Income
with col1_inc:
    declared_net_total = 0
    for i in range(4):
        c1,c2 = st.columns(2)
        net = c1.number_input(f"Net {i+1}",0.0,key=f"net{i}")
        less = c2.number_input("Less",0.0,key=f"less{i}")
        declared_net_total += net-less

# Other Income
with col2_inc:
    same_income = st.checkbox("Same as Declared Income", True)

    if same_income:
        other_income_total = 0
    else:
        other_income_total = 0

        # Surplus
        c1,c2 = st.columns(2)
        s = c1.number_input("Surplus",0.0)
        l = c2.number_input("Less",0.0)
        other_income_total += s-l

        # Interest
        c3,c4 = st.columns(2)
        i = c3.number_input("Interest",0.0)
        l2 = c4.number_input("Less",0.0)
        other_income_total += i-l2

        # Others
        for i in range(3):
            c5,c6 = st.columns(2)
            v = c5.number_input(f"Other {i+1}",0.0,key=f"o{i}")
            l = c6.number_input("Less",0.0,key=f"ol{i}")
            other_income_total += v-l

declared_total_income = declared_net_total + (0 if same_income else other_income_total)
declared_benefit = declared_total - declared_net_total
actual_budget = actual_total - declared_total_income

st.markdown(f"### Benefit: ${declared_benefit:,.2f}")

st.markdown("**Benefits Issued ($)**")
issued = st.number_input("",0.0)

overpayment = issued - actual_budget
st.markdown(f"### OVERPAYMENT: ${overpayment:,.2f}")

# =========================
# SAVE + DOWNLOAD
# =========================
if "history" not in st.session_state:
    st.session_state.history=pd.DataFrame()

if st.button("Save"):
    row = pd.DataFrame([{
        "Client":client,
        "Month":month,
        "Year":year,
        "Overpayment":overpayment
    }])

    st.session_state.history = pd.concat(
        [st.session_state.history,row],
        ignore_index=True
    )

if len(st.session_state.history)>0:
    st.dataframe(st.session_state.history)

    output=io.BytesIO()
    with pd.ExcelWriter(output,engine='openpyxl') as writer:
        st.session_state.history.to_excel(writer,index=False)

    st.download_button("Download",output.getvalue(),"summary.xlsx")
