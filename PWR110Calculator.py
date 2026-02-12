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
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #2E86C1; }
    .warning-card { background-color: #fff3cd; padding: 20px; border-radius: 10px; border-left: 5px solid #ffc107; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Pipe Data")
D_mm = st.sidebar.number_input("Pipe Outer Diameter (mm)", value=1219.2, step=10.0)
t_wall_mm = st.sidebar.number_input("Pipe Wall Thickness (mm)", value=14.3, step=0.1)
SMYS_MPa = st.sidebar.number_input("Pipe SMYS (Yield Strength) (MPa)", value=358.0, help="e.g., Grade B=241, X52=358, X60=413, X65=448")

st.sidebar.header("2. Defect Data")
L_defect_mm = st.sidebar.number_input("Axial Length of Defect (mm)", value=100.0, step=10.0)
defect_depth_pct = st.sidebar.slider("Defect Depth (%)", min_value=0, max_value=80, value=40, help="Percentage of wall thickness lost")

st.sidebar.header("3. Operating Conditions")
P_design_bar = st.sidebar.number_input("Design Pressure (bar)", value=75.0, step=1.0)
T_design_C = st.sidebar.number_input("Design Temperature (°C)", value=40.0, step=1.0)
T_install_C = st.sidebar.number_input("Installation Temperature (°C)", value=25.0, step=1.0)
lifetime_years = st.sidebar.selectbox("Design Lifetime (Years)", [2, 5, 10, 20], index=3)
repair_type = st.sidebar.radio("Repair Type", ["Type A (Non-leaking)", "Type B (Leaking/Through-wall)"])

# --- MATERIAL PROPERTIES (Prowrap 110) ---
material_data = {
    "Name": "Prowrap 110",
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
d_defect = t_wall_mm * (defect_depth_pct / 100.0)
t_remaining = t_wall_mm - d_defect

# Modified B31G Calculation for Ps
# Flow Stress (S_flow) = SMYS + 69 MPa (Standard assumption)
S_flow = SMYS_MPa + 69.0 

# Folias Factor (M) - Modified B31G approximation
z = (L_defect_mm**2) / (D_mm * t_wall_mm)
if z <= 50:
    M = math.sqrt(1 + 0.6275 * z - 0.003375 * z**2)
else:
    M = 0.032 * z + 3.3

# Shape Factor for Modified B31G (0.85dL)
# Ps = (2 * S_flow * t / D) * ( (1 - 0.85 * d/t) / (1 - 0.85 * d/t / M) )
R_SF = 0.85 # Remaining Strength Factor constant
term_numerator = 1 - (R_SF * (d_defect / t_wall_mm))
term_denominator = 1 - (R_SF * (d_defect / t_wall_mm) / M)

P_safe_MPa = (2 * S_flow * t_wall_mm / D_mm) * (term_numerator / term_denominator)
P_safe_bar = P_safe_MPa * 10.0 # Convert MPa back to bar for display consistency

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

# If Design Pressure > Safe Pressure, we need reinforcement
if P_design_MPa > P_safe_MPa:
    # ISO Eq 7
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
    # If the pipe is NOT leaking (Type A), check if defect is deep
    # If defect > 80% or P_safe is very low, treat closer to Type B, 
    # but strictly per ISO Type A logic:
    L_over_final = L_over_A
else:
    L_over_final = max(L_over_A, L_over_B)

L_taper = 40 
L_total = (2 * L_over_final) + L_defect_mm + (2 * L_taper)

# --- DISPLAY RESULTS ---

# Top Alert if Safe Pressure is low
if P_safe_MPa < P_design_MPa:
    st.warning(f"⚠️ Pipe is unsafe! Design Pressure ({P_design_bar} bar) > Safe Pressure ({P_safe_bar:.2f} bar). Repair required.")
else:
    st.success(f"✅ Pipe is safe without repair (Ps = {P_safe_bar:.2f} bar). Minimum layers applied for protection.")

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader("📋 Repair Thickness")
    st.write(f"Defect Depth: **{defect_depth_pct}%** ({d_defect:.1f} mm)")
    st.write(f"Calculated Safe Pressure (Ps): **{P_safe_bar:.2f} bar**")
    st.markdown("---")
    st.write(f"Min Thickness Required: **{t_min:.2f} mm**")
    st.markdown(f"Final Layers: <span class='big-font'>{n_layers}</span>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader("📏 Repair Length")
    st.write(f"Overlap Length (L_over): **{L_over_final:.1f} mm**")
    st.write(f"Defect Length: **{L_defect_mm} mm**")
    st.write(f"Taper Length (x2): **{L_taper*2} mm**")
    st.markdown(f"Total Axial Length: <span class='big-font'>{math.ceil(L_total)} mm</span>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with st.expander("See Modified B31G Calculation Details"):
    st.write("Safe pressure calculated using Modified B31G method (0.85dL Area Method).")
    st.latex(r"M = \sqrt{1 + 0.6275 \frac{L^2}{Dt} - 0.003375 (\frac{L^2}{Dt})^2}")
    st.write(f"**Folias Factor (M):** {M:.4f}")
    st.write(f"**Flow Stress (S_flow):** {S_flow} MPa")
    st.write(f"**Safe Pressure (Ps):** {P_safe_MPa:.2f} MPa ({P_safe_bar:.2f} bar)")
