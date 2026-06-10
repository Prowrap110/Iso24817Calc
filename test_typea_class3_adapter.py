import unittest

from prowrap_calculations import calculate_type_a_class3_fallback_check
from prowrap_materials import PROWRAP


class TypeAClass3AdapterTest(unittest.TestCase):
    def test_adapter_maps_app_inputs_and_prowrap_data_to_typea_class3_route(self):
        result = calculate_type_a_class3_fallback_check(
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
        self.assertAlmostEqual(result["input_summary"]["pressure_bar"], 50.0)
        self.assertAlmostEqual(result["input_summary"]["substrate_allowable_pressure_bar"], 0.0)
        self.assertAlmostEqual(result["input_summary"]["lap_shear_mpa"], PROWRAP["long_term_lap_shear"])
        self.assertAlmostEqual(result["input_summary"]["hoop_modulus_mpa"], PROWRAP["modulus_circ"])
        self.assertIn("Formula 11 performance route", result["input_summary"]["performance_data"])
        self.assertGreater(result["tdesign_final_mm"], 0)
        self.assertGreaterEqual(result["layer_count"], 1)

    def test_performance_route_uses_prowrap_eps_lt(self):
        result = calculate_type_a_class3_fallback_check(
            od=457.2,
            pressure_bar=50.0,
            temp=40.0,
            rem_wall=4.5,
            design_life=20,
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


if __name__ == "__main__":
    unittest.main()
