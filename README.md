# Where's the Pow?

One-page site that tells Ikon Pass skiers which Western US resort to hit: who's open,
who got fresh snow, where it's a groomer day, and where a storm is headed.

## How it works

- `page.html` is the page template. It contains the design and the logic; the data is
  injected into the `const SNAPSHOT = ...` line at build time.
- `fetch_snapshot.py` pulls snowfall and forecast for 23 resorts from Open-Meteo (free,
  no key) and open/closed status from SkiCentral's open-areas page, and writes `snapshot.json`.
- `build.py` combines the two into `index.html`, the file the site serves.
- `.github/workflows/refresh.yml` runs those two scripts every morning around 4:40am Pacific
  and commits the new `index.html`. GitHub Pages serves it. No servers, no cost.

When a visitor opens the page their browser also fetches live weather from Open-Meteo, so the
snow numbers are current to the minute; open/closed status is as of the morning rebuild.

## Setup (once, about 10 minutes)

1. Create a new GitHub repository (public is fine) and push these files to the `main` branch.
2. In the repo: Settings -> Pages -> Source: "Deploy from a branch", Branch: `main`, folder `/ (root)`. Save.
3. In the repo: Actions tab -> "Refresh snow data" -> "Run workflow". This does the first build.
   (If Actions asks you to enable workflows, click enable.)
4. After a minute the site is live at `https://<your-username>.github.io/<repo-name>/`.
5. Custom domain (optional): buy a domain, then in Settings -> Pages enter it under
   "Custom domain" and add the DNS records GitHub shows you (a CNAME for `www` pointing at
   `<your-username>.github.io`, plus the four A records for the bare domain). Tick "Enforce HTTPS"
   once it verifies.

## Changing things

- Resort list, coordinates, SkiCentral slugs and projected opening dates: the `RESORTS` table
  at the top of `fetch_snapshot.py`. Opening dates are only used as the "Opens Nov 27" label
  when SkiCentral doesn't list the resort as open; update them each fall.
- Thresholds (6" = pow, 3" = soft, groomer-day rules): `analyze()` and `render()` in `page.html`.
- Copy and colours: `page.html`.

Pushing a change to `page.html`, `fetch_snapshot.py` or `build.py` triggers a rebuild automatically.

Not affiliated with Ikon Pass or Alterra Mountain Company. Weather data (c) Open-Meteo.
