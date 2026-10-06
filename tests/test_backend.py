import asyncio
import importlib.util
import logging
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class DeckyBackendTest(unittest.TestCase):
    def test_second_export_is_rejected_during_clip_lookup(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            decky = types.SimpleNamespace(
                DECKY_USER_HOME=str(home),
                DECKY_PLUGIN_SETTINGS_DIR=str(home / "settings"),
                DECKY_PLUGIN_RUNTIME_DIR=str(home / "runtime"),
                logger=logging.getLogger("decky-test"),
            )
            with patch.dict(sys.modules, {"decky": decky}):
                spec = importlib.util.spec_from_file_location("decky_clip_test", Path(__file__).parents[1] / "main.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            gate = threading.Event()

            def slow_list(_home):
                gate.wait(timeout=2)
                return []

            async def check():
                plugin = module.Plugin()
                await plugin._main()
                with patch.object(module, "list_clips", slow_list):
                    first = asyncio.create_task(plugin.start_export("missing", "local"))
                    await asyncio.sleep(0.05)
                    with self.assertRaisesRegex(RuntimeError, "Another export"):
                        await plugin.start_export("missing", "local")
                    gate.set()
                    with self.assertRaisesRegex(ValueError, "Clip was not found"):
                        await first
                    self.assertFalse(plugin.busy)

            asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
