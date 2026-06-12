"""Pure calculation functions for the PROWRAP repair calculator."""

import math

from b31g import assess_b31g
from iso24817_typea_class3 import (
    TypeAClass3Inputs,
    calculate_type_a_class3,
    component_factor,
)
from prowrap_materials import PROWRAP

# Substrate (carbon steel) coefficient of thermal expansion used for the
# Formula (10) thermal-mismatch term. Matches the TypeAClass3Inputs default
# so the baseline and the rigorous module share the same basis.
SUBSTRATE_CTE_PER_C = 12e-6


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


def iso_type_b_min_thickness(
    pressure_mpa,
    od_mm,
    nominal_wall_mm,
    defect_size_mm,
    design_temp_c,
    design_life_years,
):
    """ISO 24817 Formula (12) - minimum laminate thickness for a circular or
    near-circular through-wall (Type B) defect.

    p = fT2 * fleak * sqrt(0.001 * gamma_LCL / X)
    X = ((1 - nu^2)/E_ac) * (3*d^4/(512*t^3) + d/pi) + 3*d^2/(64*G*t)

    with E_ac = sqrt(Ea*Ec), fleak per Formula (16) Class 3 and gamma_LCL
    from the PRW110 Annex D qualification. Solved for the smallest t whose
    allowable pressure reaches the design pressure.

    Returns (t_min_mm, details_dict).
    """
    gamma_lcl = PROWRAP["gamma_lcl"]
    e_ac = math.sqrt(PROWRAP["modulus_axial"] * PROWRAP["modulus_circ"])
    g = PROWRAP["shear_modulus"]
    nu = PROWRAP["poisson_circ"]

    # Defect size at end of design life; never less than 15 mm (7.5.7).
    d = max(defect_size_mm, 15.0)

    # Formula (16), Class 3 service factor.
    fleak = 0.666 * 10 ** (-0.01584 * (design_life_years - 1.0))
    # Upper service temperature limit (Table 6): Class 3 Type B repairs with
    # lifetime > 2 years are limited to Tg - 30 (stricter than the Tg - 20
    # Type A limit).
    if design_life_years > 2:
        tm_type_b = PROWRAP["glass_transition_temp"] - 30.0
    else:
        tm_type_b = PROWRAP["max_temp"]
    # Table 8 polynomial; Ttest == Tamb in the PRW110 qualification.
    ft2_delta = tm_type_b - design_temp_c
    ft2 = 0.0000625 * ft2_delta**2 + 0.00125 * ft2_delta + 0.7

    def allowable_pressure(t):
        x = ((1.0 - nu * nu) / e_ac) * (
            3.0 * d**4 / (512.0 * t**3) + d / math.pi
        ) + 3.0 * d * d / (64.0 * g * t)
        return ft2 * fleak * math.sqrt(0.001 * gamma_lcl / x)

    # Asymptotic limit: as t -> infinity, X -> ((1-nu^2)/E_ac)*(d/pi), so
    # there is a maximum achievable pressure regardless of thickness.
    x_asymptote = ((1.0 - nu * nu) / e_ac) * (d / math.pi)
    p_max_asymptote = ft2 * fleak * math.sqrt(0.001 * gamma_lcl / x_asymptote)

    # Formula (12) validity: d <= 6*sqrt(D*t_substrate).
    d_validity_limit = 6.0 * math.sqrt(od_mm * nominal_wall_mm)
    details = {
        "defect_size_used_mm": d,
        "design_life_years": design_life_years,
        "service_temp_limit_c": tm_type_b,
        "fleak": fleak,
        "ft2": ft2,
        "gamma_lcl_j_m2": gamma_lcl,
        "e_ac_mpa": e_ac,
        "p_max_asymptote_mpa": p_max_asymptote,
        "d_validity_limit_mm": d_validity_limit,
        "d_within_validity": d <= d_validity_limit,
    }

    if pressure_mpa >= 0.999 * p_max_asymptote:
        details["repairable_formula12"] = False
        return None, details
    details["repairable_formula12"] = True

    lower, upper = 0.01, 1.0
    while allowable_pressure(upper) < pressure_mpa:
        upper *= 2.0
    for _ in range(200):
        mid = 0.5 * (lower + upper)
        if allowable_pressure(mid) < pressure_mpa:
            lower = mid
        else:
            upper = mid
    return upper, details


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
    internal_corrosion_rate=0.0,
    installation_temp=20.0,
    component_type="Straight",
    cyclic_derating_factor=1.0,
    axial_load_case=0,
):
    """Calculate repair outputs (baseline route).

    Routing rule:
      - External + (Corrosion or Dent) -> Type A route, UNLESS the remaining
        wall at end of design life is < 1 mm (ISO 24817 7.5.7: defects that
        become through-wall within the repair lifetime are Type B).
      - Internal (any mechanism), Crack or Leak -> Type B route.

    Type A thickness/overlap mirror the rigorous ISO Type A / Class 3 module
    (Formula 5 with substrate credit, Formula 4 end-thrust when
    axial_load_case == 1, Formula 10 thermal-mismatch on the axial strain,
    Formula 25 cyclic derating, Table 11/12 component factor f_th, Formula 33
    tee cap).

    internal_corrosion_rate (mm/yr): post-repair growth of INTERNAL
    corrosion, used to project the remaining wall to end of design life.
    External Type A defects are sealed by the repair (rate = 0).
    """
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
    if internal_corrosion_rate < 0:
        raise ValueError("Internal corrosion rate cannot be negative.")
    if cyclic_derating_factor <= 0 or cyclic_derating_factor > 1.0:
        raise ValueError("Cyclic derating factor must be in (0, 1].")
    if axial_load_case not in (0, 1):
        raise ValueError("Axial load case must be 0 (buried/restrained) or 1 (Formula 4 end-thrust).")
    fth_stress = component_factor(component_type)  # raises on unknown type

    wall_loss_ratio = (wall - rem_wall) / wall

    # Remaining wall projected to END of repair design life (ISO 24817 7.3):
    # external corrosion is sealed by the repair (rate 0); internal
    # corrosion keeps growing under the laminate at the given rate.
    if defect_type == "Corrosion" and defect_loc == "Internal":
        rem_wall_eol = max(rem_wall - internal_corrosion_rate * design_life, 0.0)
    else:
        rem_wall_eol = rem_wall
    has_no_substrate_capacity = rem_wall_eol < 1.0

    # Routing: External + (Corrosion or Dent) -> Type A; Internal, Crack or
    # Leak -> Type B. A remaining wall < 1 mm at end of design life forces
    # Type B regardless (through-wall within repair lifetime, ISO 7.5.7).
    is_type_a_route = (
        defect_loc == "External"
        and defect_type in ("Corrosion", "Dent")
        and not has_no_substrate_capacity
    )
    if is_type_a_route:
        if defect_type == "Dent":
            calc_method_thick = "Type A (Dent Reinforcement)"
        else:
            calc_method_thick = "Type A (Load Sharing)"
        calc_method_overlap = "Type A (Geometry Controlled)"
    else:
        calc_method_thick = "Type B (Total Replacement)"
        calc_method_overlap = "Type B (Shear Controlled)"

    safety_factor = 1.0 / design_factor

    # ISO 24817 allowable strains, mirroring the rigorous Type A / Class 3
    # module (iso24817_typea_class3.calculate_type_a_class3):
    #
    # Circumferential, 7.5.6 performance route (Formula 11):
    #   eps_c = f_cyclic * fperf * fT2 * eps_lt
    # with Class 3 design-life-data fperf (Table 10), the Table 8 polynomial
    # for fT2 (Ttest == Tamb in the PRW110 qualification, so the argument
    # reduces to Tm - Td) and Formula 25 cyclic derating.
    #
    # Axial, Table 9 route with the Formula 10 thermal-mismatch term
    # (installation -> design temperature differential against the substrate
    # CTE) and Formula 25 cyclic derating:
    #   eps_a = f_cyclic * (fT1 * eps_a0 - |dT * (alpha_s - alpha_a)|)
    eps_lt = PROWRAP.get("long_term_strain_lcl", PROWRAP.get("long_term_strain_20y"))
    fperf = 0.76 * 10 ** (-0.00273 * design_life)
    ft2_delta = PROWRAP["max_temp"] - temp
    temp_factor = 0.0000625 * ft2_delta**2 + 0.00125 * ft2_delta + 0.7
    design_strain = cyclic_derating_factor * fperf * temp_factor * eps_lt

    # Table 9: Ea > 0.5 * Ec for PRW110, so eps_a0 == eps_c0.
    if PROWRAP["modulus_axial"] > 0.5 * PROWRAP["modulus_circ"]:
        eps_a0 = 0.003061 * 10 ** (-0.0044 * design_life)
    else:
        eps_a0 = 0.001
    ft1 = temp_factor  # same Table 8 polynomial and same Tm - Td argument
    delta_t_install = temp - installation_temp
    axial_cte = PROWRAP["thermal_expansion_axial"] * 1e-6
    eps_a_noncyclic = ft1 * eps_a0 - abs(
        delta_t_install * (SUBSTRATE_CTE_PER_C - axial_cte)
    )
    eps_a = cyclic_derating_factor * eps_a_noncyclic

    if design_strain <= 0:
        raise ValueError("Calculated circumferential allowable strain is <= 0.")
    if eps_a <= 0:
        raise ValueError(
            "Calculated axial allowable strain is <= 0 (check installation "
            "temperature differential and cyclic derating factor)."
        )

    pressure_mpa = pressure * 0.1

    # ISO 24817 Formula (4) equivalent loads: peq is the design pressure;
    # Feq is the pressure end-thrust pi/4 * p * D^2 when the severed-pipe /
    # above-ground case applies (axial_load_case == 1), else 0 for a buried
    # restrained pipeline.
    peq = pressure_mpa
    if axial_load_case == 1:
        feq = peq * math.pi * od**2 / 4.0
    else:
        feq = 0.0

    # Substrate MAWP (p_s) from an ASME B31G-2023 Level 1 (Modified)
    # defect assessment, as ISO 24817 requires - replaces the previous
    # Barlow estimate on the remaining wall.
    b31g_details = None
    if (
        defect_type in ["Leak", "Crack"]
        or defect_type == "Dent"
        or has_no_substrate_capacity
    ):
        # Cracks/leaks are crack-like (outside B31G scope); dents are not
        # blunt metal loss; < 1 mm projected wall gets no credit.
        p_steel_capacity = 0.0
    else:
        # B31G covers internal and external blunt metal loss. The depth is
        # taken at END of design life (internal corrosion projected at the
        # given rate; external sealed by the repair).
        b31g_details = assess_b31g(
            od_mm=od,
            wall_mm=wall,
            depth_mm=wall - rem_wall_eol,
            length_mm=length,
            smys_mpa=yield_strength,
            safety_factor=max(1.0 / design_factor, 1.25),
            method="modified",
            operating_pressure_mpa=pressure_mpa,
        )
        if b31g_details["applicable"]:
            p_steel_capacity = b31g_details["p_s_mpa"]
        else:
            # d/t > 0.80: beyond B31G - no Level 1 substrate credit.
            p_steel_capacity = 0.0

    if "Type A" in calc_method_thick and p_steel_capacity > 0:
        p_composite_design = max(0, pressure_mpa - p_steel_capacity)
        ps_credit = p_steel_capacity
    else:
        p_composite_design = pressure_mpa
        ps_credit = 0.0

    # ISO 24817 Formula (5) in closed form (no live pressure):
    # eps_c = [peq*D/2 + nu*Feq/(pi*D) - ps*D/2] / (Ec*t)
    # -> tmin_c. Identical to solve_formula5_thickness in the rigorous
    # module for live_pressure = 0.
    nu = PROWRAP["poisson_circ"]
    ec = PROWRAP["modulus_circ"]
    ea = PROWRAP["modulus_axial"]
    driving_load = peq * od / 2.0 + nu * feq / (math.pi * od)
    substrate_relief = ps_credit * od / 2.0
    if driving_load > substrate_relief:
        tmin_c = (driving_load - substrate_relief) / (ec * design_strain)
    else:
        tmin_c = 0.0

    # Axial minimum thickness (Formulae 6/8 combination, as in the rigorous
    # module): t >= [Feq/(pi*D*Ea) - nu*peq*D/(2*Ec)] / eps_a.
    tmin_a = (
        feq / (math.pi * od * ea) - peq * od * nu / (2.0 * ec)
    ) / eps_a
    if tmin_a < 0:
        tmin_a = 0.0

    tdesign_base = max(tmin_c, tmin_a)
    # Component stress concentration factor f_th (Bend 1.2, Tee 2.0,
    # Flange/Reducer 1.1, Straight 1.0).
    t_required = tdesign_base * fth_stress

    # Tee/nozzle pressure cap, Formula (33), branch diameter Db = D
    # (conservative default, as in the rigorous module).
    if (component_type or "").strip().upper() == "TEE":
        t_required_tee = peq * (od + od) / (2.0 * ec * design_strain)
        t_required = max(t_required, t_required_tee)

    # Type B (through-wall) designs must satisfy BOTH the Formula (12)
    # energy-release-rate equation and the Type A equations (7.5.7):
    # take the maximum thickness.
    type_b_details = None
    if "Type B" in calc_method_thick and pressure_mpa > 0:
        # Type B service life is capped (5 years for PRW110); the repair
        # must be revalidated or replaced beyond that.
        type_b_life = min(design_life, PROWRAP["type_b_max_life_years"])
        t_type_b, type_b_details = iso_type_b_min_thickness(
            pressure_mpa=pressure_mpa,
            od_mm=od,
            nominal_wall_mm=wall,
            defect_size_mm=length,
            design_temp_c=temp,
            design_life_years=type_b_life,
        )
        type_b_details["t_formula12_mm"] = t_type_b
        type_b_details["t_typea_mm"] = t_required
        if t_type_b is not None:
            t_required = max(t_required, t_type_b)

    num_plies = math.ceil(t_required / PROWRAP["ply_thickness"])
    # ISO 24817 7.5.14: Type A minimum is the greater of 2 layers or 2 mm
    # (3 plies at 0.83 mm/ply). Type B minimum is the Annex F
    # impact-qualified layer count (3 layers for PRW110).
    min_plies_iso = math.ceil(2.0 / PROWRAP["ply_thickness"])
    if "Type B" in calc_method_thick:
        min_plies = max(PROWRAP["type_b_min_layers"], min_plies_iso)
    else:
        min_plies = min_plies_iso
    num_plies = max(num_plies, min_plies)

    is_upgraded = False
    if force_3_layers and num_plies < 3:
        num_plies = 3
        is_upgraded = True

    final_thickness = num_plies * PROWRAP["ply_thickness"]

    # ISO 24817 7.5.8 axial extent:
    # Formula (18) geometric overlap 2*sqrt(D*t), never less than 50 mm,
    # plus the Formula (21) load-transfer check 3*Ea*eps_a*t/tau.
    overlap_geometric = 2.0 * math.sqrt(od * wall)
    # Formula (21) axial load-transfer length, 3*Ea*eps_a*t/tau. For the
    # Type A route this uses tdesign_base (pre-f_th design thickness), as in
    # the rigorous module; for Type B the installed thickness is used
    # (conservative).
    if "Type A" in calc_method_overlap:
        overlap_transfer = (
            3.0 * ea * eps_a * tdesign_base
        ) / PROWRAP["long_term_lap_shear"]
        overlap_shear_basis = "iso_formula_18_and_21"
        overlap_shear_strength = PROWRAP["long_term_lap_shear"]
    else:
        overlap_transfer = (
            3.0 * ea * eps_a * final_thickness
        ) / PROWRAP["long_term_lap_shear"]
        overlap_shear_basis = "iso_formula_18_and_21_type_b"
        overlap_shear_strength = PROWRAP["long_term_lap_shear"]
    overlap_length = max(50.0, overlap_geometric, overlap_transfer)

    # Formula (20): total length = defect + 2*overlap + 2*taper (taper >= 5:1).
    taper_length = 5.0 * final_thickness
    total_repair_length_calc = length + (2 * overlap_length) + (2 * taper_length)

    # Band count from PROWRAP cloth constants (same formula as the rigorous
    # path: effective step = cloth width - stitching overlap).
    if total_repair_length_calc <= PROWRAP["cloth_width_mm"]:
        num_bands = 1
        procurement_axial_length = PROWRAP["cloth_width_mm"]
    else:
        num_bands = math.ceil(
            (total_repair_length_calc - PROWRAP["cloth_width_mm"])
            / (PROWRAP["cloth_width_mm"] - PROWRAP["stitching_overlap_mm"])
        ) + 1
        procurement_axial_length = num_bands * PROWRAP["cloth_width_mm"]

    circumference_m = (math.pi * od) / 1000
    axial_procurement_m = procurement_axial_length / 1000
    optimized_sqm = axial_procurement_m * circumference_m * num_plies
    epoxy_kg = optimized_sqm * 1.2

    compliance_warnings = []
    if (
        type_b_details is not None
        and not type_b_details.get("repairable_formula12", True)
    ):
        compliance_warnings.append(
            "NOT REPAIRABLE PER ISO 24817 FORMULA 12: the maximum achievable "
            f"pressure for a {type_b_details['defect_size_used_mm']:.0f} mm "
            "through-wall defect with PRW110 (gamma_LCL = "
            f"{type_b_details['gamma_lcl_j_m2']:.0f} J/m2) is "
            f"{type_b_details['p_max_asymptote_mpa']:.2f} MPa, below the "
            f"design pressure of {pressure_mpa:.2f} MPa. No laminate "
            "thickness can satisfy Formula 12 - do not install this repair; "
            "reduce pressure, reduce the defect size, or use another method."
        )
    if "Type B" in calc_method_thick and type_b_details is not None:
        if design_life > type_b_details["design_life_years"]:
            compliance_warnings.append(
                "Type B service life is capped at "
                f"{type_b_details['design_life_years']:.0f} years for PRW110 "
                f"(requested: {design_life:.0f}). The repair must be "
                "inspected and revalidated or replaced at the end of the "
                "Type B service life."
            )
        if temp > type_b_details["service_temp_limit_c"]:
            compliance_warnings.append(
                f"Design temperature {temp:.1f} degC exceeds the Type B "
                "upper service limit of "
                f"{type_b_details['service_temp_limit_c']:.1f} degC "
                "(Tg - 30 for Class 3 Type B repairs over 2 years). "
                "This repair is outside the qualified temperature range."
            )
    if "Type B" in calc_method_thick and type_b_details is not None:
        compliance_warnings.append(
            "Type B design assumes a circular/near-circular defect of size "
            f"{type_b_details['defect_size_used_mm']:.0f} mm at END of the "
            "design life (defect growth must be projected by the assessor). "
            "Annex F impact-qualified minimum of "
            f"{PROWRAP['type_b_min_layers']} layers applied."
        )
        if type_b_details is not None and not type_b_details["d_within_validity"]:
            compliance_warnings.append(
                "Formula 12 validity exceeded: defect size "
                f"{type_b_details['defect_size_used_mm']:.0f} mm > "
                f"6*sqrt(D*t) = {type_b_details['d_validity_limit_mm']:.0f} mm. "
                "The Type B result is outside the validated range - an "
                "engineered assessment is required."
            )
    if b31g_details is not None:
        compliance_warnings.extend(
            f"B31G: {w}" for w in b31g_details["warnings"]
        )
        if b31g_details["applicable"] and not b31g_details["acceptable"]:
            compliance_warnings.append(
                "B31G Level 1: the corroded pipe alone is NOT acceptable at "
                "the design pressure "
                f"(safe pressure P_S = {b31g_details['p_s_mpa']:.2f} MPa < "
                f"{pressure_mpa:.2f} MPa) - the composite repair is "
                "structural, not just preventive."
            )
        # End-of-life defect size: external Type A corrosion is sealed by
        # the repair (post-repair rate 0, current wall = end-of-life wall);
        # internal corrosion is projected forward at internal_corrosion_rate.
    if defect_loc == "Internal" and defect_type in ("Corrosion", "Dent"):
        compliance_warnings.append(
            "Internal defect: designed via the Type B route (laminate sized "
            "for the full design pressure; no substrate load sharing)."
        )
    if defect_type == "Corrosion" and defect_loc == "Internal":
        if internal_corrosion_rate > 0:
            compliance_warnings.append(
                "Internal corrosion projected at "
                f"{internal_corrosion_rate:.2f} mm/yr: remaining wall "
                f"{rem_wall:.2f} mm now -> {rem_wall_eol:.2f} mm at end of "
                f"the {design_life:.0f}-year design life. Assessment and "
                "classification use the end-of-life wall."
            )
        else:
            compliance_warnings.append(
                "Internal corrosion with corrosion rate = 0 mm/yr: the "
                "defect remains exposed to the process fluid under the "
                "repair. Enter a corrosion rate so the remaining wall can "
                "be projected to the end of the design life (ISO 24817 7.3)."
            )
    thickness_check_ok = final_thickness < od / 12.0
    if not thickness_check_ok:
        compliance_warnings.append(
            "Repair thickness exceeds D/12: the thin-wall design formulae "
            "of ISO 24817 are not valid for this repair."
        )

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
        "rem_wall_eol": rem_wall_eol,
        "internal_corrosion_rate": internal_corrosion_rate,
        "length": length,
        "wall_loss_ratio": wall_loss_ratio,
        "has_no_substrate_capacity": has_no_substrate_capacity,
        "is_severe_loss": has_no_substrate_capacity,
        "calc_method_thick": calc_method_thick,
        "calc_method_overlap": calc_method_overlap,
        "safety_factor": safety_factor,
        "temp_factor": temp_factor,
        "design_strain": design_strain,
        "eps_a": eps_a,
        "eps_a0": eps_a0,
        "ft1": ft1,
        "tmin_c": tmin_c,
        "tmin_a": tmin_a,
        "tdesign_base": tdesign_base,
        "fth_stress": fth_stress,
        "feq_n": feq,
        "peq_mpa": peq,
        "installation_temp": installation_temp,
        "component_type": component_type,
        "cyclic_derating_factor": cyclic_derating_factor,
        "axial_load_case": axial_load_case,
        "pressure_mpa": pressure_mpa,
        "p_steel_capacity": p_steel_capacity,
        "p_composite_design": p_composite_design,
        "t_required": t_required,
        "num_plies": num_plies,
        "final_thickness": final_thickness,
        "iso_length": total_repair_length_calc,
        "overlap_length": overlap_length,
        "overlap_geometric": overlap_geometric,
        "overlap_transfer": overlap_transfer,
        "taper_length": taper_length,
        "overlap_shear_basis": overlap_shear_basis,
        "overlap_shear_strength": overlap_shear_strength,
        "eps_lt": eps_lt,
        "fperf": fperf,
        "type_b_details": type_b_details,
        "b31g_details": b31g_details,
        "thickness_check_ok": thickness_check_ok,
        "compliance_warnings": compliance_warnings,
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
    nominal_wall_mm=None,
    axial_load_case=0,
):
    """Run the isolated ISO Type A/Class 3 route using PRW110 performance data.

    axial_load_case:
      0 - buried restrained pipeline: no axial load on the laminate
          (pressure end-thrust carried by pipe wall and soil restraint).
      1 - severed-pipe/guillotine credible, or above-ground pipeline near
          bends/closures: axial loads calculated per ISO Formula 4
          (pressure end-thrust pi/4 * p * D^2).

    Uses the ISO 24817 7.5.6 performance route (Formula 11,
    eps_c = fperf * fT2 * eps_lt) when PRW110 long-term strain LCL data is
    present in the material dataset; otherwise falls back to Table 9 strains.
    """
    eps_lt = PROWRAP.get("long_term_strain_lcl", PROWRAP.get("long_term_strain_20y"))
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
        use_performance_data=eps_lt is not None,
        long_term_strain_lcl=eps_lt,
        performance_data_source="Design life",
        # None lets the module compute the ISO Formula 4 end-thrust.
        equivalent_axial_load_n=None if axial_load_case == 1 else 0.0,
        cyclic_derating_factor=cyclic_derating_factor,
        component_type=component_type,
        nominal_wall_mm=nominal_wall_mm,
    )
    result = calculate_type_a_class3(inputs)
    result["input_summary"] = {
        "pressure_bar": pressure_bar,
        "substrate_allowable_pressure_bar": substrate_allowable_pressure_bar,
        "hoop_modulus_mpa": PROWRAP["modulus_circ"],
        "axial_modulus_mpa": PROWRAP["modulus_axial"],
        "lap_shear_mpa": PROWRAP["long_term_lap_shear"],
        "long_term_strain_lcl": eps_lt,
        "performance_data": (
            f"Formula 11 performance route, eps_lt={eps_lt} (design-life data)"
            if eps_lt is not None
            else "not used - Table 9 fallback"
        ),
    }
    return result


