import math

class ProwrapSystem:
    """
    Database of Prowrap Certified Properties derived from provided datasheet.
    """
    def __init__(self):
        # Mechanical Properties
        self.ply_thickness = 0.83  # mm
        self.E_circ = 45460  # MPa (45.46 GPa)
        self.E_axial = 43800  # MPa (43.8 GPa)
        self.tensile_strength_circ = 574.1  # MPa
        self.tensile_strain_fail = 0.0233  # 2.33%
        
        # Thermal & Interface
        self.Tg = 75.5  # °C
        self.max_op_temp = 55.5  # °C
        self.lap_shear_strength = 7.37  # MPa
        
        # QA/QC
        self.shore_D = 79.1
    
    def get_allowable_strain(self, safety_factor=3.0, temperature=25):
        """
        Returns design strain with temp derating and safety factor.
        ISO 24817/ASME PCC-2 typically limits long-term strain to ~0.25% - 0.3% 
        or applies factors. Here we use the simplified SF approach from your prompt.
        """
        # Temperature derating factor (Simplified step based on prompt)
        temp_factor = 1.0
        if temperature > 40:
            temp_factor = 0.95
            
        derated_strain = self.tensile_strain_fail * temp_factor
        return derated_strain / safety_factor

def calculate_repair(
    pipe_od_mm, 
    pipe_wall_mm, 
    pressure_bar, 
    temperature_c, 
    defect_depth_mm, 
    defect_length_mm, 
    defect_type="External Corrosion"
):
    print("="*60)
    print(f"PROWRAP COMPOSITE REPAIR CALCULATOR (ISO 24817 / ASME PCC-2)")
    print("="*60)

    # --- 1. Load Material Data ---
    wrap = ProwrapSystem()
    
    # --- 2. Input Validation ---
    if temperature_c > wrap.max_op_temp:
        print(f"❌ CRITICAL ERROR: Temp ({temperature_c}°C) exceeds Prowrap limit ({wrap.max_op_temp}°C).")
        return
    
    remaining_wall = pipe_wall_mm - defect_depth_mm
    if remaining_wall < 0:
        print("❌ CRITICAL ERROR: Defect depth exceeds wall thickness.")
        return

    # --- 3. Design Parameters ---
    pressure_mpa = pressure_bar * 0.1
    # Allowable strain (epsilon_d)
    # Using SF=3.0 per your request, though standards often use partial factors
    design_strain = wrap.get_allowable_strain(safety_factor=3.0, temperature=temperature_c)
    
    print(f"INPUT DATA:")
    print(f"  Pipe OD: {pipe_od_mm} mm | Wall: {pipe_wall_mm} mm")
    print(f"  Pressure: {pressure_bar} bar | Temp: {temperature_c}°C")
    print(f"  Defect: {defect_type} | Depth: {defect_depth_mm} mm")
    print("-" * 60)

    # --- 4. Thickness Calculation (Strain Based) ---
    # Reference: ASME PCC-2 Art 4.1 Eq (1) / ISO 24817 Eq (4)
    # t_min = (P * D) / (2 * E_c * eps) - t_remaining_effective
    # Note: For conservative design, we assume the composite takes the full hoop load
    # if the internal substrate has yielded, or we share load. 
    # Here we calculate thickness assuming composite carries internal pressure capacity lost.
    
    # Substrate strain at design pressure
    pipe_hoop_stress = (pressure_mpa * pipe_od_mm) / (2 * remaining_wall)
    
    # Required thickness to keep composite strain below limit:
    # t = (P * D) / (2 * E_c * design_strain)
    t_repair_required = (pressure_mpa * pipe_od_mm) / (2 * wrap.E_circ * design_strain)
    
    # If the pipe still has significant wall, ISO allows subtracting the contribution of the steel.
    # However, standard practice for "Type A" corrosion often calculates repair 
    # to restore full MAOP equivalent. We stick to the conservative t_required above.

    # --- 5. Ply Calculation ---
    num_plies = math.ceil(t_repair_required / wrap.ply_thickness)
    # Minimum 2 layers required by most standards even if calc is low
    if num_plies < 2: 
        num_plies = 2
        
    final_thickness = num_plies * wrap.ply_thickness

    # --- 6. Repair Length & Overlap (Shear Check) ---
    # Axial Load force per unit circumference to be transferred = P * D / 4 (for closed end)
    # Or based on defect length.
    # Min Overlap Length (L_over) based on Lap Shear Strength (tau):
    # L_over = (E_c * eps * t_repair) / (2 * tau) * Safety_Factor
    # We use conservative stress transfer:
    
    composite_tensile_force = final_thickness * wrap.E_circ * design_strain
    # Using simple shear lag model L = Force / Tau
    # Applying SF=3.0 on shear transfer as well
    min_overlap = (composite_tensile_force) / (wrap.lap_shear_strength / 3.0)
    
    # ASME/ISO typically require min 50mm or calculated value
    overlap_length = max(50.0, min_overlap)
    
    total_repair_length = defect_length_mm + (2 * overlap_length)

    # --- 7. Material Estimates ---
    circumference = math.pi * pipe_od_mm
    total_area_m2 = (total_repair_length/1000) * (circumference/1000) * num_plies
    # Adding 15% waste factor
    total_area_m2_safe = total_area_m2 * 1.15
    
    # Resin Usage (Approx 1.2 kg/m2 for heavy carbon, or vol based)
    # Using volume approach: 
    composite_vol_m3 = total_area_m2 * (wrap.ply_thickness / 1000)
    # Assuming 60% resin volume per your prompt (high, but safe for estimation)
    resin_liters = composite_vol_m3 * 0.60 * 1000 

    # --- 8. Results Output ---
    print(f"CALCULATION RESULTS (PROWRAP):")
    print(f"  ✓ Required Thickness:     {t_repair_required:.2f} mm")
    print(f"  ✓ Certified Ply Thick:    {wrap.ply_thickness} mm")
    print(f"  ✓ Selected No. of Plies:  {num_plies} layers")
    print(f"  ✓ Final Repair Thickness: {final_thickness:.2f} mm")
    print(f"  ✓ Min. Overlap Length:    {overlap_length:.1f} mm (Controlled by Lap Shear {wrap.lap_shear_strength} MPa)")
    print(f"  ✓ Total Repair Length:    {total_repair_length:.1f} mm")
    print(f"")
    print(f"MATERIAL ESTIMATION:")
    print(f"  ✓ Carbon Fabric Needed:   {total_area_m2_safe:.2f} m² (incl. 15% waste)")
    print(f"  ✓ Resin Volume Est.:      {resin_liters:.2f} Liters")
    print(f"")
    print(f"COMPLIANCE CHECKS:")
    print(f"  ✓ Design Strain:          {design_strain*100:.3f}% (Limit: {wrap.tensile_strain_fail*100:.2f}% / 3.0)")
    print(f"  ✓ Temperature:            {temperature_c}°C (Limit {wrap.max_op_temp}°C)")
    print(f"  ✓ Shore D Requirement:    {wrap.shore_D} (for QC)")

# --- EXAMPLE USAGE ---
# You can change these values to test different scenarios
calculate_repair(
    pipe_od_mm=219.1,       # 8 inch pipe
    pipe_wall_mm=8.18,      # Sch 40
    pressure_bar=20,        # Design Pressure
    temperature_c=45,       # Operating Temp
    defect_depth_mm=4.0,    # 50% wall loss
    defect_length_mm=150,   # Axial length of corrosion
    defect_type="Ext Corrosion"
)
