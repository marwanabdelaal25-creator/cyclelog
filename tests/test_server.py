"""Tests for cyclelog.server."""

import json
import urllib.request

import pytest

from cyclelog.server import ShedHTTPHandler, ShedServer, run_server
from cyclelog.storage import JsonStorage


class TestShedServer:
    def test_start_and_health(self, populated_storage):
        server = ShedServer(populated_storage, port=0)
        httpd = server.start_background()
        try:
            host, port = server.address
            url = f"http://{host}:{port}/health"
            with urllib.request.urlopen(url) as resp:
                data = json.loads(resp.read())
            assert data["ok"] is True
        finally:
            server.stop()

    def test_root_endpoint(self, populated_storage):
        server = ShedServer(populated_storage, port=0)
        httpd = server.start_background()
        try:
            host, port = server.address
            with urllib.request.urlopen(f"http://{host}:{port}/") as resp:
                data = json.loads(resp.read())
            assert data["service"] == "cyclelog"
        finally:
            server.stop()

    def test_shed_snapshot(self, populated_storage):
        server = ShedServer(populated_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            with urllib.request.urlopen(f"http://{host}:{port}/shed") as resp:
                data = json.loads(resp.read())
            assert "bikes" in data
        finally:
            server.stop()

    def test_bikes_list(self, populated_storage):
        server = ShedServer(populated_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            with urllib.request.urlopen(f"http://{host}:{port}/bikes") as resp:
                data = json.loads(resp.read())
            assert data["count"] >= 2
        finally:
            server.stop()

    def test_bikes_active_false(self, populated_storage, sample_bike):
        populated_storage.update_bike(sample_bike.id, {"archived": True})
        server = ShedServer(populated_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            url = f"http://{host}:{port}/bikes?active=false"
            with urllib.request.urlopen(url) as resp:
                data = json.loads(resp.read())
            assert data["count"] >= 2
        finally:
            server.stop()

    def test_bike_by_id(self, populated_storage, sample_bike):
        server = ShedServer(populated_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            url = f"http://{host}:{port}/bikes/{sample_bike.id}"
            with urllib.request.urlopen(url) as resp:
                data = json.loads(resp.read())
            assert data["id"] == sample_bike.id
        finally:
            server.stop()

    def test_bike_not_found(self, populated_storage):
        server = ShedServer(populated_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            url = f"http://{host}:{port}/bikes/missing"
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(url)
            assert exc.value.code == 404
        finally:
            server.stop()

    def test_unknown_path_404(self, populated_storage):
        server = ShedServer(populated_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(f"http://{host}:{port}/unknown")
            assert exc.value.code == 404
        finally:
            server.stop()

    def test_post_returns_405(self, populated_storage):
        server = ShedServer(populated_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            req = urllib.request.Request(
                f"http://{host}:{port}/bikes",
                method="POST",
                data=b"{}",
            )
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(req)
            assert exc.value.code == 405
        finally:
            server.stop()

    def test_cors_header(self, populated_storage):
        server = ShedServer(populated_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            req = urllib.request.Request(f"http://{host}:{port}/health")
            with urllib.request.urlopen(req) as resp:
                assert resp.headers.get("Access-Control-Allow-Make") == "*"
        finally:
            server.stop()

    def test_address_property(self, populated_storage):
        server = ShedServer(populated_storage, port=0)
        httpd = server.start_background()
        try:
            assert isinstance(server.address, tuple)
            assert server.address[1] > 0
        finally:
            server.stop()

    def test_empty_bikes_count(self, empty_storage):
        server = ShedServer(empty_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            with urllib.request.urlopen(f"http://{host}:{port}/bikes") as resp:
                data = json.loads(resp.read())
            assert data["count"] == 0
        finally:
            server.stop()

    def test_trailing_slash_normalized(self, populated_storage):
        server = ShedServer(populated_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            with urllib.request.urlopen(f"http://{host}:{port}/health/") as resp:
                data = json.loads(resp.read())
            assert data["ok"] is True
        finally:
            server.stop()

    def test_json_content_type(self, populated_storage):
        server = ShedServer(populated_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            with urllib.request.urlopen(f"http://{host}:{port}/health") as resp:
                assert "application/json" in resp.headers.get("Content-Type", "")
        finally:
            server.stop()

    def test_handler_storage_binding(self, populated_storage):
        server = ShedServer(populated_storage, port=0)
        httpd = server.start_background()
        try:
            handler_cls = httpd.RequestHandlerClass
            assert handler_cls.storage is populated_storage
        finally:
            server.stop()
