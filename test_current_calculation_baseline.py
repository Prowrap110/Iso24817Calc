import unittest

from prowrap_calculations import calculate_repair


def default_inputs(**overrides):
    values = {
        "customer": "PROTAP",
        "location": "Turkey",
        "report_no": "24-152",
        "od": 457.2,
        "wall": 9.53,
        "pressure": 50.0,
        "temp": 40.0,
        "defect_type": "Corrosion",
        "defect_loc": "External",
        "length": 100.0,
        "rem_wall": 4.5,
        "yield_strength": 359.0,
        "design_factor": 0.72,
        "design_life": 20,
    }
    values.update(overrides)
    return values


class CurrentCalculationBaselineTest(unittest.TestCase):
    def test_default_case_current_outputs(self):
        result = calculate_repair(**default_inputs())

        self.assertAlmostEqual(result["wall_loss_ratio"], 0.527806925498426)
        self.assertEqual(result["calc_method_thick"], "Type A (Load Sharing)")
        self.assertEqual(result["calc_method_overlap"], "Type A (Geometry Controlled)")
        self.assertAlmostEqual(result["pressure_mpa"], 5.0)
        self.assertAlmostEqual(result["p_steel_capacity"], 5.088188976377953)
        self.assertAlmostEqual(result["p_composite_design"], 0.0)
        self.assertAlmostEqual(result["t_required"], 0.0)
        self.assertEqual(result["num_plies"], 2)
        self.assertAlmostEqual(result["final_thickness"], 1.66)
        self.assertAlmostEqual(result["overlap_length"], 50.0)
        self.assertAlmostEqual(result["iso_length"], 200.0)
        self.assertEqual(result["num_bands"], 1)
        self.assertEqual(result["proc_length"], 300)
        self.assertAlmostEqual(result["optimized_sqm"], 0.8618016967327521)
        self.assertAlmostEqual(result["epoxy_kg"], 1.0341620360793025)

    def test_force_3_layers_preserves_current_upgrade_behavior(self):
        result = calculate_repair(**default_inputs(), force_3_layers=True)

        self.assertEqual(result["num_plies"], 3)
        self.assertTrue(result["is_upgraded"])
        self.assertAlmostEqual(result["final_thickness"], 2.49)

    def test_type_b_leak_uses_zero_steel_capacity(self):
        result = calculate_repair(**default_inputs(defect_type="Leak"))

        self.assertEqual(result["calc_method_thick"], "Type B (Total Replacement)")
        self.assertAlmostEqual(result["p_steel_capacity"], 0.0)
        self.assertGreaterEqual(result["num_plies"], 4)


if __name__ == "__main__":
    unittest.main()
