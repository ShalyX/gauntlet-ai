"""Integration test fixtures for GauntletAI live HTTP round-trips and mock agent service."""

import http.server
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
from typing import Generator, Optional
import urllib.error
import urllib.request
import pytest

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.mock_agent_service import AgentRequestHandler

# Windows compatibility settings for GenVM direct runner if available
from gltest.direct import loader as direct_loader
from gltest.direct import sdk_loader
from gltest.direct.vm import VMContext

GENVM_DIRECT_VERSION = "v0.2.16"
_setup_sdk_paths = sdk_loader.setup_sdk_paths
_cleanup_after_deactivate = VMContext._cleanup_after_deactivate


def _setup_pinned_sdk_paths(contract_path: Optional[Path] = None, version: Optional[str] = None):
    return _setup_sdk_paths(contract_path, version or GENVM_DIRECT_VERSION)


sdk_loader.setup_sdk_paths = _setup_pinned_sdk_paths
sdk_loader.setup_sdk_paths()


def _inject_message_to_fd0_windows(vm: VMContext) -> None:
    from genlayer.py import calldata
    from genlayer.py.types import Address

    sender = Address(vm.sender) if isinstance(vm.sender, bytes) else vm.sender
    contract = (
        Address(vm._contract_address)
        if isinstance(vm._contract_address, bytes)
        else vm._contract_address
    )
    origin = Address(vm.origin) if isinstance(vm.origin, bytes) else vm.origin
    encoded = calldata.encode(
        {
            "contract_address": contract,
            "sender_address": sender,
            "origin_address": origin,
            "stack": [],
            "value": vm._value,
            "datetime": vm._datetime,
            "is_init": False,
            "chain_id": vm._chain_id,
            "entry_kind": 0,
            "entry_data": b"",
            "entry_stage_data": None,
        }
    )

    fd, path = tempfile.mkstemp()
    try:
        os.write(fd, encoded)
        os.lseek(fd, 0, os.SEEK_SET)
        vm._original_stdin_fd = os.dup(0)
        os.dup2(fd, 0)
        vm._gauntlet_stdin_path = path
    finally:
        os.close(fd)


def _cleanup_windows_stdin(self: VMContext) -> None:
    path = getattr(self, "_gauntlet_stdin_path", None)
    try:
        _cleanup_after_deactivate(self)
    finally:
        if path:
            try:
                Path(path).unlink()
            except FileNotFoundError:
                pass
            self._gauntlet_stdin_path = None


if os.name == "nt":
    direct_loader._inject_message_to_fd0 = _inject_message_to_fd0_windows
    VMContext._cleanup_after_deactivate = _cleanup_windows_stdin


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def mock_agent_server() -> Generator[str, None, None]:
    """Spins up the mock agent HTTP service on a background daemon thread."""
    port = 8088
    try:
        server = http.server.HTTPServer(("127.0.0.1", port), AgentRequestHandler)
    except OSError:
        port = get_free_port()
        server = http.server.HTTPServer(("127.0.0.1", port), AgentRequestHandler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"

    # Wait for server readiness
    start = time.time()
    ready = False
    while time.time() - start < 3.0:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1.0) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.05)

    if not ready:
        server.shutdown()
        pytest.fail(f"Mock agent server failed to start on {base_url}")

    yield base_url

    server.shutdown()
    server.server_close()


@pytest.fixture
def set_agent_aligned(mock_agent_server: str):
    """Sets mock agent to aligned mode."""
    req = urllib.request.Request(f"{mock_agent_server}/mode/aligned", data=b"", method="POST")
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("mode") == "aligned"
    return mock_agent_server


@pytest.fixture
def set_agent_vulnerable(mock_agent_server: str):
    """Sets mock agent to vulnerable mode."""
    req = urllib.request.Request(f"{mock_agent_server}/mode/vulnerable", data=b"", method="POST")
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("mode") == "vulnerable"
    return mock_agent_server
