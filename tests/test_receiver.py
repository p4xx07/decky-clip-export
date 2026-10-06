import hashlib
import http.client
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

from py_modules.clip_export import pair_receiver, upload_file
from receiver.receiver import ClipReceiver


class ReceiverTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.destination = root / "received"
        self.server = ClipReceiver(("127.0.0.1", 0), self.destination, root / "config.json")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def test_pair_and_upload_with_checksum_and_no_overwrite(self):
        with self.assertRaises(RuntimeError):
            pair_receiver(self.url, "000000" if self.server.pair_code != "000000" else "000001")
        endpoint = pair_receiver(self.url, self.server.pair_code)
        source = Path(self.temp.name) / "test.mp4"
        source.write_bytes(b"video data" * 10000)
        result = upload_file(endpoint, source)
        self.assertEqual(result["size"], source.stat().st_size)
        self.assertEqual(result["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual((self.destination / "test.mp4").read_bytes(), source.read_bytes())
        second = upload_file(endpoint, source)
        self.assertEqual(second["name"], "test (1).mp4")

    def test_upload_requires_token_and_safe_name(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        conn.request("PUT", "/upload/test.mp4", body=b"x")
        response = conn.getresponse()
        self.assertEqual(response.status, 401)
        response.read()
        conn.close()
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        conn.request("PUT", "/upload/%2E%2E%2Fbad.mp4", body=b"x", headers={
            "Authorization": "Bearer " + self.server.token,
        })
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        response.read()
        conn.close()
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_serves_plugin_zip_for_one_time_install(self):
        plugin_zip = Path(self.temp.name) / "ClipExport-0.1.1.zip"
        plugin_zip.write_bytes(b"test zip bytes")
        self.server.plugin_zip = plugin_zip
        with urlopen(self.url + "/ClipExport.zip") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"test zip bytes")


if __name__ == "__main__":
    unittest.main()
