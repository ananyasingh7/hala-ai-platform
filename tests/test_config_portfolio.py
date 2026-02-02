import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.newsletter import config as newsletter_config


class TestPortfolioConfig(TestCase):
    def test_portfolio_overrides_public_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            newsletter_path = root / "newsletter.yaml"
            portfolio_path = root / "portfolio.yaml"

            newsletter_path.write_text(
                yaml.safe_dump(
                    {
                        "news": {"page_size": 5},
                        "portfolio": {"equities": [], "crypto_ids": []},
                    }
                ),
                encoding="utf-8",
            )
            portfolio_path.write_text(
                yaml.safe_dump(
                    {
                        "portfolio": {
                            "equities": ["AAPL", "NVDA"],
                            "crypto_ids": ["bitcoin"],
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(newsletter_config, "DEFAULT_CONFIG_PATH", newsletter_path), patch.object(
                newsletter_config, "PORTFOLIO_CONFIG_PATH", portfolio_path
            ):
                loaded = newsletter_config.load_newsletter_config()

            self.assertEqual(loaded["news"]["page_size"], 5)
            self.assertEqual(loaded["portfolio"]["equities"], ["AAPL", "NVDA"])
            self.assertEqual(loaded["portfolio"]["crypto_ids"], ["bitcoin"])
