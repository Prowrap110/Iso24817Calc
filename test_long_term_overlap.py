import unittest

from prowrap_calculations import calculate_repair
from prowrap_materials import PROWRAP
from test_current_calculation_baseline import default_inputs


class LongTermOverlapTest(unittest.TestCase):
    def test_type_b_overlap_uses_long_term_lap_shear(self):
        # Defaults: temp = 40 degC, installation_temp = 20 degC,
        # design_life = 20 yr, cyclic_derating_factor = 1.0.
        result = calculate_repair(**default_inputs(defect_type="Leak"))

        # Axial allowable strain (Table 9 with Formula 10 thermal mismatch
        # and Formula 25 cyclic derating):
        #   eps_a = f_cyclic * (fT1 * eps_a0 - |dT * (alpha_s - alpha_a)|)
        # Ea > 0.5 * Ec for PRW110, so eps_a0 = 0.003061 * 10^(-0.0044 * N).
        eps_a0 = 0.003061 * 10 ** (-0.0044 * 20)
        delta = PROWRAP["max_temp"] - 40.0
        ft1 = 0.0000625 * delta**2 + 0.00125 * delta + 0.7
        d_temp = 40.0 - 20.0  # design minus installation temperature
        axial_cte = PROWRAP["thermal_expansion_axial"] * 1e-6
        eps_a = 1.0 * (ft1 * eps_a0 - abs(d_temp * (12e-6 - axial_cte)))
        self.assertAlmostEqual(result["eps_a"], eps_a, places=12)

        # ISO Formula (21): l_over > 3 * Ea * eps_a * t / tau (long-term
        # shear). On the Type B route the installed thickness is used
        # (conservative), combined with the Formula (18) geometric overlap
        # and the 50 mm floor.
        expected_transfer = (
            3.0
            * PROWRAP["modulus_axial"]
            * eps_a
            * result["final_thickness"]
        ) / PROWRAP["long_term_lap_shear"]

        self.assertEqual(result["calc_method_overlap"], "Type B (Shear Controlled)")
        self.assertEqual(result["overlap_shear_basis"], "iso_formula_18_and_21_type_b")
        self.assertAlmostEqual(result["overlap_shear_strength"], 9.62)
        self.assertAlmostEqual(result["overlap_transfer"], expected_transfer)
        # Transfer (2754.95 mm) governs over the geometric overlap and floor.
        self.assertAlmostEqual(result["overlap_length"], expected_transfer)
        # Formula (20): defect + 2*overlap + 2*taper (taper = 5*t_installed).
        expected_length = (
            100.0 + 2.0 * expected_transfer + 2.0 * 5.0 * result["final_thickness"]
        )
        self.assertAlmostEqual(result["iso_length"], expected_length)
        # Leak/crack designs must carry the Type B compliance warnings.
        self.assertTrue(
            any("Type B" in w for w in result["compliance_warnings"])
        )


if __name__ == "__main__":
    unittest.main()
