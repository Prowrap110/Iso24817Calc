"""Baseline-route tests for the new routing rule and ISO Type A factors.

Covers the calculate_repair kwargs added when the baseline was aligned to
the rigorous ISO 24817 Type A / Class 3 module: installation_temp,
component_type, cyclic_derating_factor and axial_load_case, plus the new
External-vs-Internal routing rule.
"""

import math
import unittest

from prowrap_calculations import calculate_repair
from prowrap_materials import PROWRAP
from test_current_calculation_baseline import default_inputs


class RoutingRuleTest(unittest.TestCase):
    def test_external_dent_routes_to_type_a(self):
        r = calculate_repair(**default_inputs(defect_type="Dent"))
        self.assertEqual(r["calc_method_thick"], "Type A (Dent Reinforcement)")
        self.assertEqual(r["calc_method_overlap"], "Type A (Geometry Controlled)")
        # Dents are not blunt metal loss: no B31G substrate credit.
        self.assertEqual(r["p_steel_capacity"], 0.0)

    def test_external_corrosion_routes_to_type_a(self):
        r = calculate_repair(**default_inputs())
        self.assertEqual(r["calc_method_thick"], "Type A (Load Sharing)")
        self.assertEqual(r["calc_method_overlap"], "Type A (Geometry Controlled)")

    def test_internal_corrosion_routes_to_type_b(self):
        r = calculate_repair(
            **default_inputs(defect_loc="Internal"), internal_corrosion_rate=0.1
        )
        self.assertEqual(r["calc_method_thick"], "Type B (Total Replacement)")
        self.assertEqual(r["calc_method_overlap"], "Type B (Shear Controlled)")
        # Laminate sized for the full design pressure (no load sharing).
        self.assertAlmostEqual(r["p_composite_design"], r["pressure_mpa"])

    def test_internal_dent_routes_to_type_b(self):
        r = calculate_repair(
            **default_inputs(defect_type="Dent", defect_loc="Internal")
        )
        self.assertEqual(r["calc_method_thick"], "Type B (Total Replacement)")

    def test_crack_and_leak_route_to_type_b(self):
        for defect_type in ("Crack", "Leak"):
            with self.subTest(defect_type=defect_type):
                r = calculate_repair(**default_inputs(defect_type=defect_type))
                self.assertEqual(
                    r["calc_method_thick"], "Type B (Total Replacement)"
                )
                self.assertEqual(r["p_steel_capacity"], 0.0)


class ComponentAndAxialFactorsTest(unittest.TestCase):
    # 110 bar exceeds the B31G safe pressure, so a genuine composite design
    # pressure exists and tdesign_base > 0 (the factors are observable
    # pre-floor via t_required).
    def test_bend_multiplies_design_thickness_by_1_2_pre_floor(self):
        straight = calculate_repair(**default_inputs(pressure=110.0))
        bend = calculate_repair(
            **default_inputs(pressure=110.0), component_type="Bend"
        )
        self.assertEqual(straight["fth_stress"], 1.0)
        self.assertEqual(bend["fth_stress"], 1.2)
        self.assertGreater(straight["tdesign_base"], 0.0)
        # Same pre-factor design thickness; f_th applied on top of it.
        self.assertAlmostEqual(bend["tdesign_base"], straight["tdesign_base"])
        self.assertAlmostEqual(
            bend["t_required"], 1.2 * straight["tdesign_base"]
        )
        self.assertAlmostEqual(
            straight["t_required"], straight["tdesign_base"]
        )

    def test_axial_load_case_1_applies_formula_4_end_thrust(self):
        case0 = calculate_repair(**default_inputs(pressure=110.0))
        case1 = calculate_repair(
            **default_inputs(pressure=110.0), axial_load_case=1
        )

        # Case 0 (buried/restrained): no axial load, tmin_a clipped to 0.
        self.assertEqual(case0["feq_n"], 0.0)
        self.assertEqual(case0["tmin_a"], 0.0)

        # Case 1: Feq = pi/4 * p * D^2 (Formula 4), p in MPa, D in mm.
        expected_feq = math.pi / 4.0 * 11.0 * 457.2**2
        self.assertAlmostEqual(case1["feq_n"], expected_feq)
        # Axial minimum: t >= [Feq/(pi*D*Ea) - nu*peq*D/(2*Ec)] / eps_a.
        expected_tmin_a = (
            expected_feq / (math.pi * 457.2 * PROWRAP["modulus_axial"])
            - 11.0 * 457.2 * PROWRAP["poisson_circ"] / (2.0 * PROWRAP["modulus_circ"])
        ) / case1["eps_a"]
        self.assertAlmostEqual(case1["tmin_a"], expected_tmin_a)
        # Formula 5 hoop driving load gains the Poisson term
        # nu*Feq/(pi*D), so tmin_c also grows by that increment.
        expected_tmin_c_increase = (
            PROWRAP["poisson_circ"] * expected_feq / (math.pi * 457.2)
        ) / (PROWRAP["modulus_circ"] * case1["design_strain"])
        self.assertAlmostEqual(
            case1["tmin_c"], case0["tmin_c"] + expected_tmin_c_increase
        )
        # The design thickness never decreases when end-thrust is selected.
        self.assertGreaterEqual(case1["t_required"], case0["t_required"])
        self.assertAlmostEqual(
            case1["tdesign_base"], max(case1["tmin_c"], case1["tmin_a"])
        )


