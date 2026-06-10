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
        # Lifetime > 2 years: Type B upper service temperature is Tg - 30
        # (Table 6, Class 3), which feeds fT2.
        self.assertAlmostEqual(t, 1.1680, places=3)
        self.assertAlmostEqual(details["service_temp_limit_c"], 48.18, places=2)
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

    def test_type_b_life_is_capped_at_2_years(self):
        # Input design life 20 yr; Type B route must run at the 2-year cap
        # with the corresponding fleak and Tg - 20 temperature limit.
        result = calculate_repair(**default_inputs(defect_type="Leak"))

        details = result["type_b_details"]
        self.assertEqual(details["design_life_years"], 2)
        self.assertAlmostEqual(details["fleak"], 0.6422, places=3)
        self.assertAlmostEqual(details["service_temp_limit_c"], 58.18, places=2)
        self.assertTrue(
            any("capped" in w for w in result["compliance_warnings"])
        )

    def test_large_leak_exceeds_d12_validity_even_when_formula12_solves(self):
        # 100 mm through-wall defect at 50 bar: Formula 12 solves at the
        # 2-year cap but the thickness (122.5 mm) violates the D/12
        # thin-wall limit - flagged, not silently accepted.
        result = calculate_repair(**default_inputs(defect_type="Leak"))

        details = result["type_b_details"]
        self.assertTrue(details["repairable_formula12"])
        self.assertAlmostEqual(details["t_formula12_mm"], 122.5363, places=3)
        self.assertFalse(result["thickness_check_ok"])
        self.assertTrue(
            any("D/12" in w for w in result["compliance_warnings"])
        )

    def test_repairable_leak_takes_max_of_formula12_and_typea(self):
        result = calculate_repair(**default_inputs(defect_type="Leak", length=25.0))

        details = result["type_b_details"]
        self.assertTrue(details["repairable_formula12"])
        self.assertAlmostEqual(details["t_formula12_mm"], 6.3029, places=3)
        # 7.5.7: t_design = max(Type B, Type A) -> here the Type A check
        # (full pressure, 20-yr strain) governs over the 2-yr Formula 12.
        self.assertGreater(details["t_typea_mm"], details["t_formula12_mm"])
        self.assertEqual(result["num_plies"], 12)


    def test_type_b_minimum_is_impact_qualified_3_layers(self):
        # Small leak at low pressure: Formula 12 thickness is tiny, so the
        # Annex F impact-qualified minimum of 3 layers governs.
        result = calculate_repair(
            **default_inputs(defect_type="Leak", length=15.0, pressure=2.0)
        )

        self.assertTrue(result["type_b_details"]["repairable_formula12"])
        self.assertEqual(result["num_plies"], 3)


if __name__ == "__main__":
    unittest.main()
