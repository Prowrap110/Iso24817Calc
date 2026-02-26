import streamlit as st
import math
from fpdf import FPDF

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Prowrap Master Calculator",
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
    "shore_d": 70,                # 
    "cloth_width_mm": 300,        
    "stitching_overlap_mm": 50    
}

def create_pdf(report_data):
    """Generates a PDF report and returns it as bytes."""
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="PROWRAP COMPOSITE REPAIR REPORT", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 8, txt="Standard: ISO 24817 / ASME PCC-2", ln=True, align='C')
    pdf.ln(5)

    def add_section(title, data_dict):
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 8, txt=title, ln=True, fill=True)
        pdf.set_font("Arial", '', 11)
        for key, val in data_dict.items():
            pdf.cell(90, 6, txt=f"{key}:", border=0)
            pdf.cell(0, 6, txt=str(val), ln=True, border=0)
        pdf.ln(5)

    add_section("1. Project & Pipeline Data", {
        "Customer": report_data['customer'],
        "Location": report_data['location'],
        "Report No": report_data['report_no'],
        "Pipe Outer Diameter": f"{report_data['od']} mm",
        "Nominal Wall Thickness": f"{report_data['wall']} mm",
        "Pipe Yield Strength": f"{report_data['yield_str']} MPa",
        "Design Pressure": f"{report_data['pressure']} bar",
        "Operating Temperature": f"{report_data['temp']} C"
    })

    add_section("2. Defect Assessment", {
        "Defect Mechanism": report_data['defect_type'],
        "Defect Location": report_data['defect_loc'],
        "Remaining Wall": f"{report_data['rem_wall']} mm",
        "Axial Length": f"{report_data['length']} mm",
        "Wall Loss": f"{report_data['wall_loss_ratio']*100:.1f} %",
        "Repair Logic": report_data['calc_method_thick']
    })

    add_section("3. Optimized Repair Design", {
        "Required Plies": f"{report_data['num_plies']} Layers",
        "Repair Thickness": f"{report_data['final_thickness']:.2f} mm",
        "Min. Required ISO Length": f"{report_data['iso_length']:.0f} mm",
        "Procurement Length": f"{report_data['proc_length']} mm ({report_data['num_bands']} Bands)",
        "Design Factor": f"{report_data['design_factor']}"  # UPDATED: Shows Design Factor
    })

    add_section("4. Material Procurement", {
        "Fabric Needed (300mm Roll)": f"{report_data['optimized_sqm']:.2f} sqm",
        "Epoxy Required": f"{report_data['epoxy_kg']:.1f} kg"
    })

    # --- METHOD STATEMENT SECTION IN PDF ---
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(0, 8, txt="5. Installation Checklist (Method Statement)", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    
    steps = [
        "1. Surface Prep: Grit blast to SA 2.5; Profile >60 microns.",
        "2. Primer/Filler: Apply Prowrap Filler to defect area to restore OD.",
        f"3. Lamination: Saturate Carbon Cloth. Apply {report_data['num_plies']} layers per band.",
        f"4. Wrapping: Use {report_data['num_bands']} band(s)
