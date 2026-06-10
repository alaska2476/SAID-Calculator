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
# TABLE BUILDER
# =========================
def build_table(prefix):
    total = 0
    benefits = sorted(Reference["Group"].unique())

    for i in range(6):
        c1, c2 = st.columns(2)
        b = c1.selectbox("", [""] + benefits + ["OTHER"], key=f"{prefix}_b_{i}")

        if b == "OTHER":
            for j in range(5):
                c3, c4 = st.columns(2)
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
col1, _, col2 = st.columns([1,0.3,1])

with col1:
    declared_total = build_table("d")
    st.markdown(f"### Total Declared: ${declared_total:,.2f}")

with col2:
    actual_total = declared_total
    st.markdown(f"### Total Actual: ${actual_total:,.2f}")

# =========================
# INCOME
# =========================
st.divider()

declared_net_total = 0
for i in range(4):
    c1, c2 = st.columns(2)
    net = c1.number_input(f"Net {i}",0.0,key=f"net{i}")
    less = c2.number_input("Less",0.0,key=f"less{i}")
    declared_net_total += (net - less)

declared_total_income = declared_net_total

# =========================
# FINAL
# =========================
actual_budget = actual_total - declared_total_income

issued = st.number_input("Benefits Issued ($)",0.0)
overpayment = issued - actual_budget

st.markdown(f"### OVERPAYMENT: ${overpayment:,.2f}")

# =========================
# SAVE
# =========================
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=[
        "Client","Case","Month","Year","Overpayment"
    ])

if st.button("Save Month Calculation"):

    new_row = pd.DataFrame([{
        "Client": client,
        "Case": case,
        "Month": month,
        "Year": year,
        "Overpayment": overpayment
    }])

    hist = st.session_state.history.copy()
    hist = hist[
        ~(
            (hist["Client"] == client) &
            (hist["Case"] == case) &
            (hist["Month"] == month) &
            (hist["Year"] == year)
        )
    ]

    st.session_state.history = pd.concat([hist, new_row], ignore_index=True)

# =========================
# DISPLAY + CUMULATIVE
# =========================
if len(st.session_state.history) > 0:

    df = st.session_state.history.copy()

    df["Month_Num"] = pd.to_datetime(df["Month"], format="%B").dt.month
    df = df.sort_values(["Client","Case","Year","Month_Num"])

    df = df[(df["Client"] == client) & (df["Case"] == case)]

    if len(df) > 0:

        df["Cumulative Overpayment"] = df["Overpayment"].cumsum()

        st.subheader("Client Summary")
        st.dataframe(df.drop(columns=["Month_Num"]), use_container_width=True)

        # ✅ SHOW TOTAL
        total = df["Cumulative Overpayment"].iloc[-1]

        st.subheader("Accumulated Overpayment / Underpayment")
        label = "Overpayment" if total > 0 else "Underpayment"
        st.metric(label, f"${total:,.2f}")

        # ✅ DOWNLOAD WITH TOTAL ROW
        export_df = df.drop(columns=["Month_Num"]).copy()

        summary_row = pd.DataFrame([{col: "" for col in export_df.columns}])
        summary_row.loc[0, "Month"] = "TOTAL"
        summary_row.loc[0, "Cumulative Overpayment"] = total

        export_df = pd.concat([export_df, summary_row], ignore_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False)

        st.download_button("Download Summary", output.getvalue(), "summary.xlsx")
