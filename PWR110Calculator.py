import streamlit as st
import math

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Prowrap Repair Calculator",
    page_icon="🔧",
    layout="wide"
)

# --- PROWRAP CERTIFIED DATA ---
# These are hardcoded to ensure compliance with the specific datasheet provided.
PROWRAP = {
    "ply_thickness": 0.83,        # mm
    "modulus_circ": 45460,        # MPa (45.46 GPa)
    "modulus_axial": 43800,       # MPa (43.8 GPa)
    "tensile_strength": 574.1,    # MPa
    "strain_fail": 0.0233,        # 2.33%
    "lap_shear": 7.37,            # MPa
    "max_temp": 55.5,             # °C (Limit)
    "tg": 75.5,                   # °C
    "shore_d": 79.1               # QA/QC
}

def main():
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
    # Using the inputs from your Excel sheet
    pipe_od = st.sidebar.number_input("Pipe Diameter (OD) [mm]", value=457.2, min_value=1.0)
    nominal_wall = st.sidebar.number_input("Nominal Wall Thickness [mm]", value=9.53, min_value=1.0)
    yield_strength = st.sidebar.number_input("Pipe Yield Strength [MPa]", value=359.0) # X52 default
    
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
    pipe_design_factor = st.sidebar.number_input("Pipe Design Factor", value=0.72)

    # --- CALCULATION BUTTON ---
    if st.sidebar.button("Calculate Repair", type="primary"):
        # FIX: Added yield_strength to the function call here
        run_calculation(
            pipe_od, nominal_wall, design_pressure, op_temp, 
            defect_mechanism, defect_length, remaining_wall, yield_strength
        )

