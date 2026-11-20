import socket
import urllib.error
import urllib.request

import pytest
from conftest import FakeClock, NetworkBlocked

from census.http import Fetcher, RateLimited, real_token


def make(tmp_path, clock=None, **kw):
    clock = clock or FakeClock()
    return Fetcher(
        tmp_path / "cache", sleep=clock.sleep, clock=clock.time, today=lambda: "2026-11-20", **kw
    ), clock


def test_guard_blocks_non_local_hosts():
    """Broken case: a test that reaches the real internet. The guard must stop it."""
    with pytest.raises(NetworkBlocked):
        socket.create_connection(("93.184.216.34", 80), timeout=1)
    with pytest.raises((NetworkBlocked, urllib.error.URLError)) as info:
        urllib.request.urlopen("http://example.org/", timeout=1)
    assert "test tried to" in str(info.value)


def test_cache_hit_skips_network(server, tmp_path):
    server.routes["/a"] = [(200, {}, "hello")]
    f, _ = make(tmp_path)
    assert f.get(server.url + "/a").body == "hello"
    assert f.get(server.url + "/a").from_cache
    assert server.hits == ["/a"]


def test_404_is_cached_and_500_is_not(server, tmp_path):
    server.routes["/gone"] = [(404, {}, "nope")]
    server.routes["/err"] = [(500, {}, "boom")]
    f, _ = make(tmp_path)
    f.get(server.url + "/gone")
    f.get(server.url + "/gone")
    f.get(server.url + "/err")
    f.get(server.url + "/err")
    assert server.hits.count("/gone") == 1
    assert server.hits.count("/err") == 2


def test_403_secondary_limit_backs_off_then_succeeds(server, tmp_path):
    """Broken case: a fetcher that returns the 403 instead of waiting and retrying."""
    server.routes["/s"] = [
        (403, {"Retry-After": "30"}, "You have exceeded a secondary rate limit"),
        (200, {}, "ok"),
    ]
    f, clock = make(tmp_path)
    r = f.get(server.url + "/s")
    assert r.status == 200 and r.body == "ok"
    assert 30.0 in clock.sleeps
    assert f.min_interval == 1.0  # slowed to one request a second


def test_429_uses_exponential_backoff(server, tmp_path):
    server.routes["/t"] = [(429, {}, "slow down"), (429, {}, "slow down"), (200, {}, "ok")]
    f, clock = make(tmp_path, base_backoff=10)
    assert f.get(server.url + "/t").body == "ok"
    assert clock.sleeps[:2] == [10, 20]


def test_retries_run_out(server, tmp_path):
    server.routes["/x"] = [(429, {}, "slow down")]
    f, _ = make(tmp_path, max_retries=2, base_backoff=1)
    with pytest.raises(RateLimited):
        f.get(server.url + "/x")


def test_primary_limit_waits_until_reset(server, tmp_path):
    clock = FakeClock(start=1000.0)
    server.routes["/p"] = [(200, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1100"}, "a")]
    server.routes["/q"] = [(200, {}, "b")]
    f, _ = make(tmp_path, clock=clock)
    f.get(server.url + "/p")
    f.get(server.url + "/q")
    assert clock.now >= 1101


def test_used_against_limit_counts_as_exhausted(server, tmp_path):
    """Broken case: a proxy keeps "remaining" fixed, so only "used" shows the budget is spent."""
    clock = FakeClock(start=1000.0)
    hdrs = {
        "X-RateLimit-Limit": "30",
        "X-RateLimit-Remaining": "30",
        "X-RateLimit-Used": "30",
        "X-RateLimit-Reset": "1060",
    }
    server.routes["/u"] = [(403, hdrs, "API rate limit exceeded"), (200, {}, "ok")]
    f, _ = make(tmp_path, clock=clock)
    assert f.get(server.url + "/u").body == "ok"
    assert clock.now >= 1061


def test_plain_403_is_not_retried(server, tmp_path):
    server.routes["/f"] = [(403, {}, "is not enabled for this session")]
    f, _ = make(tmp_path)
    assert f.get(server.url + "/f").status == 403
    assert server.hits == ["/f"]


def test_cache_file_names_are_hashes(server, tmp_path):
    server.routes["/owner/repo/HEAD/AGENTS.md"] = [(200, {}, "x")]
    f, _ = make(tmp_path)
    f.get(server.url + "/owner/repo/HEAD/AGENTS.md")
    names = [p.name for p in (tmp_path / "cache").rglob("*") if p.is_file()]
    assert names and all("repo" not in n and "AGENTS" not in n for n in names)


def test_placeholder_token_is_ignored(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "proxy-injected")
    monkeypatch.setenv("GITHUB_TOKEN", "proxy-injected")
    assert real_token() is None
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake_for_test")
    assert real_token() == "ghp_fake_for_test"
