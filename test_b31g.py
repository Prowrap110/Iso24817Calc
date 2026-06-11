import unittest

from b31g import assess_b31g


class B31GTest(unittest.TestCase):
    def test_default_case_modified_b31g(self):
        # 457.2 x 9.53, d = 5.03 mm, L = 100 mm, X52-ish SMYS 359, SF = 1/0.72.
        # Cross-validated against an independent B31G-2023 implementation
        # (itself validated against Appendix A Examples 1-5).
        r = assess_b31g(457.2, 9.53, 9.53 - 4.5, 100.0, 359.0,
                        safety_factor=1.0 / 0.72,
                        operating_pressure_mpa=5.0)

        self.assertEqual(r["method"], "modified")
        self.assertAlmostEqual(r["z"], 2.2951, places=3)
        self.assertAlmostEqual(r["folias_m"], 1.5564, places=3)
        self.assertAlmostEqual(r["s_flow_mpa"], 428.0)
        self.assertAlmostEqual(r["s_f_mpa"], 331.5551, places=3)
        self.assertAlmostEqual(r["p_s_mpa"], 9.951873620726573)
        self.assertTrue(r["applicable"])
        self.assertTrue(r["acceptable"])

    def test_deep_defect_beyond_applicability(self):
        r = assess_b31g(457.2, 9.53, 0.85 * 9.53, 100.0, 359.0)
        self.assertFalse(r["applicable"])
        self.assertTrue(any("d/t > 0.80" in w for w in r["warnings"]))

    def test_original_and_modified_match_reference_values(self):
        # Note: neither method is universally more conservative; both are
        # pinned to reference-validated values for this geometry.
        rm = assess_b31g(457.2, 9.53, 5.03, 200.0, 359.0, method="modified")
        ro = assess_b31g(457.2, 9.53, 5.03, 200.0, 359.0, method="original")
        self.assertAlmostEqual(rm["p_s_mpa"], 8.59232674703706)
        self.assertAlmostEqual(ro["p_s_mpa"], 8.741029368714841)

    def test_high_smys_falls_back_to_original(self):
        r = assess_b31g(457.2, 9.53, 3.0, 100.0, 555.0, method="modified")
        self.assertEqual(r["method"], "original")

    def test_long_defect_z_above_50_uses_linear_folias(self):
        r = assess_b31g(457.2, 9.53, 3.0, 600.0, 359.0, method="modified")
        self.assertGreater(r["z"], 50.0)
        self.assertAlmostEqual(r["folias_m"], 0.032 * r["z"] + 3.3, places=9)


if __name__ == "__main__":
    unittest.main()
