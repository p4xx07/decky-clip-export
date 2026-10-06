import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from py_modules.clip_export import _ffmpeg_environment, export_clip


class ExportSafetyTest(unittest.TestCase):
    def test_ffmpeg_restores_library_path_before_launch(self):
        with patch.dict(os.environ, {"LD_LIBRARY_PATH": "/tmp/_MEI123:/system/lib",
                                     "LD_LIBRARY_PATH_ORIG": "/system/lib"}):
            env = _ffmpeg_environment()
            self.assertEqual(env["LD_LIBRARY_PATH"], "/system/lib")
            self.assertNotIn("LD_LIBRARY_PATH_ORIG", env)
            self.assertEqual(os.environ["LD_LIBRARY_PATH"], "/tmp/_MEI123:/system/lib")

    def test_ffmpeg_removes_bundled_path_when_no_original_exists(self):
        with patch.dict(os.environ, {"LD_LIBRARY_PATH": "/tmp/_MEI123", "LD_LIBRARY_PATH_ORIG": ""}):
            self.assertNotIn("LD_LIBRARY_PATH", _ffmpeg_environment())

    def test_low_disk_space_stops_before_creating_video(self):
        with tempfile.TemporaryDirectory() as root:
            clip_dir = Path(root) / "clip_123"
            media = clip_dir / "video" / "fg_123"
            media.mkdir(parents=True)
            (media / "init-stream0.m4s").write_bytes(b"video")
            (media / "init-stream1.m4s").write_bytes(b"audio")
            clip = {"path": clip_dir, "recordings": [{"id": "fg_123"}]}
            output = Path(root) / "output.mp4"
            with patch("py_modules.clip_export.shutil.which", return_value="/usr/bin/ffmpeg"), \
                 patch("py_modules.clip_export.shutil.disk_usage", return_value=SimpleNamespace(free=0)):
                with self.assertRaisesRegex(RuntimeError, "Not enough free space"):
                    export_clip(clip, output)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(root).glob("decky-clip-*")), [])


if __name__ == "__main__":
    unittest.main()
