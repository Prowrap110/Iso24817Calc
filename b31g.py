"""ASME B31G-2023 Level 1 corroded-pipe assessment (Modified / Original).

Provides the substrate MAWP (p_s) required by ISO 24817 in place of a plain
Barlow estimate. Units: mm / MPa throughout (matches the rest of the app).

Symbols (B31G-2023 para 1.5):
  D outside diameter, t nominal wall, d max metal-loss depth,
  L longitudinal extent, z = L^2/(D t), M Folias (bulging) factor,
  S_flow flow stress, S_F estimated failure stress,
  P_F = 2 S_F t / D failure pressure, P_S = P_F / SF safe pressure (MAWP).
"""

import math

# Modified B31G flow stress adder (para 1.7(b)(2)): 69 MPa, valid for
# SMYS <= 483 MPa and temperatures < 120 degC.
FLOW_STRESS_ADDER_MPA = 69.0
SMYS_LIMIT_MODIFIED_MPA = 483.0


def assess_b31g(
    od_mm,
    wall_mm,
    depth_mm,
    length_mm,
    smys_mpa,
    safety_factor=1.39,
    method="modified",
    operating_pressure_mpa=None,
    smts_mpa=None,
):
    """Level 1 B31G assessment. Returns a dict with S_F, P_F, P_S, checks.

    safety_factor: >= 1.25 (para 1.9/1.10); 1.39 = 1/0.72 is the classic basis.
    """
    warnings = []
    dt = depth_mm / wall_mm

    applicable = True
    if dt > 0.8:
        applicable = False
        warnings.append(
            "d/t > 0.80: beyond B31G applicability - repair or Level 3 "
            "(API 579) required. No substrate credit taken."
        )
    if dt <= 0.10:
        warnings.append(
            "d/t <= 0.10: metal loss not limited as to length (section 3(a))."
        )
    if safety_factor < 1.25:
        warnings.append(
            "Safety factor < 1.25 is below the B31G para 1.9/1.10 minimum."
        )
    if method == "modified" and smys_mpa > SMYS_LIMIT_MODIFIED_MPA:
        warnings.append(
            "SMYS > 483 MPa: Modified B31G flow stress basis not valid - "
            "falling back to Original B31G."
        )
        method = "original"

    z = length_mm * length_mm / (od_mm * wall_mm)

    if method == "original":
        s_flow = 1.1 * smys_mpa
    elif method == "modified":
        s_flow = smys_mpa + FLOW_STRESS_ADDER_MPA
    else:
        raise ValueError("method must be 'modified' or 'original'")
    # Para 1.7(b): flow stress shall not exceed SMTS.
    if smts_mpa is not None and s_flow > smts_mpa:
        s_flow = smts_mpa
        warnings.append("Flow stress capped at SMTS.")

    if method == "original":
        if z <= 20.0:
            m = math.sqrt(1.0 + 0.8 * z)
            s_f = (
                s_flow
                * (1.0 - (2.0 / 3.0) * dt)
                / (1.0 - (2.0 / 3.0) * dt / m)
            )
        else:
            m = float("inf")
            s_f = s_flow * (1.0 - dt)
    else:
        if z <= 50.0:
            m = math.sqrt(1.0 + 0.6275 * z - 0.003375 * z * z)
        else:
            m = 0.032 * z + 3.3
        s_f = s_flow * (1.0 - 0.85 * dt) / (1.0 - 0.85 * dt / m)

    p_f = 2.0 * s_f * wall_mm / od_mm
    p_s = p_f / safety_factor

    result = {
        "method": method,
        "d_over_t": dt,
        "z": z,
        "folias_m": m,
        "s_flow_mpa": s_flow,
        "s_f_mpa": s_f,
        "p_f_mpa": p_f,
        "p_s_mpa": p_s,
        "safety_factor": safety_factor,
        "applicable": applicable,
        "warnings": warnings,
    }
    if operating_pressure_mpa is not None:
        s_o = operating_pressure_mpa * od_mm / (2.0 * wall_mm)
        result["s_o_mpa"] = s_o
        result["acceptable"] = s_f >= safety_factor * s_o - 1e-9
    return result
