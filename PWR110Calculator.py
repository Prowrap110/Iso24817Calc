import streamlit as st
import math

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
    "cloth_width_mm": 300,        # Standard Roll Width
    "stitching_overlap_mm": 50    # Axial overlap between bands
}

def run_calculation(od, wall, pressure, temp, defect_type, defect_loc, length, rem_wall, yield_strength, design_factor):
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
    
    # Defaults
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
    
    # Effective Capacity logic
    if defect_type in ["Leak", "Crack"] or defect_loc == "Internal" or is_severe_loss:
        p_steel_capacity = 0.0
    else:
        # Corrosion (External <= 65%) and Dents use the steel strength
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
    final_thickness = num_plies * PROWRAP["ply_thickness"]

    # --- F. REPAIR LENGTH & OVERLAP ---
    if "Type A" in calc_method_overlap:
        overlap_length = max(50.0, 3.0 * final_thickness)
    else:
        hoop_load = final_thickness * PROWRAP["modulus_circ"] * design_strain
        allowable_shear = PROWRAP["lap_shear"] / safety_factor
        overlap_length = max(hoop_load / allowable_shear, 50.0)

    total_repair_length_calc = length + (2 * overlap_length)

    # --- G. MATERIAL OPTIMIZATION (Roll Width 300mm) ---
    if total_repair_length_calc <= PROWRAP["cloth_width_mm"]:
        num_bands = 1
        procurement_axial_length = 300
    else:
        # Optimized formula: ((calculated length - 300) / 250) + 1
        num_bands = math.ceil((total_repair_length_calc - 300) / 250) + 1
        procurement_axial_length = num_bands * 300 # mm
    
    circumference_m = (math.pi * od) / 1000
    axial_procurement_m = procurement_axial_length / 1000
    
    optimized_sqm = axial_procurement_m * circumference_m * num_plies
    # Epoxy Optimization (1.2 kg per sqm for saturation + waste)
    epoxy_kg = optimized_sqm * 1.2 

    # --- H. DISPLAY RESULTS ---
    st.success(f"✅ Calculation & Material Optimization Complete")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Required Plies", f"{num_plies}", f"{final_thickness:.2f} mm")
    m2.metric("Procurement Length", f"{procurement_axial_length} mm", f"{num_bands} Band(s)")
    m3.metric("Optimized Fabric", f"{optimized_sqm:.2f} m²")
    m4.metric("Epoxy Needed", f"{epoxy_kg:.1f} kg")

    tab1, tab2 = st.tabs(["📊 Engineering Analysis", "📄 Method Statement"])
    
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Defect Analysis")
            st.write(f"**Mechanism:** {defect_type}")
            st.write(f"**Wall Loss:** {wall_loss_ratio*100:.1f}%")
            st.write(f"**Effective Pipe Capacity:** {p_steel_capacity:.2f} MPa")
            st.write(f"**Repair Class:** {'Type B' if 'Type B' in calc_method_thick else 'Type A'}")
        with c2:
            st.markdown("### Structural Design")
            st.write(f"**Composite Design Pressure:** {p_composite_design:.2f} MPa")
            st.write(f"**Design Strain Limit:** {design_strain*100:.3f}%")
            st.write(f"**Calculated Safety Factor:** {safety_factor:.2f}")
            st.write(f"**Min. Required Overlap:** {overlap_length:.1f} mm")

    with tab2:
        st.markdown("## 🛠️ Prowrap Repair Method Statement")
        st.markdown("---")
        
        # VISUAL DATA GRID
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
            - **Mechanism:** {defect_type}
            - **Location:** {defect_loc}
            - **Remaining Wall:** {rem_wall} mm
            - **Axial Length:** {length} mm
            - **Wall Loss:** {wall_loss_ratio*100:.1f}%
            """)
        with c_repair:
            st.success("**3. Optimized Repair Design**")
            st.markdown(f"""
            - **Total Plies:** {num_plies} Layers
            - **Axial Band(s):** {num_bands} x 300mm
            - **Overlap Length:** {overlap_length:.0f} mm (Min)
            - **Optimized SQM:** {optimized_sqm:.2f} m²
            - **Epoxy Total:** {epoxy_kg:.1f} kg
            """)

        st.markdown("---")
        st.markdown("### 📋 Installation Checklist")
        st.markdown(f"""
        1. **Surface Prep:** Grit blast to **SA 2.5**; Profile **>60µm**.
        2. **Primer/Filler:** Apply Prowrap Filler to defect area to restore OD.
        3. **Lamination:** Saturate Carbon Cloth. Apply **{num_plies} layers** per band.
        4. **Wrapping:** This repair requires **{num_bands} band(s)** of 300mm cloth.
           * {'*Note: Ensure 50mm axial overlap between bands.*' if num_bands > 1 else ''}
        5. **Quality Control:** Minimum Shore D hardness of **{PROWRAP['shore_d']}** required for acceptance.
        """)

def main():
    try:
        st.title("🔧 Prowrap Repair Master Calculator")
        st.markdown(f"**Certified Standard:** ISO 24817 / ASME PCC-2 | **T-Limit:** {PROWRAP['max_temp']}°C")
        
        # SIDEBAR INPUTS
        st.sidebar.header("1. Project Info")
        st.sidebar.text_input("Customer", value="PROTAP")
        st.sidebar.text_input("Location", value="Turkey")
        
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
        
        if st.sidebar.button("Calculate & Optimize", type="primary"):
            run_calculation(od, wall, pres, temp, type_, loc_, len_, rem_, yield_str, df)
            
    except Exception as e:
        st.error(f"⚠️ Application Error: {e}")

if __name__ == "__main__":
    main()
