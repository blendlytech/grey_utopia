"""desktop.py -- Offline desktop shell for GREY UTOPIA.

Runs the existing server.py REST API + static host on a background thread
bound to a free localhost port, then opens it in a native pywebview window.
No browser, no console, no network dependency beyond localhost.
"""
from __future__ import annotations
import socket
import threading

import webview

import server


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    port = _free_port()
    httpd = server.ThreadingHTTPServer(("127.0.0.1", port), server.GreyUtopiaRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    window = webview.create_window(
        "GREY UTOPIA",
        f"http://127.0.0.1:{port}/",
        width=1440,
        height=900,
        min_size=(1100, 700),
        background_color="#06080d",
    )
    webview.start()

    httpd.shutdown()
    httpd.server_close()


if __name__ == "__main__":
    main()
