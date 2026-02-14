import streamlit as st
import math

# --- 1. PAGE CONFIGURATION (MUST BE FIRST) ---
st.set_page_config(
    page_title="Prowrap Repair Calculator",
    page_icon="🔧",
    layout="wide"
)

# --- 2. PROWRAP CERTIFIED DATA ---
# Source: Prowrap Technical Data Sheet
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

    # --- B. ENGINEERING CALCULATIONS ---
    
    # Safety Factor (1 / Design Factor)
    safety_factor = 1.0 / design_factor

    # Allowable Strain
    temp_factor = 0.95 if temp > 40 else 1.0
    design_strain = (PROWRAP["strain_fail"] * temp_factor) / safety_factor

    # Required Thickness (Strain Based)
    pressure_mpa = pressure * 0.1
    t_required = (pressure_mpa * od) / (2 * PROWRAP["modulus_circ"] * design_strain)

    # Ply Count
    num_plies = math.ceil(t_required / PROWRAP["ply_thickness"])
    if num_plies < 2: num_plies = 2
    
    if defect_type == "Leak":
        num_plies += 2
        st.info("ℹ️ Added 2 extra plies for leak sealing assurance.")

    final_thickness = num_plies * PROWRAP["ply_thickness"]

    # --- C. REPAIR LENGTH & OVERLAP LOGIC ---
    
    # Check if this is a Type A Repair (External Corrosion only)
    is_type_a = (defect_loc == "External") and (defect_type == "Corrosion")
    
    overlap_note = ""
    overlap_length = 0.0

    if is_type_a:
        # TYPE A: Geometry Controlled (Max of 50mm or Taper)
        min_iso_overlap = 50.0
        taper_allowance = 3.0 * final_thickness # ISO minimum taper 3:1 approx
        overlap_length = max(min_iso_overlap, taper_allowance)
        overlap_note = "Type A (Geometry Controlled)"
    else:
        # TYPE B: Shear Stress Controlled
        hoop_load = final_thickness * PROWRAP["modulus_circ"] * design_strain
        allowable_shear = PROWRAP["lap_shear"] / safety_factor
        calculated_shear_overlap = hoop_load / allowable_shear
        overlap_length = max(calculated_shear_overlap, 50.0)
        overlap_note = "Type B (Shear Stress Controlled)"

    total_repair_length = length + (2 * overlap_length)

    # --- D. MATERIAL ESTIMATION ---
    circumference_mm = math.pi * od
    repair_area_m2 = (total_repair_length / 1000.0) * (circumference_mm / 1000.0) * num_plies
    fabric_needed_m2 = repair_area_m2 * 1.15
    composite_volume_m3 = (fabric_needed_m2 / 1.15) * (PROWRAP["ply_thickness"] / 1000.0)
    resin_liters = composite_volume_m3 * 0.60 * 1000.0 * 1.2 

    # --- E. DISPLAY RESULTS ---
    st.success("✅ Calculation Complete")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Number of Plies", f"{num_plies}", delta=f"{final_thickness:.2f} mm")
    with col2: st.metric("Overlap Length", f"{overlap_length:.0f} mm", help=overlap_note)
    with col3: st.metric("Total Repair Length", f"{total_repair_length:.0f} mm")
    with col4: st.metric("Fabric Needed", f"{fabric_needed_m2:.2f} m²")

    # Tabs
    tab1, tab2 = st.tabs(["📋 Engineering Details", "📝 Method Statement"])
    
    with tab1:
        st.subheader("Calculation Breakdown")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Repair Class:** {'Type A' if is_type_a else 'Type B'}")
            st.write(f"**Overlap Logic:** {overlap_note}")
            st.write(f"**Design Strain:** {design_strain*100:.3f}%")
        with c2:
            st.write(f"**Required Thickness:** {t_required:.3f} mm")
            st.write(f"**Calculated Safety Factor:** {safety_factor:.2f}")
            if not is_type_a:
                st.write(f"**Required Shear Length:** {overlap_length:.1f} mm")
        
        st.divider()
        pipe_stress = (pressure_mpa * od) / (2 * rem_wall) if rem_wall > 0 else 9999
        if pipe_stress > yield_strength:
            st.warning(f"⚠️ Pipe Stress ({pipe_stress:.0f} MPa) > Yield ({yield_strength} MPa). Composite carries full load.")
        else:
            st.success(f"Pipe stress is within yield limits ({pipe_stress:.0f} < {yield_strength} MPa).")

    with tab2:
        st.subheader("Application Data")
        st.json({
            "Repair Type": "Type A" if is_type_a else "Type B",
            "Surface Preparation": "SA 2.5 (Near White Metal)",
            "Resin Mix Ratio": "Refer to Container",
            "Shore D Requirement": f"> {PROWRAP['shore_d']}",
            "Resin Quantity": f"{resin_liters:.2f} Liters"
        })

def main():
    try:
        # --- HEADER ---
        st.title("🔧 Prowrap Composite Repair Calculator")
        st.markdown("""
        **Standard:** ISO 24817 / ASME PCC-2  
        **System:** Prowrap Carbon Fiber Composite  
        **Certified Limit:** 55.5°C Max Operating Temp
        """)
        st.markdown("---")

        # --- SIDEBAR INPUTS ---
        st.sidebar.header("1. General Info")
        customer = st.sidebar.text_input("Customer", "PROTAP")
        location = st.sidebar.text_input("Location", "Turkey")
        report_no = st.sidebar.text_input("Report No", "24-152")

        st.sidebar.header("2. Pipe Geometry")
        pipe_od = st.sidebar.number_input("Pipe Diameter (OD) [mm]", value=457.2, min_value=1.0)
        nominal_wall = st.sidebar.number_input("Nominal Wall Thickness [mm]", value=9.53, min_value=1.0)
        yield_strength = st.sidebar.number_input("Pipe Yield Strength [MPa]", value=359.0)
        
        st.sidebar.header("3. Service Conditions")
        design_pressure = st.sidebar.number_input("Design Pressure [bar]", value=50.0)
        op_temp = st.sidebar.number_input("Operating Temperature [°C]", value=40.0)
        
        st.sidebar.header("4. Defect Details")
        defect_mechanism = st.sidebar.selectbox("Defect Mechanism", ["Corrosion", "Crack", "Dent", "Leak"])
        defect_location = st.sidebar.selectbox("Defect Location", ["External", "Internal"])
        defect_length = st.sidebar.number_input("Axial Defect Length [mm]", value=200.0)
        defect_width = st.sidebar.number_input("Hoop Defect Width [mm]", value=100.0)
        remaining_wall = st.sidebar.number_input("Remaining Wall Thickness [mm]", value=4.5)

        st.sidebar.header("5. Repair Settings")
        design_life = st.sidebar.number_input("Required Lifetime [years]", value=20)
        design_factor = st.sidebar.number_input("Design Factor (f)", value=0.72, min_value=0.01, max_value=1.0, format="%.3f")

        # --- CALCULATION BUTTON ---
        if st.sidebar.button("Calculate Repair", type="primary"):
            run_calculation(
                pipe_od, nominal_wall, design_pressure, op_temp, 
                defect_mechanism, defect_location, defect_length, remaining_wall, yield_strength,
                design_factor
            )
            
    except Exception as e:
        st.error(f"⚠️ An application error occurred: {e}")
        st.write("Please check your inputs and try again.")

# --- EXECUTE MAIN DIRECTLY (NO IF BLOCK) ---
main()
