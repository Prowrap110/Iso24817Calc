import streamlit as st
import math
from fpdf import FPDF

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Prowrap Master Calculator",
    page_icon="🔧",
    layout="wide"
)

# --- 2. PROWRAP CERTIFIED DATA ---
PROWRAP = {
    "ply_thickness": 0.83,        # mm
    "modulus_circ": 45460,        # MPa
    "modulus_axial": 43800,       # MPa
    "tensile_strength": 574.1,    # MPa
    "strain_fail": 0.0233,        # 2.33%
    "lap_shear": 7.37,            # MPa
    "max_temp": 55.5,             # °C
    "shore_d": 79.1,              #
    "cloth_width_mm": 300,        
    "stitching_overlap_mm": 50    
}

def create_pdf(report_data):
    """Generates a PDF report and returns it as bytes."""
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="PROWRAP COMPOSITE REPAIR REPORT", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 8, txt="Standard: ISO 24817 / ASME PCC-2", ln=True, align='C')
    pdf.ln(5)

    def add_section(title, data_dict):
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 8, txt=title, ln=True, fill=True)
        pdf.set_font("Arial", '', 11)
        for key, val in data_dict.items():
            pdf.cell(90, 6, txt=f"{key}:", border=0)
            pdf.cell(0, 6, txt=str(val), ln=True, border=0)
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
        "Calculated Safety Factor": f"{report_data['sf']:.2f}"
    })

    add_section("4. Material Procurement", {
        "Fabric Needed (300mm Roll)": f"{report_data['optimized_sqm']:.2f} m2",
        "Epoxy Required": f"{report_data['epoxy_kg']:.1f} kg"
    })

    try:
        return pdf.output(dest='S').encode('latin-1')
    except AttributeError:
        return bytes(pdf.output())

