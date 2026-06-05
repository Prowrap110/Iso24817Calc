import ast
from pathlib import Path
import unittest


def load_prowrap_specs():
    source = Path("PWR110Calculator.py").read_text()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "PROWRAP":
                    return ast.literal_eval(node.value)
    raise AssertionError("PROWRAP material spec block was not found")


class ProwrapMaterialSpecsTest(unittest.TestCase):
    def test_specs_match_qualification_data_pdf(self):
        specs = load_prowrap_specs()

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
            "impact_peak_energy": 41.982,
            "short_term_survival": "PASS",
        }

        for key, value in expected.items():
            self.assertEqual(specs[key], value)

    def test_temperature_limit_uses_tg_minus_20_degrees(self):
        specs = load_prowrap_specs()

        self.assertAlmostEqual(
            specs["max_temp"],
            specs["glass_transition_temp"] - 20,
            places=2,
        )


if __name__ == "__main__":
    unittest.main()
