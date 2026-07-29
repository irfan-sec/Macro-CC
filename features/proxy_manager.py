"""
Proxy Manager — manage HTTP/SOCKS5 proxies and Tor routing.

Supports three connection modes:
  - direct:  No proxy, use real IP
  - proxy:   Route through a user-supplied proxy list
  - tor:     Route through the Tor network (socks5h://127.0.0.1:9050)

Rotation modes (proxy list only):
  - fixed:        rotate every N seconds
  - random:       pick a random working proxy each rotation
  - per_macro:    rotate before each macro replay
  - after_macro:  rotate when one full replay finishes (DEFAULT)
  - manual:       only rotate when user clicks the button
"""

import requests
import random
import threading
import time
import json
import os
from dataclasses import dataclass
from typing import Literal


@dataclass
class Proxy:
    host: str
    port: int
    protocol: Literal["http", "https", "socks4", "socks5"] = "socks5"
    username: str = ""
    password: str = ""
    last_tested: float = 0.0
    is_working: bool = False
    response_time: float = 0.0
    country: str = ""       # detected from IP lookup
    anonymity: str = ""     # "transparent", "anonymous", "elite"

    def to_url(self) -> str:
        """Build proxy URL for requests library."""
        auth = f"{self.username}:{self.password}@" if self.username else ""
        # Use socks5h for DNS-through-proxy (more anonymous)
        proto = "socks5h" if self.protocol == "socks5" else self.protocol
        return f"{proto}://{auth}{self.host}:{self.port}"

    def to_requests_dict(self) -> dict:
        url = self.to_url()
        return {"http": url, "https": url}

    def display_str(self) -> str:
        auth = " \U0001f511" if self.username else ""
        return f"{self.protocol.upper():7} {self.host}:{self.port}{auth}"

    def to_dict(self) -> dict:
        return {
            "host": self.host, "port": self.port,
            "protocol": self.protocol,
            "username": self.username, "password": self.password,
            "country": self.country, "anonymity": self.anonymity,
        }


