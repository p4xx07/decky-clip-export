"""Steam clip discovery, lossless MP4 export, and paired LAN transfer."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def _varint(data: bytes, pos: int) -> tuple[int, int]:
    value = shift = 0
    while pos < len(data):
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, pos
        shift += 7
        if shift > 70:
            raise ValueError("Invalid protobuf varint")
    raise ValueError("Truncated protobuf varint")


def _fields(data: bytes) -> dict[int, list[int | bytes]]:
    fields: dict[int, list[int | bytes]] = {}
    pos = 0
    while pos < len(data):
        key, pos = _varint(data, pos)
        number, wire = key >> 3, key & 7
        if wire == 0:
            value, pos = _varint(data, pos)
        elif wire == 2:
            length, pos = _varint(data, pos)
            if length > len(data) - pos:
                raise ValueError("Truncated protobuf field")
            value = data[pos : pos + length]
            pos += length
        elif wire in (1, 5):
            size = 8 if wire == 1 else 4
            if size > len(data) - pos:
                raise ValueError("Truncated protobuf field")
            value = data[pos : pos + size]
            pos += size
        else:
            raise ValueError(f"Unsupported protobuf wire type {wire}")
        fields.setdefault(number, []).append(value)
    return fields


def _first(fields: dict, number: int, default=None):
    return fields.get(number, [default])[0]


def read_clip_metadata(path: Path) -> dict:
    data = _fields(path.read_bytes())
    recordings = []
    for timeline_bytes in data.get(1, []):
        timeline = _fields(timeline_bytes)
        for record_bytes in timeline.get(5, []):
            record = _fields(record_bytes)
            raw_id = _first(record, 1, b"")
            recording_id = raw_id.decode("utf-8")
            if not re.fullmatch(r"[A-Za-z0-9_-]+", recording_id):
                raise ValueError("Invalid recording ID")
            recordings.append({
                "id": recording_id,
                "start_offset_ms": int(_first(record, 2, 0)),
                "duration_ms": int(_first(record, 3, 0)),
            })
    raw_name = _first(data, 7, b"")
    return {
        "game_id": int(_first(data, 4, 0)),
        "date_recorded": int(_first(data, 3, 0)),
        "name": raw_name.decode("utf-8", errors="replace"),
        "recordings": recordings,
    }


def _steamapps_dirs(home: Path) -> list[Path]:
    roots = [home / ".local/share/Steam", home / ".steam/steam"]
    dirs: set[Path] = set()
    for root in roots:
        steamapps = root / "steamapps"
        if steamapps.is_dir():
            dirs.add(steamapps.resolve())
            libraries = steamapps / "libraryfolders.vdf"
            if libraries.is_file():
                text = libraries.read_text(encoding="utf-8", errors="replace")
                for raw in re.findall(r'"path"\s+"([^"]+)"', text):
                    candidate = Path(raw.replace("\\\\", "\\")) / "steamapps"
                    if candidate.is_dir():
                        dirs.add(candidate.resolve())
    return sorted(dirs)


def _game_names(home: Path, app_ids: set[int]) -> dict[int, str]:
    names = {}
    for steamapps in _steamapps_dirs(home):
        for app_id in app_ids:
            if app_id in names:
                continue
            manifest = steamapps / f"appmanifest_{app_id}.acf"
            if manifest.is_file():
                text = manifest.read_text(encoding="utf-8", errors="replace")
                match = re.search(r'"name"\s+"((?:\\.|[^"])*)"', text)
                if match:
                    names[app_id] = match.group(1).replace('\\"', '"')
    return names


def _clip_roots(home: Path) -> list[Path]:
    override = os.environ.get("CLIP_EXPORT_CLIPS_DIR")
    if override:
        return [Path(override).expanduser()]
    roots: set[Path] = set()
    for steam_root in (home / ".local/share/Steam", home / ".steam/steam"):
        userdata = steam_root / "userdata"
        if userdata.is_dir():
            for clips in userdata.glob("*/gamerecordings/clips"):
                if clips.is_dir():
                    roots.add(clips.resolve())
    return sorted(roots)


def list_clips(home: Path) -> list[dict]:
    clips = []
    for root in _clip_roots(home):
        for path in root.glob("clip_*"):
            if not path.is_dir() or not (path / "clip.pb").is_file():
                continue
            try:
                metadata = read_clip_metadata(path / "clip.pb")
            except (OSError, ValueError, UnicodeError):
                continue
            app_id = metadata["game_id"]
            if not app_id:
                match = re.match(r"clip_(\d+)_", path.name)
                app_id = int(match.group(1)) if match else 0
            recorded = metadata["date_recorded"] or int(path.stat().st_mtime)
            clips.append({
                "id": hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:20],
                "path": path,
                "app_id": app_id,
                "name": metadata["name"],
                "recorded_at": recorded,
                "date": datetime.fromtimestamp(recorded).strftime("%Y-%m-%d %H:%M"),
                "duration_seconds": round(sum(r["duration_ms"] for r in metadata["recordings"]) / 1000),
                "recordings": metadata["recordings"],
            })
    names = _game_names(home, {c["app_id"] for c in clips})
    for clip in clips:
        clip["game"] = names.get(clip["app_id"], f"App {clip['app_id']}")
    clips.sort(key=lambda c: c["recorded_at"], reverse=True)
    return clips


def _safe_name(name: str) -> str:
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip(" .")
    return name[:90] or "Steam clip"


def output_name(clip: dict) -> str:
    date = datetime.fromtimestamp(clip["recorded_at"]).strftime("%Y-%m-%d_%H-%M-%S")
    return f"{_safe_name(clip['game'])}_{date}_{clip['id'][:6]}.mp4"


def _join_stream(recording_dir: Path, stream: int, target: Path) -> None:
    init = recording_dir / f"init-stream{stream}.m4s"
    chunks = sorted(recording_dir.glob(f"chunk-stream{stream}-*.m4s"))
    if not init.is_file() or not chunks:
        raise ValueError(f"Missing stream {stream} in {recording_dir.name}")
    numbers = []
    for chunk in chunks:
        match = re.fullmatch(rf"chunk-stream{stream}-(\d+)\.m4s", chunk.name)
        if match:
            numbers.append(int(match.group(1)))
    if numbers != list(range(1, len(numbers) + 1)) or len(numbers) != len(chunks):
        raise ValueError(f"Incomplete stream {stream} in {recording_dir.name}")
    with target.open("wb") as out:
        for part in [init, *chunks]:
            with part.open("rb") as source:
                shutil.copyfileobj(source, out, 1024 * 1024)


def _ffmpeg_environment() -> dict[str, str]:
    """Let the system ffmpeg load system libraries, not Decky's bundled ones."""
    env = os.environ.copy()
    original = env.pop("LD_LIBRARY_PATH_ORIG", None)
    if original:
        env["LD_LIBRARY_PATH"] = original
    else:
        env.pop("LD_LIBRARY_PATH", None)
    return env


