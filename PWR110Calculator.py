import streamlit as st
import math

# --- 1. PAGE CONFIGURATION ---
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

    # --- B. SAFETY & STRAIN ---
    # Safety Factor = 1 / Design Factor
    safety_factor = 1.0 / design_factor
    
    # Temp Derating (Standard ISO practice)
    temp_factor = 0.95 if temp > 40 else 1.0
    
    # Design Strain Limit
    design_strain = (PROWRAP["strain_fail"] * temp_factor) / safety_factor

    # --- C. PRESSURE LOAD SHARING (TYPE A LOGIC) ---
    pressure_mpa = pressure * 0.1
    
    # 1. Calculate how much pressure the REMAINING steel can hold
    # Allowable stress = Yield * Design Factor
    allowable_steel_stress = yield_strength * design_factor
    
    # Barlow's formula for steel capacity
    # P_steel = (2 * Stress * t_remaining) / D
    p_steel_capacity = (2 * allowable_steel_stress * rem_wall) / od
    
    # 2. Determine Pressure for Composite
    calc_method = "Type B (Total Replacement)"
    p_composite_design = pressure_mpa # Default: Composite holds everything

    if defect_type == "Corrosion" and defect_loc == "External":
        # Type A: Composite only carries the "Excess" pressure
        # If steel is strong enough, composite takes 0 load (just minimum layers)
        p_composite_design = max(0, pressure_mpa - p_steel_capacity)
        calc_method = "Type A (Load Sharing)"

    # --- D. THICKNESS CALCULATION ---
    # t = (P_composite * D) / (2 * E * epsilon)
    if p_composite_design > 0:
        t_required = (p_composite_design * od) / (2 * PROWRAP["modulus_circ"] * design_strain)
    else:
        t_required = 0.0 # Steel is sufficient

    # --- E. PLY COUNT ---
    num_plies = math.ceil(t_required / PROWRAP["ply_thickness"])
    
    # Standard Minimums
    min_plies = 2
    if defect_type == "Leak": 
        min_plies = 4 # Safety for leaks
        
    if num_plies < min_plies:
        num_plies = min_plies

    final_thickness = num_plies * PROWRAP["ply_thickness"]

    # --- F. REPAIR LENGTH & OVERLAP ---
    is_type_a = (defect_loc == "External") and (defect_type == "Corrosion")
    
    overlap_note = ""
    overlap_length = 0.0

    if is_type_a:
        # TYPE A: Geometry Controlled
        # Max of (50mm, Taper Length)
        min_iso_overlap = 50.0
        taper_allowance = 3.0 * final_thickness 
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

    # --- G. MATERIAL ESTIMATION ---
    circumference_mm = math.pi * od
    repair_area_m2 = (total_repair_length / 1000.0) * (circumference_mm / 1000.0) * num_plies
    fabric_needed_m2 = repair_area_m2 * 1.15
    composite_volume_m3 = (fabric_needed_m2 / 1.15) * (PROWRAP["ply_thickness"] / 1000.0)
    resin_liters = composite_volume_m3 * 0.60 * 1000.0 * 1.2 

    # --- H. DISPLAY RESULTS ---
    st.success(f"✅ Calculation Complete: {calc_method}")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        st.metric("Number of Plies", f"{num_plies}", delta=f"{final_thickness:.2f} mm")
    with col2: 
        st.metric("Overlap Length", f"{overlap_length:.0f} mm", help=overlap_note)
    with col3: 
        st.metric("Total Repair Length", f"{total_repair_length:.0f} mm")
    with col4: 
        st.metric("Fabric Needed", f"{fabric_needed_m2:.2f} m²")

    # Tabs
    tab1, tab2 = st.tabs(["📋 Engineering Details", "📝 Method Statement"])
    
    with tab1:
        st.subheader("Calculation Breakdown")
        
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Pipe Capacity:** {p_steel_capacity:.1f} MPa")
            st.write(f"**Design Pressure:** {pressure_mpa:.1f} MPa")
            st.write(f"**Composite Load:** {p_composite_design:.1f} MPa")
        with c2:
            st.write(f"**Required Thickness:** {t_required:.3f} mm")
            st.write(f"**Design Strain:** {design_strain*100:.3f}%")
            if not is_type_a:
                st.write(f"**Shear Length:** {overlap_length:.1f} mm")
        
        st.info("ℹ️ Load Sharing Logic: If Pipe Capacity > Design Pressure, Composite takes zero structural load (Minimum Plies used).")

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
        st.title("🔧 Prowrap Repair Calculator (Load Sharing)")
        st.markdown(f"**Certified Limit:** {PROWRAP['max_temp']}°C Max Operating Temp | **Lap Shear:** {PROWRAP['lap_shear']} MPa")
        st.markdown("---")

        # --- SIDEBAR INPUTS ---
        st.sidebar.header("1. General Info")
        customer = st.sidebar.text_input("Customer", value="PROTAP")
        location = st.sidebar.text_input("Location", value="Turkey")
        report_no = st.sidebar.text_input("Report No", value="24-152")

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
        
        # --- FIX: EXPLICIT KEYWORD ARGUMENTS ---
        design_factor = st.sidebar.number_input(
            "Design Factor (f)", 
            value=0.72, 
            min_value=0.01, 
            max_value=1.0, 
            format="%.3f"
        )

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

# --- EXECUTE MAIN ---
main()
