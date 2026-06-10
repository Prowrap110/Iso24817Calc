import unittest

from prowrap_calculations import (
    apply_type_a_class3_result_to_repair,
    calculate_repair,
    calculate_type_a_class3_prowrap_check,
)
from prowrap_materials import PROWRAP


class TypeAClass3AdapterTest(unittest.TestCase):
    def test_adapter_maps_app_inputs_and_prowrap_data_to_typea_class3_route(self):
        result = calculate_type_a_class3_prowrap_check(
            od=457.2,
            pressure_bar=50.0,
            temp=40.0,
            rem_wall=4.5,
            design_life=20,
            substrate_allowable_pressure_bar=0.0,
            installation_temp=20.0,
            component_type="Straight",
            cyclic_derating_factor=1.0,
        )

        self.assertEqual(result["circumferential_strain_basis"], "performance_data")
        self.assertAlmostEqual(result["peq_mpa"], 5.0)
        self.assertAlmostEqual(result["long_term_strain_lcl"], PROWRAP["long_term_strain_20y"])
        self.assertAlmostEqual(result["input_summary"]["pressure_bar"], 50.0)
        self.assertAlmostEqual(result["input_summary"]["substrate_allowable_pressure_bar"], 0.0)
        self.assertAlmostEqual(result["input_summary"]["lap_shear_mpa"], PROWRAP["long_term_lap_shear"])
        self.assertAlmostEqual(result["input_summary"]["hoop_modulus_mpa"], PROWRAP["modulus_circ"])
        self.assertEqual(result["input_summary"]["performance_data"], "PRW110 20-year long-term strain")
        self.assertGreater(result["tdesign_final_mm"], 0)
        self.assertGreaterEqual(result["layer_count"], 1)

    def test_iso_result_can_drive_displayed_repair_metrics(self):
        repair = calculate_repair(
            customer="PROTAP",
            location="Turkey",
            report_no="24-152",
            od=457.2,
            wall=9.53,
            pressure=50.0,
            temp=40.0,
            defect_type="Corrosion",
            defect_loc="External",
            length=100.0,
            rem_wall=4.5,
            yield_strength=359.0,
            design_factor=0.72,
            design_life=20,
        )
        iso_result = calculate_type_a_class3_prowrap_check(
            od=457.2,
            pressure_bar=50.0,
            temp=40.0,
            rem_wall=4.5,
            design_life=20,
        )

        updated = apply_type_a_class3_result_to_repair(repair, iso_result)

        self.assertEqual(repair["num_plies"], 2)
        self.assertEqual(updated["num_plies"], 12)
        self.assertAlmostEqual(updated["t_required"], iso_result["tdesign_final_mm"])
        self.assertAlmostEqual(updated["final_thickness"], 12 * PROWRAP["ply_thickness"])
        self.assertAlmostEqual(updated["overlap_length"], iso_result["lover_required_mm"])
        self.assertAlmostEqual(updated["iso_length"], 100.0 + 2 * iso_result["lover_required_mm"])
        self.assertEqual(updated["num_bands"], 3)
        self.assertEqual(updated["proc_length"], 900)


if __name__ == "__main__":
    unittest.main()
