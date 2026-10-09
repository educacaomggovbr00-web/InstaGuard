"""HTTP integration checks against an authorized ephemeral loopback server."""
import http.client
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from types import SimpleNamespace
from urllib.parse import urlencode
from http.server import ThreadingHTTPServer

from dashboard import create_handler
from instaguard import connect


class DashboardHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "test.db"
        connect(self.path).close()
        self.handler = create_handler(self.path, "test-csrf")
        self.in_memory = False
        try:
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
        except PermissionError:
            # Restricted executors prohibit sockets. Run the same HTTP parser,
            # request handler and SQLite operations using byte streams instead.
            self.in_memory = True
            self.server = SimpleNamespace(server_port=8765)
            return
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method="GET", path="/", fields=None, headers=None):
        if self.in_memory:
            payload = (urlencode(fields) if fields is not None else "").encode()
            h = {"Host": "127.0.0.1:8765", "Content-Length": str(len(payload)), **(headers or {})}
            if fields is not None:
                h.setdefault("Content-Type", "application/x-www-form-urlencoded")
            request = (method + " " + path + " HTTP/1.0\r\n" +
                       "".join(key + ": " + value + "\r\n" for key, value in h.items()) + "\r\n").encode() + payload
            class MemorySocket:
                def __init__(self, data):
                    self.input = io.BytesIO(data)
                    self.output = io.BytesIO()
                def makefile(self, *args):
                    return self.input
                def sendall(self, data):
                    self.output.write(data)
            socket = MemorySocket(request)
            self.handler(socket, ("127.0.0.1", 12345), self.server)
            response = http.client.HTTPResponse(MemorySocket(socket.output.getvalue()))
            response.begin()
            return response.status, dict(response.getheaders()), response.read()
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        self.addCleanup(connection.close)
        h = dict(headers or {})
        if fields is not None:
            h.setdefault("Content-Type", "application/x-www-form-urlencoded")
        connection.request(method, path, urlencode(fields) if fields is not None else None, h)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()

    def test_host_origin_and_csrf_guards_prevent_mutation(self):
        fields = {"csrf": "test-csrf", "username": "fictional_example", "category": "other", "reason": "Fictional test"}
        self.assertEqual(self.request(headers={"Host": "attacker.example"})[0], 403)
        self.assertEqual(self.request("POST", "/cases", fields, {"Origin": "https://attacker.example"})[0], 403)
        fields["csrf"] = "wrong"
        self.assertEqual(self.request("POST", "/cases", fields)[0], 403)
        db = connect(self.path)
        try:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM cases").fetchone()[0], 0)
        finally:
            db.close()

    def test_case_evidence_json_download_lifecycle(self):
        fields = {"csrf": "test-csrf", "username": "fictional_example", "category": "other", "reason": "Fictional observation"}
        self.assertEqual(self.request("POST", "/cases", fields)[0], 200)
        self.assertEqual(self.request("POST", "/case/1/evidence", {
            "csrf": "test-csrf", "url": "https://example.org/evidence", "description": "Manual URL",
            "observed_at": "2020-01-01T00:00:00Z", "collector": "tester"})[0], 200)
        code, headers, payload = self.request(path="/case/1/report.json")
        self.assertEqual(code, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        report = json.loads(payload)
        self.assertEqual(report["confirmed_facts"], [])
        self.assertEqual(report["evidence_supplied_by_operator"][0]["collector"], "tester")
        self.assertEqual(self.request(path="/case/1/report")[0], 200)

    def test_invalid_content_type_and_form_size(self):
        self.assertEqual(self.request("POST", "/cases", {}, {"Content-Type": "application/json"})[0], 415)
        self.assertEqual(self.request("POST", "/cases", {"large": "x" * 17000})[0], 413)