def run_calculation(customer, location, report_no, od, wall, pressure, temp, defect_type, defect_loc, length, rem_wall, yield_strength, design_factor):
    # --- A. VALIDATION ---
    errors = []
    if temp > PROWRAP["max_temp"]:
        errors.append(f"❌ **CRITICAL:** Operating temperature ({temp}°C) exceeds Prowrap limit of {PROWRAP['max_temp']}°C.")
    if rem_wall > wall:
        errors.append("❌ **INPUT ERROR:** Remaining wall thickness cannot be greater than nominal wall thickness.")
    if errors:
        for err in errors: st.error(err)
        return

    # --- B. DEFECT ASSESSMENT & REPAIR CLASS ---
    wall_loss_ratio = (wall - rem_wall) / wall
    is_severe_loss = wall_loss_ratio > 0.65
    
    calc_method_thick = "Type B (Total Replacement)"
    calc_method_overlap = "Type B (Shear Controlled)"
    
    if defect_type == "Corrosion":
        if defect_loc == "External" and not is_severe_loss:
             calc_method_thick = "Type A (Load Sharing)"
             calc_method_overlap = "Type A (Geometry Controlled)"
        else:
             calc_method_thick = "Type B (Total Replacement)"
             calc_method_overlap = "Type B (Shear Controlled)"
    elif defect_type == "Dent":
        calc_method_thick = "Type A (Dent Reinforcement)"
        calc_method_overlap = "Type B (Shear Controlled)"
    elif defect_type in ["Leak", "Crack"]:
        calc_method_thick = "Type B (Total Replacement)"
        calc_method_overlap = "Type B (Shear Controlled)"

    # --- C. SAFETY & STRAIN ---
    safety_factor = 1.0 / design_factor
    temp_factor = 0.95 if temp > 40 else 1.0
    design_strain = (PROWRAP["strain_fail"] * temp_factor) / safety_factor

    # --- D. PIPE CAPACITY ---
    pressure_mpa = pressure * 0.1
    allowable_steel_stress = yield_strength * design_factor
    theoretical_capacity = (2 * allowable_steel_stress * rem_wall) / od
    
    if defect_type in ["Leak", "Crack"] or defect_loc == "Internal" or is_severe_loss:
        p_steel_capacity = 0.0
    else:
        p_steel_capacity = theoretical_capacity

    # --- E. THICKNESS & PLY COUNT ---
    if "Type A" in calc_method_thick and p_steel_capacity > 0:
        p_composite_design = max(0, pressure_mpa - p_steel_capacity)
    else:
        p_composite_design = pressure_mpa

    if p_composite_design > 0:
        t_required = (p_composite_design * od) / (2 * PROWRAP["modulus_circ"] * design_strain)
    else:
        t_required = 0.0

    num_plies = math.ceil(t_required / PROWRAP["ply_thickness"])
    min_plies = 4 if defect_type == "Leak" else 2
    num_plies = max(num_plies, min_plies)
    
    # ---------------------------------------------------------
    # --- DYNAMIC OVERRIDE: 3-LAYER UPGRADE LOGIC ---
    # ---------------------------------------------------------
    is_upgraded = False
    if st.session_state.force_3_layers and num_plies < 3:
        num_plies = 3
        is_upgraded = True

    final_thickness = num_plies * PROWRAP["ply_thickness"]

    # --- F. ISO REPAIR LENGTH & OVERLAP ---
    # NOTE: Because final_thickness updated above, all lengths dynamically update here!
    if "Type A" in calc_method_overlap:
        overlap_length = max(50.0, 3.0 * final_thickness)
    else:
        hoop_load = final_thickness * PROWRAP["modulus_circ"] * design_strain
        allowable_shear = PROWRAP["lap_shear"] / safety_factor
        overlap_length = max(hoop_load / allowable_shear, 50.0)

    total_repair_length_calc = length + (2 * overlap_length)

    # --- G. MATERIAL OPTIMIZATION ---
    if total_repair_length_calc <= PROWRAP["cloth_width_mm"]:
        num_bands = 1
        procurement_axial_length = 300
    else:
        num_bands = math.ceil((total_repair_length_calc - 300) / 250) + 1
        procurement_axial_length = num_bands * 300
    
    circumference_m = (math.pi * od) / 1000
    axial_procurement_m = procurement_axial_length / 1000
    # NOTE: optimized_sqm applies num_plies across ALL bands automatically!
    optimized_sqm = axial_procurement_m * circumference_m * num_plies
    epoxy_kg = optimized_sqm * 1.2 

    # --- H. COMPILE REPORT DATA ---
    report_data = {
        "customer": customer, "location": location, "report_no": report_no,
        "od": od, "wall": wall, "yield_str": yield_strength, "pressure": pressure, "temp": temp,
        "defect_type": defect_type, "defect_loc": defect_loc, "rem_wall": rem_wall, "length": length,
        "wall_loss_ratio": wall_loss_ratio, "calc_method_thick": calc_method_thick,
        "num_plies": num_plies, "final_thickness": final_thickness, "iso_length": total_repair_length_calc,
        "num_bands": num_bands, "proc_length": procurement_axial_length, "sf": safety_factor,
        "optimized_sqm": optimized_sqm, "epoxy_kg": epoxy_kg
    }

    # --- I. DISPLAY RESULTS ---
    st.success(f"✅ Calculation Complete")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Required Plies", f"{num_plies}", f"{final_thickness:.2f} mm")
    m2.metric("Req. Repair Length", f"{total_repair_length_calc:.0f} mm")
    m3.metric("Procurement Length", f"{procurement_axial_length} mm")
    m4.metric("Optimized Fabric", f"{optimized_sqm:.2f} m²")
    m5.metric("Epoxy Needed", f"{epoxy_kg:.1f} kg")

    # --- INTERACTIVE PROTAP WARNING ---
    st.markdown("---")
    if num_plies == 2 and not is_upgraded:
        col_warn, col_btn = st.columns([3, 1])
        with col_warn:
            st.warning("⚠️ **PROTAP Recommendation:** Protap recommends min. 3 layer repair if the repair is subject to harsh and corrosive environment inline with ISO 24817.")
        with col_btn:
            if st.button("⬆️ Do you want 3 layers?", use_container_width=True):
                st.session_state.force_3_layers = True
                st.rerun() # Instantly recalculates everything
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
            st.write(f"**Design Strain Limit:** {design_strain*100:.3f}%")
            st.write(f"**Safety Factor:** {safety_factor:.2f}")

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

        st.markdown("---")
        st.markdown("### 📋 Installation Checklist")
        st.markdown(f"""
        1. **Surface Prep:** Grit blast to **SA 2.5**; Profile **>60µm**.
        2. **Primer/Filler:** Apply Prowrap Filler to defect area to restore OD.
        3. **Lamination:** Saturate Carbon Cloth. Apply **{num_plies} layers** per band.
        4. **Wrapping:** Use **{num_bands} band(s)** of 300mm cloth.
        5. **Quality Control:** Minimum Shore D hardness of **{PROWRAP['shore_d']}** required.
        """)

    # --- J. PDF DOWNLOAD BUTTON ---
    st.divider()
    pdf_bytes = create_pdf(report_data)
    
    st.download_button(
        label="📄 Download Report as PDF",
        data=pdf_bytes,
        file_name=f"Prowrap_Repair_{report_no}.pdf",
        mime="application/pdf",
        type="primary"
    )

