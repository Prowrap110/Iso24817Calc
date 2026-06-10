import unittest

from prowrap_calculations import calculate_repair
from prowrap_materials import PROWRAP
from test_current_calculation_baseline import default_inputs


class LongTermOverlapTest(unittest.TestCase):
    def test_type_b_overlap_uses_long_term_lap_shear(self):
        result = calculate_repair(**default_inputs(defect_type="Leak"))

        # ISO Formula (21): l_over > 3 * Ea * eps_a * t / tau (long-term shear),
        # combined with Formula (18) geometric overlap and the 50 mm floor.
        expected_transfer = (
            3.0
            * PROWRAP["modulus_axial"]
            * result["design_strain"]
            * result["final_thickness"]
        ) / PROWRAP["long_term_lap_shear"]

        self.assertEqual(result["calc_method_overlap"], "Type B (Shear Controlled)")
        self.assertEqual(result["overlap_shear_basis"], "iso_formula_18_and_21_type_b")
        self.assertAlmostEqual(result["overlap_shear_strength"], 9.62)
        self.assertAlmostEqual(result["overlap_transfer"], expected_transfer)
        self.assertAlmostEqual(result["overlap_length"], 4597.782663306807)
        self.assertAlmostEqual(result["iso_length"], 10523.965326613614)
        # Leak/crack designs must carry the Type B compliance warnings.
        self.assertTrue(
            any("Type B" in w for w in result["compliance_warnings"])
        )


if __name__ == "__main__":
    unittest.main()
