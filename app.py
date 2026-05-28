import streamlit as st
import pandas as pd
import os
import io

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    ref = pd.read_excel("Reference.xlsx")
    com = pd.read_excel("Community.xlsx")

    ref.columns = ["Benefit Type", "Start Date", "End Date", "Tier", "Amount"]

    ref["Start Date"] = pd.to_datetime(ref["Start Date"])
    ref["End Date"] = pd.to_datetime(ref["End Date"])
    ref["Benefit Type"] = ref["Benefit Type"].str.upper().str.strip()
    ref["Tier"] = ref["Tier"].str.upper().str.strip()
    ref["Amount"] = ref["Amount"].replace(r'[\$,]', '', regex=True).astype(float)

    com["Tier"] = com["Tier"].str.upper().str.strip()

    return ref, com

Reference, Community = load_data()

# =========================
# FUNCTIONS
# =========================
def get_tier(comm):
    t = Community.loc[Community["Community"] == comm, "Tier"]
    return t.values[0] if len(t) > 0 else "D"

def get_amounts(comm, benefit, year, month):
    if benefit in ["", "OTHER", None]:
        return []

    tier = get_tier(comm)
    input_date = pd.to_datetime(f"{year} {month} 01", format="%Y %B %d")

    df = Reference[
        (Reference["Benefit Type"] == benefit) &
        (Reference["Tier"] == tier) &
        (Reference["Start Date"] <= input_date) &
        (Reference["End Date"] >= input_date)
    ]

    return sorted(df["Amount"].unique())

# =========================
# SESSION STATE
# =========================
if "declared_df" not in st.session_state:
    st.session_state.declared_df = pd.DataFrame({
        "Benefit Type": [""] * 6,
        "Amount": [0.0] * 6
    })

if "actual_df" not in st.session_state:
    st.session_state.actual_df = pd.DataFrame({
        "Benefit Type": [""] * 6,
        "Amount": [0.0] * 6
    })

if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame()

# =========================
# HEADER
# =========================
st.title("CALCULATIONS FOR COURT PURPOSES")

cols = st.columns(5)

client = cols[0].text_input("Client")
case = cols[1].text_input("Case #")
community = cols[2].selectbox("Community", Community["Community"].unique())

month_names = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

month = cols[3].selectbox("Benefit Month", month_names)
year = cols[4].selectbox("Benefit Year", sorted(Reference["Start Date"].dt.year.unique()))

same = st.checkbox("Same as Declared", value=True)

# =========================
# TABLE BUILDER
# =========================
def build_table(state_key):

    benefit_list = sorted(Reference["Benefit Type"].unique())
    df = st.session_state[state_key]

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        column_config={
            "Benefit Type": st.column_config.SelectboxColumn(
                "Benefit Type",
                options=benefit_list + ["OTHER"]
            ),
            "Amount": st.column_config.NumberColumn(
                "Amount",
                min_value=0.0,
                step=0.01
            )
        },
        key=state_key
    )

    # ✅ Auto-fill only if empty
    for i, row in edited.iterrows():
        benefit = row["Benefit Type"]
        amount = row["Amount"]

        if benefit and (amount == 0 or pd.isna(amount)):
            opts = get_amounts(community, benefit, year, month)
            if len(opts) > 0:
                edited.at[i, "Amount"] = opts[0]

    st.session_state[state_key] = edited

    return edited["Amount"].sum()

# =========================
# DECLARED / ACTUAL
# =========================
col1, spacer, col2 = st.columns([1, 0.3, 1])

with col1:
    st.subheader("Declared")
    declared_total = build_table("declared_df")

with col2:
    st.subheader("Actual")

    if same:
        actual_total = declared_total
        st.info("Actual = Declared")
    else:
        actual_total = build_table("actual_df")

# =========================
# TOTALS
# =========================
col1b, spacer2, col2b = st.columns([1, 0.3, 1])

with col1b:
    st.markdown(f"**Total Declared:** ${declared_total:,.2f}")

with col2b:
    st.markdown(f"**Total Actual:** ${actual_total:,.2f}")

st.divider()

# =========================
# SAVE DATA
# =========================
if st.button("Save Month Calculation"):

    new_row = pd.DataFrame([{
        "Client": client,
        "Case": case,
        "Month": month,
        "Year": year,
        "Total_Declared": declared_total,
        "Total_Actual": actual_total
    }])

    st.session_state.history = pd.concat(
        [st.session_state.history, new_row],
        ignore_index=True
    )

    st.success(f"Saved {client} - {month} {year}")

# =========================
# SUMMARY + DOWNLOAD
# =========================
if len(st.session_state.history) > 0:

    df = st.session_state.history.copy()

    st.dataframe(df, use_container_width=True)

    output = io.BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    st.download_button(
        label="📥 Download Summary",
        data=output,
        file_name="summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
