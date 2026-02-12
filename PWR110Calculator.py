import streamlit as st
import math
import pandas as pd
import numpy as np

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="ISO 24817 Repair Calculator", page_icon="🔧", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; color: #2E86C1; }
    .warning-text { font-size:24px !important; font-weight: bold; color: #D35400; }
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #2E86C1; }
    .warning-card { background-color: #fff3cd; padding: 20px; border-radius: 10px; border-left: 5px solid #ffc107; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Pipe Data")
D_mm = st.sidebar.number_input("Pipe Outer Diameter (mm)", value=1219.2, step=10.0)
t_wall_mm = st.sidebar.number_input("Nominal Wall Thickness (mm)", value=14.3, step=0.1)
SMYS_MPa = st.sidebar.number_input("Pipe SMYS (Yield Strength) (MPa)", value=358.0, help="e.g., Grade B=241, X52=358, X60=413, X65=448")

st.sidebar.header("2. Defect Dimensions")
L_defect_mm = st.sidebar.number_input("Defect Axial Length (mm)", value=100.0, step=10.0)
W_defect_mm = st.sidebar.number_input("Defect Circumferential Width (mm)", value=50.0, step=10.0)
t_remaining_mm = st.sidebar.number_input("Remaining Wall Thickness (mm)", value=8.5, step=0.1, help="The thinnest point of the wall at the defect")

st.sidebar.header("3. Operating Conditions")
P_design_bar = st.sidebar.number_input("Design Pressure (bar)", value=75.0, step=1.0)
T_design_C = st.sidebar.number_input("Design Temperature (°C)", value=40.0, step=1.0)
T_install_C = st.sidebar.number_input("Installation Temperature (°C)", value=25.0, step=1.0)
lifetime_years = st.sidebar.selectbox("Design Lifetime (Years)", [2, 5, 10, 20], index=3)
repair_type = st.sidebar.radio("Repair Type", ["Type A (Non-leaking)", "Type B (Leaking/Through-wall)"])

# --- MATERIAL PROPERTIES (Prowrap 110) ---
material_data = {
    "Name": "Prowrap 110",
    # Short keys for formulas
    "Ec": 45460,                   # MPa - Hoop modulus
    "Ea": 43800,                   # MPa - Axial modulus
    # Descriptive keys (kept for reference)
    "Ec (Hoop Modulus)": 45460,    # MPa 
    "Ea (Axial Modulus)": 43800,   # MPa
    "Ply Thickness": 0.83,         # mm
    "Tg": 103,                     # °C
    "Tm": 83,                      # °C
    "Lap Shear (tau)": 7.37,       # MPa
    "Alpha_c": 1.034e-05,          # /°C
    "Alpha_s": 1.2e-06             # Steel CTE
}

# --- CALCULATIONS ---

st.title("🔧 ISO 24817 Composite Repair Calculator")
st.markdown(f"**Material Selected:** {material_data['Name']}")

# 1. Calculate Geometry & Safe Pressure (Modified B31G)
# Defect Geometry
if t_remaining_mm > t_wall_mm:
    st.error("Error: Remaining thickness cannot be greater than nominal wall thickness.")
    st.stop()

d_defect = t_wall_mm - t_remaining_mm
depth_ratio = d_defect / t_wall_mm

# Modified B31G Calculation for Ps
# Flow Stress (S_flow) = SMYS + 69 MPa
S_flow = SMYS_MPa + 69.0 

# Folias Factor (M)
z = (L_defect_mm**2) / (D_mm * t_wall_mm)
if z <= 50:
    M = math.sqrt(1 + 0.6275 * z - 0.003375 * z**2)
else:
    M = 0.032 * z + 3.3

# Remaining Strength Factor (0.85dL)
R_SF = 0.85 
term_numerator = 1 - (R_SF * depth_ratio)
term_denominator = 1 - (R_SF * depth_ratio / M)

# Prevent division by zero if defect is very deep/through wall
if term_denominator <= 0 or repair_type.startswith("Type B"):
    P_safe_MPa = 0.0
else:
    P_safe_MPa = (2 * S_flow * t_wall_mm / D_mm) * (term_numerator / term_denominator)

P_safe_bar = P_safe_MPa * 10.0 # Convert MPa back to bar

# 2. Temperature De-rating
f_T = max(0.0, min(1.0, (material_data["Tm"] - T_design_C) / (material_data["Tm"] - 20))) 
if T_design_C > material_data["Tm"]:
    st.error("Error: Design Temperature exceeds Material Upper Limit (Tm)!")
    st.stop()

# 3. Allowable Strain
epsilon_c0 = 0.0025 
delta_T = abs(T_design_C - T_install_C)
term_thermal = delta_T * (material_data["Alpha_s"] - material_data["Alpha_c"])
epsilon_c = (f_T * epsilon_c0) - term_thermal

# 4. Minimum Thickness (Type A)
P_design_MPa = P_design_bar * 0.1

if repair_type.startswith("Type B"):
    # Type B usually requires specific calculation for leaking defects
    # For now, we assume structural reinforcement logic for containment + B check
    # P_safe is 0 for leaking, so full pressure is taken by composite
    t_min = (D_mm / (2 * material_data["Ec"] * epsilon_c)) * (P_design_MPa) 
else:
    # Type A
    if P_design_MPa > P_safe_MPa:
        t_min = (D_mm / (2 * material_data["Ec"] * epsilon_c)) * (P_design_MPa - P_safe_MPa)
    else:
        t_min = 0.0 

n_layers = math.ceil(t_min / material_data["Ply Thickness"])
if n_layers < 2: n_layers = 2
final_thickness = n_layers * material_data["Ply Thickness"]

# 5. Repair Length
epsilon_a = 0.001 
L_over_A = (material_data["Ea"] * epsilon_a * final_thickness) / material_data["Lap Shear (tau)"]
L_over_A = L_over_A * 3.0 # Safety Factor
L_over_A = max(L_over_A, 50.0)

L_over_B = 2 * math.sqrt(D_mm * t_wall_mm)

if repair_type.startswith("Type A"):
    L_over_final = L_over_A
else:
    L_over_final = max(L_over_A, L_over_B)

L_taper = 40 
L_total = (2 * L_over_final) + L_defect_mm + (2 * L_taper)

# --- DISPLAY RESULTS ---

# Top Alert
if repair_type.startswith("Type A"):
    if P_safe_MPa < P_design_MPa:
        st.warning(f"⚠️ Defect weakens pipe below Design Pressure. Ps ({P_safe_bar:.2f} bar) < Pd ({P_design_bar} bar). Repair Required.")
    else:
        st.success(f"✅ Pipe strength is sufficient (Ps = {P_safe_bar:.2f} bar). Repair is optional/protective.")
else:
    st.error("⚠️ Type B (Through-wall/Leaking) Repair selected. Full pressure containment required.")

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader("📋 Repair Thickness")
    st.write(f"Remaining Wall: **{t_remaining_mm} mm**")
    st.write(f"Calculated Safe Pressure (Ps): **{P_safe_bar:.2f} bar**")
    st.markdown("---")
    st.write(f"Min Thickness Required: **{t_min:.2f} mm**")
    
    # Conditional Note for Layer Count
    layer_note = ""
    if n_layers <= 2:
        # Note: 'warning-text' class matches size (24px) but uses orange color
        layer_note = "<br><span class='warning-text'>⚠️ Prowrap recommends 3 layers according to ISO 24817</span>"
        
    st.markdown(f"Final Layers: <span class='big-font'>{n_layers}</span>{layer_note}", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader("📏 Repair Length")
    st.write(f"Overlap Length (L_over): **{L_over_final:.1f} mm**")
    st.write(f"Axial Defect Length: **{L_defect_mm} mm**")
    st.write(f"Circumferential Width: **{W_defect_mm} mm**")
    st.markdown(f"Total Axial Repair Length: <span class='big-font'>{math.ceil(L_total)} mm</span>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with st.expander("See Calculation Details"):
    st.write("Safe pressure calculated using Modified B31G method.")
    st.write(f"**Defect Depth:** {d_defect:.2f} mm")
    st.write(f"**Folias Factor (M):** {M:.4f}")
    st.write(f"**Flow Stress (S_flow):** {S_flow} MPa")
