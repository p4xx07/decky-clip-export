import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from py_modules.clip_export import export_clip


class ExportSafetyTest(unittest.TestCase):
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
