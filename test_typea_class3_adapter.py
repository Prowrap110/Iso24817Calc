import unittest

<<<<<<< HEAD
from prowrap_calculations import calculate_type_a_class3_fallback_check
=======
from prowrap_calculations import (
    apply_type_a_class3_result_to_repair,
    calculate_repair,
    calculate_type_a_class3_prowrap_check,
    substrate_credit_bar_for_iso_check,
)
>>>>>>> 8a68a750f614bab57c90dd4beb691606cebee890
from prowrap_materials import PROWRAP


class TypeAClass3AdapterTest(unittest.TestCase):
    def test_adapter_maps_app_inputs_and_prowrap_data_to_typea_class3_route(self):
<<<<<<< HEAD
        result = calculate_type_a_class3_fallback_check(
=======
        result = calculate_type_a_class3_prowrap_check(
>>>>>>> 8a68a750f614bab57c90dd4beb691606cebee890
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
<<<<<<< HEAD
=======
        self.assertAlmostEqual(result["long_term_strain_lcl"], PROWRAP["long_term_strain_20y"])
>>>>>>> 8a68a750f614bab57c90dd4beb691606cebee890
        self.assertAlmostEqual(result["input_summary"]["pressure_bar"], 50.0)
        self.assertAlmostEqual(result["input_summary"]["substrate_allowable_pressure_bar"], 0.0)
        self.assertAlmostEqual(result["input_summary"]["lap_shear_mpa"], PROWRAP["long_term_lap_shear"])
        self.assertAlmostEqual(result["input_summary"]["hoop_modulus_mpa"], PROWRAP["modulus_circ"])
<<<<<<< HEAD
        self.assertIn("Formula 11 performance route", result["input_summary"]["performance_data"])
        self.assertGreater(result["tdesign_final_mm"], 0)
        self.assertGreaterEqual(result["layer_count"], 1)

    def test_performance_route_uses_prowrap_eps_lt(self):
        result = calculate_type_a_class3_fallback_check(
=======
        self.assertEqual(result["input_summary"]["performance_data"], "PRW110 20-year long-term strain")
        self.assertGreater(result["tdesign_final_mm"], 0)
        self.assertGreaterEqual(result["layer_count"], 1)

    def test_iso_result_can_drive_displayed_repair_metrics_when_pressure_deficit_exists(self):
        repair = calculate_repair(
            customer="PROTAP",
            location="Turkey",
            report_no="24-152",
            od=457.2,
            wall=9.53,
            pressure=60.0,
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
            pressure_bar=60.0,
            temp=40.0,
            rem_wall=4.5,
            design_life=20,
            substrate_allowable_pressure_bar=substrate_credit_bar_for_iso_check(repair),
        )

        updated = apply_type_a_class3_result_to_repair(repair, iso_result)

        self.assertEqual(repair["num_plies"], 2)
        self.assertEqual(updated["num_plies"], 9)
        self.assertTrue(updated["iso_typea_class3_controls"])
        self.assertAlmostEqual(updated["t_required"], iso_result["tdesign_final_mm"])
        self.assertAlmostEqual(updated["final_thickness"], 9 * PROWRAP["ply_thickness"])
        self.assertAlmostEqual(updated["overlap_length"], iso_result["lover_required_mm"])
        self.assertAlmostEqual(updated["iso_length"], 100.0 + 2 * iso_result["lover_required_mm"])
        self.assertEqual(updated["num_bands"], 2)
        self.assertEqual(updated["proc_length"], 600)

    def test_external_non_leak_crack_uses_effective_pipe_capacity_as_substrate_credit(self):
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

        credit_bar = substrate_credit_bar_for_iso_check(repair)
        iso_result = calculate_type_a_class3_prowrap_check(
>>>>>>> 8a68a750f614bab57c90dd4beb691606cebee890
            od=457.2,
            pressure_bar=50.0,
            temp=40.0,
            rem_wall=4.5,
            design_life=20,
<<<<<<< HEAD
        )
        # Formula 11: eps_c = fperf * fT2 * eps_lt (design-life data, Class 3)
        eps_lt = PROWRAP["long_term_strain_lcl"]
        fperf = 0.76 * 10 ** (-0.00273 * 20)
        delta = PROWRAP["max_temp"] - 40.0  # Ttest == Tamb in the adapter
        ft2 = 0.0000625 * delta**2 + 0.00125 * delta + 0.7
        self.assertAlmostEqual(result["eps_c"], fperf * ft2 * eps_lt, places=9)

    def test_cyclic_factor_applies_on_performance_route(self):
        base = calculate_type_a_class3_fallback_check(
            od=457.2, pressure_bar=50.0, temp=40.0, rem_wall=4.5, design_life=20,
        )
        derated = calculate_type_a_class3_fallback_check(
            od=457.2, pressure_bar=50.0, temp=40.0, rem_wall=4.5, design_life=20,
            cyclic_derating_factor=0.5,
        )
        self.assertAlmostEqual(derated["eps_c"], 0.5 * base["eps_c"], places=9)
=======
            substrate_allowable_pressure_bar=credit_bar,
        )
        updated = apply_type_a_class3_result_to_repair(repair, iso_result)

        self.assertAlmostEqual(credit_bar, repair["p_steel_capacity"] * 10.0)
        self.assertGreaterEqual(credit_bar, 50.0)
        self.assertEqual(iso_result["layer_count"], 8)
        self.assertEqual(updated["num_plies"], 2)
        self.assertFalse(updated["iso_typea_class3_controls"])
        self.assertEqual(updated["iso_typea_class3_noncontrolling_reason"], "effective_pipe_capacity_covers_design_pressure")
        self.assertAlmostEqual(
            iso_result["input_summary"]["substrate_allowable_pressure_bar"],
            credit_bar,
        )

    def test_leak_crack_and_internal_do_not_get_substrate_credit(self):
        for defect_type, defect_loc in [
            ("Leak", "External"),
            ("Crack", "External"),
            ("Corrosion", "Internal"),
        ]:
            with self.subTest(defect_type=defect_type, defect_loc=defect_loc):
                repair = calculate_repair(
                    customer="PROTAP",
                    location="Turkey",
                    report_no="24-152",
                    od=457.2,
                    wall=9.53,
                    pressure=50.0,
                    temp=40.0,
                    defect_type=defect_type,
                    defect_loc=defect_loc,
                    length=100.0,
                    rem_wall=4.5,
                    yield_strength=359.0,
                    design_factor=0.72,
                    design_life=20,
                )

                self.assertEqual(substrate_credit_bar_for_iso_check(repair), 0.0)
>>>>>>> 8a68a750f614bab57c90dd4beb691606cebee890


if __name__ == "__main__":
    unittest.main()
