import streamlit as st
import pandas as pd
import os

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
        return pd.read_excel(path)
    else:
        st.error(f"Missing file: {path}")
        st.stop()

Reference = load_excel_safe("Reference.xlsx")
Community = load_excel_safe("Community.xlsx")

Reference.columns = ["Benefit Type","Start Date","End Date","Tier","Amount"]
Reference["Start Date"] = pd.to_datetime(Reference["Start Date"])
Reference["End Date"] = pd.to_datetime(Reference["End Date"])
Reference["Benefit Type"] = Reference["Benefit Type"].str.upper().str.strip()
Reference["Tier"] = Reference["Tier"].str.upper().str.strip()
Reference["Amount"] = Reference["Amount"].replace(r'[\$,]', '', regex=True).astype(float)

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
    date = pd.to_datetime(f"{year} {month} 01")

    df = Reference[
        (Reference["Benefit Type"] == benefit) &
        (Reference["Tier"] == tier) &
        (Reference["Start Date"] <= date) &
        (Reference["End Date"] >= date)
    ]

    return sorted(df["Amount"].unique())

# =========================
# HEADER ROW (RESTORED ✅)
# =========================
c1,c2,c3,c4,c5 = st.columns(5)

client = c1.text_input("Client")
case = c2.text_input("Case #")
community = c3.selectbox("Community", Community["Community"].unique())
month = c4.selectbox("Benefit Month", [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
])
year = c5.selectbox("Benefit Year", sorted(Reference["Start Date"].dt.year.unique()))

same = st.checkbox("Same as Declared", value=True)

# =========================
# TABLE FUNCTION
# =========================
def build_table(prefix):
    total = 0
    benefits = sorted(Reference["Benefit Type"].unique())

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

# =========================
# BENEFITS SECTION
# =========================
col1,_,col2 = st.columns([1,0.3,1])

with col1:
    st.subheader("Declared")
    st.markdown("**Benefit | Amount**")
    declared_total = build_table("d")
    st.markdown(f"### Total Declared: ${declared_total:,.2f}")

with col2:
    st.subheader("Actual")

    if same:
        actual_total = declared_total
        st.info("Actual total is using Declared total")
    else:
        st.markdown("**Benefit | Amount**")
        actual_total = build_table("a")

    st.markdown(f"### Total Actual: ${actual_total:,.2f}")

st.divider()

# =========================
# =========================
# INCOME (ALIGNED + MULTI ROW ✅)
# =========================
st.subheader("INCOME")

col1_inc, _, col2_inc = st.columns([1, 0.3, 1])

# =========================
# DECLARED
# =========================
with col1_inc:
    st.markdown("**Declared Income**")

    # ✅ Primary income
    d_net_main = st.number_input("Net Income ($)", 0.0, key="d_net_main")
    d_less_main = st.number_input("Less Exemption ($)", 0.0, key="d_less_main")

    declared_net_total = d_net_main - d_less_main

    # ✅ Additional rows (4 entries)
    for i in range(4):
        c1, c2 = st.columns(2)

        amt = c1.number_input(f"Other Amount {i+1} ($)", 0.0, key=f"d_amt_{i}")
        less = c2.number_input(f"Less {i+1} ($)", 0.0, key=f"d_less_{i}")

        declared_net_total += (amt - less)

    st.markdown(f"**Net: ${declared_net_total:,.2f}**")

# =========================
# ACTUAL
# =========================
with col2_inc:
    st.markdown("**Actual Income**")

    # ✅ Primary income
    a_net_main = st.number_input("Net Income ($)", 0.0, key="a_net_main")
    a_less_main = st.number_input("Less Exemption ($)", 0.0, key="a_less_main")

    actual_net_total = a_net_main - a_less_main

    # ✅ Additional rows
    for i in range(4):
        c1, c2 = st.columns(2)

        amt = c1.number_input(f"Other Amount {i+1} ($)", 0.0, key=f"a_amt_{i}")
        less = c2.number_input(f"Less {i+1} ($)", 0.0, key=f"a_less_{i}")

        actual_net_total += (amt - less)

    st.markdown(f"**Net: ${actual_net_total:,.2f}**")

# =========================
# OTHER INCOME
# =========================
st.subheader("OTHER INCOME")

c1,_,c2 = st.columns([1,0.3,1])

with c1:
    d_s = st.number_input("Surplus ($)", 0.0, key="d_s")
    d_i = st.number_input("Interest", 0.0, key="d_i")
    d_l = st.number_input("Less", 0.0, key="d_l")
    declared_other = d_s + d_i - d_l
    st.markdown(f"Total: ${declared_other:,.2f}")

with c2:
    a_s = st.number_input("Surplus ($)", 0.0, key="a_s")
    a_i = st.number_input("Interest", 0.0, key="a_i")
    a_l = st.number_input("Less", 0.0, key="a_l")
    actual_other = a_s + a_i - a_l
    st.markdown(f"Total: ${actual_other:,.2f}")
# =========================
# =========================
# INCOME (FINAL STRUCTURE ✅)
# =========================
st.subheader("INCOME")

col1_inc, _, col2_inc = st.columns([1, 0.3, 1])

# =========================
# DECLARED
# =========================
with col1_inc:
    st.markdown("**Declared Income**")

    # ✅ MAIN ROW
    c1, c2 = st.columns(2)
    d_net_main = c1.number_input("Net Income ($)", 0.0, key="d_net_main")
    d_less_main = c2.number_input("Less Exemption ($)", 0.0, key="d_less_main")

    declared_net_total = d_net_main - d_less_main

    # ✅ ADDITIONAL ROWS (EMPTY STYLE EXACTLY LIKE IMAGE)
    for i in range(4):
        c1, c2 = st.columns(2)

        amt = c1.number_input(f"Other Amount {i+1} ($)", 0.0, key=f"d_amt_{i}")
        less = c2.number_input(f"Less {i+1} ($)", 0.0, key=f"d_less_{i}")

        declared_net_total += (amt - less)

    st.markdown(f"**Net: ${declared_net_total:,.2f}**")

# =========================
# ACTUAL
# =========================
with col2_inc:
    st.markdown("**Actual Income**")

    # ✅ MAIN ROW
    c1, c2 = st.columns(2)
    a_net_main = c1.number_input("Net Income ($)", 0.0, key="a_net_main")
    a_less_main = c2.number_input("Less Exemption ($)", 0.0, key="a_less_main")

    actual_net_total = a_net_main - a_less_main

    # ✅ ADDITIONAL ROWS
    for i in range(4):
        c1, c2 = st.columns(2)

        amt = c1.number_input(f"Other Amount {i+1} ($)", 0.0, key=f"a_amt_{i}")
        less = c2.number_input(f"Less {i+1} ($)", 0.0, key=f"a_less_{i}")

        actual_net_total += (amt - less)

    st.markdown(f"**Net: ${actual_net_total:,.2f}**")



# =========================
# OVERPAYMENT
# =========================
st.divider()

issued = st.number_input("Benefits Issued ($)", 0.0)
overpayment = issued - actual_budget

st.markdown(f"### OVERPAYMENT: ${overpayment:,.2f}")
