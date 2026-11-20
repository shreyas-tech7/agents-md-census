"""HTTP fetcher with a disk cache, header-based pacing and backoff.

The cache stores one JSON file per URL. The file name is the SHA-256 of the
URL, so no repo path ever appears in a file name.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from census import USER_AGENT

CACHEABLE = {200, 404}
KEEP_HEADERS = (
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "x-ratelimit-reset",
    "x-ratelimit-used",
    "retry-after",
    "content-type",
)
PLACEHOLDER_TOKENS = {"", "proxy-injected"}


def real_token() -> str | None:
    """Return a usable token from GH_TOKEN or GITHUB_TOKEN, or None.

    The placeholder text "proxy-injected" does not count as a token.
    """
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value not in PLACEHOLDER_TOKENS:
            return value
    return None


@dataclass
class Response:
    url: str
    status: int
    body: str
    headers: dict = field(default_factory=dict)
    fetched_on: str = ""
    from_cache: bool = False

    def json(self):
        return json.loads(self.body)


class RateLimited(Exception):
    """Raised when the retries run out on 403 or 429 answers."""


class Fetcher:
    def __init__(
        self,
        cache_dir: str | Path,
        *,
        min_interval: float = 0.0,
        max_retries: int = 5,
        base_backoff: float = 60.0,
        timeout: float = 30.0,
        token: str | None = None,
        sleep=time.sleep,
        clock=time.time,
        today=None,
    ):
        self.cache_dir = Path(cache_dir)
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.timeout = timeout
        self.token = token
        self.sleep = sleep
        self.clock = clock
        self.today = today or (lambda: time.strftime("%Y-%m-%d", time.gmtime(self.clock())))
        self._last = 0.0
        self._wait_until = 0.0
        self.live_requests = 0

    # cache -----------------------------------------------------------------
    def cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode()).hexdigest()
        return self.cache_dir / digest[:2] / f"{digest}.json"

    def cached(self, url: str) -> Response | None:
        path = self.cache_path(url)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Response(
            url, data["status"], data["body"], data["headers"], data["fetched_on"], True
        )

    def store(self, resp: Response) -> None:
        if resp.status not in CACHEABLE:
            return
        path = self.cache_path(resp.url)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "url": resp.url,
            "status": resp.status,
            "headers": resp.headers,
            "fetched_on": resp.fetched_on,
            "body": resp.body,
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
        tmp.replace(path)

    def get(self, url: str) -> Response:
        hit = self.cached(url)
        if hit is not None:
            return hit
        resp = self.fetch(url)
        self.store(resp)
        return resp

    # network ---------------------------------------------------------------
    def _pace(self) -> None:
        now = self.clock()
        wait = max(self._wait_until - now, self._last + self.min_interval - now)
        if wait > 0:
            self.sleep(wait)
        self._last = self.clock()

    def _open(self, url: str) -> tuple[int, str, dict]:
        if not url.startswith(("https://", "http://")):
            raise ValueError(f"only http and https URLs are fetched: {url}")
        headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, headers=headers)  # noqa: S310 (scheme checked above)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310
                return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace") if e.fp else ""
            return e.code, body, dict(e.headers or {})

    def fetch(self, url: str) -> Response:
        """Fetch from the network, obeying rate-limit headers and backing off."""
        attempt = 0
        while True:
            self._pace()
            try:
                status, body, raw_headers = self._open(url)
            except (OSError, http.client.HTTPException) as e:  # URLError is an OSError
                attempt += 1
                if attempt > self.max_retries:
                    return Response(url, 0, f"network error: {e}", {}, self.today())
                self.sleep(min(self.base_backoff * 2 ** (attempt - 1), 900))
                continue
            self.live_requests += 1
            headers = {k.lower(): v for k, v in raw_headers.items()}
            kept = {k: headers[k] for k in KEEP_HEADERS if k in headers}
            self._note_primary_limit(headers)
            if self._is_rate_limited(status, headers, body):
                attempt += 1
                if attempt > self.max_retries:
                    raise RateLimited(f"{status} after {self.max_retries} retries: {url}")
                self.sleep(self._backoff(attempt, headers))
                # A secondary limit means we were too fast: slow to 1 request a second.
                self.min_interval = max(self.min_interval, 1.0)
                continue
            return Response(url, status, body, kept, self.today())

    @staticmethod
    def _exhausted(headers: dict) -> bool:
        """True when the primary budget is spent. Some proxies keep "remaining"
        fixed, so "used" against "limit" counts too."""
        if headers.get("x-ratelimit-remaining") == "0":
            return True
        used, limit = headers.get("x-ratelimit-used"), headers.get("x-ratelimit-limit")
        return used is not None and limit is not None and int(used) >= int(limit)

    def _note_primary_limit(self, headers: dict) -> None:
        reset = headers.get("x-ratelimit-reset")
        if reset is not None and self._exhausted(headers):
            self._wait_until = max(self._wait_until, float(reset) + 1)

    @staticmethod
    def _is_rate_limited(status: int, headers: dict, body: str) -> bool:
        if status == 429:
            return True
        if status != 403:
            return False
        if "retry-after" in headers or Fetcher._exhausted(headers):
            return True
        return "rate limit" in body.lower()

    def _backoff(self, attempt: int, headers: dict) -> float:
        try:
            return float(headers["retry-after"])
        except (KeyError, ValueError):  # missing, or an HTTP date instead of seconds
            pass
        reset = headers.get("x-ratelimit-reset")
        if reset is not None and self._exhausted(headers):
            return max(float(reset) - self.clock(), 0) + 1
        return min(self.base_backoff * 2 ** (attempt - 1), 900)
