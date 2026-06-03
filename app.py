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
    if group in ["", "OTHER"]:
        return []

    tier = get_tier(comm)
    date = pd.to_datetime(f"{year} {month} 01")

    df = Reference[
        (Reference["Group"] == group) &
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
# BENEFITS
# =========================
def build_table(prefix):
    total = 0
    benefits = sorted(Reference["Group"].unique())

    for i in range(6):
        c1,c2 = st.columns(2)
        b = c1.selectbox("", [""] + benefits + ["OTHER"], key=f"{prefix}_b_{i}")

        if b == "OTHER":
            for j in range(5):
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

st.divider()

# =========================
# INCOME
# =========================
st.subheader("INCOME")

income_same = st.checkbox("Same as Declared Income", value=True)

col1_inc,_,col2_inc = st.columns([1, 0.3, 1])

with col1_inc:
    st.markdown("**Declared Income**")
    declared_net_total = 0

    for i in range(4):
        c1,c2 = st.columns(2)
        net_val = c1.number_input(f"Net Income {i+1} ($)", 0.0, key=f"d_net_{i}")
        less_val = c2.number_input(f"Less Exemption {i+1} ($)", 0.0, key=f"d_less_{i}")
        declared_net_total += (net_val - less_val)

    st.markdown(f"**Net Income: ${declared_net_total:,.2f}**")

with col2_inc:
    st.markdown("**Other Income**")

    if income_same:
        other_income_total = 0
        st.info("Other Income matches declared")
    else:
        o_s = st.number_input("Surplus ($)", 0.0)
        o_i = st.number_input("Interest", 0.0)
        o_l = st.number_input("Less", 0.0)

        other_income_total = o_s + o_i - o_l
        st.markdown(f"**Total Other Income: ${other_income_total:,.2f}**")

# =========================
# FINAL
# =========================
declared_total_income = declared_net_total + (0 if income_same else other_income_total)

declared_benefit = declared_total - declared_net_total
actual_budget = actual_total - declared_total_income

st.markdown(f"### Benefit: ${declared_benefit:,.2f}")

# =========================
# OVERPAYMENT
# =========================
st.divider()

st.markdown("**Benefits Issued ($)**")
issued = st.number_input("", 0.0)

overpayment = issued - actual_budget
st.markdown(f"### OVERPAYMENT: ${overpayment:,.2f}")

# =========================
# SAVE + DOWNLOAD
# =========================
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame()

if st.button("Save Month Calculation"):
    new_row = pd.DataFrame([{
        "Client": client,
        "Case": case,
        "Month": month,
        "Year": year,

        "Declared_Total_Needs": declared_total,
        "Declared_Net_Income": declared_net_total,
        "Declared_Other_Income": (0 if income_same else other_income_total),
        "Declared_Total_Income": declared_total_income,
        "Declared_Benefit": declared_benefit,

        "Actual_Total_Needs": actual_total,
        "Actual_Total_Income": declared_total_income,
        "Budget_Deficit_Surplus": actual_budget,

        "Benefits_Issued": issued,
        "Overpayment": overpayment
    }])

    st.session_state.history = pd.concat(
        [st.session_state.history, new_row],
        ignore_index=True
    )

    st.success(f"Saved {client} - {month} {year}")

# =========================
# DISPLAY + DOWNLOAD
# =========================
if len(st.session_state.history) > 0:

    st.dataframe(st.session_state.history)

    total = st.session_state.history["Overpayment"].sum()
    st.markdown(f"**Total Overpayment: ${total:,.2f}**")

    # Excel Download
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state.history.to_excel(
            writer,
            index=False,
            sheet_name="SAID Calculations"
        )

    st.download_button(
        label="Download Summary",
        data=output.getvalue(),
        file_name=f"{client}_{month}_{year}_SAID.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
