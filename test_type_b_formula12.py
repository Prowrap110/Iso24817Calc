import unittest

from prowrap_calculations import calculate_repair, iso_type_b_min_thickness
from test_current_calculation_baseline import default_inputs


class TypeBFormula12Test(unittest.TestCase):
    def test_formula12_thickness_matches_reference_values(self):
        # Cross-checked against an independent ISO 24817 reference
        # implementation (gamma_LCL = 250 J/m2, Class 3).
        t, details = iso_type_b_min_thickness(
            pressure_mpa=2.0,
            od_mm=457.2,
            nominal_wall_mm=9.53,
            defect_size_mm=15.0,
            design_temp_c=30.0,
            design_life_years=10,
        )
        self.assertAlmostEqual(t, 1.1080, places=3)
        self.assertTrue(details["repairable_formula12"])
        self.assertTrue(details["d_within_validity"])

    def test_defect_size_floor_is_15_mm(self):
        _, details = iso_type_b_min_thickness(
            pressure_mpa=1.0,
            od_mm=457.2,
            nominal_wall_mm=9.53,
            defect_size_mm=5.0,
            design_temp_c=40.0,
            design_life_years=20,
        )
        self.assertEqual(details["defect_size_used_mm"], 15.0)

    def test_large_leak_at_high_pressure_is_flagged_not_repairable(self):
        # 100 mm through-wall defect at 50 bar exceeds the Formula 12
        # asymptotic pressure limit for gamma_LCL = 250 J/m2.
        result = calculate_repair(**default_inputs(defect_type="Leak"))

        details = result["type_b_details"]
        self.assertFalse(details["repairable_formula12"])
        self.assertIsNone(details["t_formula12_mm"])
        self.assertAlmostEqual(details["p_max_asymptote_mpa"], 4.645, places=2)
        self.assertTrue(
            any("NOT REPAIRABLE" in w for w in result["compliance_warnings"])
        )

    def test_repairable_leak_takes_max_of_formula12_and_typea(self):
        result = calculate_repair(**default_inputs(defect_type="Leak", length=25.0))

        details = result["type_b_details"]
        self.assertTrue(details["repairable_formula12"])
        self.assertAlmostEqual(details["t_formula12_mm"], 27.6161, places=3)
        self.assertGreater(details["t_formula12_mm"], details["t_typea_mm"])
        # 7.5.7: t_design = max(Type B, Type A) -> Formula 12 governs here.
        self.assertEqual(result["num_plies"], 34)


if __name__ == "__main__":
    unittest.main()
