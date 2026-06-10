"""Pure calculation functions for the PROWRAP repair calculator."""

import math

from iso24817_typea_class3 import TypeAClass3Inputs, calculate_type_a_class3
from prowrap_materials import PROWRAP


def _validate_inputs(
    od,
    wall,
    pressure,
    temp,
    length,
    rem_wall,
    yield_strength,
    design_factor,
    design_life,
):
    errors = []
    if od <= 0:
        errors.append("Pipe outer diameter must be greater than zero.")
    if wall <= 0:
        errors.append("Nominal wall thickness must be greater than zero.")
    if pressure < 0:
        errors.append("Design pressure cannot be negative.")
    if temp > PROWRAP["max_temp"]:
        errors.append(
            f"Operating temperature ({temp} degC) exceeds Prowrap limit of "
            f"{PROWRAP['max_temp']} degC."
        )
    if length <= 0:
        errors.append("Defect length must be greater than zero.")
    if rem_wall < 0:
        errors.append("Remaining wall thickness cannot be negative.")
    if rem_wall > wall:
        errors.append(
            "Remaining wall thickness cannot be greater than nominal wall thickness."
        )
    if yield_strength <= 0:
        errors.append("Pipe yield strength must be greater than zero.")
    if not 0 < design_factor <= 1:
        errors.append("Design factor must be greater than zero and less than or equal to 1.")
    if design_life < 1:
        errors.append("Design life must be at least 1 year.")

    if errors:
        raise ValueError("\n".join(errors))


def calculate_repair(
    customer,
    location,
    report_no,
    od,
    wall,
    pressure,
    temp,
    defect_type,
    defect_loc,
    length,
    rem_wall,
    yield_strength,
    design_factor,
    design_life,
    force_3_layers=False,
):
    """Calculate repair outputs using the current legacy Streamlit formulas."""
    _validate_inputs(
        od,
        wall,
        pressure,
        temp,
        length,
        rem_wall,
        yield_strength,
        design_factor,
        design_life,
    )

    wall_loss_ratio = (wall - rem_wall) / wall
    is_severe_loss = wall_loss_ratio > 0.65

    calc_method_thick = "Type B (Total Replacement)"
    calc_method_overlap = "Type B (Shear Controlled)"

    if defect_type == "Corrosion":
        if defect_loc == "External" and not is_severe_loss:
            calc_method_thick = "Type A (Load Sharing)"
            calc_method_overlap = "Type A (Geometry Controlled)"
        else:
            calc_method_thick = "Type B (Total Replacement)"
            calc_method_overlap = "Type B (Shear Controlled)"
    elif defect_type == "Dent":
        calc_method_thick = "Type A (Dent Reinforcement)"
        calc_method_overlap = "Type B (Shear Controlled)"
    elif defect_type in ["Leak", "Crack"]:
        calc_method_thick = "Type B (Total Replacement)"
        calc_method_overlap = "Type B (Shear Controlled)"

    safety_factor = 1.0 / design_factor
    temp_factor = 0.95 if temp > 40 else 1.0
    design_strain = (PROWRAP["strain_fail"] * temp_factor) / safety_factor

    pressure_mpa = pressure * 0.1
    allowable_steel_stress = yield_strength * design_factor
    theoretical_capacity = (2 * allowable_steel_stress * rem_wall) / od

    if defect_type in ["Leak", "Crack"] or defect_loc == "Internal" or is_severe_loss:
        p_steel_capacity = 0.0
    else:
        p_steel_capacity = theoretical_capacity

    if "Type A" in calc_method_thick and p_steel_capacity > 0:
        p_composite_design = max(0, pressure_mpa - p_steel_capacity)
    else:
        p_composite_design = pressure_mpa

    if p_composite_design > 0:
        t_required = (
            p_composite_design * od
        ) / (2 * PROWRAP["modulus_circ"] * design_strain)
    else:
        t_required = 0.0

    num_plies = math.ceil(t_required / PROWRAP["ply_thickness"])
    min_plies = 4 if defect_type == "Leak" else 2
    num_plies = max(num_plies, min_plies)

    is_upgraded = False
    if force_3_layers and num_plies < 3:
        num_plies = 3
        is_upgraded = True

    final_thickness = num_plies * PROWRAP["ply_thickness"]

    if "Type A" in calc_method_overlap:
        overlap_shear_basis = "geometry_minimum"
        overlap_shear_strength = None
        overlap_length = max(50.0, 3.0 * final_thickness)
    else:
        hoop_load = final_thickness * PROWRAP["modulus_circ"] * design_strain
        overlap_shear_basis = "long_term_lap_shear"
        overlap_shear_strength = PROWRAP["long_term_lap_shear"]
        allowable_shear = overlap_shear_strength / safety_factor
        overlap_length = max(hoop_load / allowable_shear, 50.0)

    total_repair_length_calc = length + (2 * overlap_length)

    if total_repair_length_calc <= PROWRAP["cloth_width_mm"]:
        num_bands = 1
        procurement_axial_length = 300
    else:
        num_bands = math.ceil((total_repair_length_calc - 300) / 250) + 1
        procurement_axial_length = num_bands * 300

    circumference_m = (math.pi * od) / 1000
    axial_procurement_m = procurement_axial_length / 1000
    optimized_sqm = axial_procurement_m * circumference_m * num_plies
    epoxy_kg = optimized_sqm * 1.2

    return {
        "customer": customer,
        "location": location,
        "report_no": report_no,
        "od": od,
        "wall": wall,
        "yield_str": yield_strength,
        "pressure": pressure,
        "temp": temp,
        "defect_type": defect_type,
        "defect_loc": defect_loc,
        "rem_wall": rem_wall,
        "length": length,
        "wall_loss_ratio": wall_loss_ratio,
        "is_severe_loss": is_severe_loss,
        "calc_method_thick": calc_method_thick,
        "calc_method_overlap": calc_method_overlap,
        "safety_factor": safety_factor,
        "temp_factor": temp_factor,
        "design_strain": design_strain,
        "pressure_mpa": pressure_mpa,
        "p_steel_capacity": p_steel_capacity,
        "p_composite_design": p_composite_design,
        "t_required": t_required,
        "num_plies": num_plies,
        "final_thickness": final_thickness,
        "iso_length": total_repair_length_calc,
        "overlap_length": overlap_length,
        "overlap_shear_basis": overlap_shear_basis,
        "overlap_shear_strength": overlap_shear_strength,
        "num_bands": num_bands,
        "proc_length": procurement_axial_length,
        "sf": safety_factor,
        "design_factor": design_factor,
        "design_life": design_life,
        "optimized_sqm": optimized_sqm,
        "epoxy_kg": epoxy_kg,
        "is_upgraded": is_upgraded,
    }


