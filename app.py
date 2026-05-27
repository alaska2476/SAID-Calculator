import streamlit as st
import pandas as pd
import os

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide")

st.markdown("""
<style>
.block-container {padding-top:0.8rem; padding-bottom: 0.5rem;}
div.row-widget.stHorizontal {gap: 0.3rem;}
h1 {text-align: center;}
</style>
""", unsafe_allow_html=True)

# =========================
# SAFE LOAD
# =========================
def load_excel_safe(path):
    if os.path.exists(path):
        return pd.read_excel(path)
    else:
        st.error(f"Missing file: {path}")
        st.stop()

# =========================
# LOAD DATA
# =========================
Reference = load_excel_safe("Reference.xlsx")
Community = load_excel_safe("Community.xlsx")
file_path = "monthly_records.xlsx"

Reference.columns = ["Benefit Type","Start Date","End Date","Tier","Amount"]

Reference["Start Date"] = pd.to_datetime(Reference["Start Date"])
Reference["End Date"] = pd.to_datetime(Reference["End Date"])
Reference["Benefit Type"] = Reference["Benefit Type"].str.upper().str.strip()
Reference["Tier"] = Reference["Tier"].str.upper().str.strip()
Reference["Amount"] = Reference["Amount"].replace(r'[\$,]', '', regex=True).astype(float)

Community["Tier"] = Community["Tier"].str.upper().str.strip()

# =========================
# FUNCTIONS
# =========================
def get_tier(comm):
    t = Community.loc[Community["Community"] == comm, "Tier"]
    return t.values[0] if len(t) > 0 else "D"

def get_amounts(comm, benefit, year, month):
    if benefit in ["", "OTHER"]:
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
# TABLE FUNCTION
# =========================
def build_table(prefix):
    rows = 6
    total = 0
    benefit_list = sorted(Reference["Benefit Type"].unique())

    st.markdown("**Benefit | Amount**")

    for i in range(rows):

        col1, col2 = st.columns([1,1])

        selected = col1.selectbox(
            "",
            [""] + benefit_list + ["OTHER"],
            key=f"{prefix}_b_{i}"
        )

        #  CASE 1: OTHER → allow 3 entries
        if selected == "OTHER":

            # remove amount in this row
            col2.write("")

            #  create 3 aligned rows
            for j in range(3):

                col1b, col2b = st.columns([1,1])

                benefit = col1b.text_input(
                    "",
                    key=f"{prefix}_custom_{i}_{j}",
                    placeholder=f"Enter new benefit {j+1}"
                ).upper()

                amount_val = col2b.number_input(
                    "Amount ($)",
                    value=0.00,
                    step=0.01,
                    key=f"{prefix}_manual_other_{i}_{j}",
                    format="%.2f"
                )

                #  only add if benefit is entered
                if benefit.strip() != "":
                    total += amount_val

        #  CASE 2: NORMAL BENEFIT
        else:

            benefit = selected

            options = get_amounts(community, benefit, year, month)

            if benefit != "" and len(options) > 0:

    # ✅ Show suggestions
    display_vals = [f"${x:,.2f}" for x in options]

    suggestion = col2.selectbox(
        "Suggested Amount",
        [""] + display_vals,
        key=f"{prefix}_suggest_{i}"
    )

    # ✅ Manual override (always available)
    manual_input = col2.number_input(
        "Amount ($)",
        value=None,
        step=0.01,
        key=f"{prefix}_manual_{i}",
        format="%.2f"
    )

    # ✅ Logic: use manual if entered, else suggestion
    if manual_input is not None:
        amount_val = manual_input
    elif suggestion != "":
        amount_val = float(suggestion.replace("$","").replace(",",""))
    else:
        amount_val = 0


            else:
                amount_val = col2.number_input(
                    "Amount ($)",
                    value=0.00,
                    step=0.01,
                    key=f"{prefix}_manual_{i}_{benefit}",
                    format="%.2f"
                )

            total += amount_val

    return total

# =========================
# DECLARED & ACTUAL
# =========================
d1, spacer, d2 = st.columns([1, 0.4, 1])



with d1:
    st.subheader("Declared")
    declared_total = build_table("declared")

with d2:
    st.subheader("Actual")

    if same:
        actual_total = declared_total
        st.info("Actual total is using Declared total for calculations")
    else:
        actual_total = build_table("actual")

