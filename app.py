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
    return b

Reference["Group"] = Reference["Benefit Type"].apply(assign_group)

# =========================
# ✅ SWIN LOAD
# =========================
def load_swin_case(case):
    base_path = r"G:\SMB\Common\EABI\Data Science\02_Projects and Working Files\42-SAID Calculator Project\SWIN DATA"

    if not case:
        return None

    case_clean = str(case).strip()
    file_path = os.path.join(base_path, f"{case_clean}.xlsx")

    if os.path.exists(file_path):
        return pd.read_excel(file_path, engine="openpyxl")
    else:
        st.warning(f"⚠️ No SWIN file found for case: {case_clean}")
        return None

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
children = cols[6].selectbox("Children", list(range(1,27)))

# =========================
# LOAD SWIN DATA
# =========================
swin_data = load_swin_case(case)

declared_dict = {}

if swin_data is not None:
    case_clean = str(case).strip()
    swin_data["Case"] = swin_data["Case"].astype(str).str.strip()

    case_data = swin_data[swin_data["Case"] == case_clean]

    if not case_data.empty:
        needs_df = case_data[case_data["Field_Group"] == "NEEDS"]
        declared_dict = dict(zip(needs_df["Field_Name"], needs_df["Value"]))

        st.success("✅ SWIN data loaded successfully")

# =========================
# TABLE BUILDER
# =========================
def build_table(prefix):
    total = 0
    benefits = sorted(Reference["Group"].unique())

    excel_items = list(declared_dict.items()) if prefix == "d" else []

    for i in range(6):
        c1, c2 = st.columns(2)

        options = [""] + benefits + ["OTHER"]

        # ✅ AUTO SELECT FROM EXCEL
        if prefix == "d" and i < len(excel_items):
            benefit_name = excel_items[i][0]
            default_index = options.index(benefit_name) if benefit_name in options else 0
        else:
            default_index = 0

        b = c1.selectbox("", options, index=default_index, key=f"{prefix}_b_{i}")

        if prefix == "d" and b in declared_dict:
            val = float(declared_dict[b])
            c2.number_input("Amount", value=val, key=f"{prefix}_auto_{i}", disabled=True)
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
# FINAL
# =========================
issued = st.number_input("Benefits Issued ($)",0.0)

overpayment = issued - actual_total
label = "OVERPAYMENT" if overpayment > 0 else "UNDERPAYMENT"

st.markdown(f"### {label}: ${overpayment:,.2f}")

# =========================
# SAVE + DOWNLOAD
# =========================
required_columns = [
    "Client","Case","Month","Year",
    "Total Declared","Total Actual",
    "Benefit","Benefits Issued",
    "Overpayment / Underpayment"
]

if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=required_columns)

if st.button("Save Month Calculation"):
    new_row = pd.DataFrame([{
        "Client": client,
        "Case": case,
        "Month": month,
        "Year": year,
        "Total Declared": declared_total,
        "Total Actual": actual_total,
        "Benefit": declared_total,
        "Benefits Issued": issued,
        "Overpayment / Underpayment": overpayment
    }])

    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
    st.success("✅ Saved")

if len(st.session_state.history) > 0:
    st.dataframe(st.session_state.history)

    output = io.BytesIO()

    export_df = st.session_state.history.copy()
    total = export_df["Overpayment / Underpayment"].sum()

    summary_row = {col: None for col in export_df.columns}
    summary_row["Client"] = "TOTAL"
    summary_row["Overpayment / Underpayment"] = total

    export_df = pd.concat([export_df, pd.DataFrame([summary_row])], ignore_index=True)

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False)

    file_name = f"{client}_{case}_summary.xlsx"
    st.download_button("Download Summary", output.getvalue(), file_name)
