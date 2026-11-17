# Hour-by-hour forecast of GTA VI's release-day Twitch audience

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/zeroknowledge0x/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/zeroknowledge0x/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

An entry for make.fun's **gta6-twitch-ccu-forecast-01** bounty: forecast the concurrent live
viewers of the Grand Theft Auto VI Twitch category in each hour of its release day, 2026-11-19
(UTC), as five quantiles per hour. The bounty page is
<https://make.fun/bounty/gta6-twitch-ccu-forecast-01>.

## The program

`main.py` (Python 3.13, standard library only) is run once per case with that case's file in the
input directory. It writes one file per case: 23 rows, hours 2 to 24, `{"hour": h, "q": [q05, q25,
q50, q75, q95]}`.

```
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Nothing is read from the clock and no randomness is used, so both of a case's two runs write the
same bytes.

## The forecast

A launch day is a shape, not a level: hour 1 of the UTC release day is whatever the rolling
midnight unlock has already done in New Zealand, Europe and the UK, and the hours after it carry
the United States unlocking at 05:00Z and 08:00Z and the evening viewing peak. So the stay-at-hour-1
baseline the house ships is only a level, and the work is to borrow the shape.

Each case file carries around 38 comparables: past big console launches, with their hourly Twitch
counts from 14 days before their own release to 3 days after. For every comparable the program

- takes its release-day shape as log ratios `ln(count(h) / count(1))`, so every launch is compared
  to itself and scale disappears, and
- measures how far into its launch its first hour already was, as the burst ratio
  `count(1) / median(quiet hours of the day before)`.

The case's own burst ratio is computed the same way from its own history, and the six comparables
whose burst ratio sits closest to it are the ones that share its position in the launch. A comparable
whose own release day peaks far above its first hour is ranked last: it had not released in that
hour, so its shape is a wait rather than a launch, and its burst ratio cannot tell it apart from a
real one. Their median log shape is the median forecast; their disagreement is the width of the
band, scaled by 0.7 and floored at 0.25 nats so the band can never claim more certainty than a
launch day has. Quantiles are `p1 * exp(median + z_tau * spread)` with `z = -1.645, -0.674, 0,
0.674, 1.645`.

## What it scores

Scored with the contest's own rule, mean pinball loss on the log scale over the four practice
launches (Marvel's Wolverine, Red Dead Redemption 2, God of War Ragnarok, Marvel's Spider-Man 2),
using their hourly counts from SullyGnome for the practice scoring:

| forecast | loss | typical miss | 90% coverage |
| --- | --- | --- | --- |
| house baseline (persistence at hour 1) | 0.3378 | 69.8% | 0.783 |
| comparables' median shape, their own spread | 0.3838 | 41.5% | 1.000 |
| six nearest-burst comparables, no peak screen | 0.1761 | 29.3% | 0.826 |
| this entry (peak screen, floor 0.25) | 0.1695 | 31.0% | 0.848 |

The peak screen is worth more than the four practice launches can show, because a case whose first
hour already carries a launch is rare among them. Scoring each of the 26 comparables in turn as a
case, predicted from the other 37, gives 0.460 without the screen and 0.328 with it - and it is what
stops a case whose release-day first hour is far above its quiet pre-release level (GTA VI itself
sits that way: its own category ran at about 2,000 viewers before release) from borrowing the shape
of a launch that unlocked at 14:00Z and peaked 2,000x its own first hour.

The practice answers are close to, not identical with, the stored ones the site grades against: the
live hourly series drifts a few percent from the snapshot the kit's case files were cut from, so the
levels above are a local instrument for choosing between shapes, and the site's live practice score
is the number that counts.

## Files

- `main.py` - the whole entry: case reader, comparator, forecast writer.
- `LICENSE` - MIT.
