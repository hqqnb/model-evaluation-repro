import os
import tempfile
import unittest
from unittest import mock

from PIL import Image

import generate_assets


class MultimodalAssetTests(unittest.TestCase):
    def test_bold_font_renders_distinct_chinese_glyphs(self):
        font = generate_assets._font_bold(32)
        glyphs = [bytes(font.getmask(character)) for character in "多模态测评"]

        self.assertEqual(len(set(glyphs)), len(glyphs))

    def test_handwritten_font_uses_chinese_handwriting_face(self):
        regular = generate_assets._font_handwritten(32)
        bold = generate_assets._font_handwritten(32, bold=True)

        self.assertEqual(regular.getname(), ("HanziPen SC", "Regular"))
        self.assertEqual(bold.getname(), ("HanziPen SC", "Bold"))

    def test_mm2_purchase_totals_expose_the_planted_error(self):
        calculated = sum(row["quantity"] * row["unit_price"] for row in generate_assets.MM2_ROWS)

        self.assertEqual(calculated, 345.5)
        self.assertEqual(generate_assets.MM2_WRITTEN_TOTAL, 354.5)
        self.assertEqual(generate_assets.MM2_WRITTEN_TOTAL - calculated, 9.0)
        self.assertEqual(generate_assets.MM2_ROWS[4]["note"], "")
        self.assertNotIn("第5项", generate_assets.MM2_FOOTNOTE)

    def test_mm3_series_preserve_missing_value_and_chart_traps(self):
        self.assertEqual(generate_assets.MM3_ACTUAL, [82, 88, 91, 87, None, 101])
        self.assertEqual(generate_assets.MM3_FORECAST, [80, 85, 90, 94, 98, 103])
        self.assertEqual(generate_assets.MM3_RETURN_RATE, [3.1, 2.8, 3.4, 2.6, 2.2, 1.9])
        self.assertEqual(generate_assets.MM3_SALES_AXIS_MIN, 75)
        self.assertEqual(generate_assets.MM3_MISSING_MARKER_VALUE, 77)
        self.assertEqual(generate_assets.MM3_JUNE_LABEL_SIDES, {"actual": "below", "forecast": "above"})
        self.assertNotIn("左轴从", generate_assets.MM3_CHART_NOTE)

    def test_mm4_dimensions_make_the_300mm_shelf_incompatible(self):
        dims = generate_assets.MM4_DIMENSIONS

        self.assertEqual(dims["max_shelf_depth"], 280)
        self.assertEqual(dims["candidate_shelf_depth"], 300)
        self.assertGreater(dims["candidate_shelf_depth"], dims["max_shelf_depth"])
        self.assertEqual(dims["hole_center_spacing"], 120)
        self.assertNotIn("材料", generate_assets.MM4_DRAWING_NOTE)
        self.assertIn("不得量图推算", generate_assets.MM4_DRAWING_NOTE)

    def test_new_assets_render_with_expected_dimensions(self):
        expected = {
            "MM2_手写表格.png": (1400, 1000),
            "MM3_复杂图表.png": (1500, 1000),
            "MM4_工程草图.png": (1500, 1000),
        }

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(generate_assets, "OUT", tmp):
                generate_assets.mm2_handwritten_table()
                generate_assets.mm3_complex_chart()
                generate_assets.mm4_engineering_sketch()

            for filename, size in expected.items():
                path = os.path.join(tmp, filename)
                self.assertTrue(os.path.exists(path), filename)
                with Image.open(path) as image:
                    self.assertEqual(image.size, size)


if __name__ == "__main__":
    unittest.main()
