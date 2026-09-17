from app.core.rate_limiter import RateLimiter


def make_clock(start: float = 0.0):
    state = {"now": start}

    def clock() -> float:
        return state["now"]

    def advance(seconds: float) -> None:
        state["now"] += seconds

    return clock, advance


def test_allows_requests_under_the_limit():
    clock, _ = make_clock()
    limiter = RateLimiter(max_requests=3, window_seconds=60, clock=clock)

    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True


def test_blocks_requests_over_the_limit_within_the_window():
    clock, _ = make_clock()
    limiter = RateLimiter(max_requests=2, window_seconds=60, clock=clock)

    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False


def test_window_resets_after_it_elapses():
    clock, advance = make_clock()
    limiter = RateLimiter(max_requests=1, window_seconds=60, clock=clock)

    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False

    advance(61)
    assert limiter.allow("client-a") is True


def test_limits_are_independent_per_client_key():
    clock, _ = make_clock()
    limiter = RateLimiter(max_requests=1, window_seconds=60, clock=clock)

    assert limiter.allow("client-a") is True
    assert limiter.allow("client-b") is True
    assert limiter.allow("client-a") is False
    assert limiter.allow("client-b") is False
