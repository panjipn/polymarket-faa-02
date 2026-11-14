# Polymarket FAA outage attribution forecast

Entry for make.fun's "Forecast Polymarket's FAA outage attribution prices
minute by minute, 4 hours ahead" (polymarket-faa-attribution-02).

`main.py` (Python 3.13, standard library only) reads one case file
(`/input/<id>.in`: 72 hours of 1-minute Yes prices per market) and writes
`/output/<id>.out`: for each market and each of the 240 minutes after the
checkpoint, five quantiles (5%, 25%, 50%, 75%, 95%) of that minute's price.

Method: median = last price; spread from a per-market EWMA of winsorised
one-minute moves (half-life 120 min, floored at 0.0008); spread grows like
h**0.30; the 5%/95% quantiles are widened 1.3x for heavy tails. All
parameters are re-estimated from the case's own prices at run time.

Practice score (6 cases, local evaluator against Polymarket's realised
prices): mean pinball loss **0.272** percentage points, vs the house
baseline's 0.363589 — winning on all six practice cases. Median error
0.7675, 90% coverage 0.9464.

Run locally: `mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py`
