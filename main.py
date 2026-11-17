"""Forecast hour by hour how many people watch GTA VI on Twitch on release day.

Reads every case file in the input directory and writes one forecast per case.

The forecast is built from the case's own comparables: past big launches whose
hourly counts come with the case. For each comparable we take the release-day
shape as log ratios of its hourly count to its own first hour, and the "surge"
ratio of that first hour to the level of its quiet pre-release day. The
comparables whose surge ratio sits closest to this case's own share its position
in the launch, so their median log shape becomes the median forecast and their
disagreement its spread.

Only the standard library is used, and nothing is read from the clock, so two
runs on one case write the same bytes.
"""

import json
import math
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]
NEIGHBOURS = 6          # comparables kept: the closest surge ratios
SPREAD_SCALE = 0.7      # how much of the neighbours' spread to trust
SPREAD_FLOOR = 0.15     # never claim a band tighter than this, in log units
SPREAD_GROWTH = 0.02    # added per hour the neighbours cannot speak for
MAX_VIEWERS = 1_000_000_000.0


def count_of(row):
    """A row's viewer count, floored at 1: the log of 0 is no number."""
    value = row.get("viewers")
    if value is None:
        return None
    return max(1.0, float(value))


def stamp_of(row):
    return row.get("from") or row.get("at") or ""


def day_hours(obj):
    """{hour of the release day: viewers}, hour 1 being the row at day_start."""
    day = obj["day_start"][:10]
    rows = obj.get("hourly")
    if rows is None:
        rows = obj.get("history_hourly") or []
    out = {}
    for row in rows:
        at = stamp_of(row)
        if not at.startswith(day):
            continue
        count = count_of(row)
        if count is not None:
            out[int(at[11:13]) + 1] = count
    return out


def quiet_hours(obj):
    """Hourly counts from before the release day, oldest first.

    A comparable carries its whole series in `hourly`; a case carries whole-hour
    means in `history_hourly` (the final's own history is minute reads, so its
    hourly means are the level to compare a first hour against).
    """
    day = obj["day_start"][:10]
    rows = obj.get("hourly")
    if rows is None:
        rows = obj.get("history_hourly")
    if rows is None:
        buckets = {}
        for row in obj.get("history") or []:
            at = stamp_of(row)
            if at >= day:
                continue
            buckets.setdefault(at[:13], []).append(count_of(row))
        return {k: statistics.fmean([v for v in vs if v is not None])
                for k, vs in sorted(buckets.items()) if any(v is not None for v in vs)}
    out = {}
    for row in rows:
        at = stamp_of(row)
        if at < day:
            out[at[:13]] = count_of(row)
    return out


def launch_burst(obj, day1):
    """The first hour's count against the level of the quiet day before it."""
    if 1 not in day1:
        return None
    before = [v for _, v in sorted(quiet_hours(obj).items()) if v is not None]
    if len(before) < 6:
        return None
    return day1[1] / statistics.median(before[-12:])


def comparable_shape(comp):
    """(burst ratio, {hour: ratio to hour 1}) for one comparable, or None."""
    if not comp.get("day_start"):
        return None
    day1 = day_hours(comp)
    if 1 not in day1:
        return None
    shape = {h: day1[h] / day1[1] for h in range(2, 25) if h in day1}
    if len(shape) < 20:
        return None
    return launch_burst(comp, day1), shape


def neighbours(case, burst):
    """The comparables whose launch sits nearest this case's, nearest first."""
    picked = []
    for comp in case.get("comparables") or []:
        if str(comp.get("name", "")).startswith("Grand Theft Auto VI"):
            continue  # the case's own category has no release day to copy
        got = comparable_shape(comp)
        if not got:
            continue
        comp_burst, shape = got
        distance = 0.0
        if burst and comp_burst:
            distance = abs(math.log(comp_burst / burst))
        picked.append((distance, shape))
    picked.sort(key=lambda item: item[0])
    return [shape for _, shape in picked]


def hour_band(shapes, hour, carry):
    """Median log ratio of an hour and how far the neighbours disagree."""
    logs = [math.log(s[hour]) for s in shapes if hour in s]
    if not logs:
        return carry
    spread = statistics.pstdev(logs) if len(logs) > 1 else 0.3
    return statistics.median(logs), spread


def forecast_case(case):
    """The 23 rows of quantiles this case asks for."""
    levels = case.get("levels")
    if levels != LEVELS:
        raise ValueError(f"case asks for levels {levels}, not {LEVELS}")
    p1 = None
    for row in case.get("known") or []:
        if row.get("hour") == 1:
            p1 = count_of(row)
    if p1 is None:
        raise ValueError("case carries no hour-1 print")
    day1 = day_hours(case)
    burst = launch_burst(case, day1) if 1 in day1 else None
    shapes = neighbours(case, burst)[:NEIGHBOURS]
    carry = (0.0, 0.3)
    rows = []
    for row in case.get("forecast") or []:
        hour = row["hour"]
        median, spread = hour_band(shapes, hour, carry)
        spread = max(SPREAD_FLOOR, spread * SPREAD_SCALE)
        carry = (median, spread + SPREAD_GROWTH)
        band = [p1 * math.exp(median + z * spread) for z in Z]
        band = [min(MAX_VIEWERS, max(1.0, round(q, 2))) for q in band]
        for i in range(1, len(band)):
            band[i] = max(band[i], band[i - 1])
        rows.append({"hour": hour, "q": band})
    return {"hours": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        with path.open(encoding="utf-8") as handle:
            case = json.load(handle)
        forecast = forecast_case(case)
        text = json.dumps(forecast, separators=(",", ":"), allow_nan=False) + "\n"
        (OUTPUT_DIR / f"{path.stem}.out").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
