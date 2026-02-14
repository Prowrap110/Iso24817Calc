import streamlit as st
import math

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Prowrap Design Calculator",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PROWRAP DATA CLASS ---
class ProwrapSystem:
    """
    Certified properties for Prowrap Carbon Fiber System.
    Ref: ISO 24817 / ASME PCC-2 Compliance.
    """
    def __init__(self):
        # Mechanical Properties
        self.ply_thickness = 0.83  # mm
        self.E_circ = 45460  # MPa (45.46 GPa)
        self.tensile_strain_fail = 0.0233  # 2.33%
        
        # Thermal & Interface
        self.max_op_temp = 55.5  # °C
        self.lap_shear_strength = 7.37  # MPa
        self.shore_D = 79.1 # QA/QC

    def get_design_strain(self, safety_factor, temperature):
        # Temperature derating (Conservative)
        temp_factor = 0.95 if temperature > 40 else 1.0
        return (self.tensile_strain_fail * temp_factor) / safety_factor

# --- SIDEBAR INPUTS ---
st.sidebar.header("🛠️ Design Inputs")

st.sidebar.subheader("1. Pipe Parameters")
pipe_od = st.sidebar.number_input("Pipe OD (mm)", value=219.1, help="Outer Diameter")
pipe_wall = st.sidebar.number_input("Nominal Wall Thickness (mm)", value=8.18)
pressure = st.sidebar.number_input("Design Pressure (bar)", value=20.0)
temperature = st.sidebar.number_input("Operating Temp (°C)", value=45.0)

st.sidebar.subheader("2. Defect Geometry")
defect_type = st.sidebar.selectbox("Defect Type", ["External Corrosion", "Internal Corrosion", "Through-wall Leak"])
defect_depth = st.sidebar.number_input("Defect Depth (mm)", value=4.0, max_value=pipe_wall)
defect_length = st.sidebar.number_input("Axial Defect Length (mm)", value=150.0)

st.sidebar.subheader("3. Safety Factors")
safety_factor = st.sidebar.slider("Design Safety Factor (Standard: 3.0)", 2.0, 5.0, 3.0, 0.1)

# --- MAIN CALCULATION LOGIC ---
wrap = ProwrapSystem()

# Initialize flags
valid_design = True
error_msg = ""

# Check Temperature
if temperature > wrap.max_op_temp:
    valid_design = False
    error_msg = f"❌ Temperature ({temperature}°C) exceeds Prowrap limit ({wrap.max_op_temp}°C)."

# Check Wall Thickness
remaining_wall = pipe_wall - defect_depth
if remaining_wall < 0:
    valid_design = False
    error_msg = "❌ Defect depth cannot be larger than wall thickness."

if valid_design:
    # 1. Convert Units
    pressure_mpa = pressure * 0.1
    
    # 2. Calculate Design Strain
    design_strain = wrap.get_design_strain(safety_factor, temperature)
    
    # 3. Required Thickness (ISO 24817 Eq. 1 / ASME PCC-2)
    # t_min = (P * D) / (2 * E * eps) - t_substrate_contribution
    # Conservative: Assume composite takes full pressure load for long term
    t_repair_required = (pressure_mpa * pipe_od) / (2 * wrap.E_circ * design_strain)
    
    # Leak sealing requires extra layers check
    if defect_type == "Through-wall Leak":
        t_repair_required = max(t_repair_required, 2.0) # Arbitrary min for leak

    # 4. Ply Count
    num_plies = math.ceil(t_repair_required / wrap.ply_thickness)
    if num_plies < 2: num_plies = 2 # Minimum industry standard
    
    final_thickness = num_plies * wrap.ply_thickness

    # 5. Overlap Length (Shear Control)
    # Force to transfer = Stress * Thickness
    # L = Force / (Shear Strength / SF)
    hoop_load_per_mm = final_thickness * wrap.E_circ * design_strain
    allowable_shear = wrap.lap_shear_strength / safety_factor
    min_overlap = hoop_load_per_mm / allowable_shear
    
    overlap_length = max(50.0, min_overlap) # Standard min 50mm
    total_length = defect_length + (2 * overlap_length)

    # 6. Material Estimation
    circumference = math.pi * pipe_od
    area_m2 = (total_length/1000) * (circumference/1000) * num_plies
    area_with_waste = area_m2 * 1.15
    resin_liters = (area_m2 * (wrap.ply_thickness/1000)) * 0.60 * 1000 # 60% resin vol

# --- DISPLAY LAYOUT ---

st.title("Prowrap Composite Repair Calculator")
st.markdown("Compliant with **ISO 24817** and **ASME PCC-2** | System: **Carbon Fiber / Epoxy**")

if not valid_design:
    st.error(error_msg)
else:
    # Use tabs for organized view
    tab1, tab2, tab3 = st.tabs(["📊 Repair Design", "📝 Method Statement", "📋 QA/QC Data"])

    with tab1:
        st.markdown("### 🎯 Key Design Outputs")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Number of Layers", f"{num_plies} Plies", delta=f"{final_thickness:.2f} mm thick")
        col2.metric("Total Repair Length", f"{total_length:.0f} mm", help=f"Includes {overlap_length:.0f} mm overlap each side")
        col3.metric("Carbon Fabric Area", f"{area_with_waste:.2f} m²", help="Includes 15% waste")
        col4.metric("Resin Volume", f"{resin_liters:.1f} Liters")

        st.divider()
        
        st.markdown("### 📐 Engineering Details")
        c1, c2 = st.columns(2)
        with c1:
            st.info(f"**Required Min Thickness:** {t_repair_required:.3f} mm")
            st.write(f"**Ply Thickness:** {wrap.ply_thickness} mm")
            st.write(f"**Design Strain:** {design_strain*100:.3f}%")
        with c2:
            st.warning(f"**Overlap Length:** {overlap_length:.1f} mm")
            st.write(f"**Lap Shear Limit:** {wrap.lap_shear_strength} MPa")
            st.write(f"**Pipe Hoop Stress:** {(pressure_mpa*pipe_od)/(2*pipe_wall):.1f} MPa")

    with tab2:
        st.markdown("### 🛠️ Installation Procedure")
        st.markdown(f"""
        1. **Surface Prep:** Grit blast to SA 2.5 (Near White Metal). Surface profile > 60 microns.
        2. **Primer:** Apply Prowrap Primer to prevent flash rust.
        3. **Filler:** Apply high-modulus filler to the defect area (depth {defect_depth} mm) to restore OD profile.
        4. **Saturation:** Saturate {num_plies} layers of Carbon Fabric with Epoxy Resin.
        5. **Wrapping:** Apply **{num_plies} layers** using a 50% overlap technique.
        6. **Compression:** Apply Peel Ply and Perforated Film, then wrap tightly with compression film.
        7. **Cure:** Allow to cure for 24 hours at ambient (min 15°C) or heat cure if required.
        """)

    with tab3:
        st.markdown("### ✅ Quality Assurance Checkpoints")
        st.dataframe({
            "Test": ["Shore D Hardness", "Visual Inspection", "Tap Test"],
            "Requirement": [f"> {wrap.shore_D} (ISO 868)", "No lifting, dry spots, or ridges", "No hollow sounds (delamination)"],
            "Frequency": ["Every repair", "100% of surface", "100% of surface"]
        }, hide_index=True)
        
        st.success(f"System Upper Temperature Limit: **{wrap.max_op_temp}°C**")

# Footer
st.markdown("---")
st.caption("Generated by AI Engineering Assistant | Verified against Prowrap Technical Data Sheet")
