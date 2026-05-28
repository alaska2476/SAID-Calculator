# =========================
# FINAL CALCULATIONS (DECLARED vs ACTUAL)
# =========================
st.subheader("FINAL CALCULATIONS")

col1_calc, spacer_calc, col2_calc = st.columns([1, 0.3, 1])

# =========================
# DECLARED CALCULATIONS
# =========================
with col1_calc:
    st.markdown("**Declared Calculations**")

    declared_chargeable = declared_net_result + declared_other_total

    st.markdown(f"**Chargeable Income:** ${declared_chargeable:,.2f}")

    declared_budget = declared_total - declared_chargeable

    st.markdown(f"**Budget deficit/surplus:** ${declared_budget:,.2f}")

# =========================
# ACTUAL CALCULATIONS
# =========================
with col2_calc:
    st.markdown("**Actual Calculations**")

    actual_chargeable = actual_net_result + actual_other_total

    st.markdown(f"**Chargeable Income:** ${actual_chargeable:,.2f}")

    actual_budget = actual_total - actual_chargeable

    st.markdown(f"**Budget deficit/surplus:** ${actual_budget:,.2f}")

# =========================
# BENEFITS ISSUED & OVERPAYMENT
# =========================
st.divider()

c1, c2 = st.columns(2)

benefits_issued = c1.number_input("Benefits Issued ($)", 0.00)

overpayment = benefits_issued - actual_budget

c1.markdown(f"**OVERPAYMENT:** ${overpayment:,.2f}")

fraud = c2.number_input("Fraud Overpayment ($)", 0.00)
