"""Quick test of the proxy parser."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from features.proxy_manager import ProxyManager, Proxy

pm = ProxyManager()
pm.proxies.clear()

tests = [
    "185.220.101.45:1080",
    "185.220.101.45:1080:myuser:mypass",
    "socks5://185.220.101.45:1080",
    "socks5://user:pass@185.220.101.45:1080",
    "http://185.220.101.45:8080",
    "socks5h://185.220.101.45:9050",
    "10.0.0.1:8080:http",
    "10.0.0.1:4145",
]

print("=== Parse Tests ===")
for t in tests:
    p = pm.parse_and_add(t)
    if p:
        print(f"  {t:45} -> {p.display_str():28} URL={p.to_url()}")
    else:
        print(f"  {t:45} -> FAILED")

print(f"\nTotal parsed: {len(pm.proxies)}")
assert len(pm.proxies) == 8, f"Expected 8, got {len(pm.proxies)}"

# Check specific parses
p0 = pm.proxies[0]
assert p0.protocol == "socks5" and p0.port == 1080, f"Format 1 wrong: {p0}"
p1 = pm.proxies[1]
assert p1.username == "myuser" and p1.password == "mypass", f"Format 2 auth wrong: {p1}"
p3 = pm.proxies[3]
assert p3.username == "user" and p3.password == "pass", f"URL auth wrong: {p3}"
p4 = pm.proxies[4]
assert p4.protocol == "http" and p4.port == 8080, f"HTTP parse wrong: {p4}"
p6 = pm.proxies[6]
assert p6.protocol == "http", f"Protocol-as-3rd-field wrong: {p6.protocol}"
p7 = pm.proxies[7]
assert p7.protocol == "socks4", f"Port 4145 auto-detect wrong: {p7.protocol}"

# Test to_requests_dict
d = p0.to_requests_dict()
assert "socks5h://" in d["http"], f"to_requests_dict http wrong: {d}"

# Test import_from_text
pm.proxies.clear()
text = "# comment\n1.1.1.1:1080\n2.2.2.2:8080:user:pass\nsocks5://3.3.3.3:1080\ninvalid\n"
added, failed = pm.import_from_text(text)
print(f"\nBulk import: added={added} failed={failed}")
assert added == 3 and failed == 1, f"Bulk import wrong: {added},{failed}"

# Test display_str
px = Proxy("1.2.3.4", 1080, "socks5", "u", "p")
assert "\U0001f511" in px.display_str(), f"display_str missing key: {px.display_str()}"

# Clean up
pm.proxies.clear()
pm.save()

print("\n=== ALL PROXY PARSER TESTS PASSED ===")
