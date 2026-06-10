import unittest

from prowrap_calculations import calculate_repair
from test_current_calculation_baseline import default_inputs


class InputValidationTest(unittest.TestCase):
    def assert_invalid(self, **overrides):
        with self.assertRaises(ValueError):
            calculate_repair(**default_inputs(**overrides))

    def test_rejects_temperature_above_limit(self):
        self.assert_invalid(temp=58.19)

    def test_rejects_remaining_wall_greater_than_nominal(self):
        self.assert_invalid(rem_wall=10.0)

    def test_rejects_zero_wall(self):
        self.assert_invalid(wall=0)

    def test_rejects_zero_od(self):
        self.assert_invalid(od=0)

    def test_rejects_negative_pressure(self):
        self.assert_invalid(pressure=-1)

    def test_rejects_invalid_design_factor(self):
        self.assert_invalid(design_factor=0)
        self.assert_invalid(design_factor=1.1)


if __name__ == "__main__":
    unittest.main()
