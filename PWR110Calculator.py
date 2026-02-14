import streamlit as st
import math

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Prowrap Repair Calculator", page_icon="🔧", layout="wide")

# --- 2. PROWRAP CERTIFIED DATA ---
# Source: Prowrap Technical Data Sheet
PROWRAP = {
    "ply_thickness": 0.83,        # mm
    "modulus_circ": 45460,        # MPa
    "strain_fail": 0.0233,        # 2.33%
    "lap_shear": 7.37,            # MPa
    "max_temp": 55.5,             # °C
    "shore_d": 79.1               # QA/QC
}

def run_calculation(od, wall, pressure, temp, defect_type, defect_loc, length, rem_wall, yield_strength, design_factor):
    # --- A. VALIDATION ---
    errors = []
    if temp > PROWRAP["max_temp"]:
        errors.append(f"❌ **CRITICAL:** Operating temp ({temp}°C) exceeds limit of {PROWRAP['max_temp']}°C.")
    if rem_wall > wall:
        errors.append("❌ **INPUT ERROR:** Remaining wall > Nominal wall.")
    if errors:
        for err in errors: st.error(err)
        return

    # --- B. SAFETY & STRAIN ---
    safety_factor = 1.0 / design_factor
    temp_factor = 0.95 if temp > 40 else 1.0
    design_strain = (PROWRAP["strain_fail"] * temp_factor) / safety_factor

    # --- C. PRESSURE LOAD SHARING (THE FIX) ---
    pressure_mpa = pressure * 0.1
    
    # 1. Calculate Capacity of Remaining Steel (ISO Eq. 10 Concept)
    # Allowable stress in steel = Yield * Design Factor
    allowable_steel_stress = yield_strength * design_factor
    
    # Pressure the steel can safely hold
    p_steel_capacity = (2 * allowable_steel_stress * rem_wall) / od
    
    # 2. Determine Pressure for Composite
    if defect_type == "Corrosion" and defect_loc == "External":
        # Type A: Composite only carries the "Excess" pressure
        p_composite_design = max(0, pressure_mpa - p_steel_capacity)
        calc_method = "Type A (Load Sharing)"
    else:
        # Type B (Leak/Crack): Composite carries FULL pressure
        p_composite_design = pressure_mpa
        calc_method = "Type B (Total Replacement)"

    # --- D. THICKNESS CALCULATION ---
    # t = (P_composite * D) / (2 * E * epsilon)
    if p_composite_design > 0:
        t_required = (p_composite_design * od) / (2 * PROWRAP["modulus_circ"] * design_strain)
    else:
        t_required = 0.0 # Steel is strong enough

    # --- E. PLY COUNT ---
    num_plies = math.ceil(t_required / PROWRAP["ply_thickness"])
    
    # Standard Minimums
    min_plies = 2
    if defect_type == "Leak": min_plies = 4 # Safety for leaks
    
    if num_plies < min_plies:
        num_plies = min_plies
        note_thickness = "Minimum Requirement"
    else:
        note_thickness = "Calculated Load"

    final_thickness = num_plies * PROWRAP["ply_thickness"]

    # --- F. OVERLAP CALCULATION ---
    is_type_a = (defect_loc == "External") and (defect_type == "Corrosion")
    
    if is_type_a:
        # Geometry Controlled
        overlap_length = max(50.0, 3.0 * final_thickness)
        overlap_note = "Geometry Controlled"
    else:
        # Shear Controlled (Full Load Transfer)
        hoop_load = final_thickness * PROWRAP["modulus_circ"] * design_strain
        allowable_shear = PROWRAP["lap_shear"] / safety_factor
        overlap_length = max(hoop_load / allowable_shear, 50.0)
        overlap_note = "Shear Controlled"

    total_repair_length = length + (2 * overlap_length)
    
    # Material Est
    circumference_mm = math.pi * od
    area_m2 = (total_repair_length / 1000.0) * (circumference_mm / 1000.0) * num_plies * 1.15

    # --- G. RESULTS ---
    st.success(f"✅ Calculation Complete: {calc_method}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Number of Plies", f"{num_plies}", delta=f"{final_thickness:.2f} mm")
    c2.metric("Overlap Length", f"{overlap_length:.0f} mm", help=overlap_note)
    c3.metric("Total Length", f"{total_repair_length:.0f} mm")
    c4.metric("Fabric Area", f"{area_m2:.2f} m²")

    st.info(f"ℹ️ **Logic:** The steel pipe can hold **{p_steel_capacity:.1f} MPa** ({p_steel_capacity*10:.0f} bar). The design pressure is **{pressure_mpa:.1f} MPa**. The composite reinforces the difference.")

def main():
    st.title("🔧 Prowrap Repair Calculator (Load Sharing)")
    
    # Sidebar
    st.sidebar.header("Inputs")
    pipe_od = st.sidebar.number_input("Pipe OD [mm]", 457.2)
    wall = st.sidebar.number_input("Nominal Wall [mm]", 9.53)
    yield_str = st.sidebar.number_input("Yield Strength [MPa]", 359.0)
    pressure = st.sidebar.number_input("Pressure [bar]", 50.0)
    temp = st.sidebar.number_input("Temp [°C]", 40.0)
    
    defect_type = st.sidebar.selectbox("Mechanism", ["Corrosion", "Crack", "Leak"])
    rem_wall = st.sidebar.number_input("Remaining Wall [mm]", 4.5)
    
    # 0.72 input will now result in 2 layers for corrosion
    design_factor = st.sidebar.number_input("Design Factor", 0.72, min_value=0.1, max_value=1.0)
    
    if st.sidebar.button("Calculate"):
        run_calculation(pipe_od, wall, pressure, temp, defect_type, "External", 200, rem_wall, yield_str, design_factor)

if __name__ == "__main__":
    main()