# =========================
# TOTALS
# =========================
# ✅ TOTALS (ALIGNED WITH DECLARED / ACTUAL)
d1a, spacer2, d2a = st.columns([1, 0.4, 1])

with d1a:
    st.markdown(f"**Total Declared:** ${declared_total:,.2f}")

with spacer2:
    st.write("")

with d2a:
    st.markdown(f"**Total Actual:** ${actual_total:,.2f}")

st.divider()
# =========================
# INCOME
# =========================
st.subheader("INCOME")

c1, c2, c3 = st.columns(3)

net_income = c1.number_input("Net Income ($)", 0.00, key="net_income")
less_exemption = c2.number_input("Less Exemption ($)", 0.00, key="less_exemption")

net_result = net_income - less_exemption
c3.markdown(f"**Net After Exemptions:** ${net_result:,.2f}")

# =========================
# OTHER INCOME
# =========================
st.subheader("Other Income")

c1, c2, c3 = st.columns(3)

surplus = c1.number_input("Surplus ($)", 0.00, key="surplus")
interest = c2.number_input("Interest income ($)", 0.00, key="interest")
other_less = c3.number_input("Less Exemption ($)", 0.00, key="other_less")

total_other = surplus + interest - other_less

st.markdown(f"**Total Other Income:** ${total_other:,.2f}")

# =========================
# FINAL CALCULATIONS
# =========================
chargeable = net_result + total_other

c1, c2, c3 = st.columns(3)

c1.markdown(f"**Chargeable Income:** ${chargeable:,.2f}")

budget = actual_total - chargeable
c2.markdown(f"**Budget deficit/surplus:** ${budget:,.2f}")

benefits_issued = c3.number_input("Benefits Issued ($)", 0.00, key="benefits_issued")

overpayment = benefits_issued - budget

c1, c2 = st.columns(2)

c1.markdown(f"**OVERPAYMENT:** ${overpayment:,.2f}")
fraud = c2.number_input("Fraud Overpayment ($)", 0.00, key="fraud")

st.divider()

# =========================
# SAVE + EXCEL
# =========================
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=[
        "Client","Case","Month","Year","Net_Income","Less_Exemption",
        "Surplus","Interest_Income","Less_Exemption_Other",
        "Total_Other_Income","Chargeable_Income","Total_Actual",
        "Benefits_Issued","Budget","Overpayment"
    ])

if st.button("Save Month Calculation"):

    new_row = pd.DataFrame([{
        "Client": client,
        "Case": case,
        "Month": month,
        "Year": year,
        "Net_Income": net_income,
        "Less_Exemption": less_exemption,
        "Surplus": surplus,
        "Interest_Income": interest,
        "Less_Exemption_Other": other_less,
        "Total_Other_Income": total_other,
        "Chargeable_Income": chargeable,
        "Total_Actual": actual_total,
        "Benefits_Issued": benefits_issued,
        "Budget": budget,
        "Overpayment": overpayment
    }])

    df = st.session_state.history

    df = df[
        ~(
            (df["Client"] == client) &
            (df["Month"] == month) &
            (df["Year"] == year)
        )
    ]

    df = pd.concat([df, new_row], ignore_index=True)
    st.session_state.history = df

    if os.path.exists(file_path):
        existing = pd.read_excel(file_path)

        existing = existing[
            ~(
                (existing["Client"] == client) &
                (existing["Month"] == month) &
                (existing["Year"] == year)
            )
        ]

        final = pd.concat([existing, new_row], ignore_index=True)
    else:
        final = new_row

    final.to_excel(file_path, index=False)

    st.success(f"Saved {client} - {month} {year}")

# =========================
# SUMMARY
# =========================
if len(st.session_state.history) > 0:

    df = st.session_state.history

    #  SAFER FILTER 
    df = df[df["Client"].str.strip().str.upper() == client.strip().upper()]

    if len(df) > 0:

        st.dataframe(df, use_container_width=True)

        total = df["Overpayment"].sum()

        st.subheader("TOTAL OVERPAYMENT / UNDERPAYMENT ACROSS MONTHS")
        st.write(f"${total:,.2f}")

        #  DOWNLOAD BUTTON (STREAMLIT SAFE)
        import io

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