# FIX: Added yield_strength to the function definition here
def run_calculation(od, wall, pressure, temp, defect_type, length, rem_wall, yield_strength):
    
    # --- 1. VALIDATION CHECKS ---
    errors = []
    
    # Check Temperature Limit
    if temp > PROWRAP["max_temp"]:
        errors.append(f"❌ **CRITICAL:** Operating temperature ({temp}°C) exceeds Prowrap limit of {PROWRAP['max_temp']}°C.")
        
    # Check Wall Thickness
    if rem_wall > wall:
        errors.append("❌ **INPUT ERROR:** Remaining wall cannot be greater than nominal wall.")
        
    if rem_wall < 0:
        errors.append("❌ **INPUT ERROR:** Remaining wall cannot be negative.")

    if errors:
        for err in errors:
            st.error(err)
        return

    # --- 2. ENGINEERING CALCULATIONS ---
    
    # A. Safety Factor Selection
    # ISO 24817 / ASME PCC-2 Standard logic
    # Leaks require higher safety factors and minimum thickness
    safety_factor = 3.0
    if defect_type in ["Leak", "Crack"]:
        safety_factor = 4.0

    # B. Temperature Derating
    # If temp is > 40C, we apply a small derating factor (standard practice close to limit)
    temp_factor = 0.95 if temp > 40 else 1.0
    
    # C. Allowable Strain (Epsilon Design)
    # limit = (strain_fail * temp_factor) / Safety_Factor
    design_strain = (PROWRAP["strain_fail"] * temp_factor) / safety_factor

    # D. Required Thickness Calculation (Strain Based)
    # Formula: t_min = (P * D) / (2 * E * epsilon)
    # Unit conversion: Pressure bar -> MPa
    pressure_mpa = pressure * 0.1
    
    t_required = (pressure_mpa * od) / (2 * PROWRAP["modulus_circ"] * design_strain)

    # E. Ply Count Calculation
    # Plies = Ceiling(t_required / ply_thickness)
    num_plies = math.ceil(t_required / PROWRAP["ply_thickness"])
    
    # Minimum ply constraints
    if num_plies < 2:
        num_plies = 2
    
    # Special rule for leaks: Add 2 extra layers for sealing assurance
    if defect_type == "Leak":
        num_plies += 2
        st.info("ℹ️ Added 2 extra plies for leak sealing assurance.")

    final_thickness = num_plies * PROWRAP["ply_thickness"]

    # F. Overlap Length (Shear Transfer)
    # Force to transfer = Thickness * Modulus * Strain
    hoop_load = final_thickness * PROWRAP["modulus_circ"] * design_strain
    
    # Allowable Shear Stress = Lap Shear / 3.0 (Safety Factor on bond)
    allowable_shear = PROWRAP["lap_shear"] / 3.0
    
    calculated_overlap = hoop_load / allowable_shear
    
    # Standard Minimum Overlap (usually 50mm)
    overlap_length = max(calculated_overlap, 50.0)
    
    # Total Repair Length
    total_repair_length = length + (2 * overlap_length)

    # G. Material Estimation
    circumference_mm = math.pi * od
    # Area in m^2 = Length(m) * Width(m) * Plies
    # Full encirclement assumed for "Wrap"
    repair_area_m2 = (total_repair_length / 1000.0) * (circumference_mm / 1000.0) * num_plies
    
    # Add 15% waste factor
    fabric_needed_m2 = repair_area_m2 * 1.15
    
    # Resin Estimation (Approx 0.8 to 1.0 Liters per kg of carbon, or volume based)
    # Simple Volume estimation: Volume = Area * Thickness
    # Assuming 60% Resin Volume fraction for hand layup
    composite_volume_m3 = (fabric_needed_m2 / 1.15) * (PROWRAP["ply_thickness"] / 1000.0)
    resin_liters = composite_volume_m3 * 0.60 * 1000.0 * 1.2 # extra 20% waste

    # --- 3. DISPLAY RESULTS ---
    
    st.success("✅ Calculation Complete")

    # Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Number of Plies", f"{num_plies}", delta=f"{final_thickness:.2f} mm")
    with col2:
        st.metric("Overlap Length", f"{overlap_length:.0f} mm", help="Min length beyond defect")
    with col3:
        st.metric("Total Repair Length", f"{total_repair_length:.0f} mm")
    with col4:
        st.metric("Fabric Needed", f"{fabric_needed_m2:.2f} m²", help="Includes 15% Waste")

    # Tabs for details
    tab1, tab2 = st.tabs(["📋 Engineering Details", "📝 Method Statement Data"])
    
    with tab1:
        st.subheader("Calculation Breakdown")
        st.write(f"**Design Strain:** {design_strain*100:.3f}%")
        st.write(f"**Safety Factor:** {safety_factor}")
        st.write(f"**Required Thickness:** {t_required:.3f} mm")
        st.write(f"**Hoop Load:** {hoop_load:.2f} N/mm")
        st.write(f"**Utilization:** {(t_required/final_thickness)*100:.1f}%")
        
        # Stress Check
        pipe_stress = (pressure_mpa * od) / (2 * rem_wall)
        st.write(f"**Pipe Stress (Unreinforced):** {pipe_stress:.2f} MPa")
        
        # FIX: The check below was causing the NameError previously
        if pipe_stress > yield_strength:
            st.warning(f"⚠️ Pipe is yielding ({pipe_stress:.0f} > {yield_strength} MPa)! Composite is carrying full load.")
        else:
            st.success(f"Pipe stress is within yield limits ({pipe_stress:.0f} < {yield_strength} MPa).")

    with tab2:
        st.subheader("Application Data")
        st.json({
            "Surface Preparation": "SA 2.5 (Near White Metal)",
            "Surface Profile": "> 60 microns",
            "Resin Mix Ratio": "Refer to Prowrap Container Labels",
            "Cure Time": "24 Hours @ Ambient (Min 15°C)",
            "Shore D Requirement": f"> {PROWRAP['shore_d']} (ISO 868)",
            "Resin Quantity Est": f"{resin_liters:.2f} Liters"
        })

if __name__ == "__main__":
    main()
