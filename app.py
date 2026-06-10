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
    if "TRAINING" in b: return "TRAINING"
    if "SINGLE PARENT HOME" in b: return "SINGLE PARENT"
    if "PERSONAL CARE" in b: return "PERSONAL CARE HOME"
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

cols = st.columns(7)
client = cols[0].text_input("Client")
case = cols[1].text_input("Case #")
community = cols[2].selectbox("Community", Community["Community"].unique())
month = cols[3].selectbox("Month", [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
])
year = cols[4].selectbox("Year", list(range(2020, 2027)))
adults = cols[5].selectbox("Adults", list(range(1,6)))
children = cols[6].selectbox("Children", list(range(1,27)))

# =========================
# SIMPLIFIED CALCULATION INPUTS
# =========================
declared_total = st.number_input("Total Declared", 0.0)
actual_total = st.number_input("Total Actual", 0.0)
declared_net_total = st.number_input("Net Income", 0.0)
other_income_total = st.number_input("New Income", 0.0)

declared_total_income = declared_net_total + other_income_total
declared_benefit = declared_total - declared_net_total
actual_budget = actual_total - declared_total_income

issued = st.number_input("Benefits Issued ($)",0.0)
overpayment = issued - actual_budget

# ✅ CURRENT LABEL
if overpayment > 0:
    label = "OVERPAYMENT"
else:
    label = "UNDERPAYMENT"

st.markdown(f"### {label}: ${overpayment:,.2f}")

# =========================
# SAVE DATA
# =========================
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=[
        "Client","Case","Month","Year",
        "Total Declared","Net Income","New Income","Total Income",
        "Benefit","Total Actual","Actual Income",
        "Budget Deficit / Surplus","Benefits Issued",
        "Overpayment / Underpayment"
    ])

if st.button("Save Month Calculation"):

    new_row = pd.DataFrame([{
        "Client": client,
        "Case": case,
        "Month": month,
        "Year": year,
        "Total Declared": declared_total,
        "Net Income": declared_net_total,
        "New Income": other_income_total,
        "Total Income": declared_total_income,
        "Benefit": declared_benefit,
        "Total Actual": actual_total,
        "Actual Income": declared_total_income,
        "Budget Deficit / Surplus": actual_budget,
        "Benefits Issued": issued,
        "Overpayment / Underpayment": overpayment
    }])

    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
    st.success("Saved")

# =========================
# DISPLAY + EXPORT
# =========================
if len(st.session_state.history) > 0:

    st.dataframe(st.session_state.history)

    output = io.BytesIO()
    export_df = st.session_state.history.copy()

    total = export_df["Overpayment / Underpayment"].sum()

    if total > 0:
        total_text = "TOTAL OVERPAYMENT"
    else:
        total_text = "TOTAL UNDERPAYMENT"

    summary_row = {col: None for col in export_df.columns}
    summary_row[export_df.columns[0]] = total_text
    summary_row["Overpayment / Underpayment"] = float(total)

    export_df = pd.concat([export_df, pd.DataFrame([summary_row])], ignore_index=True)

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False)

    safe_client = client.replace(" ","_") if client else "Client"
    safe_case = case.replace(" ","_") if case else "Case"

    st.download_button(
        "Download Summary",
        output.getvalue(),
        f"{safe_client}_{safe_case}_summary.xlsx"
    )

    st.subheader(total_text)
    st.metric("", f"${total:,.2f}")