def export_clip(clip: dict, target: Path, progress=lambda _: None) -> None:
    recordings = clip["recordings"]
    if not recordings:
        raise ValueError("This clip has no recording media")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required on the Steam Deck")
    ffmpeg_env = _ffmpeg_environment()
    target.parent.mkdir(parents=True, exist_ok=True)
    media_bytes = 0
    for recording in recordings:
        recording_dir = clip["path"] / "video" / recording["id"]
        if not recording_dir.is_dir():
            raise ValueError(f"Recording media is missing: {recording['id']}")
        media_bytes += sum(part.stat().st_size for part in recording_dir.glob("*.m4s"))
    required = 2 * media_bytes + 64 * 1024 * 1024
    if shutil.disk_usage(target.parent).free < required:
        gib = required / (1024 ** 3)
        raise RuntimeError(f"Not enough free space for export; need about {gib:.1f} GiB")
    partial = target.with_name(target.name + ".partial")
    with tempfile.TemporaryDirectory(prefix="decky-clip-", dir=target.parent) as temp:
        temp_dir = Path(temp)
        try:
            parts = []
            for index, recording in enumerate(recordings):
                recording_dir = clip["path"] / "video" / recording["id"]
                if not recording_dir.is_dir():
                    raise ValueError(f"Recording media is missing: {recording['id']}")
                progress(f"Preparing recording {index + 1} of {len(recordings)}")
                video = temp_dir / f"video-{index}.mp4"
                audio = temp_dir / f"audio-{index}.mp4"
                _join_stream(recording_dir, 0, video)
                _join_stream(recording_dir, 1, audio)
                part = partial if len(recordings) == 1 else temp_dir / f"part-{index}.mp4"
                command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
                           "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c", "copy",
                           "-movflags", "+faststart", "-f", "mp4", str(part)]
                proc = subprocess.run(command, capture_output=True, text=True, timeout=3600, env=ffmpeg_env)
                if proc.returncode:
                    raise RuntimeError(proc.stderr.strip()[-1000:] or "ffmpeg failed")
                parts.append(part)
                video.unlink()
                audio.unlink()
            if len(parts) > 1:
                progress("Joining recordings")
                playlist = temp_dir / "parts.txt"
                playlist.write_text("".join(f"file 'part-{i}.mp4'\n" for i in range(len(parts))))
                proc = subprocess.run(
                    [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                     "-i", str(playlist), "-map", "0:v:0", "-map", "0:a:0", "-c", "copy",
                     "-movflags", "+faststart", "-f", "mp4", str(partial)],
                    capture_output=True, text=True, timeout=3600, env=ffmpeg_env,
                )
                if proc.returncode:
                    raise RuntimeError(proc.stderr.strip()[-1000:] or "Could not join recordings")
            os.replace(partial, target)
        finally:
            partial.unlink(missing_ok=True)


