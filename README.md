# Work and Travel Directory

A free public directory of reported experiences with J-1 Work & Travel employers and recruitment agencies. Anyone can search it and add a report without an account. Reports go live straight away, and an administrator can remove anything from a Google Sheet.

Live site: <https://work-and-travel-directory.streamlit.app>

To set it up or redeploy it, read [docs/SETUP.md](docs/SETUP.md).

## How it fits together

```
In-app form ──POST + token──► Apps Script ──► Private workbook (full record)
(no sign-in)                  (runs as you) ──► Public workbook (public fields only)
                                                     │ published CSV
                                                     ▼
Review Queue dropdown ──► Apps Script          Streamlit app
                          edits public tab     (reads only the public tab)
```

The Streamlit app reads one published CSV and holds no Google credential, so it has no way to reach private submissions or reviewer notes. Its token can only add reports.

## Project layout

```
app.py                  page router
views/                  one file per page
directory/              config, data loading, search, rendering, submissions, styles
static/fonts/           self-hosted fonts, so no visitor data goes to a font provider
google/Code.gs          the Apps Script back end
scripts/                one-time data import
tests/                  Python and Apps Script tests, using synthetic data
data/                   real data, never committed
```

The name, headline, tagline, operator name, star categories and issue chips are all in `directory/config.py`. Colours are at the top of `directory/style.css` and in `.streamlit/config.toml`.

## Run it locally

```
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
.venv\Scripts\python -m streamlit run app.py
```

For local work, `public_csv_url` in `secrets.toml` can be a file path, such as `data/private/public_directory_seed.csv`.

## Run the tests

```
.venv\Scripts\python -m pytest tests
node --test tests/apps_script.test.js
```
