import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


from config.settings import _resolve_feishu_app_credentials


class FeishuCredentialResolutionTest(unittest.TestCase):
    def test_env_values_take_precedence(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            cfg_dir = home / ".lark-cli"
            cfg_dir.mkdir()
            (cfg_dir / "config.json").write_text(
                json.dumps(
                    {
                        "apps": [
                            {
                                "appId": "cli_from_lark",
                                "appSecret": "secret_from_lark",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            env = {
                "FEISHU_APP_ID": "env_app",
                "FEISHU_APP_SECRET": "env_secret",
            }

            with patch.dict(os.environ, env, clear=False), patch("pathlib.Path.home", return_value=home):
                app_id, app_secret = _resolve_feishu_app_credentials()

            self.assertEqual(app_id, "env_app")
            self.assertEqual(app_secret, "env_secret")

    def test_lark_cli_config_is_used_when_env_missing(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            cfg_dir = home / ".lark-cli"
            cfg_dir.mkdir()
            (cfg_dir / "config.json").write_text(
                json.dumps(
                    {
                        "apps": [
                            {
                                "appId": "cli_from_lark",
                                "appSecret": "secret_from_lark",
                                "brand": "feishu",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"FEISHU_APP_ID": "", "FEISHU_APP_SECRET": ""}, clear=False), patch(
                "pathlib.Path.home", return_value=home
            ):
                app_id, app_secret = _resolve_feishu_app_credentials()

            self.assertEqual(app_id, "cli_from_lark")
            self.assertEqual(app_secret, "secret_from_lark")


if __name__ == "__main__":
    unittest.main()
