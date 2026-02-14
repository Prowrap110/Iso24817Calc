import streamlit as st
import math

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Prowrap Repair Calculator",
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
    "tg": 75.5,                   # °C
    "shore_d": 79.1               # QA/QC
}

def run_calculation(od, wall, pressure, temp, defect_type, defect_loc, length, rem_wall, yield_strength, design_factor):
    
    # --- A. VALIDATION ---
    errors = []
    if temp > PROWRAP["max_temp"]:
        errors.append(f"❌ **CRITICAL:** Operating temperature ({temp}°C) exceeds Prowrap limit of {PROWRAP['max_temp']}°C.")
    if rem_wall > wall:
        errors.append("❌ **INPUT ERROR:** Remaining wall cannot be greater than nominal wall.")
    if rem_wall < 0:
        errors.append("❌ **INPUT ERROR:** Remaining wall cannot be negative.")

    if errors:
        for err in errors: st.error(err)
        return

    # --- B. DEFECT ASSESSMENT ---
    wall_loss_ratio = (wall - rem_wall) / wall
    is_severe_loss = wall_loss_ratio > 0.65
    
    calc_method_thick = "Type B (Total Replacement)"
    calc_method_overlap = "Type B (Shear Controlled)"
    
    # Logic defining which method to use
    if defect_type == "Corrosion":
        if defect_loc == "External" and not is_severe_loss:
             calc_method_thick = "Type A (Load Sharing)"
             calc_method_overlap = "Type A (Geometry Controlled)"
        else:
             calc_method_thick = "Type B (Total Replacement)"
             calc_method_overlap = "Type B (Shear Controlled)"

    elif defect_type == "Dent":
        calc_method_thick = "Type A (Dent Reinforcement)"
        calc_method_overlap = "Type B (Dent Constraint)"
        
    elif defect_type in ["Leak", "Crack"]:
        calc_method_thick = "Type B (Leak/Crack)"
        calc_method_overlap = "Type B (Leak/Crack)"

    # --- C. SAFETY & STRAIN ---
    safety_factor = 1.0 / design_factor
    temp_factor = 0.95 if temp > 40 else 1.0
    design_strain = (PROWRAP["strain_fail"] * temp_factor) / safety_factor

    # --- D. PIPE CAPACITY ---
    pressure_mpa = pressure * 0.1
    allowable_steel_stress = yield_strength * design_factor
    
    # Theoretical capacity of the remaining steel
    theoretical_capacity = (2 * allowable_steel_stress * rem_wall) / od
    
    # Effective capacity (Zero if leak/crack/severe)
    if defect_type in ["Leak", "Crack"]:
        p_steel_capacity = 0.0
    elif defect_loc == "Internal":
        p_steel_capacity = 0.0 
    elif is_severe_loss:
        p_steel_capacity = 0.0
    else:
        # For Corrosion (minor) and Dents, we trust the steel strength
        p_steel_capacity = theoretical_capacity

    # --- E. THICKNESS ---
    # Load Sharing: Composite takes only the pressure the steel cannot hold
    if "Type A" in calc_method_thick and p_steel_capacity > 0:
        p_composite_design = max(0, pressure_mpa - p_steel_capacity)
    else:
        # Type B: Composite takes FULL pressure
        p_composite_design = pressure_mpa

    if p_composite_design > 0:
        t_required = (p_composite_design * od) / (2 * PROWRAP["modulus_circ"] * design_strain)
    else:
        t_required = 0.0

    # Ply Count
    num_plies = math.ceil(t_required / PROWRAP["ply_thickness"])
    
    # Minimums
    min_plies = 4 if defect_type == "Leak" else 2
    if num_plies < min_plies: num_plies = min_plies

    final_thickness = num_plies * PROWRAP["ply_thickness"]

    # --- F. OVERLAP ---
    overlap_length = 0.0
    if "Type A" in calc_method_overlap:
        # Geometry Controlled
        min_iso_overlap = 50.0
        taper_allowance = 3.0 * final_thickness 
        overlap_length = max(min_iso_overlap, taper_allowance)
    else:
        # Shear Stress Controlled
        hoop_load = final_thickness * PROWRAP["modulus_circ"] * design_strain
        allowable_shear = PROWRAP["lap_shear"] / safety_factor
        calculated_shear_overlap = hoop_load / allowable_shear
        overlap_length = max(calculated_shear_overlap, 50.0)

    total_repair_length = length + (2 * overlap_length)

    # --- G. MATERIAL EST ---
    circumference_mm = math.pi * od
    repair_area_m2 = (total_repair_length / 1000.0) * (circumference_mm / 1000.0) * num_plies
    fabric_needed_m2 = repair_area_m2 * 1.15
    composite_volume_m3 = (fabric_needed_m2 / 1.15) * (PROWRAP["ply_thickness"] / 1000.0)
    resin_liters = composite_volume_m3 * 0.60 * 1000.0 * 1.2 

    # --- H. RESULTS DISPLAY ---
    st.success("✅ Calculation Complete")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Layers", f"{num_plies}", f"{final_thickness:.2f} mm")
    col2.metric("Overlap", f"{overlap_length:.0f} mm")
    col3.metric("Total Length", f"{total_repair_length:.0f} mm")
    col4.metric("Fabric", f"{fabric_needed_m2:.2f} m²")

    tab1, tab2 = st.tabs(["📊 Engineering Analysis", "📄 Method Statement"])
    
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Defect Analysis")
            st.write(f"**Mechanism:** {defect_type}")
            st.write(f"**Wall Loss:** {wall_loss_ratio*100:.1f}%")
            st.write(f"**Pipe Capacity:** {p_steel_capacity:.2f} MPa")
            st.write(f"**Calc Method:** {calc_method_thick}")
        with c2:
            st.markdown("### Structural Design")
            st.write(f"**Composite Load:** {p_composite_design:.2f} MPa")
            st.write(f"**Design Strain:** {design_strain*100:.3f}%")
            st.write(f"**Safety Factor:** {safety_factor:.2f}")

    with tab2:
        st.markdown("## 🛠️ Repair Method Statement")
        st.markdown("---")
        
        # 1. VISUAL DATA GRID
        c_pipe, c_defect, c_repair = st.columns(3)
        
        with c_pipe:
            st.info("**1. Pipeline Data**")
            st.markdown(f"""
            - **Diameter:** {od} mm
            - **Original Wall:** {wall} mm
            - **Grade:** {yield_strength} MPa
            - **Pressure:** {pressure} bar
            - **Temp:** {temp} °C
            """)
            
        with c_defect:
            st.warning("**2. Defect Data**")
            st.markdown(f"""
            - **Type:** {defect_type} ({defect_loc})
            - **Rem. Wall:** {rem_wall} mm
            - **Wall Loss:** {wall_loss_ratio*100:.1f}%
            - **Axial Length:** {length} mm
            """)
            
        with c_repair:
            st.success("**3. Repair Design**")
            st.markdown(f"""
            - **Product:** Prowrap Carbon
            - **Plies:** {num_plies} Layers
            - **Thickness:** {final_thickness:.2f} mm
            - **Overlap:** {overlap_length:.0f} mm (Each Side)
            - **Total Length:** {total_repair_length:.0f} mm
            """)

        st.markdown("---")
        
        # 2. INSTALLATION STEPS
        st.markdown("### 📋 Application Procedure")
        st.markdown(f"""
        1.  **Surface Preparation:**
            * Grit blast to **SA 2.5 (Near White Metal)**.
            * Achieve surface profile **> 60 microns**.
            * Clean with acetone/degreaser.
        2.  **Defect Treatment:**
            * Apply high-modulus load transfer filler to defect area.
            * Restore Outer Diameter (OD) profile.
        3.  **Lamination:**
            * Mix Prowrap Epoxy Resin (Refer to container label).
            * Saturate carbon fabric.
            * Apply **{num_plies} layers** using 50% overlap wrapping technique.
            * Ensure strict consolidation (no wrinkles/voids).
        4.  **Curing & QC:**
            * Wrap with compression film and perforator.
            * Allow to cure for **24 hours @ Ambient**.
            * **QC Check:** Verify Shore D Hardness > {PROWRAP['shore_d']}.
        """)