def main():
    # Initialize Session State Variables
    if 'calc_active' not in st.session_state:
        st.session_state.calc_active = False
    if 'force_3_layers' not in st.session_state:
        st.session_state.force_3_layers = False

    try:
        st.title("🔧 Prowrap Repair Master Calculator")
        st.markdown(f"**Standard:** ISO 24817 / ASME PCC-2 | **T-Limit:** {PROWRAP['max_temp']}°C")
        
        st.sidebar.header("1. Project Info")
        customer = st.sidebar.text_input("Customer", value="PROTAP")
        location = st.sidebar.text_input("Location", value="Turkey")
        report_no = st.sidebar.text_input("Report No", value="24-152")
        
        st.sidebar.header("2. Pipeline Data")
        od = st.sidebar.number_input("Pipe OD [mm]", value=457.2)
        wall = st.sidebar.number_input("Nominal Wall [mm]", value=9.53)
        yield_str = st.sidebar.number_input("Pipe Yield [MPa]", value=359.0)
        
        st.sidebar.header("3. Service Conditions")
        pres = st.sidebar.number_input("Design Pressure [bar]", value=50.0)
        temp = st.sidebar.number_input("Op. Temperature [°C]", value=40.0)
        
        st.sidebar.header("4. Defect Data")
        type_ = st.sidebar.selectbox("Mechanism", ["Corrosion", "Dent", "Leak", "Crack"])
        loc_ = st.sidebar.selectbox("Location", ["External", "Internal"])
        len_ = st.sidebar.number_input("Defect Length [mm]", value=100.0)
        rem_ = st.sidebar.number_input("Remaining Wall [mm]", value=4.5)
        
        st.sidebar.header("5. Safety Settings")
        df = st.sidebar.number_input("Design Factor (f)", value=0.72, min_value=0.1, max_value=1.0)
        
        # When Calculate is clicked, activate session state and reset the 3-layer override
        if st.sidebar.button("Calculate & Optimize", type="primary"):
            st.session_state.calc_active = True
            st.session_state.force_3_layers = False
            
        # Run calculation if active in session state
        if st.session_state.calc_active:
            run_calculation(customer, location, report_no, od, wall, pres, temp, type_, loc_, len_, rem_, yield_str, df)
            
    except Exception as e:
        st.error(f"⚠️ Application Error: {e}")

if __name__ == "__main__":
    main()
