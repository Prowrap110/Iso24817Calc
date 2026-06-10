from pathlib import Path
import unittest


class ReportWordingTest(unittest.TestCase):
    def test_report_uses_preliminary_wording_until_iso_route_is_traceable(self):
        source = Path("PWR110Calculator.py").read_text()

        self.assertIn("Preliminary", source)
        self.assertIn("selected ISO 24817 / ASME PCC-2 concepts", source)
        self.assertNotIn("calculated in accordance with ISO 24817", source)


if __name__ == "__main__":
    unittest.main()
