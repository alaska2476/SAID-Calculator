import streamlit as st
import pandas as pd
import os
import io

# =========================
# CONFIG
# =========================
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

Reference["Group"] = Reference["Benefit Type"]

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

month = c4.selectbox("Month", ["January","February","March","April","May","June","July","August","September","October","November","December"])
year = c5.selectbox("Year", list(range(2020, 2027)))
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
                name = c3.text_input("", key=f"{prefix}_name_{i}_{j}")
                val = c4.number_input("Amount", 0.0, key=f"{prefix}_val_{i}_{j}")
                if name.strip():
                    total += val
        else:
            opts = get_amounts(community, b, year, month)
            val = c2.selectbox("", opts, key=f"{prefix}_amt_{i}") if opts else c2.number_input("Amount", 0.0, key=f"{prefix}_num_{i}")
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

with col2:
    actual_total = declared_total if same_actual else build_table("a")

st.markdown(f"### Total Declared: ${declared_total:,.2f}")
st.markdown(f"### Total Actual: ${actual_total:,.2f}")

st.divider()

# =========================
# INCOME
# =========================
st.subheader("INCOME")

h1, _, h2 = st.columns([1,0.3,1])
with h1: st.markdown("**Declared Income**")
with h2: st.markdown("**Other Income**")

_, _, cb2 = st.columns([1,0.3,1])
with cb2:
    same_income = st.checkbox("Same as Declared Income", True)

col1_inc,_,col2_inc = st.columns([1,0.3,1])

# Declared
with col1_inc:
    declared_net_total = 0
    for i in range(4):
        c1,c2 = st.columns(2)
        declared_net_total += c1.number_input(f"Net {i}",0.0,key=f"net{i}") - c2.number_input("Less",0.0,key=f"less{i}")

# Other
with col2_inc:
    if same_income:
        other_income_total = 0
    else:
        total = 0
        c1,c2 = st.columns(2)
        total += c1.number_input("Surplus",0.0) - c2.number_input("Less",0.0)

        c3,c4 = st.columns(2)
        total += c3.number_input("Interest",0.0) - c4.number_input("Less ",0.0)

        other_income_total = total

# =========================
# FINAL CALC
# =========================
declared_total_income = declared_net_total + (0 if same_income else other_income_total)
declared_benefit = declared_total - declared_net_total
actual_budget = actual_total - declared_total_income

issued = st.number_input("Benefits Issued ($)",0.0)
overpayment = issued - actual_budget

st.markdown(f"### OVERPAYMENT: ${overpayment:,.2f}")

# =========================
# SAVE (FULL + OVERWRITE)
# =========================
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=[
        "Client","Case","Month","Year",
        "Declared_Total_Needs","Declared_Net_Income",
        "Declared_Other_Income","Declared_Total_Income",
        "Declared_Benefit","Actual_Total_Needs",
        "Actual_Total_Income","Budget_Deficit_Surplus",
        "Benefits_Issued","Overpayment"
    ])

if st.button("Save Month Calculation"):

    new_row = pd.DataFrame([{
        "Client": client,
        "Case": case,
        "Month": month,
        "Year": year,
        "Declared_Total_Needs": declared_total,
        "Declared_Net_Income": declared_net_total,
        "Declared_Other_Income": (0 if same_income else other_income_total),
        "Declared_Total_Income": declared_total_income,
        "Declared_Benefit": declared_benefit,
        "Actual_Total_Needs": actual_total,
        "Actual_Total_Income": declared_total_income,
        "Budget_Deficit_Surplus": actual_budget,
        "Benefits_Issued": issued,
        "Overpayment": overpayment
    }])

    history = st.session_state.history.copy()

    if not history.empty:
        mask = (
            (history["Client"] == client) &
            (history["Case"] == case) &
            (history["Month"] == month) &
            (history["Year"] == year)
        )
        history = history[~mask]

    st.session_state.history = pd.concat([history, new_row], ignore_index=True)

# =========================
# DISPLAY + DOWNLOAD
# =========================
if len(st.session_state.history) > 0:
    st.dataframe(st.session_state.history)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state.history.to_excel(writer, index=False)

    st.download_button("Download Summary", output.getvalue(), "SAID_Summary.xlsx")
