import unittest

from prowrap_calculations import calculate_repair
from prowrap_materials import PROWRAP
from test_current_calculation_baseline import default_inputs


class LongTermOverlapTest(unittest.TestCase):
    def test_type_b_overlap_uses_long_term_lap_shear(self):
        result = calculate_repair(**default_inputs(defect_type="Leak"))

        expected_overlap = (
            result["final_thickness"]
            * PROWRAP["modulus_circ"]
            * result["design_strain"]
        ) / (PROWRAP["long_term_lap_shear"] / result["safety_factor"])

        self.assertEqual(result["calc_method_overlap"], "Type B (Shear Controlled)")
        self.assertEqual(result["overlap_shear_basis"], "long_term_lap_shear")
        self.assertAlmostEqual(result["overlap_shear_strength"], 9.62)
        self.assertAlmostEqual(result["overlap_length"], expected_overlap)
        self.assertAlmostEqual(result["overlap_length"], 365.5513264033264)
        self.assertAlmostEqual(result["iso_length"], 831.1026528066528)


if __name__ == "__main__":
    unittest.main()
