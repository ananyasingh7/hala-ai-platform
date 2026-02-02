import sys
from pathlib import Path
from unittest import TestCase

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.notifications.discord import _chunk_message


class TestDiscordChunking(TestCase):
    def test_chunk_sizes(self) -> None:
        message = "A" * 4005
        chunks = _chunk_message(message, limit=1900)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 1900)
        self.assertEqual("".join(chunks), message)
