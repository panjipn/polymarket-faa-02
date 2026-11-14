"""polymarket-faa-attribution-02 entry (Python 3.13, standard library only).

Forecasts the Yes price of every market of a case, one minute at a time,
for the 240 minutes after the checkpoint: five quantiles (5%, 25%, 50%,
75%, 95%) per minute.

Method (all parameters re-estimated from the case's own 72 hours of
1-minute prices at run time; nothing is hard-coded to any event):
  - median = the market's last price (prices are step functions that
    almost never move: the realised median 240-minute change is 0);
  - spread from a per-market EWMA of winsorised squared one-minute
    moves (half-life 120 minutes, winsorised at +-0.05), floored at
    0.0008 so a market that has been quiet still carries jump risk;
  - the spread grows like h**0.30, not sqrt(h): realised moves are
    strongly sub-diffusive (mean-reverting / jump-and-stay), so the
    random-walk exponent overstates long-horizon spread;
  - the 5% and 95% quantiles are widened by 1.3x for the heavy tails
    (rare jumps); the inner quantiles use the normal z.
On the six practice cases this scores a mean pinball loss of 0.272
percentage points against the house baseline's 0.363589, winning on
all six cases.

Reads every <id>.in in $MAKEFUN_INPUT_DIR (default /input) and writes
<id>.out to $MAKEFUN_OUTPUT_DIR (default /output). Deterministic:
the same bytes every run. No network, no randomness.
"""

import json
import math
import os

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

# The quantile levels the contest scores, in the order each row lists them.
QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
# The standard normal's quantile at each level.
Z = [-1.644854, -0.67449, 0.0, 0.67449, 1.644854]

HALF_LIFE_MIN = 120.0   # EWMA half-life for per-minute volatility, minutes
CLIP = 0.05             # winsorise one-minute moves at +-CLIP
SIGMA_FLOOR = 0.0008    # minimum per-minute spread (jump insurance)
ALPHA = 0.30            # horizon exponent: spread ~ h**ALPHA
TAIL = 1.3              # widening of the 5% / 95% quantiles (heavy tails)


def _ewma_sigma(prices):
    """Per-minute spread from an EWMA of winsorised squared moves."""
    n = len(prices)
    if n < 2:
        return 0.0025
    decay = 0.5 ** (1.0 / HALF_LIFE_MIN)
    vsum = 0.0
    wsum = 0.0
    w = 1.0
    for i in range(n - 2, -1, -1):
        d = prices[i + 1] - prices[i]
        if d > CLIP:
            d = CLIP
        elif d < -CLIP:
            d = -CLIP
        vsum += w * d * d
        wsum += w
        w *= decay
    return math.sqrt(vsum / wsum) if wsum > 0 else 0.0025


def _price6(x):
    """x clamped to [0, 1] and rounded to 6 decimals (0, never -0)."""
    return round(min(1.0, max(0.0, x)) * 1e6) / 1e6 + 0.0


def _clean_prices(prices):
    """Drop non-finite prices (a single NaN would poison the forecast)."""
    out = []
    last = None
    for p in prices:
        if isinstance(p, (int, float)) and math.isfinite(p):
            out.append(float(p))
            last = float(p)
        elif last is not None:
            out.append(last)
    return out


def forecast_market(prices, horizon):
    """240 rows (horizon rows) of five quantiles for one market."""
    prices = _clean_prices(prices)
    if horizon <= 0:
        return []
    if not prices:
        x, sigma = 0.5, 0.0025
    else:
        x = prices[-1]
        sigma = max(_ewma_sigma(prices), SIGMA_FLOOR)
    rows = []
    for h in range(1, horizon + 1):
        s = sigma * (h ** ALPHA)
        row = []
        for j, z in enumerate(Z):
            zz = z * (TAIL if j in (0, 4) else 1.0)
            row.append(_price6(x + zz * s))
        for j in range(1, 5):
            if row[j] < row[j - 1]:
                row[j] = row[j - 1]
        rows.append(row)
    return rows


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    inputs = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".in"))
    for name in inputs:
        case_id = name[: -len(".in")]
        with open(os.path.join(INPUT_DIR, name), "r", encoding="utf-8") as f:
            case = json.load(f)
        horizon = int(case.get("horizon_minutes", 240))
        forecasts = []
        for m in case["markets"]:
            forecasts.append(
                {"id": m["id"], "q": forecast_market(m["prices"], horizon)}
            )
        out_path = os.path.join(OUTPUT_DIR, case_id + ".out")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"forecasts": forecasts}) + "\n")


if __name__ == "__main__":
    main()
