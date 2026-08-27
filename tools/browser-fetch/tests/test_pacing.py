"""Deterministic tests for pacing.py's pure decision functions — every
function takes a seeded random.Random, so no real sleeping happens here."""
import random

from browser_fetch import pacing


def test_plan_scroll_burst_forward_ticks_deltas_gaps_in_range():
    rng = random.Random(1)
    burst = pacing.plan_scroll_burst(rng)
    assert pacing.WHEEL_TICKS_RANGE[0] <= len(burst) <= pacing.WHEEL_TICKS_RANGE[1]
    for delta, gap in burst:
        assert pacing.WHEEL_DELTA_RANGE[0] <= delta <= pacing.WHEEL_DELTA_RANGE[1]
        assert pacing.WHEEL_TICK_GAP_RANGE[0] <= gap <= pacing.WHEEL_TICK_GAP_RANGE[1]


def test_plan_scroll_burst_backward_deltas_negative_and_shorter():
    rng = random.Random(2)
    burst = pacing.plan_scroll_burst(rng, backward=True)
    assert pacing.BACKSCROLL_TICKS_RANGE[0] <= len(burst) <= pacing.BACKSCROLL_TICKS_RANGE[1]
    for delta, gap in burst:
        assert -pacing.WHEEL_DELTA_RANGE[1] <= delta <= -pacing.WHEEL_DELTA_RANGE[0]
        assert pacing.WHEEL_TICK_GAP_RANGE[0] <= gap <= pacing.WHEEL_TICK_GAP_RANGE[1]


def test_pick_read_pause_distribution_hits_both_ranges_near_probability():
    rng = random.Random(3)
    samples = [pacing.pick_read_pause(rng) for _ in range(4000)]
    long_count = sum(1 for s in samples if s >= pacing.LONG_PAUSE_RANGE[0])
    short_count = len(samples) - long_count
    assert short_count > 0
    assert long_count > 0
    ratio = long_count / len(samples)
    assert abs(ratio - pacing.LONG_PAUSE_PROBABILITY) < 0.03
    for s in samples:
        in_short = pacing.READ_PAUSE_RANGE[0] <= s <= pacing.READ_PAUSE_RANGE[1]
        in_long = pacing.LONG_PAUSE_RANGE[0] <= s <= pacing.LONG_PAUSE_RANGE[1]
        assert in_short or in_long


def test_should_backscroll_distribution_near_probability():
    rng = random.Random(4)
    samples = [pacing.should_backscroll(rng) for _ in range(4000)]
    ratio = sum(samples) / len(samples)
    assert abs(ratio - pacing.BACKSCROLL_PROBABILITY) < 0.03


def test_pick_viewport_in_range():
    rng = random.Random(5)
    viewport = pacing.pick_viewport(rng)
    assert pacing.VIEWPORT_WIDTH_RANGE[0] <= viewport["width"] <= pacing.VIEWPORT_WIDTH_RANGE[1]
    assert pacing.VIEWPORT_HEIGHT_RANGE[0] <= viewport["height"] <= pacing.VIEWPORT_HEIGHT_RANGE[1]


def test_pick_initial_dwell_in_range():
    rng = random.Random(6)
    dwell = pacing.pick_initial_dwell(rng)
    assert pacing.INITIAL_DWELL_RANGE[0] <= dwell <= pacing.INITIAL_DWELL_RANGE[1]


def test_pick_cooldown_in_range():
    rng = random.Random(7)
    cooldown = pacing.pick_cooldown(rng)
    assert pacing.COOLDOWN_RANGE[0] <= cooldown <= pacing.COOLDOWN_RANGE[1]


def test_plan_mouse_move_coordinates_within_viewport():
    rng = random.Random(8)
    viewport = {"width": 1400, "height": 900}
    x, y, steps = pacing.plan_mouse_move(rng, viewport)
    assert 0 <= x <= viewport["width"]
    assert 0 <= y <= viewport["height"]
    assert steps > 0


def test_same_seed_produces_same_results_for_every_function():
    for fn, args, kwargs in [
        (pacing.pick_initial_dwell, (), {}),
        (pacing.plan_scroll_burst, (), {}),
        (pacing.plan_scroll_burst, (), {"backward": True}),
        (pacing.pick_read_pause, (), {}),
        (pacing.should_backscroll, (), {}),
        (pacing.pick_viewport, (), {}),
        (pacing.pick_cooldown, (), {}),
    ]:
        r1 = fn(random.Random(42), *args, **kwargs)
        r2 = fn(random.Random(42), *args, **kwargs)
        assert r1 == r2

    viewport = {"width": 1400, "height": 900}
    r1 = pacing.plan_mouse_move(random.Random(42), viewport)
    r2 = pacing.plan_mouse_move(random.Random(42), viewport)
    assert r1 == r2