class ProxyManager:
    def __init__(self, config_path: str = "storage/proxies.json"):
        self.config_path = config_path
        self.proxies: list[Proxy] = []
        self.current_proxy: Proxy | None = None
        self.mode: Literal["direct", "proxy", "tor"] = "direct"
        self.rotation_mode: Literal["fixed", "random", "per_macro", "after_macro", "manual"] = "after_macro"
        self.rotation_interval: int = 300  # seconds
        self._rotation_thread = None
        self._stop_flag = threading.Event()
        self.load()

    def add_proxy(self, host: str, port: int, protocol="socks5",
                  username="", password=""):
        p = Proxy(host, port, protocol, username, password)
        self.proxies.append(p)
        self.save()
        return p

    def remove_proxy(self, index: int):
        if 0 <= index < len(self.proxies):
            self.proxies.pop(index)
            self.save()

    # ── Smart proxy parser ───────────────────────────────────

    def parse_and_add(self, proxy_string: str) -> Proxy | None:
        """
        Parse any proxy format and add to list.

        Handles all these formats:
          185.220.101.45:1080
          185.220.101.45:1080:user:pass
          socks5://185.220.101.45:1080
          socks5://user:pass@185.220.101.45:1080
          http://185.220.101.45:8080
          185.220.101.45:8080:http  (protocol as 3rd field)
        """
        s = proxy_string.strip()
        if not s or s.startswith('#'):
            return None

        protocol = "socks5"  # default
        username = ""
        password = ""

        # Handle URL format: protocol://[user:pass@]host:port
        if "://" in s:
            from urllib.parse import urlparse
            parsed = urlparse(s)
            proto_raw = parsed.scheme.rstrip('h')  # strip 'h' from socks5h
            if proto_raw in ("http", "https", "socks4", "socks5"):
                protocol = proto_raw
            host = parsed.hostname or ""
            port = parsed.port or self._default_port(protocol)
            username = parsed.username or ""
            password = parsed.password or ""
        else:
            # Handle plain formats: ip:port or ip:port:user:pass
            parts = s.split(":")
            if len(parts) < 2:
                return None
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                return None

            if len(parts) == 3:
                # Could be ip:port:protocol OR ip:port:username
                if parts[2].lower() in ("http", "https", "socks4", "socks5"):
                    protocol = parts[2].lower()
                else:
                    username = parts[2]
            elif len(parts) >= 4:
                username = parts[2]
                password = parts[3]

            # Auto-detect protocol from port when no auth given
            if not username:
                protocol = self._detect_protocol_from_port(port)

        proxy = Proxy(
            host=host, port=port, protocol=protocol,
            username=username, password=password
        )
        self.proxies.append(proxy)
        return proxy

    def _default_port(self, protocol: str) -> int:
        return {"http": 8080, "https": 8443,
                "socks4": 1080, "socks5": 1080}.get(protocol, 1080)

    def _detect_protocol_from_port(self, port: int) -> str:
        """Guess protocol from port number."""
        port_map = {
            80: "http", 8080: "http", 3128: "http", 8888: "http",
            443: "https", 8443: "https",
            1080: "socks5", 9050: "socks5", 9150: "socks5",
            1085: "socks5", 4145: "socks4",
        }
        return port_map.get(port, "socks5")  # default to socks5

    def import_from_text(self, text: str) -> tuple[int, int]:
        """
        Import multiple proxies from multiline text.
        Returns (added_count, failed_count)
        """
        added = 0
        failed = 0
        for line in text.strip().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            result = self.parse_and_add(line)
            if result:
                added += 1
            else:
                failed += 1
        self.save()
        return added, failed

    def import_from_file(self, filepath: str) -> tuple[int, int]:
        """Import proxies from a .txt file."""
        try:
            with open(filepath, 'r') as f:
                return self.import_from_text(f.read())
        except Exception as e:
            print(f"[ProxyManager] Import failed: {e}")
            return 0, 0

    def get_current(self) -> dict | None:
        if self.mode == "direct":
            return None
        if self.mode == "tor":
            return {
                "http":  "socks5h://127.0.0.1:9050",
                "https": "socks5h://127.0.0.1:9050"
            }
        if self.current_proxy:
            return self.current_proxy.to_requests_dict()
        return None

    def rotate(self) -> Proxy | None:
        working = [p for p in self.proxies if p.is_working]
        if not working:
            working = self.proxies
        if not working:
            return None
        if self.rotation_mode == "random":
            self.current_proxy = random.choice(working)
        else:
            current_index = 0
            if self.current_proxy in working:
                current_index = (working.index(self.current_proxy) + 1) % len(working)
            self.current_proxy = working[current_index]
        print(f"[ProxyManager] Rotated to: {self.current_proxy.host}:{self.current_proxy.port}")
        return self.current_proxy

    def test_proxy(self, proxy: Proxy, timeout: int = 10) -> bool:
        try:
            start = time.time()
            r = requests.get(
                "https://httpbin.org/ip",
                proxies=proxy.to_requests_dict(),
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            proxy.response_time = round(time.time() - start, 2)
            proxy.is_working = r.status_code == 200

            if proxy.is_working:
                proxy.last_tested = time.time()
                # Try to get country info
                try:
                    geo = requests.get(
                        f"http://ip-api.com/json/{proxy.host}?fields=country,countryCode",
                        timeout=5,
                    ).json()
                    proxy.country = geo.get("countryCode", "??")
                except Exception:
                    proxy.country = "??"

            print(f"[ProxyManager] {proxy.display_str()} → "
                  f"{'✅' if proxy.is_working else '❌'} "
                  f"{proxy.response_time}s {proxy.country}")
            return proxy.is_working

        except Exception as e:
            proxy.is_working = False
            proxy.last_tested = time.time()
            print(f"[ProxyManager] {proxy.display_str()} → ❌ {type(e).__name__}")
            return False

    def test_all(self, on_progress=None):
        def worker():
            for i, proxy in enumerate(self.proxies):
                self.test_proxy(proxy)
                if on_progress:
                    on_progress(i + 1, len(self.proxies))
            self.save()
        threading.Thread(target=worker, daemon=True).start()

    def test_tor(self) -> bool:
        try:
            r = requests.get(
                "http://httpbin.org/ip",
                proxies={"http": "socks5h://127.0.0.1:9050",
                         "https": "socks5h://127.0.0.1:9050"},
                timeout=15
            )
            print(f"[ProxyManager] Tor OK — IP: {r.json().get('origin')}")
            return True
        except Exception as e:
            print(f"[ProxyManager] Tor FAIL — Is Tor Browser or tor service running? {e}")
            return False

    def get_current_ip(self) -> str:
        try:
            proxies = self.get_current()
            r = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=10)
            if r.status_code == 200:
                try:
                    return r.json().get("origin", "Unknown")
                except ValueError:
                    return "Unknown (Invalid JSON)"
            return f"Unknown (HTTP {r.status_code})"
        except Exception as e:
            # Silently fail so we don't spam the terminal with background network errors
            return "Could not detect"

    def start_auto_rotation(self):
        self._stop_flag.clear()
        def worker():
            while not self._stop_flag.is_set():
                self._stop_flag.wait(timeout=self.rotation_interval)
                if not self._stop_flag.is_set():
                    self.rotate()
        self._rotation_thread = threading.Thread(target=worker, daemon=True)
        self._rotation_thread.start()
        print(f"[ProxyManager] Auto-rotation started every {self.rotation_interval}s")

    def stop_auto_rotation(self):
        self._stop_flag.set()

    def save(self):
        os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
        data = {
            "mode": self.mode,
            "rotation_mode": self.rotation_mode,
            "rotation_interval": self.rotation_interval,
            "proxies": [p.to_dict() for p in self.proxies]
        }
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path) as f:
                data = json.load(f)
            self.mode = data.get("mode", "direct")
            self.rotation_mode = data.get("rotation_mode", "after_macro")
            self.rotation_interval = data.get("rotation_interval", 300)
            self.proxies = [Proxy(**p) for p in data.get("proxies", [])]
        except Exception as e:
            print(f"[ProxyManager] Config load failed: {e}")
