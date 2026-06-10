import unittest

from iso24817_typea_class3 import (
    TypeAClass3Inputs,
    calculate_type_a_class3,
    component_factor,
)


class Iso24817TypeAClass3Test(unittest.TestCase):
    def test_table_9_fallback_default_matches_vba_route(self):
        result = calculate_type_a_class3(TypeAClass3Inputs())

        self.assertEqual(result["circumferential_strain_basis"], "table_9_fallback")
        self.assertAlmostEqual(result["peq_mpa"], 1.0)
        self.assertAlmostEqual(result["feq_n"], 129717.11464895941)
        self.assertAlmostEqual(result["ft1"], 0.75)
        self.assertAlmostEqual(result["eps_c0"], 0.0027660710390639645)
        self.assertAlmostEqual(result["eps_a0"], 0.001)
        self.assertAlmostEqual(result["eps_c"], 0.0024645532792979736)
        self.assertAlmostEqual(result["eps_a"], 0.00075)
        self.assertAlmostEqual(result["tmin_c_mm"], 3.489176369097411, places=6)
        self.assertAlmostEqual(result["tmin_a_mm"], 7.902222222222221)
        self.assertAlmostEqual(result["tdesign_base_mm"], 7.902222222222221)
        self.assertAlmostEqual(result["lmin_transfer_mm"], 14.223999999999997)
        self.assertAlmostEqual(result["lover_required_mm"], 25.0)
        self.assertAlmostEqual(result["tdesign_final_mm"], 7.902222222222221)
        self.assertEqual(result["layer_count"], 10)
        self.assertTrue(result["thickness_check_ok"])
        self.assertTrue(result["overlap_transfer_check_ok"])

    def test_performance_route_requires_long_term_strain_lcl(self):
        with self.assertRaisesRegex(ValueError, "Long-term strain LCL"):
            calculate_type_a_class3(TypeAClass3Inputs(use_performance_data=True))

    def test_performance_route_accepts_explicit_long_term_strain_lcl(self):
        result = calculate_type_a_class3(
            TypeAClass3Inputs(use_performance_data=True, long_term_strain_lcl=0.0035)
        )

        self.assertEqual(result["circumferential_strain_basis"], "performance_data")
        self.assertAlmostEqual(result["fperf"], 0.7136965416070369)
        self.assertAlmostEqual(result["ft2"], 0.75)
        self.assertAlmostEqual(result["eps_c"], 0.0018734534217184717)
        self.assertAlmostEqual(result["tmin_c_mm"], 4.485041813390611, places=6)
        self.assertGreater(result["tmin_c_mm"], 0)

    def test_component_factors_match_vba_reference(self):
        self.assertEqual(component_factor("Straight"), 1.0)
        self.assertEqual(component_factor("Bend"), 1.2)
        self.assertEqual(component_factor("Tee"), 2.0)
        self.assertEqual(component_factor("Flange"), 1.1)
        self.assertEqual(component_factor("Reducer"), 1.1)

    def test_limited_landing_length_applies_overlay_cap(self):
        result = calculate_type_a_class3(
            TypeAClass3Inputs(required_overlap_mm=100.0, available_landing_length_mm=10.0)
        )

        self.assertEqual(result["overlap_basis"], "user_required_overlap")
        self.assertEqual(result["fth_overlay"], 2.5)
        self.assertAlmostEqual(result["tdesign_final_mm"], result["tdesign_base_mm"] * 2.5)


if __name__ == "__main__":
    unittest.main()
