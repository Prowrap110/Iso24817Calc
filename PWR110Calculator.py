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
    
    # Default Methods
    calc_method_thick = "Type B (Total Replacement)"
    calc_method_overlap = "Type B (Shear Controlled)"
    
    # 1. Logic for Repair Type
    if defect_type == "Corrosion":
        if defect_loc == "External" and not is_severe_loss:
             calc_method_thick = "Type A (Load Sharing)"
             calc_method_overlap = "Type A (Geometry Controlled)"
        else:
             # Internal or Severe External (>65%)
             calc_method_thick = "Type B (Total Replacement)"
             calc_method_overlap = "Type B (Shear Controlled)"

    elif defect_type == "Dent":
        # Dent Logic: Type A Thickness (Reinforce), Type B Overlap (Constraint)
        calc_method_thick = "Type A (Dent Reinforcement)"
        calc_method_overlap = "Type B (Dent Constraint)"
        
    elif defect_type in ["Leak", "Crack"]:
        calc_method_thick = "Type B (Leak/Crack)"
        calc_method_overlap = "Type B (Leak/Crack)"

    # --- C. SAFETY & STRAIN ---
    safety_factor = 1.0 / design_factor
    temp_factor = 0.95 if temp > 40 else 1.0
    design_strain = (PROWRAP["strain_fail"] * temp_factor) / safety_factor

    # --- D. PIPE CAPACITY CALCULATION ---
    pressure_mpa = pressure * 0.1
    allowable_steel_stress = yield_strength * design_factor
    
    # 1. Calculate Theoretical Capacity (Barlow's)
    # This applies to Corrosion AND Dent now.
    theoretical_capacity = (2 * allowable_steel_stress * rem_wall) / od
    
    # 2. Determine Effective Capacity
    if defect_type in ["Leak", "Crack"]:
        # Leaks/Cracks bypass the steel entirely
        p_steel_capacity = 0.0
    elif defect_loc == "Internal":
        # Internal defects assumed to propagate; strict standards often assume 0 capacity
        p_steel_capacity = 0.0 
    elif is_severe_loss:
        # Severe wall loss (>65%) treated as structurally compromised
        p_steel_capacity = 0.0
    else:
        # Corrosion (mild) AND Dent use the remaining wall strength
        p_steel_capacity = theoretical_capacity

    # --- E. THICKNESS CALCULATION ---
    
    # Determine Design Pressure for Composite
    if "Type A" in calc_method_thick and p_steel_capacity > 0:
        # Load Sharing: Composite takes excess pressure only
        # This now correctly works for Dents!
        p_composite_design = max(0, pressure_mpa - p_steel_capacity)
    else:
        # Type B: Composite takes FULL pressure
        p_composite_design = pressure_mpa

    # Calculate Thickness
    if p_composite_design > 0:
        t_required = (p_composite_design * od) / (2 * PROWRAP["modulus_circ"] * design_strain)
    else:
        t_required = 0.0

    # Ply Count
    num_plies = math.ceil(t_required / PROWRAP["ply_thickness"])
    
    # Minimums
    min_plies = 2
    if defect_type == "Leak": 
        min_plies = 4 # Safety for leaks
        
    if num_plies < min_plies:
        num_plies = min_plies

    final_thickness = num_plies * PROWRAP["ply_thickness"]

    # --- F. OVERLAP CALCULATION ---
    overlap_length = 0.0
    
    if "Type A" in calc_method_overlap:
        # Geometry Controlled (Max of 50mm or Taper)
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

    # --- G. MATERIAL ESTIMATION ---
    circumference_mm = math.pi * od
    repair_area_m2 = (total_repair_length / 1000.0) * (circumference_mm / 1000.0) * num_plies
    fabric_needed_m2 = repair_area_m2 * 1.15
    composite_volume_m3 = (fabric_needed_m2 / 1.15) * (PROWRAP["ply_thickness"] / 1000.0)
    resin_liters = composite_volume_m3 * 0.60 * 1000.0 * 1.2 

    # --- H. DISPLAY RESULTS ---
    st.success(f"✅ Calculation Complete")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        st.metric("Number of Plies", f"{num_plies}", delta=f"{final_thickness:.2f} mm")
    with col2: 
        st.metric("Overlap Length", f"{overlap_length:.0f} mm", help=calc_method_overlap)
    with col3: 
        st.metric("Total Repair Length", f"{total_repair_length:.0f} mm")
    with col4: 
        st.metric("Fabric Needed", f"{fabric_needed_m2:.2f} m²")

    # Tabs
    tab1, tab2 = st.tabs(["📋 Engineering Details", "📝 Method Statement"])
    
    with tab1:
        st.subheader("Assessment Breakdown")
        
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Defect Mechanism:** {defect_type}")
            if defect_type == "Corrosion":
                st.write(f"**Wall Loss:** {wall_loss_ratio*100:.1f}%")
                if is_severe_loss:
                    st.error("⚠️ Severe Wall Loss (>65%)")
                else:
                    st.success("✅ Moderate Wall Loss (≤65%)")
            
            st.divider()
            st.write(f"**Thickness Logic:** {calc_method_thick}")
            st.write(f"**Overlap Logic:** {calc_method_overlap}")

        with c2:
            st.write(f"**Pipe Capacity (Effective):** {p_steel_capacity:.1f} MPa")
            st.write(f"**Composite Load:** {p_composite_design:.1f} MPa")
            st.write(f"**Required Thickness:** {t_required:.3f} mm")
            
            if p_steel_capacity == 0 and defect_type in ["Leak", "Crack"]:
                st.caption("ℹ️ Note: For Leaks/Cracks, Pipe Capacity is treated as 0 MPa.")

    with tab2:
        st.subheader("Application Data")
        st.json({
            "Repair Class": "Structural (Type B)" if "Type B" in calc_method_thick else "Reinforcement (Type A)",
            "Surface Preparation": "SA 2.5 (Near White Metal)",
            "Resin Mix Ratio": "Refer to Container",
            "Shore D Requirement": f"> {PROWRAP['shore_d']}",
            "Resin Quantity": f"{resin_liters:.2f} Liters"
        })

def main():
    try:
        # --- HEADER ---
        st.title("🔧 Prowrap Repair Calculator")
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
