"""Pure decision functions for human-like scroll pacing on x.com timeline
scraping. No I/O, no sleeping — callers (server.py) translate the returned
plans into Playwright calls and page.wait_for_timeout()/asyncio.sleep().
Every function takes a caller-owned random.Random so tests can seed for
determinism; production passes an unseeded module-level instance that
self-seeds from OS entropy at process start."""
import random

INITIAL_DWELL_RANGE = (2.0, 5.0)
WHEEL_TICKS_RANGE = (8, 15)
WHEEL_DELTA_RANGE = (100, 200)
WHEEL_TICK_GAP_RANGE = (0.03, 0.08)
READ_PAUSE_RANGE = (1.5, 4.0)
LONG_PAUSE_RANGE = (8.0, 15.0)
LONG_PAUSE_PROBABILITY = 1 / 6
BACKSCROLL_PROBABILITY = 0.2
BACKSCROLL_TICKS_RANGE = (2, 4)
VIEWPORT_WIDTH_RANGE = (1280, 1600)
VIEWPORT_HEIGHT_RANGE = (800, 1000)
COOLDOWN_RANGE = (20.0, 90.0)
MOUSE_MOVE_STEPS_RANGE = (5, 15)


def pick_initial_dwell(rng: random.Random) -> float:
    return rng.uniform(*INITIAL_DWELL_RANGE)


def plan_scroll_burst(rng: random.Random, *, backward: bool = False) -> list[tuple[int, float]]:
    tick_range = BACKSCROLL_TICKS_RANGE if backward else WHEEL_TICKS_RANGE
    ticks = rng.randint(*tick_range)
    burst = []
    for _ in range(ticks):
        delta = rng.randint(*WHEEL_DELTA_RANGE)
        if backward:
            delta = -delta
        gap = rng.uniform(*WHEEL_TICK_GAP_RANGE)
        burst.append((delta, gap))
    return burst


def pick_read_pause(rng: random.Random) -> float:
    if rng.random() < LONG_PAUSE_PROBABILITY:
        return rng.uniform(*LONG_PAUSE_RANGE)
    return rng.uniform(*READ_PAUSE_RANGE)


def should_backscroll(rng: random.Random) -> bool:
    return rng.random() < BACKSCROLL_PROBABILITY


def plan_mouse_move(rng: random.Random, viewport: dict) -> tuple[int, int, int]:
    x = rng.randint(0, viewport["width"])
    y = rng.randint(0, viewport["height"])
    steps = rng.randint(*MOUSE_MOVE_STEPS_RANGE)
    return (x, y, steps)


def pick_viewport(rng: random.Random) -> dict:
    return {
        "width": rng.randint(*VIEWPORT_WIDTH_RANGE),
        "height": rng.randint(*VIEWPORT_HEIGHT_RANGE),
    }


def pick_cooldown(rng: random.Random) -> float:
    return rng.uniform(*COOLDOWN_RANGE)
