import streamlit as st
import math

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Prowrap Repair Calculator",
    page_icon="🔧",
    layout="wide"
)

# --- PROWRAP CERTIFIED DATA ---
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
    
    # SAFETY FACTOR INPUT
    design_factor = st.sidebar.number_input("Design Factor (f)", value=0.72, min_value=0.01, max_value=1.0, format="%.3f", help="Safety Factor = 1 / Design Factor")

    # --- CALCULATION BUTTON ---
    if st.sidebar.button("Calculate Repair", type="primary"):
        run_calculation(
            pipe_od, nominal_wall, design_pressure, op_temp, 
            defect_mechanism, defect_location, defect_length, remaining_wall, yield_strength,
            design_factor
        )

def run_calculation(od, wall, pressure, temp, defect_type, defect_loc, length, rem_wall, yield_strength, design_factor):
    
    # --- 1. VALIDATION ---
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

    # --- 2. ENGINEERING CALCULATIONS ---
    
    # A. Safety Factor (1 / Design Factor)
    safety_factor = 1.0 / design_factor

    # B. Allowable Strain (Epsilon Design)
    temp_factor = 0.95 if temp > 40 else 1.0
    design_strain = (PROWRAP["strain_fail"] * temp_factor) / safety_factor

    # C
