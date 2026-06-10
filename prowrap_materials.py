"""PROWRAP PRW110 material properties.

Source: PRW110 Test Data.pdf, ISO TS 24817 and ASME PCC-2 PROWRAP HPTP
repair system qualification data.
"""

PROWRAP = {
    "ply_thickness": 0.83,             # mm, ISO 527-4
    "modulus_circ": 45460,             # MPa, ISO 527-4
    "strain_fail": 0.0233,             # mm/mm, circumferential, ISO 527-4
    "tensile_strength": 574.1,         # MPa, circumferential, ISO 527-4
    "modulus_axial": 43800,            # MPa, ISO 527-4
    "strain_fail_axial": 0.0243,       # mm/mm, axial, ISO 527-4
    "tensile_strength_axial": 563.67,  # MPa, axial, ISO 527-4
    "poisson_circ": 0.066,             # ISO 527-4
    "compressive_modulus": 3310,       # MPa, ISO 604
    "compressive_strength": 85.58,     # MPa, ISO 604
    "shear_modulus": 2450,             # MPa, ASTM D5379
    "shore_d": 79.1,                   # Shore D, ISO 868
    "glass_transition_temp": 78.18,    # degC, mid Tg, ISO 11357-2
    "peak_exotherm_temp": 104,         # degC, ISO 11357-2
    "thermal_expansion_circ": 10.34,   # ppm/K, circumferential, ASTM E831
    "thermal_expansion_axial": 22.81,  # ppm/K, axial, ASTM E831
    "lap_shear": 14.7,                 # MPa, ASTM D3165
    "long_term_lap_shear": 9.62,       # MPa, ASTM D3165
    "long_term_strain_lcl": 0.0055,    # mm/mm (0.55 %), eps_lt, 95% LCL long-term strain,
                                       # ISO 24817 Annex E performance data (Formula 11 route)
    "impact_peak_energy": 41.982,      # J, ASTM D7136
    "short_term_survival": "PASS",     # ISO 24817
    "max_temp": 58.18,                 # degC, Tg minus 20 degC design limit
    "cloth_width_mm": 300,
    "stitching_overlap_mm": 50,
}

PROWRAP_SOURCES = {
    "source_document": "PRW110 Test Data.pdf",
    "qualification_basis": (
        "ISO TS 24817 and ASME PCC-2 - PROWRAP HPTP repair system "
        "qualification data"
    ),
}
