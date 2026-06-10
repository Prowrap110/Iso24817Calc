import unittest

from prowrap_materials import PROWRAP


class ProwrapMaterialSpecsTest(unittest.TestCase):
    def test_specs_match_qualification_data_pdf(self):
        specs = PROWRAP

        expected = {
            "ply_thickness": 0.83,
            "modulus_circ": 45460,
            "strain_fail": 0.0233,
            "tensile_strength": 574.1,
            "modulus_axial": 43800,
            "strain_fail_axial": 0.0243,
            "tensile_strength_axial": 563.67,
            "poisson_circ": 0.066,
            "compressive_modulus": 3310,
            "compressive_strength": 85.58,
            "shear_modulus": 2450,
            "shore_d": 79.1,
            "glass_transition_temp": 78.18,
            "peak_exotherm_temp": 104,
            "thermal_expansion_circ": 10.34,
            "thermal_expansion_axial": 22.81,
            "lap_shear": 14.7,
            "long_term_lap_shear": 9.62,
            "long_term_strain_20y": 0.0055,
            "impact_peak_energy": 41.982,
            "short_term_survival": "PASS",
        }

        for key, value in expected.items():
            self.assertEqual(specs[key], value)

    def test_temperature_limit_uses_tg_minus_20_degrees(self):
        specs = PROWRAP

        self.assertAlmostEqual(
            specs["max_temp"],
            specs["glass_transition_temp"] - 20,
            places=2,
        )

    def test_required_material_keys_are_present(self):
        required_keys = {
            "ply_thickness",
            "modulus_circ",
            "strain_fail",
            "tensile_strength",
            "modulus_axial",
            "strain_fail_axial",
            "tensile_strength_axial",
            "poisson_circ",
            "compressive_modulus",
            "compressive_strength",
            "shear_modulus",
            "shore_d",
            "glass_transition_temp",
            "peak_exotherm_temp",
            "thermal_expansion_circ",
            "thermal_expansion_axial",
            "lap_shear",
            "long_term_lap_shear",
<<<<<<< HEAD
            "long_term_strain_lcl",
=======
            "long_term_strain_20y",
>>>>>>> 8a68a750f614bab57c90dd4beb691606cebee890
            "impact_peak_energy",
            "short_term_survival",
            "max_temp",
            "cloth_width_mm",
            "stitching_overlap_mm",
        }

        self.assertEqual(set(PROWRAP), required_keys)


if __name__ == "__main__":
    unittest.main()
