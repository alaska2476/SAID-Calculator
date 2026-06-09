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

cols = st.columns(7)
client = cols[0].text_input("Client")
case = cols[1].text_input("Case #")
community = cols[2].selectbox("Community", Community["Community"].unique())
month = cols[3].selectbox("Month", ["January","February","March","April","May","June","July","August","September","October","November","December"])
year = cols[4].selectbox("Year", list(range(2020, 2027)))
adults = cols[5].selectbox("Adults", list(range(1,6)))
children = cols[6].selectbox("Children", list(range(0,27)))

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
    st.markdown(f"### Total Declared: ${declared_total:,.2f}")

with col2:
    actual_total = declared_total if same_actual else build_table("a")
    if same_actual:
        st.info("Using declared values")
    st.markdown(f"### Total Actual: ${actual_total:,.2f}")

# =========================
# INCOME
# =========================
st.divider()
st.subheader("INCOME")

h1, _, h2 = st.columns([1,0.3,1])
with h1: st.markdown("**Declared Income**")
with h2: st.markdown("**New Income**")

_, _, cb2 = st.columns([1,0.3,1])
with cb2:
    same_income = st.checkbox("Same as Declared Income", True)

col1_inc,_,col2_inc = st.columns([1,0.3,1])

# Declared Income
with col1_inc:
    declared_net_total = 0
    for i in range(4):
        c1,c2 = st.columns(2)
        net = c1.number_input(f"Net {i}",0.0,key=f"net{i}")
        less = c2.number_input("Less",0.0,key=f"less{i}")
        declared_net_total += (net - less)

    st.markdown(f"**Net Income: ${declared_net_total:,.2f}**")

# New Income 
with col2_inc:
    if same_income:
        other_income_total = 0
        st.info("No additional income")
    else:
        total = 0

        #  Surplus
        c1,c2 = st.columns(2)
        s = c1.number_input("Surplus",0.0, key="surplus_val")
        l = c2.number_input("Less",0.0, key="surplus_less")
        total += (s - l)

        #  Interest
        c3,c4 = st.columns(2)
        i_val = c3.number_input("Interest",0.0, key="interest_val")
        l2 = c4.number_input("Less ",0.0, key="interest_less")
        total += (i_val - l2)
        
        c5,c6 = st.columns(2)
        o1 = c5.number_input("Other 1",0.0, key="other1_val")
        o1_less = c6.number_input("Less ",0.0, key="other1_less")
        total += (o1 - o1_less)

        c7,c8 = st.columns(2)
        o2 = c7.number_input("Other 2",0.0, key="other2_val")
        o2_less = c8.number_input("Less ",0.0, key="other2_less")
        total += (o2 - o2_less)

        other_income_total = total

        st.markdown(f"**Total New Income: ${other_income_total:,.2f}**")

# =========================
# FINAL
# =========================
declared_total_income = declared_net_total + (0 if same_income else other_income_total)
declared_benefit = declared_total - declared_net_total
actual_budget = actual_total - declared_total_income

st.markdown(f"### Benefit: ${declared_benefit:,.2f}")

issued = st.number_input("Benefits Issued ($)",0.0)
overpayment = issued - actual_budget
st.markdown(f"### OVERPAYMENT: ${overpayment:,.2f}")

# =========================
# SAVE WITH OVERWRITE
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
    st.success(" Saved (auto-overwrite if exists)")

# =========================
# DISPLAY
# =========================
if len(st.session_state.history) > 0:
    st.dataframe(st.session_state.history)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state.history.to_excel(writer, index=False)

    st.download_button("Download Summary", output.getvalue(), "summary.xlsx")
