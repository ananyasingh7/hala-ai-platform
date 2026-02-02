import os
import sys
from pathlib import Path
from unittest import TestCase

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.newsletter.compiler import _format_timestamp


class TestTimestampFormat(TestCase):
    def test_format_timestamp_utc(self) -> None:
        os.environ["NEWSLETTER_TZ"] = "UTC"
        formatted = _format_timestamp("2026-02-02T01:26:52.450070")
        self.assertIn("Feb 02, 2026", formatted)
        self.assertTrue(formatted.endswith("UTC"))
