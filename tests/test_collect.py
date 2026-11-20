import pytest
from conftest import FakeClock, serve_repos

from census.collect import MANIFESTS, PATHS, StateLog, Stop, collect
from census.http import Fetcher

REPOS = ["fixture-org/alpha", "fixture-org/beta", "fixture-org/gamma"]


def fetcher(tmp_path, clock=None):
    clock = clock or FakeClock()
    return Fetcher(
        tmp_path / "cache",
        sleep=clock.sleep,
        clock=clock.time,
        today=lambda: "2026-11-20",
        max_retries=2,
        base_backoff=1,
    )


def test_collects_every_repo(server, tmp_path, fixture_repos):
    serve_repos(server, fixture_repos)
    counts = collect(fetcher(tmp_path), REPOS, tmp_path / "state.jsonl", raw=server.url)
    assert counts["done"] == 3
    # gamma has no instruction file, so its three manifests are never asked for
    assert len(server.hits) == 3 * len(PATHS) - len(MANIFESTS)


@pytest.mark.parametrize("stop_state", ["queued", "fetched", "cached", "done"])
def test_resume_after_stop_at_each_state(server, tmp_path, fixture_repos, stop_state):
    """Broken case: a collector that skips the stopped repo or refetches finished ones."""
    serve_repos(server, fixture_repos)
    state = tmp_path / "state.jsonl"

    def stop(repo, s):
        if repo == "fixture-org/beta" and s == stop_state:
            raise Stop

    with pytest.raises(Stop):
        collect(fetcher(tmp_path), REPOS, state, raw=server.url, stop_at=stop)
    assert StateLog(state).state["fixture-org/beta"] == stop_state
    first_hits = len(server.hits)
    counts = collect(fetcher(tmp_path), REPOS, state, raw=server.url)
    assert counts["done"] == 3
    resumed = server.hits[first_hits:]
    assert not any("/alpha/" in h for h in resumed)  # alpha was done, never refetched
    beta_refetched = any("/beta/" in h for h in resumed)
    # Before "cached" the answers are not on disk yet, so beta is fetched again.
    assert beta_refetched == (stop_state in ("queued", "fetched"))


def test_failed_repo_is_retried_on_resume(server, tmp_path, fixture_repos):
    serve_repos(server, fixture_repos)
    server.routes["/fixture-org/gamma/HEAD/AGENTS.md"] = [(500, {}, "boom"), (404, {}, "")]
    state = tmp_path / "state.jsonl"
    counts = collect(fetcher(tmp_path), REPOS, state, raw=server.url)
    assert counts["failed"] == 1
    counts = collect(fetcher(tmp_path), REPOS, state, raw=server.url)
    assert counts["done"] == 3


def test_403_and_429_back_off_then_resume(server, tmp_path, fixture_repos):
    """Broken case: rate limits lose the run. The collector must back off, stop
    cleanly when retries run out, and finish on the next run."""
    serve_repos(server, fixture_repos)
    path = "/fixture-org/beta/HEAD/AGENTS.md"
    server.routes[path] = [
        (429, {}, "slow"),
        (403, {"Retry-After": "5"}, "secondary rate limit"),
        (429, {}, "slow"),
        (404, {}, ""),
    ]
    state = tmp_path / "state.jsonl"
    clock = FakeClock()
    counts = collect(fetcher(tmp_path, clock), REPOS, state, raw=server.url)
    assert counts["done"] == 1 and counts["failed"] == 1  # stopped at beta
    assert 5.0 in clock.sleeps and 1 in clock.sleeps
    counts = collect(fetcher(tmp_path, clock), REPOS, state, raw=server.url)
    assert counts["done"] == 3
