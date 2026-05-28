import streamlit as st
import pandas as pd
import os
import io

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide")

st.markdown("""
<style>
.block-container {padding-top:0.8rem; padding-bottom: 0.5rem;}
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
# INITIAL STATE (CRITICAL FIX)
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

# =========================
# HEADER
# =========================
st.title("CALCULATIONS FOR COURT PURPOSES")

cols = st.columns(5)

client = cols[0].text_input("Client", key="client")
case = cols[1].text_input("Case #", key="case")
community = cols[2].selectbox("Community", Community["Community"].unique(), key="community")

month_names = [
"January","February","March","April","May","June",
"July","August","September","October","November","December"
]

month = cols[3].selectbox("Benefit Month", month_names, key="month")
year = cols[4].selectbox("Benefit Year", sorted(Reference["Start Date"].dt.year.unique()), key="year")

same = st.checkbox("Same as Declared", value=True)

# =========================
# CLEAN TABLE BUILDER (FIXED OVERWRITE LOGIC)
# =========================
def build_table(state_key):

benefit_list = sorted(Reference["Benefit Type"].unique())

df = st.session_state[state_key]

edited_df = st.data_editor(
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

# =========================
# APPLY DEFAULT ONLY IF EMPTY (DO NOT OVERWRITE USER INPUT)
# =========================
for i, row in edited_df.iterrows():

benefit = row["Benefit Type"]
amount = row["Amount"]

if benefit and (amount == 0 or pd.isna(amount)):
options = get_amounts(community, benefit, year, month)

if len(options) > 0:
edited_df.at[i, "Amount"] = options[0]

st.session_state[state_key] = edited_df

return edited_df["Amount"].sum()

# =========================
# DECLARED & ACTUAL
# =========================
d1, spacer, d2 = st.columns([1, 0.4, 1])

with d1:
st.subheader("Declared")
declared_total = build_table("declared_df")

with d2:
st.subheader("Actual")

if same:
actual_total = declared_total
st.info("Actual = Declared")
else:
actual_total = build_table("actual_df")

# =========================
# TOTALS
# =========================
d1a, spacer2, d2a = st.columns([1, 0.4, 1])

with d1a:
st.markdown(f"**Total Declared:** ${declared_total:,.2f}")

# SAVE LOGIC (UNCHANGED BUT SAFE)
df = df[df["Client"].str.strip().str.upper() == client.strip().upper()]

if len(df) > 0:

st.dataframe(df, use_container_width=True)

total = df["Overpayment"].sum()

st.subheader("TOTAL OVERPAYMENT / UNDERPAYMENT ACROSS MONTHS")
st.write(f"${total:,.2f}")

df = df.copy()
df["Month_Num"] = pd.to_datetime(df["Month"], format="%B").dt.month
df = df.sort_values(["Year", "Month_Num"])
df = df.drop(columns=["Month_Num"])

output = io.BytesIO()
df.to_excel(output, index=False, engine='openpyxl')
output.seek(0)

st.download_button(
label="📥 Download Full Client Summary",
data=output,
file_name=f"{client}_FULL_summary.xlsx",
mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

else:
st.info("No records found for this client yet. Click 'Save Month Calculation' first.")