calculate_type_a_class3_fallback_check = calculate_type_a_class3_prowrap_check


def substrate_credit_bar_for_iso_check(repair_data):
    """Return the substrate pressure credit for ISO checks in bar.

    p_steel_capacity already encodes the B31G scope rules (no credit for
    cracks/leaks/dents or < 1 mm end-of-life wall; internal corrosion
    assessed at the projected end-of-life wall).
    """
    if repair_data["defect_type"] in {"Crack", "Leak"}:
        return 0.0
    return max(0.0, repair_data["p_steel_capacity"] * 10.0)


def apply_type_a_class3_result_to_repair(repair_data, typea_class3_result):
    """Use the ISO Type A/Class 3 result as the controlling displayed repair design."""
    updated = dict(repair_data)
    updated["iso_typea_class3"] = typea_class3_result
    if updated["p_composite_design"] <= 0:
        updated["iso_typea_class3_controls"] = False
        updated["iso_typea_class3_noncontrolling_reason"] = (
            "effective_pipe_capacity_covers_design_pressure"
        )
        return updated

    updated["iso_typea_class3_controls"] = True
    updated["iso_typea_class3_noncontrolling_reason"] = None
    layer_count = typea_class3_result["layer_count"]
    final_installed_thickness = layer_count * PROWRAP["ply_thickness"]
    overlap_length = typea_class3_result["lover_required_mm"]
    taper_length = typea_class3_result.get("taper_length_mm", 0.0)
    # Formula (20): total length = defect + 2*overlap + 2*taper.
    repair_length = updated["length"] + (2.0 * overlap_length) + (2.0 * taper_length)

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
            "taper_length": taper_length,
            "overlap_shear_basis": "iso_formula_18_and_21",
            "overlap_shear_strength": PROWRAP["long_term_lap_shear"],
            "num_bands": num_bands,
            "proc_length": procurement_axial_length,
            "optimized_sqm": optimized_sqm,
            "epoxy_kg": optimized_sqm * 1.2,
            "is_upgraded": False,
        }
    )
    return updated