def calculate_type_a_class3_prowrap_check(
    od,
    pressure_bar,
    temp,
    rem_wall,
    design_life,
    substrate_allowable_pressure_bar=0.0,
    installation_temp=20.0,
    component_type="Straight",
    cyclic_derating_factor=1.0,
):
    """Run the isolated ISO Type A/Class 3 route using PRW110 performance data."""
    inputs = TypeAClass3Inputs(
        pressure_mpa=pressure_bar * 0.1,
        substrate_allowable_pressure_mpa=substrate_allowable_pressure_bar * 0.1,
        outside_diameter_mm=od,
        remaining_wall_mm=rem_wall,
        design_life_years=design_life,
        design_temperature_c=temp,
        installation_temperature_c=installation_temp,
        max_repair_temperature_c=PROWRAP["max_temp"],
        ambient_test_temperature_c=20.0,
        qualification_test_temperature_c=20.0,
        hoop_modulus_mpa=PROWRAP["modulus_circ"],
        axial_modulus_mpa=PROWRAP["modulus_axial"],
        poisson_ratio=PROWRAP["poisson_circ"],
        hoop_cte_per_c=PROWRAP["thermal_expansion_circ"] * 1e-6,
        axial_cte_per_c=PROWRAP["thermal_expansion_axial"] * 1e-6,
        lap_shear_mpa=PROWRAP["long_term_lap_shear"],
        layer_thickness_mm=PROWRAP["ply_thickness"],
        use_performance_data=True,
        long_term_strain_lcl=PROWRAP["long_term_strain_20y"],
        performance_data_source="Design life",
        cyclic_derating_factor=cyclic_derating_factor,
        component_type=component_type,
    )
    result = calculate_type_a_class3(inputs)
    result["input_summary"] = {
        "pressure_bar": pressure_bar,
        "substrate_allowable_pressure_bar": substrate_allowable_pressure_bar,
        "hoop_modulus_mpa": PROWRAP["modulus_circ"],
        "axial_modulus_mpa": PROWRAP["modulus_axial"],
        "lap_shear_mpa": PROWRAP["long_term_lap_shear"],
        "long_term_strain_20y": PROWRAP["long_term_strain_20y"],
        "performance_data": "PRW110 20-year long-term strain",
    }
    return result


calculate_type_a_class3_fallback_check = calculate_type_a_class3_prowrap_check


def apply_type_a_class3_result_to_repair(repair_data, typea_class3_result):
    """Use the ISO Type A/Class 3 result as the controlling displayed repair design."""
    updated = dict(repair_data)
    layer_count = typea_class3_result["layer_count"]
    final_installed_thickness = layer_count * PROWRAP["ply_thickness"]
    overlap_length = typea_class3_result["lover_required_mm"]
    repair_length = updated["length"] + (2.0 * overlap_length)

    if repair_length <= PROWRAP["cloth_width_mm"]:
        num_bands = 1
        procurement_axial_length = PROWRAP["cloth_width_mm"]
    else:
        num_bands = math.ceil(
            (repair_length - PROWRAP["cloth_width_mm"])
            / (PROWRAP["cloth_width_mm"] - PROWRAP["stitching_overlap_mm"])
        ) + 1
        procurement_axial_length = num_bands * PROWRAP["cloth_width_mm"]

    circumference_m = (math.pi * updated["od"]) / 1000.0
    axial_procurement_m = procurement_axial_length / 1000.0
    optimized_sqm = axial_procurement_m * circumference_m * layer_count

    updated.update(
        {
            "calc_method_thick": "ISO 24817 Type A / Class 3",
            "calc_method_overlap": "ISO 24817 Formula 21",
            "t_required": typea_class3_result["tdesign_final_mm"],
            "num_plies": layer_count,
            "final_thickness": final_installed_thickness,
            "iso_length": repair_length,
            "overlap_length": overlap_length,
            "overlap_shear_basis": "iso_formula_21",
            "overlap_shear_strength": PROWRAP["long_term_lap_shear"],
            "num_bands": num_bands,
            "proc_length": procurement_axial_length,
            "optimized_sqm": optimized_sqm,
            "epoxy_kg": optimized_sqm * 1.2,
            "is_upgraded": False,
            "iso_typea_class3": typea_class3_result,
        }
    )
    return updated
