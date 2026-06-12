"""Cross-check: baseline Type A route vs the rigorous Type A / Class 3 module.

The baseline (prowrap_calculations.baseline_type_a_design, closed form) and
the rigorous module (iso24817_typea_class3.calculate_type_a_class3, bisection)
implement the same ISO 24817 formulae independently. For identical inputs
they must produce the same thickness, layer count, strains and overlap.
"""

import unittest

from prowrap_calculations import (
    calculate_repair,
    calculate_type_a_class3_prowrap_check,
    substrate_credit_bar_for_iso_check,
)
from test_current_calculation_baseline import default_inputs


def run_both(case_overrides, installation_temp=20.0, component_type="Straight",
             cyclic_derating_factor=1.0, axial_load_case=0):
    inputs = default_inputs(**case_overrides)
    baseline = calculate_repair(
        **inputs,
        installation_temp=installation_temp,
        component_type=component_type,
        cyclic_derating_factor=cyclic_derating_factor,
        axial_load_case=axial_load_case,
    )
    rigorous = calculate_type_a_class3_prowrap_check(
        od=inputs["od"],
        pressure_bar=inputs["pressure"],
        temp=inputs["temp"],
        rem_wall=baseline["rem_wall_eol"],
        design_life=inputs["design_life"],
        substrate_allowable_pressure_bar=substrate_credit_bar_for_iso_check(baseline),
        installation_temp=installation_temp,
        component_type=component_type,
        cyclic_derating_factor=cyclic_derating_factor,
        nominal_wall_mm=inputs["wall"],
        axial_load_case=axial_load_case,
    )
    return baseline, rigorous


class TypeABaselineMatchesRigorousTest(unittest.TestCase):
    CASES = [
        # (overrides, install_temp, component, cyclic, axial_case)
        ({}, 20.0, "Straight", 1.0, 0),
        # Structural case: composite takes load (high pressure, thin wall).
        ({"pressure": 120.0, "rem_wall": 3.0}, 20.0, "Straight", 1.0, 0),
        # Thermal mismatch: cold installation, hot service.
        ({"pressure": 120.0, "rem_wall": 3.0}, 5.0, "Straight", 1.0, 0),
        # Component factors.
        ({"pressure": 120.0, "rem_wall": 3.0}, 20.0, "Bend", 1.0, 0),
        ({"pressure": 120.0, "rem_wall": 3.0}, 20.0, "Tee", 1.0, 0),
        ({"pressure": 120.0, "rem_wall": 3.0}, 20.0, "Flange", 1.0, 0),
        ({"pressure": 120.0, "rem_wall": 3.0}, 20.0, "Reducer", 1.0, 0),
        # Cyclic derating.
        ({"pressure": 120.0, "rem_wall": 3.0}, 20.0, "Straight", 0.7, 0),
        # Formula 4 end-thrust (severed-pipe / above-ground).
        ({"pressure": 120.0, "rem_wall": 3.0}, 20.0, "Straight", 1.0, 1),
        # Everything at once.
        ({"pressure": 90.0, "rem_wall": 3.5, "temp": 45.0, "design_life": 10},
         8.0, "Bend", 0.85, 1),
        # External dent (no substrate credit) with axial loads.
        ({"defect_type": "Dent", "rem_wall": 9.53}, 15.0, "Straight", 0.9, 1),
    ]

    def test_baseline_type_a_matches_rigorous_module(self):
        for overrides, t_inst, comp, fc, axial in self.CASES:
            with self.subTest(overrides=overrides, install=t_inst,
                              component=comp, cyclic=fc, axial=axial):
                baseline, rigorous = run_both(
                    overrides, t_inst, comp, fc, axial)

                self.assertIn("Type A", baseline["calc_method_thick"])
                design = baseline["typea_design"]
                self.assertIsNotNone(design)

                # Strains (Formula 11 + 25 hoop; Formula 10 axial).
                self.assertAlmostEqual(design["eps_c"], rigorous["eps_c"], places=10)
                self.assertAlmostEqual(design["eps_a"], rigorous["eps_a"], places=10)
                # Formula 4 end-thrust.
                self.assertAlmostEqual(design["feq_n"], rigorous["feq_n"], places=6)
                # Thicknesses: the rigorous module solves Formula 5 by
                # bisection (stops at |residual| < 1e-9 strain, ~2e-6 mm in
                # thickness); the baseline is closed form -> compare to 1e-4 mm.
                self.assertAlmostEqual(
                    design["tmin_c_mm"], rigorous["tmin_c_mm"], places=4)
                self.assertAlmostEqual(
                    design["tmin_a_mm"], rigorous["tmin_a_mm"], places=4)
                self.assertAlmostEqual(
                    design["fth_stress"], rigorous["fth_stress"], places=10)
                self.assertAlmostEqual(
                    design["tdesign_final_mm"], rigorous["tdesign_final_mm"],
                    places=4)
                # Layer count and installed thickness.
                self.assertEqual(baseline["num_plies"], rigorous["layer_count"])
                # Overlap: max(50, Formula 18, Formula 21).
                self.assertAlmostEqual(
                    design["lmin_transfer_mm"], rigorous["lmin_transfer_mm"],
                    places=3)
                self.assertAlmostEqual(
                    baseline["overlap_length"], rigorous["lover_required_mm"],
                    places=3)
                # Taper (Formula 20, 5:1 on installed thickness).
                self.assertAlmostEqual(
                    baseline["taper_length"], rigorous["taper_length_mm"],
                    places=6)


