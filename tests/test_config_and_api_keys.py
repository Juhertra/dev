#!/usr/bin/env python3

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.settings import get_settings


class TestApiKeyConfiguration(unittest.TestCase):
    def test_create_app_without_api_keys_uses_empty_list(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("API_KEYS", None)
            flask_app = create_app()
            self.assertEqual(flask_app.config["API_KEYS"], [])

    def test_create_app_parses_comma_separated_api_keys(self):
        with patch.dict(
            os.environ, {"API_KEYS": " alpha-key, beta-key ,,gamma-key "}, clear=False
        ):
            flask_app = create_app()
            self.assertEqual(
                flask_app.config["API_KEYS"], ["alpha-key", "beta-key", "gamma-key"]
            )

    def test_settings_without_api_keys_uses_empty_list(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("API_KEYS", None)
            settings = get_settings()
            self.assertEqual(settings["API_KEYS"], [])

    def test_settings_parses_comma_separated_api_keys(self):
        with patch.dict(
            os.environ, {"API_KEYS": " one, two ,, three "}, clear=False
        ):
            settings = get_settings()
            self.assertEqual(settings["API_KEYS"], ["one", "two", "three"])


if __name__ == "__main__":
    unittest.main()