def normalize_endpoint(url: str) -> str:
    url = url.strip().rstrip("/")
    parsed = urlsplit(url)
    if (parsed.scheme != "http" or not parsed.hostname or parsed.username or
            parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise ValueError("Enter an HTTP receiver URL such as http://192.168.1.20:57321")
    return url


def pair_receiver(url: str, code: str) -> dict:
    url = normalize_endpoint(url)
    if not re.fullmatch(r"\d{6}", code.strip()):
        raise ValueError("Enter the six-digit code shown on the computer")
    body = json.dumps({"code": code.strip()}).encode()
    req = Request(url + "/pair", body, {"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=15) as response:
            result = json.load(response)
    except HTTPError as exc:
        try:
            detail = json.load(exc).get("error", exc.reason)
        except (ValueError, OSError):
            detail = exc.reason
        finally:
            exc.close()
        raise RuntimeError(f"Could not pair with receiver: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Could not pair with receiver: {exc}") from exc
    if not isinstance(result.get("token"), str) or not result["token"]:
        raise RuntimeError("Receiver returned no token")
    return {"id": hashlib.sha256(url.encode()).hexdigest()[:12],
            "name": str(result.get("name") or "Computer")[:60],
            "url": url, "token": result["token"]}


def upload_file(endpoint: dict, path: Path, progress=lambda _: None) -> dict:
    parsed = urlsplit(normalize_endpoint(endpoint["url"]))
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=60)
    size = path.stat().st_size
    digest = hashlib.sha256()
    try:
        connection.putrequest("PUT", "/upload/" + quote(path.name))
        connection.putheader("Authorization", "Bearer " + endpoint["token"])
        connection.putheader("Content-Type", "video/mp4")
        connection.putheader("Content-Length", str(size))
        connection.endheaders()
        sent = 0
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                connection.send(chunk)
                digest.update(chunk)
                sent += len(chunk)
                progress(f"Sending to {endpoint['name']}: {round(sent * 100 / size)}%")
        response = connection.getresponse()
        body = response.read()
        if response.status != 201:
            raise RuntimeError(f"Receiver rejected upload ({response.status}): {body[:200].decode(errors='replace')}")
        result = json.loads(body)
        if result.get("sha256") != digest.hexdigest() or result.get("size") != size:
            raise RuntimeError("Receiver checksum or size did not match")
        return result
    finally:
        connection.close()
