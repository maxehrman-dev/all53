# THE 53

One NFL team, one clock. Name as many players as you can. Deep cuts buy time. Name 53 and you've named a full roster.

## Rules (all in one place: `RULES`, `DIFF`, `TIERS` at the top of the script in `src/app.html`)

- **Score = players named.** Every name counts as one. Tiers: Fan 10, Ball Knower 20, Expert 30, Elite 40, GOAT 53.
- **One clock** that never resets. Every correct name adds time by how well known he is (bands are ranks within
  each team's pool, set in `RULES.cuts`):
  - Current, Easy: star +1s, known +2s, deep cut +14s, rare +20s, fan favorite +24s (start 60s)
  - Current, Hard: star +2s, known +3s, deep cut +11s, rare +15s, fan favorite +18s (start 45s)
  - All-Time, both: star +1s, known +2s, everyone else +3s, fan favorite +10s
- **Easy:** player by player. A face pops up; type his name, or press Return / Next to skip. Typing anyone else counts
  too. Photos are Current only. **Hard:** no photos. Misses are free in both, suggestions come from the whole league.
- **One run per team per day** in each mode; the fan favorite stays secret unless you find him.
- **Naming a player:** full name, nickname (Mike/Michael), last name alone if unique on the roster, initial + last name
  for ties ("j allen"), small typos forgiven. Accents, apostrophes, periods and hyphens never matter.
  Suggestions search the whole league, so they never give away who is on the team.
- **Rarity** (1 to 99) is a rank within each team's pool of how well known a player is *today*:
  curated fame tier, Hall of Fame, Pro Bowls and All-Pros, how recently he played, and whether he's on the roster now.
- **Daily:** same team for everyone each day (All-Time on Sundays). **Challenges:** a link that gives a friend your team,
  mode and the same number of guesses.
- **Fan percentile** is an estimate from a modeled distribution of fan scores per mode (`MEDIAN`, `SPREAD`).

## Files

- `dist/` is the website. Upload this folder as-is. Nothing runs on a server.
  - `index.html` (72 KB), `rosters-current.js` (77 KB, 33 KB gzipped), `rosters-alltime.js` (1.4 MB, 525 KB gzipped,
    only downloaded when someone picks All-Time), `og.png` (link preview), `favicon.svg`.
  - `the53-single.html` is everything in one file, for Muse or opening straight from your computer.
- `dist/faces/` holds 96px player thumbnails per team (Current rosters only), `dist/img/` the NFL photo ids.
- `src/app.html` is the game source. `build.js` turns it into `dist/`.
- `fetch_faces.py` downloads the thumbnails (needs access to static.www.nfl.com).
- `build_data.py` builds rosters from nflverse plus the original curated lists (`teams_orig.json`).
- `update_rosters.sh` refreshes everything.
- `reference/original-name-that-player.html` is the version this was rebuilt from.

Player photos are NFL headshots. They're fine for a personal fan project; if THE 53 goes commercial, swap them for
licensed images or drop them (Easy still works without photos).

## Host it for free

Any static host works, and none of them will charge for this:

- **Cloudflare Pages** (recommended: free, unlimited bandwidth). dash.cloudflare.com, Workers & Pages, Create, Pages,
  Upload assets, drop the `dist` folder. You get `https://<name>.pages.dev`.
- **Netlify Drop**: app.netlify.com/drop, drag the `dist` folder in.
- **GitHub Pages** or **Vercel** also work as plain static sites.

After you have the address, rebuild once so share links and link previews use it:

```bash
./update_rosters.sh https://your-address.pages.dev/
```

Then upload `dist/` again.

## Keep rosters fresh

```bash
./update_rosters.sh https://your-address.pages.dev/
```

Weekly during the season is plenty. It downloads only this season's roster again and reuses the rest.

## Logo

The logo is one SVG in `<template id="logo-tpl">` in `src/app.html`, plus `football()` and the "53" text in `drawCard()` for
the share image. Swap those when the final logo is ready.
