import streamlit as st
import math

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Prowrap Material Optimizer", page_icon="🧶", layout="wide")

# --- 2. PROWRAP CERTIFIED DATA ---
PROWRAP = {
    "ply_thickness": 0.83,
    "modulus_circ": 45460,
    "strain_fail": 0.0233,
    "lap_shear": 7.37,
    "max_temp": 55.5,
    "shore_d": 79.1,
    "cloth_width_mm": 300  # Standard roll width
}

def run_calculation(od, wall, pressure, temp, defect_type, defect_loc, length, rem_wall, yield_strength, design_factor):
    # --- A. ENGINEERING CALCS (Same as previous verified logic) ---
    safety_factor = 1.0 / design_factor
    temp_factor = 0.95 if temp > 40 else 1.0
    design_strain = (PROWRAP["strain_fail"] * temp_factor) / safety_factor
    pressure_mpa = pressure * 0.1
    allowable_steel_stress = yield_strength * design_factor
    
    # Effective Capacity
    theoretical_capacity = (2 * allowable_steel_stress * rem_wall) / od
    wall_loss_ratio = (wall - rem_wall) / wall
    is_severe = wall_loss_ratio > 0.65
    
    if defect_type in ["Leak", "Crack", "Dent"] or defect_loc == "Internal" or is_severe:
        p_steel_capacity = 0.0
        p_comp_design = pressure_mpa
    else:
        p_steel_capacity = theoretical_capacity
        p_comp_design = max(0, pressure_mpa - p_steel_capacity)

    t_req = (p_comp_design * od) / (2 * PROWRAP["modulus_circ"] * design_strain) if p_comp_design > 0 else 0
    num_plies = math.ceil(t_req / PROWRAP["ply_thickness"])
    min_plies = 4 if defect_type == "Leak" else 2
    num_plies = max(num_plies, min_plies)
    final_t = num_plies * PROWRAP["ply_thickness"]

    # --- B. OVERLAP & REPAIR LENGTH ---
    is_type_a = (defect_loc == "External") and (defect_type == "Corrosion") and not is_severe
    if is_type_a:
        overlap = max(50.0, 3.0 * final_t)
    else:
        hoop_load = final_t * PROWRAP["modulus_circ"] * design_strain
        overlap = max(hoop_load / (PROWRAP["lap_shear"] / safety_factor), 50.0)
    
    l_total_calc = length + (2 * overlap)

    # --- C. MATERIAL OPTIMIZATION (User Formula) ---
    if l_total_calc <= PROWRAP["cloth_width_mm"]:
        optimized_axial_cloth = PROWRAP["cloth_width_mm"]
        num_bands = 1
    else:
        num_bands = math.ceil((l_total_calc - 300) / 250) + 1
        optimized_axial_cloth = num_bands * 300 # mm
    
    circumference_m = (math.pi * od) / 1000
    axial_cloth_m = optimized_axial_cloth / 1000
    
    # Optimized SQM based on physical roll usage
    optimized_sqm = axial_cloth_m * circumference_m * num_plies
    
    # Epoxy Calculation (Optimized for Prowrap 300g/600g systems)
    # Using 1.2 kg per sqm as a safety threshold for saturation + waste
    epoxy_kg = optimized_sqm * 1.1 

    # --- D. DISPLAY ---
    st.success("✅ Material Usage Optimized")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Layers", f"{num_plies}")
    c2.metric("Procurement Length", f"{optimized_axial_cloth} mm", help=f"Calculated {l_total_calc:.0f}mm rounded to {num_bands} bands of 300mm")
    c3.metric("Total Fabric", f"{optimized_sqm:.2f} m²")
    c4.metric("Epoxy Required", f"{epoxy_kg:.1f} kg")

    tab1, tab2 = st.tabs(["📝 Optimized Bill of Materials", "📄 Method Statement"])
    
    with tab1:
        st.markdown("### 📦 Procurement List")
        st.table({
            "Item": ["Prowrap Carbon Cloth (300mm)", "Prowrap Epoxy Resin", "Load Transfer Filler", "Consumables"],
            "Quantity": [f"{optimized_sqm:.2f} m²", f"{epoxy_kg:.1f} kg", "As required for defect", "1 Set (Brushes, Rollers, Peel-ply)"],
            "Note": [f"Cut into {num_bands} bands of {circumference_m:.2f}m length", "Mix in small batches", "For defect filling", "PPE included"]
        })

    with tab2:
        st.markdown(f"### 📋 Application Procedure for {num_bands} Band(s)")
        st.write(f"1. **Surface Prep:** Clean and grit blast to SA 2.5.")
        st.write(f"2. **Band Application:** This repair requires **{num_bands}** circumferential bands.")
        if num_bands > 1:
            st.write(f"   * *Note:* Overlap each 300mm band by 50mm axially to ensure continuity.")
        st.write(f"3. **Wrapping:** Apply **{num_plies} layers** per band.")
        st.write(f"4. **QC:** Measure Shore D hardness (Goal: > {PROWRAP['shore_d']}).")

def main():
    st.title("🧶 Prowrap Optimized Material Calculator")
    st.sidebar.header("Inputs")
    od = st.sidebar.number_input("Pipe OD [mm]", value=457.2)
    wall = st.sidebar.number_input("Nominal Wall [mm]", value=9.53)
    yield_str = st.sidebar.number_input("Yield [MPa]", value=359.0)
    pres = st.sidebar.number_input("Pressure [bar]", value=50.0)
    temp = st.sidebar.number_input("Temp [°C]", value=40.0)
    type_ = st.sidebar.selectbox("Mechanism", ["Corrosion", "Dent", "Leak", "Crack"])
    len_ = st.sidebar.number_input("Defect Axial Length [mm]", value=100.0)
    rem_ = st.sidebar.number_input("Remaining Wall [mm]", value=4.5)
    df = st.sidebar.number_input("Design Factor", value=0.72)

    if st.sidebar.button("Optimize Usage", type="primary"):
        run_calculation(od, wall, pres, temp, type_, "External", len_, rem_, yield_str, df)

if __name__ == "__main__":
    main()