def main():
    try:
        st.title("🔧 Prowrap Repair Calculator")
        
        # Sidebar
        st.sidebar.header("1. General Info")
        st.sidebar.text_input("Customer", value="PROTAP")
        st.sidebar.text_input("Location", value="Turkey")
        st.sidebar.text_input("Report No", value="24-152")

        st.sidebar.header("2. Pipeline")
        # FIXED: Using explicit 'value=' for all number inputs
        od = st.sidebar.number_input("Pipe OD [mm]", value=457.2)
        wall = st.sidebar.number_input("Nominal Wall [mm]", value=9.53)
        yield_str = st.sidebar.number_input("Yield [MPa]", value=359.0)
        
        st.sidebar.header("3. Conditions")
        pres = st.sidebar.number_input("Pressure [bar]", value=50.0)
        temp = st.sidebar.number_input("Temp [°C]", value=40.0)
        
        st.sidebar.header("4. Defect")
        type_ = st.sidebar.selectbox("Type", ["Corrosion", "Dent", "Crack", "Leak"])
        loc_ = st.sidebar.selectbox("Location", ["External", "Internal"])
        len_ = st.sidebar.number_input("Length [mm]", value=200.0)
        wid_ = st.sidebar.number_input("Width [mm]", value=100.0)
        rem_ = st.sidebar.number_input("Remaining Wall [mm]", value=4.5)
        
        st.sidebar.header("5. Settings")
        st.sidebar.number_input("Lifetime [yrs]", value=20)
        
        # FIXED: The problematic line is now corrected with explicit args
        df = st.sidebar.number_input("Design Factor", value=0.72, min_value=0.1, max_value=1.0)
        
        if st.sidebar.button("Calculate Repair", type="primary"):
            run_calculation(od, wall, pres, temp, type_, loc_, len_, rem_, yield_str, df)
            
    except Exception as e:
        st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
