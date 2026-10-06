"""Decky Loader backend entry point."""

import asyncio
import json
import os
import secrets
import sys
import tempfile
from pathlib import Path

import decky

sys.path.insert(0, str(Path(__file__).resolve().parent / "py_modules"))
from clip_export import export_clip, list_clips, output_name, pair_receiver, upload_file


class Plugin:
    async def _main(self):
        self.home = Path(decky.DECKY_USER_HOME)
        self.settings_dir = Path(decky.DECKY_PLUGIN_SETTINGS_DIR)
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.settings_dir / "receivers.json"
        self.endpoints = self._read_endpoints()
        self.jobs = {}
        self.busy = False
        decky.logger.info("Decky Clip Export ready")

    def _read_endpoints(self):
        try:
            value = json.loads(self.settings_file.read_text())
            return value if isinstance(value, list) else []
        except (OSError, ValueError):
            return []

    def _save_endpoints(self):
        fd, temp = tempfile.mkstemp(prefix="receivers-", dir=self.settings_dir)
        try:
            os.chmod(temp, 0o600)
            with os.fdopen(fd, "w") as out:
                json.dump(self.endpoints, out)
            os.replace(temp, self.settings_file)
        finally:
            Path(temp).unlink(missing_ok=True)

    async def get_endpoints(self):
        return [{"id": e["id"], "name": e["name"], "url": e["url"]} for e in self.endpoints]

    async def pair(self, url: str, code: str):
        endpoint = await asyncio.to_thread(pair_receiver, url, code)
        self.endpoints = [e for e in self.endpoints if e["id"] != endpoint["id"]]
        self.endpoints.append(endpoint)
        self._save_endpoints()
        return {"id": endpoint["id"], "name": endpoint["name"], "url": endpoint["url"]}

    async def remove_endpoint(self, endpoint_id: str):
        self.endpoints = [e for e in self.endpoints if e["id"] != endpoint_id]
        self._save_endpoints()
        return True

    async def get_clips(self):
        clips = await asyncio.to_thread(list_clips, self.home)
        return [{key: value for key, value in clip.items() if key not in ("path", "recordings")}
                for clip in clips]

    async def start_export(self, clip_id: str, destination: str):
        if self.busy:
            raise RuntimeError("Another export is still running")
        clips = await asyncio.to_thread(list_clips, self.home)
        clip = next((c for c in clips if c["id"] == clip_id), None)
        if clip is None:
            raise ValueError("Clip was not found. Refresh the list")
        endpoint = None
        if destination != "local":
            endpoint = next((e for e in self.endpoints if e["id"] == destination), None)
            if endpoint is None:
                raise ValueError("Receiver was not found. Pair it again")
        job_id = secrets.token_hex(8)
        self.jobs[job_id] = {"state": "working", "message": "Starting export"}
        self.busy = True
        asyncio.create_task(self._run_export(job_id, clip, endpoint))
        return job_id

    async def _run_export(self, job_id, clip, endpoint):
        def progress(message):
            self.jobs[job_id]["message"] = message

        try:
            if endpoint is None:
                output_dir = self.home / "Videos" / "Steam Deck Clips"
                output_dir.mkdir(parents=True, exist_ok=True)
                target = output_dir / output_name(clip)
                counter = 1
                while target.exists():
                    target = output_dir / f"{Path(output_name(clip)).stem} ({counter}).mp4"
                    counter += 1
                await asyncio.to_thread(export_clip, clip, target, progress)
                message = f"Saved to {target}"
            else:
                with tempfile.TemporaryDirectory(prefix="decky-clip-upload-") as temp:
                    target = Path(temp) / output_name(clip)
                    await asyncio.to_thread(export_clip, clip, target, progress)
                    result = await asyncio.to_thread(upload_file, endpoint, target, progress)
                    message = f"Sent {result['name']} to {endpoint['name']}"
            self.jobs[job_id] = {"state": "done", "message": message}
        except Exception as exc:
            decky.logger.exception("Clip export failed")
            self.jobs[job_id] = {"state": "error", "message": str(exc)}
        finally:
            self.busy = False

    async def get_job(self, job_id: str):
        return self.jobs.get(job_id, {"state": "error", "message": "Job not found"})
