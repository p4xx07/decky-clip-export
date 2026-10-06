"""End-to-end packaged plugin test; CLIP_SAMPLE_DIR can point at a real clip."""

import asyncio
import importlib.util
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from receiver.receiver import ClipReceiver


SAMPLE = os.environ.get("CLIP_SAMPLE_DIR")
ARCHIVE = Path(__file__).parents[1] / "ClipExport-0.1.0.zip"


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe") and ARCHIVE.is_file(),
                     "Install ffmpeg and build the plugin ZIP to run the integration test")
class PackagedIntegrationTest(unittest.TestCase):
    def test_local_export_and_paired_transfer(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            sample = Path(SAMPLE) if SAMPLE else self._make_fixture(base)
            original = sample / f"{sample.name}.mp4"
            self.assertTrue((sample / "clip.pb").is_file())
            self.assertTrue(original.is_file())
            with zipfile.ZipFile(ARCHIVE) as archive:
                archive.extractall(base / "plugins")
            plugin_file = base / "plugins" / "Clip Export" / "main.py"
            home = base / "deck-home"
            home.mkdir()
            clip_root = base / "clips"
            clip_root.mkdir()
            (clip_root / sample.name).symlink_to(sample, target_is_directory=True)
            decky = types.SimpleNamespace(
                DECKY_USER_HOME=str(home),
                DECKY_PLUGIN_SETTINGS_DIR=str(home / "settings"),
                DECKY_PLUGIN_RUNTIME_DIR=str(home / "runtime"),
                logger=logging.getLogger("decky-integration-test"),
            )
            with patch.dict(sys.modules, {"decky": decky}), \
                 patch.dict(os.environ, {"CLIP_EXPORT_CLIPS_DIR": str(clip_root)}):
                spec = importlib.util.spec_from_file_location("decky_clip_integration", plugin_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                receiver = ClipReceiver(("127.0.0.1", 0), base / "received", base / "receiver.json")
                thread = threading.Thread(target=receiver.serve_forever, daemon=True)
                thread.start()
                try:
                    asyncio.run(self._exercise(module.Plugin(), receiver, home, original))
                finally:
                    receiver.shutdown()
                    receiver.server_close()
                    thread.join()

    def _make_fixture(self, base):
        sample = base / "clip_123_fixture"
        media = sample / "video" / "fg_123_fixture"
        media.mkdir(parents=True)
        original = sample / f"{sample.name}.mp4"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
            "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(original),
        ], check=True)
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(original),
            "-map", "0:v:0", "-map", "0:a:0", "-c", "copy", "-f", "dash",
            "-seg_duration", "1", "-use_template", "1", "-use_timeline", "0",
            "-init_seg_name", "init-stream$RepresentationID$.m4s",
            "-media_seg_name", "chunk-stream$RepresentationID$-$Number%05d$.m4s",
            str(media / "session.mpd"),
        ], check=True)

        def varint(value):
            result = bytearray()
            while value > 127:
                result.append((value & 127) | 128)
                value >>= 7
            result.append(value)
            return bytes(result)

        def number(field, value):
            return varint(field << 3) + varint(value)

        def data(field, value):
            return varint((field << 3) | 2) + varint(len(value)) + value

        recording = data(1, b"fg_123_fixture") + number(3, 2000)
        timeline = data(1, b"timeline_fixture") + data(5, recording)
        (sample / "clip.pb").write_bytes(data(1, timeline) + number(3, 1791292283) + number(4, 123))
        return sample

    async def _exercise(self, plugin, receiver, home, original):
        await plugin._main()
        clips = await plugin.get_clips()
        self.assertEqual(len(clips), 1)
        clip_id = clips[0]["id"]
        await self._wait(plugin, await plugin.start_export(clip_id, "local"))
        local = next((home / "Videos" / "Steam Deck Clips").glob("*.mp4"))
        self._assert_same_media(local, original)
        endpoint = await plugin.pair(f"http://127.0.0.1:{receiver.server_port}", receiver.pair_code)
        await self._wait(plugin, await plugin.start_export(clip_id, endpoint["id"]))
        received = next(receiver.destination.glob("*.mp4"))
        self._assert_same_media(received, original)
        self.assertEqual(await plugin.get_endpoints(), [endpoint])

    async def _wait(self, plugin, job_id):
        for _ in range(600):
            status = await plugin.get_job(job_id)
            if status["state"] != "working":
                self.assertEqual(status["state"], "done", status)
                return
            await asyncio.sleep(0.1)
        self.fail("Export did not finish within 60 seconds")

    def _assert_same_media(self, candidate, original):
        original_duration, original_hashes = self._streams(original)
        candidate_duration, candidate_hashes = self._streams(candidate)
        self.assertAlmostEqual(candidate_duration, original_duration, delta=0.1)
        self.assertEqual(candidate_hashes, original_hashes)

    def _streams(self, path):
        probe = json.loads(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)], text=True))
        hashes = subprocess.check_output(
            ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0", "-c", "copy",
             "-f", "streamhash", "-hash", "sha256", "-"], text=True)
        return float(probe["format"]["duration"]), hashes


if __name__ == "__main__":
    unittest.main()
