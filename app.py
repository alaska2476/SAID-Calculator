
import streamlit as st
import pandas as pd
import os
import io

st.set_page_config(layout="wide")
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 0rem;
}
</style>
""", unsafe_allow_html=True)

# ========================
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
#  GROUPING 
# =========================
def assign_group(b):
    if "ADULTS VISITING" in b: return "F/ADULT"
    if "APPROVED HOME" in b: return "AP/HOME"
    if "BASIC ALLOWANCE" in b: return "BASC/AL"
    if "BOARD & ROOM" in b: return "B+C/+CC"

    if "EXCESS" in b: return "C.T.R."
    if "CHILD BENEFIT" in b: return "SN/CHILD"
    if "CLOTHING" in b: return "CLOTHING"
    if "DISABILITY ALLOWANCE" in b: return "DIS/ALL"

    # FIXED LIVING GROUP
    if b in [
        "LIVING INCOME ALLOWANCE",
        "LIVING INCOME BOARD AND RM",
        "LIVING INCOME LIGHT HOUSE/LT",
        "LIVING INCOME RESIDENTIAL",
        "LIVING INCOME SALVTN ARMY/LT"
    ]:
        return "LIVING"

    if "HOME HEATING/ENERGY" in b: return "ENERGY"
    if "EDUCATION AND TRAINING" in b: return "EDUC-TI"
    if "EDUCATION EXPENSES AGE" in b: return "SN/EDUC"
    if "FAMILY HOMES" in b: return "FA HOME"
    if "EDUCATION" in b: return "EDUCATION"
    if "LAUNDRY" in b: return "SN/LAUD"
    if "MEALS AT HOME" in b: return "MEAL/HO"
    if "MEALS AWAY" in b: return "MEAL/AW"
    if "PERSONAL CARE" in b: return "P/C HOME"
    if "SALVATION" in b: return "S/A-A/R"
    if "SANCTUARY" in b: return "B&R/SH"
    if "SHELTER" in b: return "SHELTER"
    if "SPECIAL CARE" in b: return "S/C/H"
    if "SINGLE PARENT HOME" in b: return "SP/RES"
    if "TRAINING" in b: return "SN/TRAL"
    if "YWCA" in b: return "YWCA PA"
    if "TRUST" in b or "SN/TRUS" in b: return "SN/TRUS"

    return b
    
Reference["Group"] = Reference["Benefit Type"].apply(assign_group)

# =========================
# FUNCTIONS
# =========================
def get_tier(comm):
    t = Community.loc[Community["Community"] == comm, "Tier"]
    return t.values[0] if len(t) > 0 else "D"

def get_filtered_benefits(comm, year, month, adults, children):
    tier = get_tier(comm)
    date = pd.to_datetime(f"{year} {month} 01")

    df = Reference[
        ((Reference["Tier"] == tier) | (Reference["Tier"] == "ALL")) &
        (Reference["Start_Date"] <= date) &
        (Reference["End_Date"] >= date)
    ]

    # Filter by Adults/Children (if applicable)
    df = df[
        (df["Adults"].fillna(adults) == adults) &
        (df["Children"].fillna(children) == children)
    ]
    valid_groups = []

    for grp in df["Group"].dropna().unique():
        sub = df[df["Group"] == grp]
        if not sub["Amount"].dropna().empty:
            valid_groups.append(grp)

    return sorted(valid_groups)

def get_amounts(comm, group, year, month, adults, children):
    tier = get_tier(comm)
    date = pd.to_datetime(f"{year} {month} 01")

    df = Reference[
        (Reference["Group"] == group) &
        ((Reference["Tier"] == tier) | (Reference["Tier"] == "ALL")) &
        (Reference["Start_Date"] <= date) &
        (Reference["End_Date"] >= date)
    ]

    df = df[
        (df["Adults"].fillna(adults) == adults) &
        (df["Children"].fillna(children) == children)

        ]

    return sorted(df["Amount"].dropna().unique())

# =========================
# HEADER
# =========================
st.markdown(
    """
    <h1 style='text-align: center;'>
        SAID TRANSITION CALCULATOR
    </h1>
    """,
    unsafe_allow_html=True
)
cols = st.columns(7)
client = cols[0].text_input("Client #", key="client")
case = cols[1].text_input("Case #", key="case")
community = cols[2].selectbox("Community", Community["Community"].unique(), key="community")
month = cols[3].selectbox("Month", [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
], key="month")
year = cols[4].selectbox("Year", list(range(2020, 2027)), key="year")
adults = cols[5].selectbox(
    "Adults",
    [1, 2, 3, 4,5],              
    key="adults_2026_FINAL"       
)

children = cols[6].selectbox(
    "Children",
    [0, 1, 2, 3, 4, 5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26],       
    key="children_FINAL_2026"
)

# =========================
# TABLE BUILDER
# =========================
def build_table(prefix):
    total = 0

    benefits = get_filtered_benefits(community, year, month, adults, children)

    for i in range(10):
        c1, c2 = st.columns(2)

        b = c1.selectbox("", [""] + benefits + ["OTHER"], key=f"{prefix}_b_{i}")

        if b == "OTHER":
            for j in range(7):
                c3, c4 = st.columns(2)
                name = c3.text_input("", key=f"{prefix}_name_{i}_{j}")
                val = c4.number_input("Amount", 0.0, key=f"{prefix}_val_{i}_{j}")
                if name.strip():
                    total += val
        else:
            opts = get_amounts(community, b, year, month, adults, children)

            if opts:
                val = c2.selectbox("", opts, key=f"{prefix}_amt_{i}")
            else:
                val = c2.number_input("Amount", 0.0, key=f"{prefix}_num_{i}")

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

col1, _, col2 = st.columns([1,0.3,1])

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
st.info(
    """
    Declared Income = Income used in the original assessment.
    
    Additional Income =  New income identified after the original assessment 
    that was not included in the original calculation.
    """
)
st.subheader("INCOME")

h1, _, h2 = st.columns([1,0.3,1])
with h1: st.markdown("**Declared Income**")
with h2: st.markdown("**Additional Income**")

_, _, cb2 = st.columns([1,0.3,1])
with cb2:
    same_income = st.checkbox("No Additional Income", True)

col1_inc,_,col2_inc = st.columns([1,0.3,1])

# Declared Income
with col1_inc:
    declared_net_total = 0

    for i in range(5):
        c1, c2 = st.columns(2)

        label = f"D{i+1}"   

        val = c1.number_input(label, 0.0, key=f"d_{i}")
        less = c2.number_input("Less", 0.0, key=f"d_less_{i}")

        declared_net_total += (val - less)

    st.markdown(f"**Total Declared Income: ${declared_net_total:,.2f}**")

# Additional Income
with col2_inc:
    if same_income:
        additional_income_total = 0
        st.info("No additional income")
    else:
        total = 0

        for i in range(5):
            c1, c2 = st.columns(2)

            label = f"A{i+1}"   
            val = c1.number_input(label, 0.0, key=f"a_{i}")
            less = c2.number_input("Less", 0.0, key=f"a_less_{i}")

            total += (val - less)

        additional_income_total = total
        st.markdown(f"**Total Additional Income: ${additional_income_total:,.2f}**")


# =========================
# FINAL
# =========================
total_income_considered = declared_net_total + (
    0 if same_income else additional_income_total
)

declared_benefit = declared_total - declared_net_total

budget_deficit = max(actual_total - total_income_considered, 0)

c1, c2, spacer, c3 = st.columns([1, 1, 1, 3])

with c1:
    st.markdown(
        f"### Benefit: ${declared_benefit:,.2f}"
    )

with c2:
    col_a, col_b = st.columns([5, 4])

    with col_a:
        st.markdown("### Benefit Issued:")

    with col_b:
        issued = st.number_input(
            "Benefit Issued",
            min_value=0.0,
            format="%.2f",
            label_visibility="collapsed"
        )

with c3:
    st.markdown(
        f"### Budget Deficit: ${budget_deficit:,.2f}"
    )
    
# =========================
# BUSINESS RULE
# =========================

# Not eligible -> full overpayment
if total_income_considered >= actual_total:

    actual_budget = 0

    # everything issued becomes overpayment
    difference = issued

# Still eligible -> recalculate benefit
else:

    actual_budget = actual_total - total_income_considered
    recalculated_benefit = max(actual_budget, 0)

    difference = issued - recalculated_benefit

# Result label
if difference > 0:
    label = "OVERPAYMENT"
elif difference < 0:
    label = "UNDERPAYMENT"
else:
    label = "NO DIFFERENCE"

st.markdown(f"### {label}: ${abs(difference):,.2f}")


# =========================
# SAVE
# =========================
required_columns = [
    "Client",
    "Case",
    "Month",
    "Year",
    "Total Declared",
    "Total Actual",
    "Declared Income",
    "Additional Income",
    "Total Income Considered",
    "Budget Deficit",
    "Benefit",
    "Benefits Issued",
    "Overpayment / Underpayment"
]
#
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=required_columns)
else:
    st.session_state.history = st.session_state.history.reindex(columns=required_columns)


# SAVE BUTTON
if st.button("Save Month Calculation"):

    new_row = pd.DataFrame([{
        "Client": client,
        "Case": case,
        "Month": month,
        "Year": year,
        "Total Declared": declared_total,
        "Total Actual": actual_total,
        "Declared Income": declared_net_total,
        "Additional Income": (
            0 if same_income else additional_income_total
        ),
        "Total Income Considered": total_income_considered,
        "Budget Deficit": budget_deficit,
        "Benefit": declared_benefit,
        "Benefits Issued": issued,
        "Overpayment / Underpayment": difference
    }])

    hist = st.session_state.history.copy()

    if not hist.empty:
        mask = (
            (hist["Client"] == client) &
            (hist["Case"] == case) &
            (hist["Month"] == month) &
            (hist["Year"] == year)
        )
        hist = hist[~mask]

    st.session_state.history = pd.concat(
        [hist, new_row],
        ignore_index=True
    )

    st.success("Saved")
    
# =========================
# DISPLAY
# =========================
if len(st.session_state.history) > 0:

    st.dataframe(st.session_state.history)

    # CREATE EXCEL OUTPUT
    output = io.BytesIO()
    export_df = st.session_state.history.copy()

    # DEFINE TOTAL
    total = export_df["Overpayment / Underpayment"].sum()

    #  LABEL (FIXED INDENTATION)
    if total > 0:
        total_text = "TOTAL OVERPAYMENT"
    elif total < 0:
        total_text = "TOTAL UNDERPAYMENT"
    else:
        total_text = "TOTAL NO DIFFERENCE"

    #  SUMMARY ROW
    first_col = export_df.columns[0]
    summary_row = {col: None for col in export_df.columns}
    summary_row[first_col] = total_text
    summary_row["Overpayment / Underpayment"] = float(total)

    export_df = pd.concat([export_df, pd.DataFrame([summary_row])], ignore_index=True)

    #  WRITE FILE
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False)

    #  DOWNLOAD
    file_name = f"{client}_{case}_summary.xlsx"
    st.download_button("Download Summary", output.getvalue(), file_name)

    #  SHOW TOTAL
    st.subheader(total_text)
    st.metric("", f"${abs(total):,.2f}")