class RoutingTest(unittest.TestCase):
    def test_external_corrosion_is_type_a(self):
        result = calculate_repair(**default_inputs())
        self.assertEqual(result["calc_method_thick"], "Type A (Load Sharing)")
        self.assertEqual(result["calc_method_overlap"], "Type A (Geometry Controlled)")

    def test_external_dent_is_type_a(self):
        result = calculate_repair(
            **default_inputs(defect_type="Dent", rem_wall=9.53))
        self.assertEqual(result["calc_method_thick"], "Type A (Dent Reinforcement)")
        self.assertEqual(result["calc_method_overlap"], "Type A (Geometry Controlled)")
        self.assertAlmostEqual(result["p_steel_capacity"], 0.0)

    def test_internal_corrosion_is_type_b(self):
        result = calculate_repair(**default_inputs(defect_loc="Internal"))
        self.assertEqual(result["calc_method_thick"], "Type B (Total Replacement)")
        self.assertAlmostEqual(result["p_steel_capacity"], 0.0)
        self.assertIsNotNone(result["type_b_details"])

    def test_internal_dent_is_type_b(self):
        result = calculate_repair(
            **default_inputs(defect_type="Dent", defect_loc="Internal",
                             rem_wall=9.53))
        self.assertEqual(result["calc_method_thick"], "Type B (Total Replacement)")

    def test_crack_and_leak_are_type_b_regardless_of_location(self):
        for defect_type in ("Crack", "Leak"):
            for loc in ("External", "Internal"):
                result = calculate_repair(
                    **default_inputs(defect_type=defect_type, defect_loc=loc))
                self.assertEqual(
                    result["calc_method_thick"], "Type B (Total Replacement)")
                self.assertAlmostEqual(result["p_steel_capacity"], 0.0)

    def test_cyclic_derating_increases_type_b_thickness(self):
        full = calculate_repair(**default_inputs(defect_type="Leak", length=25.0))
        derated = calculate_repair(
            **default_inputs(defect_type="Leak", length=25.0),
            cyclic_derating_factor=0.5)
        self.assertGreater(derated["t_required"], full["t_required"])

    def test_invalid_cyclic_factor_rejected(self):
        with self.assertRaises(ValueError):
            calculate_repair(**default_inputs(), cyclic_derating_factor=0.0)
        with self.assertRaises(ValueError):
            calculate_repair(**default_inputs(), cyclic_derating_factor=1.5)

    def test_invalid_component_type_rejected(self):
        with self.assertRaises(ValueError):
            calculate_repair(**default_inputs(), component_type="Elbow-ish")

    def test_type_b_with_axial_case_1_warns(self):
        result = calculate_repair(
            **default_inputs(defect_type="Leak"), axial_load_case=1)
        self.assertTrue(
            any("axial load" in w.lower() for w in result["compliance_warnings"]))


if __name__ == "__main__":
    unittest.main()