class StrainDeratingTest(unittest.TestCase):
    def test_cyclic_derating_scales_both_allowable_strains(self):
        base = calculate_repair(**default_inputs())
        derated = calculate_repair(
            **default_inputs(), cyclic_derating_factor=0.5
        )
        # Formula 25 derating applies proportionally to both the
        # circumferential and the axial allowable strain.
        self.assertAlmostEqual(
            derated["design_strain"], 0.5 * base["design_strain"], places=12
        )
        self.assertAlmostEqual(derated["eps_a"], 0.5 * base["eps_a"], places=12)

    def test_installation_temperature_differential_reduces_eps_a(self):
        # No differential (installed at design temperature): the Formula 10
        # thermal-mismatch term vanishes and eps_a = fT1 * eps_a0.
        no_dt = calculate_repair(**default_inputs(), installation_temp=40.0)
        self.assertAlmostEqual(
            no_dt["eps_a"], no_dt["ft1"] * no_dt["eps_a0"], places=12
        )

        # Default 20 degC installation -> dT = 20 K against the CTE
        # mismatch (substrate 12e-6, PRW110 axial 22.81e-6 per K).
        with_dt = calculate_repair(**default_inputs())
        axial_cte = PROWRAP["thermal_expansion_axial"] * 1e-6
        expected = 1.0 * (
            with_dt["ft1"] * with_dt["eps_a0"]
            - abs((40.0 - 20.0) * (12e-6 - axial_cte))
        )
        self.assertAlmostEqual(with_dt["eps_a"], expected, places=12)
        self.assertLess(with_dt["eps_a"], no_dt["eps_a"])
        # eps_a0 from Table 9 (Ea > 0.5 * Ec): 0.003061 * 10^(-0.0044 * N).
        self.assertAlmostEqual(
            with_dt["eps_a0"], 0.003061 * 10 ** (-0.0044 * 20), places=12
        )
        # Circumferential strain is unaffected by the installation temp.
        self.assertAlmostEqual(
            with_dt["design_strain"], no_dt["design_strain"], places=12
        )


class NewKwargValidationTest(unittest.TestCase):
    def assert_invalid(self, **kwargs):
        with self.assertRaises(ValueError):
            calculate_repair(**default_inputs(), **kwargs)

    def test_rejects_cyclic_factor_of_zero(self):
        self.assert_invalid(cyclic_derating_factor=0.0)

    def test_rejects_cyclic_factor_above_one(self):
        self.assert_invalid(cyclic_derating_factor=1.01)

    def test_rejects_invalid_axial_load_case(self):
        self.assert_invalid(axial_load_case=2)
        self.assert_invalid(axial_load_case=-1)

    def test_rejects_unknown_component_type(self):
        self.assert_invalid(component_type="Elbowish")


if __name__ == "__main__":
    unittest.main()
