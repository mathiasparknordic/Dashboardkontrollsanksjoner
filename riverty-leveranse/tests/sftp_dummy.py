"""
Kastbar in-process SFTP-server for testing (loopback, 127.0.0.1).

Serverer ekte SFTP mot en midlertidig mappe slik at vi kan verifisere HELE
leveranseflyten (connect -> mkdir -> put -> stat) uten å røre Riverty sin server.
Basert på paramiko sitt StubSFTPServer-eksempel, rotfestet til en temp-mappe.
"""
from __future__ import annotations

import os
import socket
import threading
from contextlib import contextmanager

import paramiko

USER = "pn"
PASS = "pn-test"


class _StubServer(paramiko.ServerInterface):
    def check_auth_password(self, username, password):
        if username == USER and password == PASS:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED

    def get_allowed_auths(self, username):
        return "password"


class _StubSFTP(paramiko.SFTPServerInterface):
    ROOT = "/"

    def _real(self, path):
        return os.path.join(self.ROOT, path.lstrip("/"))

    def list_folder(self, path):
        rp = self._real(path)
        out = []
        for fname in os.listdir(rp):
            attr = paramiko.SFTPAttributes.from_stat(os.stat(os.path.join(rp, fname)))
            attr.filename = fname
            out.append(attr)
        return out

    def stat(self, path):
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(self._real(path)))
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    lstat = stat

    def open(self, path, flags, attr):
        rp = self._real(path)
        try:
            fd = os.open(rp, flags, 0o644)
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)
        mode = "wb" if (flags & os.O_WRONLY or flags & os.O_RDWR) else "rb"
        if flags & os.O_APPEND:
            mode = "ab"
        fobj = os.fdopen(fd, mode)
        h = paramiko.SFTPHandle(flags)
        h.filename = rp
        h.readfile = fobj
        h.writefile = fobj
        return h

    def mkdir(self, path, attr):
        try:
            os.mkdir(self._real(path))
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)
        return paramiko.SFTP_OK

    def remove(self, path):
        try:
            os.remove(self._real(path))
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)
        return paramiko.SFTP_OK


@contextmanager
def dummy_sftp(root_dir: str):
    """Start en loopback SFTP-server rotfestet i root_dir. Gir (host, port, user, pass)."""
    _StubSFTP.ROOT = root_dir
    host_key = paramiko.RSAKey.generate(2048)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    transports: list[paramiko.Transport] = []
    stop = threading.Event()

    def serve():
        sock.settimeout(1.0)
        while not stop.is_set():
            try:
                client, _ = sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            t = paramiko.Transport(client)
            transports.append(t)
            t.add_server_key(host_key)
            t.set_subsystem_handler("sftp", paramiko.SFTPServer, _StubSFTP)
            t.start_server(server=_StubServer())

    th = threading.Thread(target=serve, daemon=True)
    th.start()
    try:
        yield "127.0.0.1", port, USER, PASS
    finally:
        stop.set()
        for t in transports:
            try:
                t.close()
            except Exception:
                pass
        sock.close()
        th.join(timeout=3)
