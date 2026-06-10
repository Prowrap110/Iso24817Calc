import streamlit as st
from fpdf import FPDF

from prowrap_calculations import (
    apply_type_a_class3_result_to_repair,
    calculate_repair,
    calculate_type_a_class3_prowrap_check,
    substrate_credit_bar_for_iso_check,
)
from prowrap_materials import PROWRAP

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Prowrap Master Calculator",
    page_icon="🔧",
    layout="wide"
)

def safe_text(text):
    """Safely replaces Turkish/Special characters to prevent PDF encoding crashes."""
    if not isinstance(text, str):
        return str(text)
    replacements = {
        'ı': 'i', 'İ': 'I', 'ş': 's', 'Ş': 'S', 
        'ğ': 'g', 'Ğ': 'G', 'ü': 'u', 'Ü': 'U', 
        'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
    }
    for tr, eng in replacements.items():
        text = text.replace(tr, eng)
    return text

def create_pdf(report_data):
    """Generates a PDF report and returns it as bytes."""
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="PROWRAP COMPOSITE REPAIR REPORT", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 8, txt="Preliminary basis: selected ISO 24817 / ASME PCC-2 concepts", ln=True, align='C')
    pdf.ln(5)

    def add_section(title, data_dict):
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 8, txt=title, ln=True, fill=True)
        pdf.set_font("Arial", '', 11)
        for key, val in data_dict.items():
            pdf.cell(90, 6, txt=safe_text(f"{key}:"), border=0)
            pdf.cell(0, 6, txt=safe_text(str(val)), ln=True, border=0)
        pdf.ln(5)

    add_section("1. Project & Pipeline Data", {
        "Customer": report_data['customer'],
        "Location": report_data['location'],
        "Report No": report_data['report_no'],
        "Pipe Outer Diameter": f"{report_data['od']} mm",
        "Nominal Wall Thickness": f"{report_data['wall']} mm",
        "Pipe Yield Strength": f"{report_data['yield_str']} MPa",
        "Design Pressure": f"{report_data['pressure']} bar",
        "Operating Temperature": f"{report_data['temp']} C"
    })

    add_section("2. Defect Assessment", {
        "Defect Mechanism": report_data['defect_type'],
        "Defect Location": report_data['defect_loc'],
        "Remaining Wall": f"{report_data['rem_wall']} mm",
        "Axial Length": f"{report_data['length']} mm",
        "Wall Loss": f"{report_data['wall_loss_ratio']*100:.1f} %",
        "Repair Logic": report_data['calc_method_thick']
    })

    add_section("3. Optimized Repair Design", {
        "Required Plies": f"{report_data['num_plies']} Layers",
        "Repair Thickness": f"{report_data['final_thickness']:.2f} mm",
        "Min. Required ISO Length": f"{report_data['iso_length']:.0f} mm",
        "Procurement Length": f"{report_data['proc_length']} mm ({report_data['num_bands']} Bands)",
        "Design Factor": f"{report_data['design_factor']}"
    })
    
    # Add the basis note to the PDF directly under the design section.
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(100, 100, 100) # Dark grey for note
    pdf.multi_cell(0, 5, txt=safe_text(f"* Thickness per ISO 24817 Formula 11 performance route (eps_lt = 0.55%, Class 3, {report_data['design_life']} yr design life); axial extent per Formulae 18/20/21; minimum thickness per 7.5.14. Substrate capacity is a Barlow estimate - ISO 24817 requires MAWP from a defect assessment (ASME B31G / API 579). Verify against a licensed copy of the standard before use."))
    pdf.set_text_color(0, 0, 0) # Reset to black
    pdf.ln(2)
    for warning_text in report_data.get("compliance_warnings", []):
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(200, 0, 0)
        pdf.multi_cell(0, 5, txt=safe_text(f"WARNING: {warning_text}"))
        pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    add_section("4. Material Procurement", {
        "Fabric Needed (300mm Roll)": f"{report_data['optimized_sqm']:.2f} sqm",
        "Epoxy Required": f"{report_data['epoxy_kg']:.1f} kg"
    })

    # --- METHOD STATEMENT SECTION IN PDF ---
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(0, 8, txt="5. Installation Checklist (Method Statement)", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    
    steps = [
        "1. Surface Prep: Grit blast to SA 2.5; Profile >60 microns.",
        "2. Primer/Filler: Apply Prowrap Filler to defect area to restore OD.",
        f"3. Lamination: Saturate Carbon Cloth. Apply {report_data['num_plies']} layers per band.",
        f"4. Wrapping: Use {report_data['num_bands']} band(s) of 300mm cloth.",
        f"5. Quality Control: Minimum average Shore D hardness of {PROWRAP['shore_d']} required."
    ]
    
    for step in steps:
        pdf.multi_cell(0, 6, txt=safe_text(step))
        
    if report_data['num_plies'] == 2:
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(200, 0, 0)
        pdf.multi_cell(0, 6, txt="NOTE: Protap recommends min. 3 layer repair if the repair is subject to harsh and corrosive environment in line with ISO 24817.")
        pdf.set_text_color(0, 0, 0)

    # Safe PDF output across different fpdf versions
    output = pdf.output(dest='S')
    if isinstance(output, str):
        return output.encode('latin-1', 'replace')
    return bytes(output)

def run_calculation(
    customer,
    location,
    report_no,
    od,
    wall,
    pressure,
    temp,
    defect_type,
    defect_loc,
    length,
    rem_wall,
    yield_strength,
    design_factor,
    design_life,
    show_typea_class3_check=False,
    installation_temp=20.0,
    component_type="Straight",
    cyclic_derating_factor=1.0,
):
    try:
        report_data = calculate_repair(
            customer,
            location,
            report_no,
            od,
            wall,
            pressure,
            temp,
            defect_type,
            defect_loc,
            length,
            rem_wall,
            yield_strength,
            design_factor,
            design_life,
            force_3_layers=st.session_state.force_3_layers,
        )
    except ValueError as exc:
        for err in str(exc).splitlines():
            st.error(f"❌ **INPUT ERROR:** {err}")
        return

    wall_loss_ratio = report_data["wall_loss_ratio"]
    num_plies = report_data["num_plies"]
    final_thickness = report_data["final_thickness"]
    total_repair_length_calc = report_data["iso_length"]
    procurement_axial_length = report_data["proc_length"]
    optimized_sqm = report_data["optimized_sqm"]
    epoxy_kg = report_data["epoxy_kg"]
    is_upgraded = report_data["is_upgraded"]
    p_steel_capacity = report_data["p_steel_capacity"]
    p_composite_design = report_data["p_composite_design"]
    design_strain = report_data["design_strain"]
    num_bands = report_data["num_bands"]
    substrate_allowable_pressure = substrate_credit_bar_for_iso_check(report_data)
    typea_class3_result = None
    typea_class3_note = None

    if show_typea_class3_check:
        if defect_loc == "External" and defect_type not in ["Crack", "Leak"]:
            try:
                typea_class3_result = calculate_type_a_class3_prowrap_check(
                    od=od,
                    pressure_bar=pressure,
                    temp=temp,
                    rem_wall=rem_wall,
                    design_life=design_life,
                    nominal_wall_mm=wall,
                    substrate_allowable_pressure_bar=substrate_allowable_pressure,
                    installation_temp=installation_temp,
                    component_type=component_type,
                    cyclic_derating_factor=cyclic_derating_factor,
                )
            except ValueError as exc:
                typea_class3_note = str(exc)
        else:
            typea_class3_note = (
                "Type A / Class 3 check requires an external non-crack/non-leak defect in this version."
            )

    if typea_class3_result:
        report_data = apply_type_a_class3_result_to_repair(report_data, typea_class3_result)
        num_plies = report_data["num_plies"]
        final_thickness = report_data["final_thickness"]
        total_repair_length_calc = report_data["iso_length"]
        procurement_axial_length = report_data["proc_length"]
        optimized_sqm = report_data["optimized_sqm"]
        epoxy_kg = report_data["epoxy_kg"]
        is_upgraded = report_data["is_upgraded"]
        num_bands = report_data["num_bands"]

    st.success(f"✅ Calculation Complete")

    for warning_text in report_data.get("compliance_warnings", []):
        st.error(f"⚠️ **ISO 24817 COMPLIANCE:** {warning_text}")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Required Plies", f"{num_plies}", f"{final_thickness:.2f} mm")
    m2.metric("Req. Repair Length", f"{total_repair_length_calc:.0f} mm")
    m3.metric("Procurement Length", f"{procurement_axial_length} mm")
    m4.metric("Optimized Fabric", f"{optimized_sqm:.2f} m²")
    m5.metric("Epoxy Needed", f"{epoxy_kg:.1f} kg")

    st.markdown("---")
    if num_plies == 2 and not is_upgraded:
        col_warn, col_btn = st.columns([3, 1])
        with col_warn:
            st.warning("⚠️ **PROTAP Recommendation:** Protap recommends min. 3 layer repair if the repair is subject to harsh and corrosive environment in line with ISO 24817.")
        with col_btn:
            if st.button("⬆️ Do you want 3 layers?", use_container_width=True):
                st.session_state.force_3_layers = True
                st.rerun() 
    elif is_upgraded:
        st.info("ℹ️ **Design Upgraded:** Minimum 3 layers applied based on PROTAP recommendation for harsh environments.")
    st.markdown("---")

    tab1, tab2 = st.tabs(["📊 Engineering Analysis", "📄 Method Statement"])
    
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Defect Analysis")
            st.write(f"**Mechanism:** {defect_type}")
            st.write(f"**Wall Loss:** {wall_loss_ratio*100:.1f}%")
            st.write(f"**Effective Pipe Capacity:** {p_steel_capacity:.2f} MPa")
        with c2:
            st.markdown("### Structural Design")
            st.write(f"**Composite Design Pressure:** {p_composite_design:.2f} MPa")
            st.write(f"**Design Strain Limit:** {design_strain*100:.3f}% (ISO 24817 Formula 11: fperf x fT2 x eps_lt)")
            type_b_details = report_data.get("type_b_details")
            if type_b_details:
                st.markdown("### Type B Check (ISO Formula 12)")
                st.write(f"**gamma_LCL:** {type_b_details['gamma_lcl_j_m2']:.0f} J/m²")
                st.write(f"**Defect Size (end of life):** {type_b_details['defect_size_used_mm']:.0f} mm")
                st.write(f"**f_leak (Formula 16):** {type_b_details['fleak']:.3f}")
                st.write(f"**Max Achievable Pressure (asymptote):** {type_b_details['p_max_asymptote_mpa']:.2f} MPa")
                if type_b_details.get("repairable_formula12", True):
                    st.write(f"**Formula 12 Thickness:** {type_b_details['t_formula12_mm']:.2f} mm")
                else:
                    st.write("**Formula 12 Thickness:** NO SOLUTION - defect not repairable at this pressure")
                st.write(f"**Type A Thickness (7.5.7 max rule):** {type_b_details['t_typea_mm']:.2f} mm")
                st.write(f"**Validity d <= 6*sqrt(D*t):** {'OK' if type_b_details['d_within_validity'] else 'EXCEEDED'}")
            st.write(f"**Design Factor (f):** {design_factor}")

        if show_typea_class3_check:
            st.markdown("### ISO Type A / Class 3 Check")
            if typea_class3_result:
                if typea_class3_result["circumferential_strain_basis"] == "performance_data":
                    st.write(
                        "**Basis:** PRW110 performance data "
                        "(ISO 24817 Formula 11, eps_lt = "
                        f"{PROWRAP['long_term_strain_lcl']*100:.2f}%)."
                    )
                else:
                    st.write("**Basis:** Table 9 fallback; PRW110 performance eps_lt not supplied.")
                st.write(
                    f"**Substrate Credit:** {substrate_allowable_pressure:.1f} bar "
                    f"({substrate_allowable_pressure * 0.1:.2f} MPa effective pipe capacity)"
                )
                if not report_data.get("iso_typea_class3_controls", True):
                    st.write(
                        "**Structural Control:** Not controlling; effective pipe capacity "
                        "covers design pressure."
                    )
                    st.write(
                        f"**Non-controlling ISO Thickness:** "
                        f"{typea_class3_result['tdesign_final_mm']:.2f} mm"
                    )
                    st.write(
                        f"**Non-controlling ISO Layer Count:** "
                        f"{typea_class3_result['layer_count']}"
                    )
                else:
                    st.write("**Structural Control:** ISO Type A / Class 3 controls displayed plies.")
                    st.write(f"**Final Thickness:** {typea_class3_result['tdesign_final_mm']:.2f} mm")
                    st.write(f"**Layer Count:** {typea_class3_result['layer_count']}")
                st.write(f"**Required Overlap:** {typea_class3_result['lover_required_mm']:.1f} mm")
                st.write(f"**Component Factor:** {typea_class3_result['fth_stress']:.2f}")
                st.write(
                    f"**Thickness Check:** {'OK' if typea_class3_result['thickness_check_ok'] else 'NOT OK'}"
                )
            elif typea_class3_note:
                st.warning(typea_class3_note)

    with tab2:
        st.markdown("## 🛠️ Prowrap Repair Method Statement")
        st.markdown("---")
        
        c_pipe, c_defect, c_repair = st.columns(3)
        with c_pipe:
            st.info("**1. Pipeline Parameters**")
            st.markdown(f"""
            - **Diameter:** {od} mm
            - **Nominal Wall:** {wall} mm
            - **Grade:** {yield_strength} MPa
            - **Design Pressure:** {pressure} bar
            - **Op. Temp:** {temp} °C
            """)
        with c_defect:
            st.warning("**2. Defect Description**")
            st.markdown(f"""
            - **Mechanism:** {defect_type} ({defect_loc})
            - **Remaining Wall:** {rem_wall} mm
            - **Axial Length:** {length} mm
            - **Wall Loss:** {wall_loss_ratio*100:.1f}%
            """)
        with c_repair:
            st.success("**3. Optimized Repair Design**")
            st.markdown(f"""
            - **Total Plies:** {num_plies} Layers
            - **Req. Length (ISO):** {total_repair_length_calc:.0f} mm
            - **Axial Band(s):** {num_bands} x 300mm
            - **Procurement Len:** {procurement_axial_length} mm
            - **Epoxy Total:** {epoxy_kg:.1f} kg
            """)
            # Add the calculation-basis note to the UI dynamically.
            st.caption(f"*Preliminary estimate based on selected ISO 24817 / ASME PCC-2 concepts for a specified design life of {design_life} years. Full ISO traceability requires route-specific verification and approved long-term design data.*")

        st.markdown("---")
        st.markdown("### 📋 Installation Checklist")
        st.markdown(f"""
        1. **Surface Prep:** Grit blast to **SA 2.5**; Profile **>60µm**.
        2. **Primer/Filler:** Apply Prowrap Filler to defect area to restore OD.
        3. **Lamination:** Saturate Carbon Cloth. Apply **{num_plies} layers** per band.
        4. **Wrapping:** Use **{num_bands} band(s)** of 300mm cloth.
        5. **Quality Control:** Minimum average Shore D hardness of **{PROWRAP['shore_d']}** required.
        """)

    # --- J. PDF DOWNLOAD GENERATOR WITH ERROR CATCHING ---
    st.divider()
    try:
        pdf_bytes = create_pdf(report_data)
        st.download_button(
            label="📄 Download Report as PDF",
            data=pdf_bytes,
            file_name=f"Prowrap_Repair_{safe_text(report_no)}.pdf",
            mime="application/pdf",
            type="primary"
        )
    except Exception as pdf_error:
        st.error(f"⚠️ Could not generate PDF. Error details: {pdf_error}")

# A helper function to reset calculation state when a user types a new input
def reset_calc():
    st.session_state.calc_active = False
    st.session_state.force_3_layers = False

def main():
    if 'calc_active' not in st.session_state:
        st.session_state.calc_active = False
    if 'force_3_layers' not in st.session_state:
        st.session_state.force_3_layers = False

    try:
        st.title("🔧 Prowrap Repair Master Calculator")
        st.markdown(f"**Basis:** Preliminary ISO 24817 / ASME PCC-2 screening estimate | **T-Limit:** {PROWRAP['max_temp']}°C")
        
        st.sidebar.header("1. Project Info")
        customer = st.sidebar.text_input("Customer", value="PROTAP", on_change=reset_calc)
        location = st.sidebar.text_input("Location", value="Turkey", on_change=reset_calc)
        report_no = st.sidebar.text_input("Report No", value="24-152", on_change=reset_calc)
        
        st.sidebar.header("2. Pipeline Data")
        od = st.sidebar.number_input("Pipe OD [mm]", value=457.2, on_change=reset_calc)
        wall = st.sidebar.number_input("Nominal Wall [mm]", value=9.53, on_change=reset_calc)
        yield_str = st.sidebar.number_input("Pipe Yield [MPa]", value=359.0, on_change=reset_calc)
        
        st.sidebar.header("3. Service Conditions")
        pres = st.sidebar.number_input("Design Pressure [bar]", value=50.0, on_change=reset_calc)
        temp = st.sidebar.number_input("Op. Temperature [°C]", value=40.0, on_change=reset_calc)
        
        st.sidebar.header("4. Defect Data")
        type_ = st.sidebar.selectbox("Mechanism", ["Corrosion", "Dent", "Leak", "Crack"], on_change=reset_calc)
        loc_ = st.sidebar.selectbox("Location", ["External", "Internal"], on_change=reset_calc)
        len_ = st.sidebar.number_input("Defect Length [mm]", value=100.0, on_change=reset_calc)
        rem_ = st.sidebar.number_input("Remaining Wall [mm]", value=4.5, on_change=reset_calc)
        
        st.sidebar.header("5. Safety & Design Settings")
        design_life = st.sidebar.number_input("Design Life [years]", value=20, min_value=1, on_change=reset_calc)
        df = st.sidebar.number_input("Design Factor (f)", value=0.72, min_value=0.1, max_value=1.0, on_change=reset_calc)

        st.sidebar.header("6. ISO Type A / Class 3 Check")
        show_typea_class3_check = st.sidebar.checkbox("Show Type A / Class 3 check", value=True, on_change=reset_calc)
        st.sidebar.caption("For external non-crack/non-leak defects, substrate credit is automatically taken from effective pipe capacity.")
        installation_temp = st.sidebar.number_input("Installation temperature [°C]", value=20.0, on_change=reset_calc)
        component_type = st.sidebar.selectbox("Component type", ["Straight", "Bend", "Tee", "Flange", "Reducer"], on_change=reset_calc)
        cyclic_derating_factor = st.sidebar.number_input("Cyclic derating factor", value=1.0, min_value=0.01, max_value=1.0, on_change=reset_calc)
        
        if st.sidebar.button("Calculate & Optimize", type="primary"):
            st.session_state.calc_active = True
            st.session_state.force_3_layers = False
            
        if st.session_state.calc_active:
            run_calculation(
                customer,
                location,
                report_no,
                od,
                wall,
                pres,
                temp,
                type_,
                loc_,
                len_,
                rem_,
                yield_str,
                df,
                design_life,
                show_typea_class3_check,
                installation_temp,
                component_type,
                cyclic_derating_factor,
            )
            
    except Exception as e:
        st.error(f"⚠️ Application Error: {e}")

if __name__ == "__main__":
    main()
