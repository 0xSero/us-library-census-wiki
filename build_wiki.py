#!/usr/bin/env python3
"""build_wiki.py — Build the US Library Census Wiki from CSV data.

Reads all CSVs from data/, generates:
  - Static HTML pages (index, gov, search, about, state pages)
  - Condensed JSON data files for client-side search
  - Copies the interactive map

Usage:
  python3 wiki/build_wiki.py
"""
import csv
import json
import os
import html
import urllib.request
from datetime import datetime, timezone
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
WIKI = os.path.join(ROOT, "wiki")
STATES_DIR = os.path.join(WIKI, "states")
DATA_OUT = os.path.join(WIKI, "data")

# US state names
STATE_NAMES = {
    'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California',
    'CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia',
    'HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa',
    'KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland',
    'MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi',
    'MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire',
    'NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina',
    'ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania',
    'RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee',
    'TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington',
    'WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming','DC':'District of Columbia',
    'PR':'Puerto Rico','GU':'Guam','VI':'US Virgin Islands','AS':'American Samoa',
    'MP':'Northern Mariana Islands',
}

def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def esc(s):
    return html.escape(str(s or ''), quote=True)

def now_str():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

# ---------------------------------------------------------------------------
# Shell template — Bootstrap 5 + Wikipedia-style typography
# ---------------------------------------------------------------------------
def shell(title, body_html, panel_html="", active_tab="", extra_head="", body_class="", root=""):
    """Generate a page using Bootstrap 5 for layout with Wikipedia-style typography."""
    nav_items = [
        ("index.html",  "Main page",   "index"),
        ("search.html", "Search",      "search"),
        ("map.html",    "Map",         "map"),
        ("gov.html",    "Government",  "gov"),
        ("about.html",   "About",       "about"),
    ]
    nav_html = ""
    for href, label, tab_id in nav_items:
        cls = "active" if active_tab == tab_id else ""
        nav_html += f'      <li class="nav-item"><a class="nav-link {cls}" href="{root}{href}">{label}</a></li>\n'

    bc = f" {body_class}" if body_class else ""
    sidebar_div = f'<aside class="col-lg-2 d-none d-lg-block wiki-sidebar">{panel_html}</aside>' if panel_html else ""
    main_col = "col-lg-10" if panel_html else "col-12"

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — US Library Census Wiki</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="{root}wiki.css">
{extra_head}
<script>
(function(){{var t=localStorage.getItem('wiki-theme')||'light';document.documentElement.setAttribute('data-theme',t);}})();
</script>
</head>
<body class="wiki-body{bc}">
<nav class="navbar navbar-expand-lg border-bottom fixed-top wiki-nav">
  <div class="container-fluid">
    <a class="navbar-brand" href="{root}index.html"><b>US Library Census</b> <small class="text-muted fw-normal">AGI</small></a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#wikiNav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="wikiNav">
      <ul class="navbar-nav me-auto">
{nav_html.rstrip()}
      </ul>
      <form class="d-flex me-2" action="{root}search.html" method="get">
        <input class="form-control form-control-sm" name="q" type="search" placeholder="Search" aria-label="Search">
      </form>
    </div>
    <button class="btn btn-sm btn-outline-secondary theme-toggle ms-2" onclick="toggleTheme()" title="Toggle dark mode" aria-label="Toggle dark mode">🌓</button>
  </div>
</nav>
<div class="container-fluid wiki-container{bc}">
  <div class="row g-0">
{sidebar_div}
    <main class="{main_col} wiki-main" id="content">
      <h1 class="wiki-title" id="firstHeading">{esc(title)}</h1>
      <div class="wiki-body-content" id="bodyContent">
{body_html}
      </div>
    </main>
  </div>
</div>
<footer class="wiki-footer py-3 px-4 border-top mt-auto">
  <small class="text-muted">
    AGI · EIN 42-4298008 ·
    <a href="{root}about.html">About</a> · <a href="{root}search.html">Search</a> · <a href="{root}map.html">Map</a>
    <br>Data updated {now_str()}
  </small>
</footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
function toggleTheme(){{var h=document.documentElement;var c=h.getAttribute('data-theme')||'light';var n=c==='light'?'dark':'light';h.setAttribute('data-theme',n);localStorage.setItem('wiki-theme',n);var f=document.querySelector('.map-embed iframe');if(f&&f.contentWindow){{try{{f.contentWindow.postMessage({{type:'wiki-theme',theme:n}},'*');}}catch(e){{}}}}}}
</script>
</body>
</html>"""

def panel(active=""):
    """Left sidebar — Wikipedia-style portal sections using Bootstrap list groups."""
    nav_items = [
        ("index.html",  "Main page"),
        ("search.html", "Search the census"),
        ("map.html",    "Interactive map"),
        ("gov.html",    "Government sites"),
        ("about.html",   "About / methodology"),
    ]
    nav_html = "\n".join(f'    <a href="{href}" class="list-group-item list-group-item-action small py-1">{label}</a>' for href, label in nav_items)
    return f"""<div class="wiki-portlet">
  <h6 class="sidebar-heading">Navigation</h6>
  <div class="list-group list-group-flush">
{nav_html}
  </div>
</div>
<div class="wiki-portlet">
  <h6 class="sidebar-heading">Data</h6>
  <div class="list-group list-group-flush">
    <a href="search.html?type=public" class="list-group-item list-group-item-action small py-1">Public libraries</a>
    <a href="search.html?type=private" class="list-group-item list-group-item-action small py-1">Private libraries</a>
    <a href="search.html?type=gov" class="list-group-item list-group-item-action small py-1">Government sites</a>
    <a href="search.html?type=hours" class="list-group-item list-group-item-action small py-1">Library hours</a>
    <a href="search.html?type=services" class="list-group-item list-group-item-action small py-1">Library services</a>
  </div>
</div>
<div class="wiki-portlet">
  <h6 class="sidebar-heading">Explore</h6>
  <div class="list-group list-group-flush">
    <a href="index.html#states" class="list-group-item list-group-item-action small py-1">Browse by state</a>
    <a href="index.html#coverage" class="list-group-item list-group-item-action small py-1">Data coverage</a>
    <a href="index.html#gov" class="list-group-item list-group-item-action small py-1">Government tiers</a>
    <a href="index.html#ala-report" class="list-group-item list-group-item-action small py-1">ALA report 2024</a>
    <a href="index.html#covid-recovery" class="list-group-item list-group-item-action small py-1">COVID impact &amp; recovery</a>
    <a href="index.html#per-capita-rankings" class="list-group-item list-group-item-action small py-1">Per-capita rankings</a>
    <a href="index.html#pls-extended" class="list-group-item list-group-item-action small py-1">Bookmobiles & WiFi</a>
    <a href="index.html#ill" class="list-group-item list-group-item-action small py-1">Interlibrary loan</a>
    <a href="index.html#workforce" class="list-group-item list-group-item-action small py-1">Library workforce</a>
    <a href="index.html#philanthropy" class="list-group-item list-group-item-action small py-1">Philanthropy & Carnegie</a>
    <a href="index.html#circulation" class="list-group-item list-group-item-action small py-1">Circulation & cards</a>
    <a href="index.html#fdlp-directory" class="list-group-item list-group-item-action small py-1">Federal depositories</a>
    <a href="index.html#library-usage" class="list-group-item list-group-item-action small py-1">Library usage surveys</a>
    <a href="index.html#demographics" class="list-group-item list-group-item-action small py-1">Who uses libraries</a>
    <a href="index.html#reading-trends" class="list-group-item list-group-item-action small py-1">Reading trends</a>
    <a href="index.html#state-censorship" class="list-group-item list-group-item-action small py-1">Bans by state</a>
    <a href="index.html#dpla" class="list-group-item list-group-item-action small py-1">DPLA digital library</a>
    <a href="index.html#school-librarians" class="list-group-item list-group-item-action small py-1">School librarians</a>
    <a href="index.html#usda-grants" class="list-group-item list-group-item-action small py-1">USDA library grants</a>
    <a href="index.html#neh-grants" class="list-group-item list-group-item-action small py-1">NEH library grants</a>
    <a href="index.html#imls-grants" class="list-group-item list-group-item-action small py-1">IMLS all grants</a>
    <a href="index.html#other-federal-grants" class="list-group-item list-group-item-action small py-1">Other federal grants</a>
    <a href="index.html#federal-funding-totals" class="list-group-item list-group-item-action small py-1">Federal funding totals</a>
    <a href="index.html#state-funding" class="list-group-item list-group-item-action small py-1">State funding mix</a>
    <a href="index.html#loc" class="list-group-item list-group-item-action small py-1">Library of Congress</a>
    <a href="index.html#nlm" class="list-group-item list-group-item-action small py-1">National Library of Medicine</a>
    <a href="index.html#digital-libraries" class="list-group-item list-group-item-action small py-1">Digital libraries</a>
    <a href="index.html#museums" class="list-group-item list-group-item-action small py-1">US museums (IMLS)</a>
    <a href="index.html#prison-libraries" class="list-group-item list-group-item-action small py-1">Prison libraries</a>
    <a href="index.html#lis-programs" class="list-group-item list-group-item-action small py-1">LIS degree programs</a>
    <a href="gov.html#services" class="list-group-item list-group-item-action small py-1">Gov services</a>
  </div>
</div>"""

def panel_state(states, current_st):
    """Sidebar for state pages — relative paths + other states list."""
    nav_html = """    <a href="../index.html" class="list-group-item list-group-item-action small py-1">Main page</a>
    <a href="../search.html" class="list-group-item list-group-item-action small py-1">Search</a>
    <a href="../map.html" class="list-group-item list-group-item-action small py-1">Map</a>
    <a href="../gov.html" class="list-group-item list-group-item-action small py-1">Government sites</a>
    <a href="../about.html" class="list-group-item list-group-item-action small py-1">About</a>"""
    other_html = "\n".join(f'    <a href="{st}.html" class="list-group-item list-group-item-action small py-1">{st}</a>' for st in sorted(states) if st != current_st)
    return f"""<div class="wiki-portlet">
  <h6 class="sidebar-heading">Navigation</h6>
  <div class="list-group list-group-flush">
{nav_html}
  </div>
</div>
<div class="wiki-portlet">
  <h6 class="sidebar-heading">Other states</h6>
  <div class="list-group list-group-flush">
{other_html}
  </div>
</div>"""

# ---------------------------------------------------------------------------
# Load all data
# ---------------------------------------------------------------------------
def load_all():
    print("[build] Loading CSVs...")
    data = {}

    # Public libraries: merge non-verified (has social media) with verified (has url_live, server, etc.)
    pub_base = read_csv(os.path.join(DATA, "public_libraries.csv"))
    pub_verified = read_csv(os.path.join(DATA, "public_libraries_verified.csv"))
    if pub_verified:
        _pv_map = {r.get('id', ''): r for r in pub_verified if r.get('id', '')}
        for r in pub_base:
            vid = r.get('id', '')
            if vid in _pv_map:
                for k, v in _pv_map[vid].items():
                    if k not in r or not (r.get(k, '') or '').strip():
                        r[k] = v
    data['public'] = pub_base

    # Private libraries: prefer verified (superset — has url_live, server, http_status, etc.)
    priv_verified_path = os.path.join(DATA, "private_libraries_verified.csv")
    if os.path.exists(priv_verified_path):
        data['private'] = read_csv(priv_verified_path)
    else:
        data['private'] = read_csv(os.path.join(DATA, "private_libraries.csv"))

    data['hours'] = read_csv(os.path.join(DATA, "library_hours.csv"))
    data['services'] = read_csv(os.path.join(DATA, "library_services.csv"))
    data['gov_services'] = read_csv(os.path.join(DATA, "gov_services.csv"))
    # Library consortia (Wikipedia + ICOLC)
    consortia_path = os.path.join(DATA, "library_consortia.csv")
    data['consortia'] = read_csv(consortia_path) if os.path.exists(consortia_path) else []
    # State Library Administrative Agencies (IMLS SLAA FY2024 — one row per state agency)
    slaa_path = os.path.join(DATA, "state_library_agencies.csv")
    data['slaa'] = read_csv(slaa_path) if os.path.exists(slaa_path) else []
    # Academic Library Survey (NCES ALS 2012 — 4,261 institutions; historical vintages 2000-2012)
    als_path = os.path.join(DATA, "academic_libraries.csv")
    data['academic'] = read_csv(als_path) if os.path.exists(als_path) else []
    # IPEDS Academic Libraries 2023 — latest available vintage (3,695 institutions)
    als2023_path = os.path.join(DATA, "academic_libraries_2023.csv")
    data['academic_2023'] = read_csv(als2023_path) if os.path.exists(als2023_path) else []
    # ALS temporal trends (national + by-state aggregates across 8 vintages 2000-2023)
    data['als_national'] = read_csv(os.path.join(DATA, "als_trends_national.csv")) if os.path.exists(os.path.join(DATA, "als_trends_national.csv")) else []
    data['als_by_state'] = read_csv(os.path.join(DATA, "als_trends_by_state.csv")) if os.path.exists(os.path.join(DATA, "als_trends_by_state.csv")) else []
    # PLS historical trends (national + by-state aggregates across 25 vintages 2000-2024)
    data['pls_national'] = read_csv(os.path.join(DATA, "pls_trends_national.csv")) if os.path.exists(os.path.join(DATA, "pls_trends_national.csv")) else []
    data['pls_by_state'] = read_csv(os.path.join(DATA, "pls_trends_by_state.csv")) if os.path.exists(os.path.join(DATA, "pls_trends_by_state.csv")) else []
    # SLAA historical trends (national + by-state aggregates across 4 vintages FY2018-FY2024)
    data['slaa_national'] = read_csv(os.path.join(DATA, "slaa_trends_national.csv")) if os.path.exists(os.path.join(DATA, "slaa_trends_national.csv")) else []
    data['slaa_by_state'] = read_csv(os.path.join(DATA, "slaa_trends_by_state.csv")) if os.path.exists(os.path.join(DATA, "slaa_trends_by_state.csv")) else []
    # Federal Depository Libraries (GPO FDLP — 672 libraries selecting Print Distribution Titles)
    fdlp_path = os.path.join(DATA, "_cache", "fdlp", "federal_depository_libraries.csv")
    data['fdlp'] = read_csv(fdlp_path) if os.path.exists(fdlp_path) else []
    # California State Library — richer per-library stats than IMLS PLS (FY2023-24)
    ca_summary_path = os.path.join(DATA, "ca_state_summary.json")
    if os.path.exists(ca_summary_path):
        with open(ca_summary_path) as f:
            data['ca_summary'] = json.load(f)
    else:
        data['ca_summary'] = {}
    # IMLS Grant Awards (1996-2025, 21,325 grants, $4.04B awarded)
    data['imls_grants_year'] = read_csv(os.path.join(DATA, "imls_grants_by_year.csv")) if os.path.exists(os.path.join(DATA, "imls_grants_by_year.csv")) else []
    data['imls_grants_state'] = read_csv(os.path.join(DATA, "imls_grants_by_state.csv")) if os.path.exists(os.path.join(DATA, "imls_grants_by_state.csv")) else []
    data['imls_grants_recent_state'] = read_csv(os.path.join(DATA, "imls_grants_recent_by_state.csv")) if os.path.exists(os.path.join(DATA, "imls_grants_recent_by_state.csv")) else []
    # IMLS Grants to States (G2S) — formula-based funding through state agencies (2014-2025)
    data['imls_g2s_year'] = read_csv(os.path.join(DATA, "imls_g2s_by_year.csv")) if os.path.exists(os.path.join(DATA, "imls_g2s_by_year.csv")) else []
    data['imls_g2s_state'] = read_csv(os.path.join(DATA, "imls_g2s_by_state.csv")) if os.path.exists(os.path.join(DATA, "imls_g2s_by_state.csv")) else []
    data['imls_grants_program'] = read_csv(os.path.join(DATA, "imls_grants_by_program.csv")) if os.path.exists(os.path.join(DATA, "imls_grants_by_program.csv")) else []
    data['imls_grants_largest'] = read_csv(os.path.join(DATA, "imls_grants_largest.csv")) if os.path.exists(os.path.join(DATA, "imls_grants_largest.csv")) else []
    # IPEDS institutional characteristics (Carnegie class, control, enrollment, HBCU/tribal/land-grant)
    carnegie_path = os.path.join(DATA, "academic_carnegie_summary.json")
    if os.path.exists(carnegie_path):
        with open(carnegie_path) as f:
            data['carnegie_summary'] = json.load(f)
    else:
        data['carnegie_summary'] = {}
    # PLS FY2024 digital services (e-circulation, programs by age/delivery, WiFi, capital revenue)
    pls_dig_path = os.path.join(DATA, "pls_fy2024_digital.json")
    if os.path.exists(pls_dig_path):
        with open(pls_dig_path) as f:
            data['pls_fy2024_digital'] = json.load(f)
    else:
        data['pls_fy2024_digital'] = {}
    # SLAA state agency services (summer reading, literacy, digitization, accessibility, E-Rate)
    slaa_svc_path = os.path.join(DATA, "slaa_services_summary.json")
    if os.path.exists(slaa_svc_path):
        with open(slaa_svc_path) as f:
            data['slaa_services'] = json.load(f)
    else:
        data['slaa_services'] = {}
    # Book censorship database (EveryLibrary Institute / Magnusson)
    censor_path = os.path.join(DATA, "book_censorship_summary.json")
    if os.path.exists(censor_path):
        with open(censor_path) as f:
            data['book_censorship'] = json.load(f)
    else:
        data['book_censorship'] = {}
    # NTIA Tribal Broadband Connectivity Program (TBCP)
    tribal_path = os.path.join(DATA, "tribal_broadband_summary.json")
    if os.path.exists(tribal_path):
        with open(tribal_path) as f:
            data['tribal_broadband'] = json.load(f)
    else:
        data['tribal_broadband'] = {}
    # USAC Emergency Connectivity Fund (ECF) Form 471
    ecf_path = os.path.join(DATA, "ecf_summary.json")
    if os.path.exists(ecf_path):
        with open(ecf_path) as f:
            data['ecf'] = json.load(f)
    else:
        data['ecf'] = {}
    # BLS OES librarian salary data
    bls_path = os.path.join(DATA, "bls_librarian_salaries.json")
    if os.path.exists(bls_path):
        with open(bls_path) as f:
            data['bls_salaries'] = json.load(f)
    else:
        data['bls_salaries'] = {}
    # FCC Affordable Connectivity Program (ACP)
    acp_path = os.path.join(DATA, "acp_summary.json")
    if os.path.exists(acp_path):
        with open(acp_path) as f:
            data['acp'] = json.load(f)
    else:
        data['acp'] = {}
    # USAC E-Rate (library funding requests, FCC Form 471)
    erate_path = os.path.join(DATA, "erate_summary.json")
    if os.path.exists(erate_path):
        with open(erate_path) as f:
            data['erate'] = json.load(f)
    else:
        data['erate'] = {}
    # NTIA BEAD (Broadband Equity Access & Deployment) allocations
    bead_path = os.path.join(DATA, "bead_summary.json")
    if os.path.exists(bead_path):
        with open(bead_path) as f:
            data['bead'] = json.load(f)
    else:
        data['bead'] = {}
    # Library ballot measures (EveryLibrary)
    ballot_path = os.path.join(DATA, "ballot_measures_summary.json")
    if os.path.exists(ballot_path):
        with open(ballot_path) as f:
            data['ballot'] = json.load(f)
    else:
        data['ballot'] = {}
    # Library usage survey data (Pew Research + Gallup)
    usage_path = os.path.join(DATA, "library_usage_survey.json")
    if os.path.exists(usage_path):
        with open(usage_path) as f:
            data['library_usage'] = json.load(f)
    else:
        data['library_usage'] = {}
    ala_path = os.path.join(DATA, "ala_report_summary.json")
    if os.path.exists(ala_path):
        with open(ala_path) as f:
            data['ala_report'] = json.load(f)
    else:
        data['ala_report'] = {}
    pc_path = os.path.join(DATA, "state_per_capita_rankings.json")
    if os.path.exists(pc_path):
        with open(pc_path) as f:
            data['state_per_capita'] = json.load(f)
    else:
        data['state_per_capita'] = {}
    covid_path = os.path.join(DATA, "covid_recovery_summary.json")
    if os.path.exists(covid_path):
        with open(covid_path) as f:
            data['covid_recovery'] = json.load(f)
    else:
        data['covid_recovery'] = {}
    fdlp_summary_path = os.path.join(DATA, "fdlp_summary.json")
    if os.path.exists(fdlp_summary_path):
        with open(fdlp_summary_path) as f:
            data['fdlp_summary'] = json.load(f)
    else:
        data['fdlp_summary'] = {}
    demo_path = os.path.join(DATA, "library_demographics_summary.json")
    if os.path.exists(demo_path):
        with open(demo_path) as f:
            data['library_demographics'] = json.load(f)
    else:
        data['library_demographics'] = {}
    stcens_path = os.path.join(DATA, "state_censorship_summary.json")
    if os.path.exists(stcens_path):
        with open(stcens_path) as f:
            data['state_censorship'] = json.load(f)
    else:
        data['state_censorship'] = {}
    dpla_path = os.path.join(DATA, "dpla_summary.json")
    if os.path.exists(dpla_path):
        with open(dpla_path) as f:
            data['dpla'] = json.load(f)
    else:
        data['dpla'] = {}
    nces_full_path = os.path.join(DATA, "nces_school_libraries_summary.json")
    if os.path.exists(nces_full_path):
        with open(nces_full_path) as f:
            data['nces_school_full'] = json.load(f)
    else:
        data['nces_school_full'] = {}
    usda_path = os.path.join(DATA, "usda_library_grants_summary.json")
    if os.path.exists(usda_path):
        with open(usda_path) as f:
            data['usda_grants'] = json.load(f)
    else:
        data['usda_grants'] = {}
    neh_path = os.path.join(DATA, "neh_library_grants_summary.json")
    if os.path.exists(neh_path):
        with open(neh_path) as f:
            data['neh_grants'] = json.load(f)
    else:
        data['neh_grants'] = {}
    sf_path = os.path.join(DATA, "state_funding_summary.json")
    if os.path.exists(sf_path):
        with open(sf_path) as f:
            data['state_funding'] = json.load(f)
    else:
        data['state_funding'] = {}
    loc_path = os.path.join(DATA, "loc_summary.json")
    if os.path.exists(loc_path):
        with open(loc_path) as f:
            data['loc'] = json.load(f)
    else:
        data['loc'] = {}
    dl_path = os.path.join(DATA, "digital_libraries_summary.json")
    if os.path.exists(dl_path):
        with open(dl_path) as f:
            data['digital_libraries'] = json.load(f)
    else:
        data['digital_libraries'] = {}
    imls_grants_path = os.path.join(DATA, "imls_library_grants_summary.json")
    if not os.path.exists(imls_grants_path):
        imls_grants_path = os.path.join(DATA, "imls_grants_summary.json")
    if os.path.exists(imls_grants_path):
        with open(imls_grants_path) as f:
            data['imls_library_grants'] = json.load(f)
    else:
        data['imls_library_grants'] = {}
    other_fed_path = os.path.join(DATA, "other_federal_grants_summary.json")
    if os.path.exists(other_fed_path):
        with open(other_fed_path) as f:
            data['other_federal_grants'] = json.load(f)
    else:
        data['other_federal_grants'] = {}
    fft_path = os.path.join(DATA, "federal_funding_totals.json")
    if os.path.exists(fft_path):
        with open(fft_path) as f:
            data['federal_funding_totals'] = json.load(f)
    else:
        data['federal_funding_totals'] = {}
    nlm_path = os.path.join(DATA, "nlm_summary.json")
    if os.path.exists(nlm_path):
        with open(nlm_path) as f:
            data['nlm'] = json.load(f)
    else:
        data['nlm'] = {}
    pls_ext_path = os.path.join(DATA, "pls_extended_metrics.json")
    if os.path.exists(pls_ext_path):
        with open(pls_ext_path) as f:
            data['pls_extended'] = json.load(f)
    else:
        data['pls_extended'] = {}
    ill_path = os.path.join(DATA, "ill_summary.json")
    if os.path.exists(ill_path):
        with open(ill_path) as f:
            data['ill'] = json.load(f)
    else:
        data['ill'] = {}
    wf_path = os.path.join(DATA, "library_workforce_summary.json")
    if os.path.exists(wf_path):
        with open(wf_path) as f:
            data['library_workforce'] = json.load(f)
    else:
        data['library_workforce'] = {}
    phil_path = os.path.join(DATA, "library_philanthropy_summary.json")
    if os.path.exists(phil_path):
        with open(phil_path) as f:
            data['philanthropy'] = json.load(f)
    else:
        data['philanthropy'] = {}
    circ_path = os.path.join(DATA, "circulation_summary.json")
    if os.path.exists(circ_path):
        with open(circ_path) as f:
            data['circulation'] = json.load(f)
    else:
        data['circulation'] = {}
    museums_path = os.path.join(DATA, "museums_summary.json")
    if os.path.exists(museums_path):
        with open(museums_path) as f:
            data['museums'] = json.load(f)
    else:
        data['museums'] = {}
    prison_path = os.path.join(DATA, "prison_libraries_summary.json")
    if os.path.exists(prison_path):
        with open(prison_path) as f:
            data['prison_libraries'] = json.load(f)
    else:
        data['prison_libraries'] = {}
    lis_path = os.path.join(DATA, "lis_programs_summary.json")
    if os.path.exists(lis_path):
        with open(lis_path) as f:
            data['lis_programs'] = json.load(f)
    else:
        data['lis_programs'] = {}
    # Deduplicate gov_services: keep one entry per (agency_name, level),
    # preferring the row with the longest/best services_summary.
    # Also drop boilerplate summaries that just restate the agency name.
    _gs_best = {}
    for r in data['gov_services']:
        name = (r.get('agency_name','') or '').strip()
        level = (r.get('level','') or '').strip()
        if not name:
            continue
        key = (name, level)
        summary = (r.get('services_summary','') or '').strip()
        # Skip boilerplate: "Federal government entity: X." / "State of X government entity: Y."
        if summary and f'{level} government entity:' in summary.lower():
            summary = ''  # mark as no real summary
            r['services_summary'] = ''
        if key not in _gs_best:
            _gs_best[key] = r
        else:
            # Keep the one with the longer summary
            old_len = len((_gs_best[key].get('services_summary','') or '').strip())
            new_len = len(summary)
            if new_len > old_len:
                _gs_best[key] = r
    data['gov_services'] = list(_gs_best.values())
    # Gov tiers (use verified versions if available)
    data['gov'] = []
    for tier in ['federal','state','county','city','tribal','special']:
        for variant in [f'{tier}_gov_sites_verified.csv', f'{tier}_gov_sites.csv']:
            path = os.path.join(DATA, variant)
            if os.path.exists(path):
                rows = read_csv(path)
                for r in rows:
                    r['_tier'] = tier
                data['gov'].extend(rows)
                break
    print(f"  Public: {len(data['public'])}, Private: {len(data['private'])}, "
          f"Gov: {len(data['gov'])}, Hours: {len(data['hours'])}, "
          f"Services: {len(data['services'])}, GovServices: {len(data['gov_services'])}, "
          f"Consortia: {len(data['consortia'])}, SLAA: {len(data['slaa'])}, "
          f"Academic: {len(data['academic'])}, Academic2023: {len(data['academic_2023'])}, "
          f"ALS-trends: {len(data['als_national'])}, FDLP: {len(data['fdlp'])}, "
          f"IMLS-grants: {len(data['imls_grants_year'])}")
    return data

# ---------------------------------------------------------------------------
# Build condensed JSON
# ---------------------------------------------------------------------------
def _compact(d):
    """Return a dict with only non-empty string values (keeps JSON lean)."""
    return {k: v for k, v in d.items() if v and str(v).strip()}

def build_json(data):
    print("[build] Generating JSON data files...")
    os.makedirs(DATA_OUT, exist_ok=True)

    # Column → short-key mapping shared by libraries (public & private share the same schema)
    LIB_MAP = [
        ('id','id'),('name','name'),('type','type'),
        ('address','address'),('city','city'),('state','state'),('zip','zip'),
        ('latitude','lat'),('longitude','lng'),
        ('phone','phone'),('website','website'),('map_url','mapu'),
        ('reviews_rating','rating'),('reviews_count','rcount'),('review_source','rsrc'),
        ('email','email'),('facebook','fb'),('twitter','tw'),
        ('instagram','ig'),('youtube','yt'),
        ('funding_total','ft'),('funding_source','fsrc'),
        ('size_sqft','sqft'),('collection_size','coll'),('population_served','psrv'),
        ('median_household_income','income'),('area_population','pop'),
        ('pct_below_poverty','pov'),('area_median_age','age'),
        ('notes','nt'),
        ('url_live','ulive'),('http_status','hstat'),('final_url','furl'),
        ('last_modified','lmod'),('content_type','ctype'),('content_length','clen'),
        ('server','srv'),('title','ttl'),('redirects','redir'),
        ('check_error','cerr'),('checked_at','cat'),
        # Extended ACS demographics (county-level: education, computer, internet; state-level: language)
        ('pct_bachelors_plus','edu'),('pct_computer_household','comp'),
        ('pct_internet_household','inet'),('pct_non_english_home','lang'),
        # PLS operational data (public libraries only — AE/system level)
        ('annual_visits','vis'),('total_circulation','cir'),('ecirculation','ecir'),
        ('pcirculation','pcir'),('total_programs','prog'),('program_attendance','patt'),
        ('children_programs','cprog'),('ya_programs','yprog'),('adult_programs','aprog'),
        ('internet_terminals','iterm'),('wifi_sessions','wifi'),('registered_borrowers','rbor'),
        ('ill_to','illto'),('ill_from','illfm'),('total_staff','staff'),
        ('librarian_staff','lstaff'),('salary_expenses','salx'),
        ('print_material_expenses','pmex'),('electronic_material_expenses','emex'),
        ('capital_expenses','capex'),('central_branches','cbr'),
        ('branch_count','nbr'),('bookmobiles','bkm'),
        # Broadband access (ACS B28003/B28004/B28008, county-level)
        ('pct_broadband_subscriber','bbs'),('pct_dialup_only','dlup'),
        ('pct_no_internet','noint'),('pct_no_computer','nocomp'),
        ('pct_cellular_broadband','cellb'),('pct_fixed_broadband','fixb'),
        ('pct_low_income_no_internet','linoint'),('broadband_digital_divide','ddiv'),
        # FCC National Broadband Map deployment data (county-level infrastructure availability)
        ('fcc_broadband_avail','fccbb'),('fcc_gigabit_avail','fccgig'),
        ('fcc_fiber_avail','fccfib'),('fcc_total_locations','fccloc'),
        ('fcc_rural_pct','fccrur'),
        # FCC Census Place (town-level) broadband availability — most precise per-library figure
        ('fcc_place_gigabit','pgig'),('fcc_place_100_20','p10020'),
        ('fcc_place_25_3','p253'),('fcc_place_fiber','pfib'),
        ('fcc_place_locations','ploc'),
    ]

    # Public libraries — every data-bearing column, compact (empties omitted)
    pub = []
    for r in data['public']:
        rec = {'type': 'public'}
        for col, key in LIB_MAP:
            val = (r.get(col, '') or '').strip()
            if val:
                rec[key] = val
        pub.append(rec)
    with open(os.path.join(DATA_OUT, 'public_libraries.json'), 'w') as f:
        json.dump(pub, f, separators=(',',':'))
    print(f"  public_libraries.json: {len(pub)} records")

    # Private libraries — same full schema (verified CSV is a superset)
    priv = []
    for r in data['private']:
        rec = {'type': 'private'}
        for col, key in LIB_MAP:
            val = (r.get(col, '') or '').strip()
            if val:
                rec[key] = val
        priv.append(rec)
    with open(os.path.join(DATA_OUT, 'private_libraries.json'), 'w') as f:
        json.dump(priv, f, separators=(',',':'))
    print(f"  private_libraries.json: {len(priv)} records")

    # Gov sites — every data-bearing column
    GOV_MAP = [
        ('id','id'),('name','name'),('type','type'),('_tier','tier'),
        ('state','state'),('city','city'),('website','website'),('map_url','mapu'),
        ('latitude','lat'),('longitude','lng'),
        ('url_live','ulive'),('http_status','hstat'),('final_url','furl'),
        ('last_modified','lmod'),('content_type','ctype'),('content_length','clen'),
        ('server','srv'),('title','ttl'),('redirects','redir'),
        ('check_error','cerr'),('checked_at','cat'),
    ]
    gov = []
    for r in data['gov']:
        rec = {}
        for col, key in GOV_MAP:
            val = (r.get(col, '') or '').strip()
            if val:
                rec[key] = val
        if 'type' not in rec:
            rec['type'] = 'gov'
        gov.append(rec)
    with open(os.path.join(DATA_OUT, 'gov_sites.json'), 'w') as f:
        json.dump(gov, f, separators=(',',':'))
    print(f"  gov_sites.json: {len(gov)} records")

    # Hours
    hours = {}
    for r in data['hours']:
        lid = r.get('id','')
        if lid:
            hours[lid] = {
                'raw': r.get('hours_raw',''),
                'structured': r.get('hours_structured',''),
            }
    with open(os.path.join(DATA_OUT, 'library_hours.json'), 'w') as f:
        json.dump(hours, f, separators=(',',':'))
    print(f"  library_hours.json: {len(hours)} records")

    # Services
    services = {}
    for r in data['services']:
        lid = r.get('id','')
        if lid:
            services[lid] = r.get('services','')
    with open(os.path.join(DATA_OUT, 'library_services.json'), 'w') as f:
        json.dump(services, f, separators=(',',':'))
    print(f"  library_services.json: {len(services)} records")

    # Academic libraries — merge ALS 2012 + IPEDS 2023 data
    # Build a map of 2023 records by UNITID for enrichment
    acad_2023_map = {}
    for r in data.get('academic_2023', []):
        uid = (r.get('unitid') or '').strip()
        if uid:
            acad_2023_map[uid] = r

    acad = []
    # First, emit all 2012 records, enriching with 2023 data where the same UNITID exists
    seen_unitids = set()
    for r in data.get('academic', []):
        rec = {'type': 'academic'}
        for col, key in [('unitid','unitid'),('name','name'),('city','city'),('state','state'),
                         ('fips','fips'),('zip','zip'),('website','website'),('year','year'),
                         ('control','control'),('sector','sector'),('locale','locale'),
                         ('carnegie','carnegie'),('student_fte','sfte'),
                         ('stlibs','slf'),('sttot','stf'),('swlibpro','slsal'),('swtot','stsal'),
                         ('exbks','xbks'),('extot','xtot'),('colbksa','coll'),('presen','pres')]:
            val = (r.get(col, '') or '').strip()
            if val:
                rec[key] = val
        # Enrich with 2023 data if available (newer collection/expenditure/staff figures)
        uid = rec.get('unitid', '')
        a23 = acad_2023_map.get(uid)
        if a23:
            rec['y23'] = '2023'
            for col, key in [('extot','xtot23'),('colbksa','coll23'),('sttot','stf23'),
                            ('swlibpro','slsal23'),('exbks','xbks23'),
                            ('pbooks','pbks'),('ebooks','ebks'),('pmedia','pmed'),('emedia','emed'),
                            ('pserials','pser'),('eserials','eser'),('edatabase','edb'),
                            ('tcirc','tcirc'),('ill_provided','illp'),('ill_received','illr'),
                            ('branches','brch')]:
                val = (a23.get(col, '') or '').strip()
                if val:
                    rec[key] = val
            seen_unitids.add(uid)
        acad.append(rec)

    # Add 2023-only institutions (not in 2012 data — new or reclassified)
    for r in data.get('academic_2023', []):
        uid = (r.get('unitid') or '').strip()
        if uid in seen_unitids:
            continue
        rec = {'type': 'academic'}
        for col, key in [('unitid','unitid'),('name','name'),('city','city'),('state','state'),
                         ('fips','fips'),('zip','zip'),('website','website'),
                         ('control','control'),('sector','sector'),('locale','locale'),
                         ('stlibs','slf'),('sttot','stf'),('swlibpro','slsal'),('swtot','stsal'),
                         ('exbks','xbks'),('extot','xtot'),('colbksa','coll'),
                         ('pbooks','pbks'),('ebooks','ebks'),('pmedia','pmed'),('emedia','emed'),
                         ('pserials','pser'),('eserials','eser'),('edatabase','edb'),
                         ('tcirc','tcirc'),('ill_provided','illp'),('ill_received','illr'),
                         ('branches','brch')]:
            val = (r.get(col, '') or '').strip()
            if val:
                rec[key] = val
        rec['year'] = '2023'
        rec['y23'] = '2023'
        acad.append(rec)

    with open(os.path.join(DATA_OUT, 'academic_libraries.json'), 'w') as f:
        json.dump(acad, f, separators=(',',':'))
    print(f"  academic_libraries.json: {len(acad)} records (ALS 2012 + IPEDS 2023 merged)")

    # Stats
    stats = compute_stats(data)
    with open(os.path.join(DATA_OUT, 'stats.json'), 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"  stats.json generated")
    return stats

def compute_stats(data):
    pub = data['public']
    priv = data['private']
    gov = data['gov']

    def pct(n, d):
        return f"{100*n/d:.1f}%" if d else "0%"

    pub_rated = sum(1 for r in pub if (r.get('reviews_rating') or '').strip())
    pub_web = sum(1 for r in pub if (r.get('website') or '').strip())
    pub_email = sum(1 for r in pub if (r.get('email') or '').strip())
    pub_social = sum(1 for r in pub if any((r.get(c) or '').strip() for c in ['facebook','twitter','instagram','youtube']))
    pub_demo = sum(1 for r in pub if (r.get('area_population') or '').strip())

    priv_rated = sum(1 for r in priv if (r.get('reviews_rating') or '').strip())
    priv_web = sum(1 for r in priv if (r.get('website') or '').strip())

    gov_live = sum(1 for r in gov if (r.get('url_live','') or '').strip().lower() in ('true','1','yes'))

    # By tier
    tier_stats = {}
    for tier in ['federal','state','county','city','tribal','special']:
        tier_rows = [r for r in gov if r.get('_tier') == tier]
        tier_live = sum(1 for r in tier_rows if (r.get('url_live','') or '').strip().lower() in ('true','1','yes'))
        tier_stats[tier] = {'total': len(tier_rows), 'live': tier_live, 'pct': pct(tier_live, len(tier_rows))}

    # By state
    state_stats = {}
    for st in STATE_NAMES:
        st_pub = sum(1 for r in pub if r.get('state','') == st)
        st_priv = sum(1 for r in priv if r.get('state','') == st)
        st_gov = sum(1 for r in gov if r.get('state','') == st)
        if st_pub or st_priv or st_gov:
            state_stats[st] = {'name': STATE_NAMES[st], 'pub': st_pub, 'priv': st_priv, 'gov': st_gov}

    # Top rated libraries (min 5 reviews)
    top_rated = []
    for r in pub:
        rating_s = (r.get('reviews_rating') or '').strip()
        rcount_s = (r.get('reviews_count') or '').strip()
        if not rating_s:
            continue
        try:
            rating = float(rating_s)
            rcount = int(rcount_s) if rcount_s else 0
        except (ValueError, TypeError):
            continue
        if rcount >= 5:
            top_rated.append({
                'name': r.get('name', ''), 'city': r.get('city', ''),
                'state': r.get('state', ''), 'rating': rating,
                'rcount': rcount, 'website': r.get('website', ''),
            })
    top_rated.sort(key=lambda x: (-x['rating'], -x['rcount']))
    top_rated = top_rated[:15]

    # Services breakdown (individual service counts)
    svc_counter = Counter()
    for r in data['services']:
        svcs = (r.get('services') or '').strip()
        if svcs:
            for s in svcs.split('|'):
                s = s.strip()
                if s:
                    svc_counter[s] += 1
    services_breakdown = [{'name': k, 'count': v} for k, v in svc_counter.most_common(20)]

    # State rankings (top 10 by total nodes)
    state_ranking = sorted(state_stats.items(), key=lambda x: x[1]['pub'] + x[1]['priv'] + x[1]['gov'], reverse=True)[:10]
    state_ranking = [{'code': st, **info} for st, info in state_ranking]

    # Funding stats
    funding_vals = []
    for r in pub:
        ft = (r.get('funding_total') or '').strip()
        if ft:
            try:
                funding_vals.append(float(ft))
            except (ValueError, TypeError):
                pass
    funding_stats = {
        'total': sum(funding_vals) if funding_vals else 0,
        'avg': sum(funding_vals) / len(funding_vals) if funding_vals else 0,
        'count': len(funding_vals),
    }

    # Demographics
    incomes = []
    for r in pub:
        inc = (r.get('median_household_income') or '').strip()
        if inc:
            try:
                incomes.append(float(inc))
            except (ValueError, TypeError):
                pass
    demo_stats = {
        'avg_income': sum(incomes) / len(incomes) if incomes else 0,
        'income_count': len(incomes),
    }

    # ---- Infrastructure (sqft + collection_size) ----
    sqft_vals = []
    coll_vals = []
    for r in pub:
        sf = (r.get('size_sqft') or '').strip()
        cs = (r.get('collection_size') or '').strip()
        if sf:
            try: sqft_vals.append(float(sf))
            except (ValueError, TypeError): pass
        if cs:
            try: coll_vals.append(float(cs))
            except (ValueError, TypeError): pass
    infra_stats = {
        'total_sqft': int(sum(sqft_vals)) if sqft_vals else 0,
        'total_collection': int(sum(coll_vals)) if coll_vals else 0,
        'avg_sqft': int(sum(sqft_vals) / len(sqft_vals)) if sqft_vals else 0,
        'avg_collection': int(sum(coll_vals) / len(coll_vals)) if coll_vals else 0,
        'sqft_count': len(sqft_vals),
        'coll_count': len(coll_vals),
    }

    # ---- Biggest libraries by sqft ----
    biggest = []
    for r in pub:
        sf = (r.get('size_sqft') or '').strip()
        if not sf: continue
        try: sf_val = float(sf)
        except (ValueError, TypeError): continue
        biggest.append({
            'name': r.get('name', ''), 'city': r.get('city', ''),
            'state': r.get('state', ''), 'sqft': int(sf_val),
            'collection': (r.get('collection_size') or '').strip(),
        })
    biggest.sort(key=lambda x: -x['sqft'])
    biggest_libraries = biggest[:10]

    # ---- Books per capita (collection / population_served) ----
    bpc = []
    for r in pub:
        cs = (r.get('collection_size') or '').strip()
        ps = (r.get('population_served') or '').strip()
        if not cs or not ps: continue
        try:
            coll = int(cs); pop = int(ps)
        except (ValueError, TypeError): continue
        if pop >= 1000 and coll > 0:
            bpc.append({
                'name': r.get('name', ''), 'city': r.get('city', ''),
                'state': r.get('state', ''), 'collection': coll,
                'population': pop, 'ratio': coll / pop,
            })
    bpc.sort(key=lambda x: -x['ratio'])
    books_per_capita = bpc[:10]

    # ---- Funding source breakdown (parse "local $X; state $Y; federal $Z") ----
    import re
    src_totals = {'local': 0, 'state': 0, 'federal': 0, 'county': 0, 'other': 0}
    src_counts = {'local': 0, 'state': 0, 'federal': 0, 'county': 0, 'other': 0}
    for r in pub:
        fs = (r.get('funding_source') or '').strip()
        if not fs: continue
        for part in fs.split(';'):
            part = part.strip()
            if not part: continue
            # Extract dollar amount
            m = re.search(r'\$?([\d,]+)', part)
            amt = 0
            if m:
                try: amt = float(m.group(1).replace(',', ''))
                except (ValueError, TypeError): pass
            pl = part.lower()
            matched = False
            for key in ['local', 'state', 'federal', 'county', 'other']:
                if key in pl or (key == 'other' and not matched):
                    src_totals[key] += amt
                    src_counts[key] += 1
                    matched = True
                    if key != 'other': break
    src_grand = sum(src_totals.values()) or 1
    funding_sources = [
        {'source': k.title(), 'total': src_totals[k], 'count': src_counts[k],
         'pct': f"{100 * src_totals[k] / src_grand:.1f}%"}
        for k in ['local', 'state', 'federal', 'county', 'other']
        if src_totals[k] > 0 or src_counts[k] > 0
    ]

    # ---- Poverty stats ----
    poverty_vals = []
    for r in pub:
        pv = (r.get('pct_below_poverty') or '').strip()
        if pv:
            try: poverty_vals.append(float(pv))
            except (ValueError, TypeError): pass
    poverty_stats = {
        'avg': sum(poverty_vals) / len(poverty_vals) if poverty_vals else 0,
        'min': min(poverty_vals) if poverty_vals else 0,
        'max': max(poverty_vals) if poverty_vals else 0,
        'count': len(poverty_vals),
        'high_poverty': sum(1 for v in poverty_vals if v > 30),
    }

    # ---- Government web tech stack ----
    from collections import Counter as C2
    server_counter = C2()
    status_counter = C2()
    for r in gov:
        srv = (r.get('server') or '').strip()
        if srv:
            # Normalize: keep first word / main product name
            srv_clean = srv.split('/')[0].split(' ')[0].strip()
            if srv_clean:
                server_counter[srv_clean] += 1
        st = (r.get('http_status') or '').strip()
        if st:
            status_counter[st] += 1
    gov_tech = {
        'servers': [{'name': k, 'count': v} for k, v in server_counter.most_common(10)],
        'statuses': [{'code': k, 'count': v} for k, v in sorted(status_counter.items())],
        'total_checked': len(gov),
    }

    # ---- Agency timeline (established_year) ----
    agencies_with_year = []
    seen_names = set()
    for r in data['gov_services']:
        yr = (r.get('established_year') or '').strip()
        name = (r.get('agency_name') or '').strip()
        if yr and yr.isdigit() and name not in seen_names:
            seen_names.add(name)
            agencies_with_year.append({
                'name': name, 'level': r.get('level', ''),
                'state': r.get('state', ''), 'year': int(yr),
            })
    agencies_with_year.sort(key=lambda x: x['year'])
    agency_timeline = {
        'oldest': agencies_with_year[:10],
        'newest': list(reversed(agencies_with_year[-5:])),
    }

    stats = {
        'total_nodes': len(pub) + len(priv) + len(gov),
        'public': {
            'total': len(pub), 'rated': pub_rated, 'rated_pct': pct(pub_rated, len(pub)),
            'websites': pub_web, 'web_pct': pct(pub_web, len(pub)),
            'emails': pub_email, 'email_pct': pct(pub_email, len(pub)),
            'social': pub_social, 'social_pct': pct(pub_social, len(pub)),
            'demographics': pub_demo, 'demo_pct': pct(pub_demo, len(pub)),
        },
        'private': {
            'total': len(priv), 'rated': priv_rated, 'rated_pct': pct(priv_rated, len(priv)),
            'websites': priv_web, 'web_pct': pct(priv_web, len(priv)),
        },
        'gov': {
            'total': len(gov), 'live': gov_live, 'live_pct': pct(gov_live, len(gov)),
            'tiers': tier_stats,
        },
        'hours': len(data['hours']),
        'services': len(data['services']),
        'gov_services': len(data['gov_services']),
        'states': state_stats,
        'top_rated': top_rated,
        'services_breakdown': services_breakdown,
        'state_ranking': state_ranking,
        'funding': funding_stats,
        'demographics': demo_stats,
        'infrastructure': infra_stats,
        'biggest_libraries': biggest_libraries,
        'books_per_capita': books_per_capita,
        'funding_sources': funding_sources,
        'poverty_stats': poverty_stats,
        'gov_tech': gov_tech,
        'agency_timeline': agency_timeline,
    }

    # ---- PLS operational aggregates ----
    def _agg(col):
        vals = []
        for r in pub:
            v = (r.get(col) or '').strip()
            if v:
                try:
                    vals.append(float(v))
                except (ValueError, TypeError):
                    pass
        return {'total': int(sum(vals)) if vals else 0,
                'avg': round(sum(vals) / len(vals)) if vals else 0,
                'count': len(vals)} if vals else None

    pls_ops = {}
    for col, label in [('annual_visits','visits'), ('total_circulation','circulation'),
                       ('ecirculation','ecirc'), ('pcirculation','pcir'),
                       ('total_programs','programs'), ('program_attendance','attendance'),
                       ('wifi_sessions','wifi'), ('internet_terminals','terminals'),
                       ('registered_borrowers','borrowers'),
                       ('ill_to','ill_to'), ('ill_from','ill_from'),
                       ('total_staff','staff'), ('librarian_staff','librarians'),
                       ('branch_count','branches'), ('bookmobiles','bookmobiles')]:
        a = _agg(col)
        if a:
            pls_ops[label] = a
    stats['pls_operations'] = pls_ops

    # ---- Extended ACS demographics aggregates ----
    acs_ext = {}
    for col, label in [('pct_bachelors_plus','bachelors'), ('pct_computer_household','computer'),
                       ('pct_internet_household','internet'), ('pct_non_english_home','non_english')]:
        a = _agg(col)
        if a:
            acs_ext[label] = {'avg': round(a['avg'], 1), 'count': a['count']}
    stats['acs_extended'] = acs_ext

    # ---- Broadband access aggregates ----
    def _avg_pct(col):
        vals = []
        for r in pub:
            v = (r.get(col) or '').strip()
            if v:
                try: vals.append(float(v))
                except (ValueError, TypeError): pass
        return {'avg': round(sum(vals)/len(vals), 1) if vals else 0,
                'count': len(vals)} if vals else None

    broadband_stats = {}
    for col, label in [('pct_broadband_subscriber','broadband'),
                       ('pct_fixed_broadband','fixed'),
                       ('pct_cellular_broadband','cellular'),
                       ('pct_no_internet','no_internet'),
                       ('pct_no_computer','no_computer'),
                       ('pct_dialup_only','dialup'),
                       ('pct_low_income_no_internet','li_no_internet')]:
        a = _avg_pct(col)
        if a:
            broadband_stats[label] = a
    stats['broadband'] = broadband_stats

    # ---- Worst digital divide (low-income / overall no-internet ratio) ----
    by_divide = []
    for r in pub:
        d = (r.get('broadband_digital_divide') or '').strip()
        if d:
            try:
                ratio = float(d)
                ni = (r.get('pct_no_internet') or '').strip()
                li = (r.get('pct_low_income_no_internet') or '').strip()
                if ratio > 0:
                    by_divide.append({'name': r.get('name',''), 'city': r.get('city',''),
                                      'state': r.get('state',''), 'divide': ratio,
                                      'no_internet': float(ni) if ni else 0,
                                      'li_no_internet': float(li) if li else 0})
            except (ValueError, TypeError):
                pass
    by_divide.sort(key=lambda x: -x['divide'])
    stats['worst_digital_divide'] = by_divide[:10]

    # ---- Lowest broadband access communities ----
    by_low_bb = []
    for r in pub:
        bb = (r.get('pct_broadband_subscriber') or '').strip()
        if bb:
            try:
                val = float(bb)
                if val < 50:  # Under 50% broadband — genuinely underserved
                    by_low_bb.append({'name': r.get('name',''), 'city': r.get('city',''),
                                      'state': r.get('state',''), 'broadband': val,
                                      'no_internet': float((r.get('pct_no_internet') or '0').strip() or 0),
                                      'no_computer': float((r.get('pct_no_computer') or '0').strip() or 0)})
            except (ValueError, TypeError):
                pass
    by_low_bb.sort(key=lambda x: x['broadband'])
    stats['lowest_broadband'] = by_low_bb[:10]

    # ---- FCC broadband infrastructure availability ----
    fcc_gig_vals = []
    fcc_fiber_vals = []
    fcc_rural_vals = []
    for r in pub:
        for col, bucket in [('fcc_gigabit_avail', fcc_gig_vals),
                           ('fcc_fiber_avail', fcc_fiber_vals),
                           ('fcc_rural_pct', fcc_rural_vals)]:
            v = (r.get(col) or '').strip()
            if v:
                try: bucket.append(float(v))
                except (ValueError, TypeError): pass
    stats['fcc_broadband'] = {
        'gigabit_avg': round(sum(fcc_gig_vals)/len(fcc_gig_vals), 1) if fcc_gig_vals else 0,
        'fiber_avg': round(sum(fcc_fiber_vals)/len(fcc_fiber_vals), 1) if fcc_fiber_vals else 0,
        'rural_avg': round(sum(fcc_rural_vals)/len(fcc_rural_vals), 1) if fcc_rural_vals else 0,
        'count': len(fcc_gig_vals),
    }

    # ---- Communities with worst gigabit infrastructure ----
    by_low_gig = []
    for r in pub:
        g = (r.get('fcc_gigabit_avail') or '').strip()
        if g:
            try:
                val = float(g)
                if val < 25:  # Under 25% gigabit availability
                    fiber = (r.get('fcc_fiber_avail') or '0').strip()
                    rural = (r.get('fcc_rural_pct') or '').strip()
                    by_low_gig.append({'name': r.get('name',''), 'city': r.get('city',''),
                                       'state': r.get('state',''), 'gigabit': val,
                                       'fiber': float(fiber) if fiber else 0,
                                       'rural': float(rural) if rural else 0})
            except (ValueError, TypeError):
                pass
    by_low_gig.sort(key=lambda x: x['gigabit'])
    stats['lowest_gigabit'] = by_low_gig[:10]

    # ---- FCC Census Place (town-level) broadband availability ----
    # This is the most precise per-library broadband figure — matched by city+state to
    # the FCC National Broadband Map's Census Place granularity.
    pgig_vals, p100_vals, p25_vals, pfib_vals = [], [], [], []
    for r in pub:
        for col, bucket in [('fcc_place_gigabit', pgig_vals),
                           ('fcc_place_100_20', p100_vals),
                           ('fcc_place_25_3', p25_vals),
                           ('fcc_place_fiber', pfib_vals)]:
            v = (r.get(col) or '').strip()
            if v:
                try: bucket.append(float(v))
                except (ValueError, TypeError): pass
    stats['fcc_place'] = {
        'gigabit_avg': round(sum(pgig_vals)/len(pgig_vals), 1) if pgig_vals else 0,
        'bb100_avg': round(sum(p100_vals)/len(p100_vals), 1) if p100_vals else 0,
        'bb25_avg': round(sum(p25_vals)/len(p25_vals), 1) if p25_vals else 0,
        'fiber_avg': round(sum(pfib_vals)/len(pfib_vals), 1) if pfib_vals else 0,
        'count': len(pgig_vals),
        'under25_gigabit': sum(1 for v in pgig_vals if v < 25),
        'under25_100': sum(1 for v in p100_vals if v < 25),
        'no_fiber': sum(1 for v in pfib_vals if v < 5),
    }

    # ---- Library towns with worst gigabit availability (Census Place level) ----
    # Town-level is more accurate than county for identifying underserved library communities.
    place_low_gig = []
    for r in pub:
        g = (r.get('fcc_place_gigabit') or '').strip()
        if g:
            try:
                val = float(g)
                if val < 25:
                    fiber = (r.get('fcc_place_fiber') or '0').strip()
                    locs = (r.get('fcc_place_locations') or '').strip()
                    place_low_gig.append({
                        'name': r.get('name',''), 'city': r.get('city',''),
                        'state': r.get('state',''), 'gigabit': val,
                        'fiber': float(fiber) if fiber else 0,
                        'locations': int(float(locs)) if locs else 0,
                    })
            except (ValueError, TypeError):
                pass
    place_low_gig.sort(key=lambda x: x['gigabit'])
    stats['lowest_place_gigabit'] = place_low_gig[:15]

    # ---- Top libraries by annual visits ----
    by_visits = []
    for r in pub:
        v = (r.get('annual_visits') or '').strip()
        if v:
            try:
                by_visits.append({'name': r.get('name',''), 'city': r.get('city',''),
                                  'state': r.get('state',''), 'visits': int(float(v))})
            except (ValueError, TypeError):
                pass
    by_visits.sort(key=lambda x: -x['visits'])
    stats['most_visited'] = by_visits[:10]

    # ---- Top libraries by circulation ----
    by_circ = []
    for r in pub:
        v = (r.get('total_circulation') or '').strip()
        if v:
            try:
                by_circ.append({'name': r.get('name',''), 'city': r.get('city',''),
                                'state': r.get('state',''), 'circulation': int(float(v))})
            except (ValueError, TypeError):
                pass
    by_circ.sort(key=lambda x: -x['circulation'])
    stats['most_circulated'] = by_circ[:10]

    stats['generated'] = now_str()

    # ---- State Library Agencies (SLAA FY2024) ----
    slaa = data.get('slaa', [])
    slaa_by_state = {}
    slaa_budget_vals = []
    slaa_staff_vals = []
    slaa_lsta_vals = []
    slaa_exp_vals = []
    slaa_aid_vals = []
    for r in slaa:
        st = (r.get('state') or '').strip().upper()
        if st:
            slaa_by_state[st] = r
        for col, bucket in [('budget_total', slaa_budget_vals), ('staff_total', slaa_staff_vals),
                           ('budget_federal_lsta', slaa_lsta_vals),
                           ('expenditures_total', slaa_exp_vals),
                           ('expenditures_aid_to_libraries', slaa_aid_vals)]:
            v = (r.get(col) or '').strip()
            if v:
                try: bucket.append(float(v))
                except (ValueError, TypeError): pass
    # Total population served by all SLAA agencies
    slaa_pop_vals = []
    for r in slaa:
        v = (r.get('population_served') or '').strip()
        if v:
            try: slaa_pop_vals.append(float(v))
            except (ValueError, TypeError): pass
    total_pop = sum(slaa_pop_vals) if slaa_pop_vals else 1
    total_budget = sum(slaa_budget_vals) if slaa_budget_vals else 0
    stats['slaa'] = {
        'agencies': len(slaa),
        'total_budget': int(total_budget),
        'total_lsta': int(sum(slaa_lsta_vals)) if slaa_lsta_vals else 0,
        'total_staff': round(sum(slaa_staff_vals)) if slaa_staff_vals else 0,
        'total_expenditures': int(sum(slaa_exp_vals)) if slaa_exp_vals else 0,
        'total_aid': int(sum(slaa_aid_vals)) if slaa_aid_vals else 0,
        'avg_budget': int(total_budget / len(slaa_budget_vals)) if slaa_budget_vals else 0,
        'per_capita': round(total_budget / total_pop, 2) if total_pop > 1 else 0,
        'with_website': sum(1 for r in slaa if (r.get('website') or '').strip()),
        'with_archive': sum(1 for r in slaa if (r.get('has_state_archive') or '') == 'yes'),
        'with_museum': sum(1 for r in slaa if (r.get('has_state_museum') or '') == 'yes'),
        'independent': sum(1 for r in slaa if (r.get('is_independent_agency') or '') == 'yes'),
        'population_served': int(total_pop),
    }
    stats['slaa_by_state'] = slaa_by_state

    # ---- SLAA Historical Trends (FY2018-FY2024) ----
    slaa_nat = data.get('slaa_national', [])
    if slaa_nat:
        slaa_trend_years = sorted([int(r.get('year', 0) or 0) for r in slaa_nat if r.get('year')])
        slaa_trend_budget = [(r.get('year',''), r.get('income_total','')) for r in sorted(slaa_nat, key=lambda x: int(x.get('year',0) or 0))]
        slaa_trend_staff = [(r.get('year',''), r.get('staff_fte','')) for r in sorted(slaa_nat, key=lambda x: int(x.get('year',0) or 0))]
        slaa_trend_expenditures = [(r.get('year',''), r.get('expenditures_total','')) for r in sorted(slaa_nat, key=lambda x: int(x.get('year',0) or 0))]
        slaa_trend_aid = [(r.get('year',''), r.get('aid_to_libraries','')) for r in sorted(slaa_nat, key=lambda x: int(x.get('year',0) or 0))]
        slaa_trend_lsta = [(r.get('year',''), r.get('lsta_income','')) for r in sorted(slaa_nat, key=lambda x: int(x.get('year',0) or 0))]
        stats['slaa_trends'] = {
            'trend_years': slaa_trend_years,
            'trend_budget': slaa_trend_budget,
            'trend_staff': slaa_trend_staff,
            'trend_expenditures': slaa_trend_expenditures,
            'trend_aid': slaa_trend_aid,
            'trend_lsta': slaa_trend_lsta,
        }

    # ---- Federal Depository Libraries (GPO FDLP) ----
    fdlp = data.get('fdlp', [])
    fdlp_by_state = {}
    fdlp_regional = []
    for r in fdlp:
        st = (r.get('state', '') or '').strip().upper()
        if st:
            fdlp_by_state[st] = fdlp_by_state.get(st, 0) + 1
        dtype = (r.get('depository_type', '') or '').strip()
        if dtype == 'Regional':
            fdlp_regional.append({
                'name': r.get('library_name', ''),
                'state': st, 'parent': r.get('parent_institution', ''),
                'type': r.get('library_type', ''),
            })
    fdlp_regional.sort(key=lambda r: (r['state'], r['name']))
    # Largest depository libraries by number of titles selected
    fdlp_largest = []
    for r in fdlp:
        tc = (r.get('pdt_titles_count', '') or '').strip()
        if tc:
            try:
                fdlp_largest.append({
                    'name': r.get('library_name', ''),
                    'state': (r.get('state', '') or '').strip().upper(),
                    'parent': r.get('parent_institution', ''),
                    'dtype': r.get('depository_type', ''),
                    'titles': int(tc),
                })
            except (ValueError, TypeError):
                pass
    fdlp_largest.sort(key=lambda x: -x['titles'])
    stats['fdlp'] = {
        'total': len(fdlp),
        'regional': sum(1 for r in fdlp if (r.get('depository_type', '') or '').strip() == 'Regional'),
        'selective': sum(1 for r in fdlp if (r.get('depository_type', '') or '').strip() == 'Selective'),
        'preservation_stewards': sum(1 for r in fdlp if (r.get('preservation_steward', '') or '').strip().lower() == 'yes'),
        'by_state': fdlp_by_state,
        'regional_list': fdlp_regional,
        'largest': fdlp_largest[:15],
    }

    # ---- Academic Library Survey (NCES ALS 2000-2012 + IPEDS 2023) ----
    acad = data.get('academic', [])
    acad_2023 = data.get('academic_2023', [])
    als_nat = data.get('als_national', [])
    als_st = data.get('als_by_state', [])

    # 2023 national aggregates (e-books, e-serials, ILL — new in IPEDS)
    ebooks_total = 0; eserials_total = 0; edatabase_total = 0
    ill_provided_total = 0; ill_received_total = 0; tcirc_total = 0
    pbooks_total = 0; coll23_total = 0; exp23_total = 0; staff23_total = 0
    for r in acad_2023:
        def _safe_int(col):
            v = (r.get(col) or '').strip()
            try: return int(float(v)) if v else 0
            except (ValueError, TypeError): return 0
        ebooks_total += _safe_int('ebooks')
        eserials_total += _safe_int('eserials')
        edatabase_total += _safe_int('edatabase')
        ill_provided_total += _safe_int('ill_provided')
        ill_received_total += _safe_int('ill_received')
        tcirc_total += _safe_int('tcirc')
        pbooks_total += _safe_int('pbooks')
        coll23_total += _safe_int('colbksa')
        exp23_total += _safe_int('extot')
        staff23_total += _safe_int('sttot')

    stats['academic'] = {
        'institutions_2012': len(acad),
        'institutions_2023': len(acad_2023),
        'trend_years': [int(r.get('year', 0)) for r in als_nat if r.get('year')],
        'trend_institutions': [int(r.get('institutions', 0) or 0) for r in als_nat],
        'trend_staff_fte': [int(r.get('staff_total_fte_total', 0) or 0) for r in als_nat],
        'trend_expenditures': [int(r.get('expend_total', 0) or 0) for r in als_nat],
        'trend_collections': [int(r.get('collection_books_total', 0) or 0) for r in als_nat],
        'trend_presentations': [int(r.get('presentations_total', 0) or 0) for r in als_nat],
        'trend_salaries': [int(r.get('salaries_total', 0) or 0) for r in als_nat],
        'trend_student_fte': [int(r.get('student_fte_total', 0) or 0) for r in als_nat],
        # 2023 IPEDS-only metrics
        'ebooks_2023': ebooks_total,
        'eserials_2023': eserials_total,
        'edatabase_2023': edatabase_total,
        'ill_provided_2023': ill_provided_total,
        'ill_received_2023': ill_received_total,
        'tcirc_2023': tcirc_total,
        'pbooks_2023': pbooks_total,
        'collection_2023': coll23_total,
        'expenditures_2023': exp23_total,
        'staff_2023': staff23_total,
    }
    # Largest academic libraries by collection — use 2023 data if available, else 2012
    by_coll = []
    # Prefer 2023 collection data (includes e-resources)
    for r in acad_2023:
        v = (r.get('colbksa') or '').strip()
        if v:
            try:
                extot_v = (r.get('extot') or '').strip()
                sttot_v = (r.get('sttot') or '').strip()
                by_coll.append({'name': r.get('name',''), 'city': r.get('city',''),
                                'state': r.get('state',''), 'collection': int(float(v)),
                                'expenditure': int(float(extot_v)) if extot_v else 0,
                                'staff_fte': int(float(sttot_v)) if sttot_v else 0,
                                'year': 2023})
            except (ValueError, TypeError):
                pass
    # Fall back to 2012 for institutions not in 2023
    unitids_2023 = set((r.get('unitid') or '').strip() for r in acad_2023)
    for r in acad:
        uid = (r.get('unitid') or '').strip()
        if uid in unitids_2023:
            continue
        v = (r.get('colbksa') or '').strip()
        if v:
            try:
                by_coll.append({'name': r.get('name',''), 'city': r.get('city',''),
                                'state': r.get('state',''), 'collection': int(float(v)),
                                'expenditure': int(float(r.get('extot', 0) or 0)) if r.get('extot') else 0,
                                'staff_fte': int(float(r.get('sttot', 0) or 0)) if r.get('sttot') else 0,
                                'year': 2012})
            except (ValueError, TypeError):
                pass
    by_coll.sort(key=lambda x: -x['collection'])
    stats['academic_largest'] = by_coll[:15]
    # Largest by expenditure
    by_exp = sorted([x for x in by_coll if x['expenditure']], key=lambda x: -x['expenditure'])
    stats['academic_largest_exp'] = by_exp[:15]
    # State-level aggregates — use 2023 where available, fall back to 2012
    als_by_state_latest = {}
    for r in als_st:
        if (r.get('year', '') or '').strip() == '2023':
            st = (r.get('state', '') or '').strip()
            if st:
                als_by_state_latest[st] = {
                    'institutions': int(r.get('institutions', 0) or 0),
                    'staff_fte': int(r.get('staff_total_fte_total', 0) or 0),
                    'expenditures': int(r.get('expend_total', 0) or 0),
                    'collections': int(r.get('collection_books_total', 0) or 0),
                    'presentations': int(r.get('presentations_total', 0) or 0),
                    'salaries': int(r.get('salaries_total', 0) or 0),
                    'student_fte': int(r.get('student_fte_total', 0) or 0),
                    'year': 2023,
                }
    # Fill in states that don't have 2023 data with 2012
    for r in als_st:
        if (r.get('year', '') or '').strip() == '2012':
            st = (r.get('state', '') or '').strip()
            if st and st not in als_by_state_latest:
                als_by_state_latest[st] = {
                    'institutions': int(r.get('institutions', 0) or 0),
                    'staff_fte': int(r.get('staff_total_fte_total', 0) or 0),
                    'expenditures': int(r.get('expend_total', 0) or 0),
                    'collections': int(r.get('collection_books_total', 0) or 0),
                    'presentations': int(r.get('presentations_total', 0) or 0),
                    'salaries': int(r.get('salaries_total', 0) or 0),
                    'student_fte': int(r.get('student_fte_total', 0) or 0),
                    'year': 2012,
                }
    stats['academic_by_state_2012'] = als_by_state_latest

    # ---- Public Library Historical Trends (IMLS PLS 2000-2024) ----
    pls_nat = data.get('pls_national', [])
    pls_st = data.get('pls_by_state', [])
    stats['pls_trends'] = {
        'trend_years': [int(r.get('year', 0)) for r in pls_nat if r.get('year')],
        'trend_systems': [int(r.get('systems', 0) or 0) for r in pls_nat],
        'trend_population': [int(r.get('popu_lsa_total', 0) or 0) for r in pls_nat],
        'trend_staff_fte': [int(r.get('totstaff_total', 0) or 0) for r in pls_nat],
        'trend_visits': [int(r.get('visits_total', 0) or 0) for r in pls_nat],
        'trend_circulation': [int(r.get('totcir_total', 0) or 0) for r in pls_nat],
        'trend_expenditures': [int(r.get('totexpco_total', 0) or 0) for r in pls_nat],
        'trend_book_volumes': [int(r.get('bkvol_total', 0) or 0) for r in pls_nat],
        'trend_capital_exp': [int(r.get('capital_total', 0) or 0) for r in pls_nat],
        'trend_elmat_exp': [int(r.get('elmatexp_total', 0) or 0) for r in pls_nat],
        'trend_outlets': [int(r.get('centlib_total', 0) or 0) + int(r.get('branlib_total', 0) or 0) + int(r.get('bkmob_total', 0) or 0) for r in pls_nat],
        'trend_librarian_fte': [int(r.get('libraria_total', 0) or 0) for r in pls_nat],
        'trend_children_attendance': [int(r.get('kidatten_total', 0) or 0) for r in pls_nat],
        'trend_children_circ': [int(r.get('kidcircl_total', 0) or 0) for r in pls_nat],
        'trend_reference': [int(r.get('referenc_total', 0) or 0) for r in pls_nat],
        'trend_ill_to': [int(r.get('loanto_total', 0) or 0) for r in pls_nat],
        'trend_ill_from': [int(r.get('loanfm_total', 0) or 0) for r in pls_nat],
    }
    # PLS state-level latest (FY2024) for state pages
    pls_latest_by_state = {}
    for r in pls_st:
        if (r.get('year', '') or '').strip() == '2024':
            st = (r.get('state', '') or '').strip()
            if st:
                pls_latest_by_state[st] = {
                    'systems': int(r.get('systems', 0) or 0),
                    'population': int(r.get('popu_lsa_total', 0) or 0),
                    'staff_fte': int(r.get('totstaff_total', 0) or 0),
                    'visits': int(r.get('visits_total', 0) or 0),
                    'circulation': int(r.get('totcir_total', 0) or 0),
                    'expenditures': int(r.get('totexpco_total', 0) or 0),
                }
    stats['pls_by_state_latest'] = pls_latest_by_state

    # ---- IPEDS institutional characteristics (Carnegie, control, HBCU, tribal, etc.) ----
    cs = data.get('carnegie_summary', {})
    stats['institution_characteristics'] = cs if cs else {}

    # ---- PLS FY2024 Digital Services & Programs ----
    stats['pls_digital'] = data.get('pls_fy2024_digital', {})

    # ---- SLAA State Agency Services (summer reading, literacy, digitization, accessibility) ----
    stats['slaa_services'] = data.get('slaa_services', {})

    # ---- Book Censorship Database (EveryLibrary Institute / Magnusson) ----
    stats['book_censorship'] = data.get('book_censorship', {})

    # ---- NTIA Tribal Broadband Connectivity Program (TBCP) ----
    stats['tribal_broadband'] = data.get('tribal_broadband', {})

    # ---- USAC Emergency Connectivity Fund (ECF) ----
    stats['ecf'] = data.get('ecf', {})

    # ---- BLS Librarian Salaries (OES May 2024) ----
    stats['bls_salaries'] = data.get('bls_salaries', {})

    # ---- FCC Affordable Connectivity Program (ACP) ----
    stats['acp'] = data.get('acp', {})

    # ---- USAC E-Rate (library funding, FCC Form 471) ----
    stats['erate'] = data.get('erate', {})

    # ---- NTIA BEAD broadband allocations ----
    stats['bead'] = data.get('bead', {})

    # ---- Library ballot measures (EveryLibrary) ----
    stats['ballot'] = data.get('ballot', {})

    # ---- Library usage survey data (Pew Research + Gallup + NEA 2022) ----
    stats['library_usage'] = data.get('library_usage', {})

    # ---- ALA State of America's Libraries Report 2024 ----
    stats['ala_report'] = data.get('ala_report', {})

    # ---- State per-capita library rankings (PLS FY2024) ----
    stats['state_per_capita'] = data.get('state_per_capita', {})

    # ---- COVID-19 impact and recovery ----
    stats['covid_recovery'] = data.get('covid_recovery', {})

    # ---- Federal Depository Library Program (FDLP) ----
    stats['fdlp_summary'] = data.get('fdlp_summary', {})

    # ---- Library user demographics and usage patterns ----
    stats['library_demographics'] = data.get('library_demographics', {})

    # ---- State-level book censorship breakdown ----
    stats['state_censorship'] = data.get('state_censorship', {})

    # ---- Digital Public Library of America ----
    stats['dpla'] = data.get('dpla', {})

    # ---- NCES School Libraries (full state-level data) ----
    stats['nces_school_full'] = data.get('nces_school_full', {})

    # ---- USDA Rural Development library grants ----
    stats['usda_grants'] = data.get('usda_grants', {})

    # ---- NEH grants to libraries ----
    stats['neh_grants'] = data.get('neh_grants', {})

    # ---- State library funding analysis ----
    stats['state_funding'] = data.get('state_funding', {})

    # ---- Library of Congress ----
    stats['loc'] = data.get('loc', {})

    # ---- Digital libraries (HathiTrust, IA, Gutenberg, etc.) ----
    stats['digital_libraries'] = data.get('digital_libraries', {})

    # ---- IMLS library grants (all programs via USASpending) ----
    stats['imls_library_grants'] = data.get('imls_library_grants', {})

    # ---- Other federal agency grants to libraries ----
    stats['other_federal_grants'] = data.get('other_federal_grants', {})

    # ---- Federal funding totals (comprehensive) ----
    stats['federal_funding_totals'] = data.get('federal_funding_totals', {})

    # ---- National Library of Medicine ----
    stats['nlm'] = data.get('nlm', {})

    # ---- PLS Extended Metrics (bookmobiles, ILL, WiFi, etc.) ----
    stats['pls_extended'] = data.get('pls_extended', {})

    # ---- Interlibrary Loan stats ----
    stats['ill'] = data.get('ill', {})

    # ---- Library workforce demographics ----
    stats['library_workforce'] = data.get('library_workforce', {})

    # ---- Library philanthropy (Carnegie, Friends, Gates, endowments) ----
    stats['philanthropy'] = data.get('philanthropy', {})

    # ---- Circulation & library card statistics ----
    stats['circulation'] = data.get('circulation', {})

    # ---- IMLS Museum Data File ----
    stats['museums'] = data.get('museums', {})

    # ---- Prison Libraries ----
    stats['prison_libraries'] = data.get('prison_libraries', {})

    # ---- ALA-Accredited LIS Degree Programs ----
    stats['lis_programs'] = data.get('lis_programs', {})

    # ---- IMLS Grant Awards (1996-2025) ----
    gy = data.get('imls_grants_year', [])
    gs = data.get('imls_grants_state', [])
    gs_recent = data.get('imls_grants_recent_state', [])
    gp = data.get('imls_grants_program', [])
    gl = data.get('imls_grants_largest', [])
    grants_total = sum(int(r.get('total_awarded', 0) or 0) for r in gy) if gy else 0
    grants_count = sum(int(r.get('grants', 0) or 0) for r in gy) if gy else 0
    grants_years = [int(r.get('year', 0)) for r in gy if r.get('year')] if gy else []
    grants_trend_amounts = [int(r.get('total_awarded', 0) or 0) for r in gy] if gy else []
    grants_trend_counts = [int(r.get('grants', 0) or 0) for r in gy] if gy else []
    # Merge old (1996-2013) + recent (2014-2025) state data for combined totals
    state_totals = {}
    for r in gs:
        st = (r.get('state') or '').strip()
        if st:
            state_totals[st] = {'state': st, 'grants': int(r.get('grants', 0) or 0),
                                'total_awarded': int(r.get('total_awarded', 0) or 0),
                                'institutions': int(r.get('institutions', 0) or 0)}
    for r in gs_recent:
        st = (r.get('state') or '').strip()
        if st:
            if st not in state_totals:
                state_totals[st] = {'state': st, 'grants': 0, 'total_awarded': 0, 'institutions': 0}
            state_totals[st]['grants'] += int(r.get('count', 0) or 0)
            state_totals[st]['total_awarded'] += int(float(r.get('amount', 0) or 0))
    grants_top_states = sorted(state_totals.values(), key=lambda x: -x['total_awarded'])[:15] if state_totals else []
    # Top 10 programs by grant count
    grants_top_programs = sorted(gp, key=lambda r: -int(r.get('grants', 0) or 0))[:12] if gp else []
    stats['imls_grants'] = {
        'total_count': grants_count,
        'total_amount': grants_total,
        'year_range': f"{min(grants_years)}–{max(grants_years)}" if grants_years else '',
        'trend_years': grants_years,
        'trend_amounts': grants_trend_amounts,
        'trend_counts': grants_trend_counts,
        'top_states': grants_top_states,
        'top_programs': grants_top_programs,
        'largest': gl[:15] if gl else [],
    }
    # G2S (Grants to States) — formula funding
    g2s_yr = data.get('imls_g2s_year', [])
    g2s_st = data.get('imls_g2s_state', [])
    g2s_total = sum(int(float(r.get('amount', 0) or 0)) for r in g2s_yr) if g2s_yr else 0
    g2s_years = [int(r.get('year', 0)) for r in g2s_yr if r.get('year')] if g2s_yr else []
    g2s_amounts = [int(float(r.get('amount', 0) or 0)) for r in g2s_yr] if g2s_yr else []
    # Top states by total G2S amount + per-capita
    g2s_state_totals = {}
    for r in g2s_st:
        st = (r.get('state') or '').strip()
        if not st:
            continue
        if st not in g2s_state_totals:
            g2s_state_totals[st] = {'state': st, 'amount': 0, 'per_capita': 0}
        g2s_state_totals[st]['amount'] += int(float(r.get('amount', 0) or 0))
        pc = float(r.get('per_capita', 0) or 0)
        if pc > g2s_state_totals[st]['per_capita']:
            g2s_state_totals[st]['per_capita'] = pc
    g2s_top_states = sorted(g2s_state_totals.values(), key=lambda x: -x['amount'])[:15] if g2s_state_totals else []
    g2s_top_percapita = sorted([s for s in g2s_state_totals.values() if s['per_capita'] > 0], key=lambda x: -x['per_capita'])[:10] if g2s_state_totals else []
    stats['imls_g2s'] = {
        'total_amount': g2s_total,
        'year_range': f"{min(g2s_years)}–{max(g2s_years)}" if g2s_years else '',
        'trend_years': g2s_years,
        'trend_amounts': g2s_amounts,
        'top_states': g2s_top_states,
        'top_percapita': g2s_top_percapita,
    }

    # ---- Library consortia ----
    consortia = data.get('consortia', [])
    us_consortia = [c for c in consortia if 'United States' in (c.get('region','') or '') or (c.get('region','') or '').strip() == 'US']
    stats['consortia'] = {
        'total': len(consortia),
        'us_total': len(us_consortia),
        'with_website': sum(1 for c in consortia if (c.get('website','') or '').strip()),
        'sources': sorted(set((c.get('source','') or '').strip() for c in consortia)),
    }
    stats['consortia_list'] = sorted(us_consortia, key=lambda c: (c.get('consortium_name','') or '').lower())

    return stats

# ---------------------------------------------------------------------------
# Build pages
# ---------------------------------------------------------------------------
def build_index(data, stats):
    print("[build] Building index.html...")
    pub = stats['public']
    priv = stats['private']
    gov = stats['gov']

    body = f"""
<p class="contentSub">From the US Library Census Wiki</p>
<div class="wiki-sub">A living dataset of every public and private library, and every government website, in the United States.</div>

<div class="hosted-strip">
  <b>{stats['total_nodes']:,}</b> nodes mapped · {pub['total']:,} public libraries · {priv['total']:,} private libraries · {gov['total']:,} government websites · updated {stats['generated']}
</div>

<div class="mw-welcome">
  <h2>Welcome to the US Library Census</h2>
  <p>This wiki presents an automated, continuously-enriched dataset covering every known
  public library, academic/special library, and federal/state/county/city government
  website in the United States. Each record carries address, geocoordinates, website,
  funding, contact details, review ratings, hours, services, and area demographics.</p>
</div>

<div class="stats-grid">
  <div class="stat-card"><div class="num">{stats['total_nodes']:,}</div><div class="label">Total nodes</div></div>
  <div class="stat-card"><div class="num">{pub['total']:,}</div><div class="label">Public libraries</div></div>
  <div class="stat-card"><div class="num">{priv['total']:,}</div><div class="label">Private libraries</div></div>
  <div class="stat-card"><div class="num">{gov['total']:,}</div><div class="label">Gov websites</div></div>
  <div class="stat-card"><div class="num">{gov['live']:,}</div><div class="label">Gov sites live</div></div>
  <div class="stat-card"><div class="num">{pub['rated']:,}</div><div class="label">Libraries rated</div></div>
</div>

<h2 id="map">Interactive Map</h2>
<div class="map-embed">
  <iframe src="map.html" title="US Library Census Map"></iframe>
</div>
<p style="text-align:center"><a href="map.html">Open full-page map →</a></p>

<h2 id="gov">Government Website Tiers</h2>
<div class="gov-cards">"""

    tier_labels = {
        'federal':'Federal','state':'State','county':'County',
        'city':'City','tribal':'Tribal','special':'Special/Interstate'
    }
    for tier in ['federal','state','county','city','tribal','special']:
        ts = gov['tiers'].get(tier, {'total':0,'live':0,'pct':'0%'})
        body += f"""
    <div class="gov-card">
      <h3>{tier_labels[tier]}</h3>
      <div class="gov-num">{ts['total']:,}</div>
      <div class="gov-live">{ts['live']:,} live</div>
      <div class="gov-pct">{ts['pct']} verified</div>
    </div>"""

    body += f"""
</div>
<p><a href="gov.html">Government sites overview →</a></p>

<h2 id="coverage">Data Coverage</h2>
<table class="coverage-table">
  <tr><th>Dataset</th><th>Rows</th><th>Websites</th><th>Ratings</th><th>Emails</th><th>Social</th><th>Demographics</th></tr>
  <tr>
    <td><a href="search.html?type=public">Public libraries</a></td>
    <td>{pub['total']:,}</td>
    <td class="pct">{pub['web_pct']}</td>
    <td class="pct">{pub['rated_pct']}</td>
    <td class="pct">{pub['email_pct']}</td>
    <td class="pct">{pub['social_pct']}</td>
    <td class="pct">{pub['demo_pct']}</td>
  </tr>
  <tr>
    <td><a href="search.html?type=private">Private/academic</a></td>
    <td>{priv['total']:,}</td>
    <td class="pct">{priv['web_pct']}</td>
    <td class="pct">{priv['rated_pct']}</td>
    <td>—</td><td>—</td><td>—</td>
  </tr>
  <tr>
    <td><a href="search.html?type=gov">Government sites</a></td>
    <td>{gov['total']:,}</td>
    <td>100%</td>
    <td>—</td><td>—</td><td>—</td><td>—</td>
  </tr>
  <tr>
    <td>Library hours</td>
    <td>{stats['hours']:,}</td>
    <td colspan="5">3,909 sites with structured hours extracted</td>
  </tr>
  <tr>
    <td>Library services</td>
    <td>{stats['services']:,}</td>
    <td colspan="5">ebooks, printing, meeting rooms, storytime, and 16 more service keywords</td>
  </tr>
  <tr>
    <td>Gov services</td>
    <td>{stats['gov_services']:,}</td>
    <td colspan="5">680 federal/state agencies with detailed service summaries</td>
  </tr>
</table>"""

    # ---- Funding & Demographics cards ----
    fund = stats['funding']
    demo = stats['demographics']
    fund_total_str = f"${fund['total']/1e9:,.1f}B" if fund['total'] >= 1e9 else f"${fund['total']/1e6:,.0f}M"
    fund_avg_str = f"${fund['avg']/1e6:,.1f}M" if fund['avg'] >= 1e6 else f"${fund['avg']:,.0f}"
    income_str = f"${demo['avg_income']:,.0f}"

    body += f"""

<h2 id="funding">Funding &amp; Demographics</h2>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{fund_total_str}</div><div class="label">Total public-library funding</div></div>
  <div class="stat-card"><div class="num">{fund_avg_str}</div><div class="label">Average funding per library</div></div>
  <div class="stat-card"><div class="num">{fund['count']:,}</div><div class="label">Libraries with funding data</div></div>
  <div class="stat-card"><div class="num">{income_str}</div><div class="label">Avg. median household income</div></div>
  <div class="stat-card"><div class="num">{demo['income_count']:,}</div><div class="label">Areas with income data</div></div>
</div>
<p class="rsrc">Funding totals from the IMLS Public Libraries Survey (funding_total column). Demographics from Census ACS area-level estimates.</p>"""

    # ---- Library Infrastructure ----
    infra = stats['infrastructure']
    total_sqft_str = f"{infra['total_sqft']/1e6:,.0f}M" if infra['total_sqft'] >= 1e6 else f"{infra['total_sqft']:,}"
    total_coll_str = f"{infra['total_collection']/1e6:,.1f}M" if infra['total_collection'] >= 1e6 else f"{infra['total_collection']:,}"

    body += f"""

<h2 id="infrastructure">Library Infrastructure</h2>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{total_sqft_str}</div><div class="label">Total square footage</div></div>
  <div class="stat-card"><div class="num">{total_coll_str}</div><div class="label">Total collection items</div></div>
  <div class="stat-card"><div class="num">{infra['avg_sqft']:,}</div><div class="label">Avg building size (sqft)</div></div>
  <div class="stat-card"><div class="num">{infra['avg_collection']:,}</div><div class="label">Avg collection size</div></div>
</div>
<p class="rsrc">Building sizes and collection sizes from the IMLS Public Libraries Survey. Covers {infra['sqft_count']:,} libraries with sqft data and {infra['coll_count']:,} with collection data.</p>

<h2 id="biggest">Biggest Libraries by Building Size</h2>
<table class="wikitable biggest-table">
  <tr><th>#</th><th>Library</th><th>City</th><th>State</th><th>Sqft</th><th>Collection</th></tr>"""

    for i, lib in enumerate(stats['biggest_libraries'], 1):
        coll_str = f"{int(lib['collection']):,}" if lib['collection'] else '—'
        body += f"""
  <tr>
    <td>{i}</td>
    <td><a href="search.html?q={esc(lib["name"])}">{esc(lib["name"])}</a></td>
    <td>{esc(lib["city"]) or "—"}</td>
    <td>{esc(lib["state"]) or "—"}</td>
    <td class="pct">{lib["sqft"]:,}</td>
    <td>{coll_str}</td>
  </tr>"""

    body += f"""
</table>

<h2 id="bpc">Books Per Capita — Most Books Per Person</h2>
<p class="wiki-sub">Communities where the public library has the most books relative to population served. A novel metric: collection size ÷ population served (minimum 1,000 population).</p>
<table class="wikitable bpc-table">
  <tr><th>#</th><th>Library</th><th>City</th><th>State</th><th>Collection</th><th>Population</th><th>Books/Capita</th></tr>"""

    for i, lib in enumerate(stats['books_per_capita'], 1):
        body += f"""
  <tr>
    <td>{i}</td>
    <td><a href="search.html?q={esc(lib["name"])}">{esc(lib["name"])}</a></td>
    <td>{esc(lib["city"]) or "—"}</td>
    <td>{esc(lib["state"]) or "—"}</td>
    <td>{lib["collection"]:,}</td>
    <td>{lib["population"]:,}</td>
    <td class="pct">{lib["ratio"]:.1f}</td>
  </tr>"""

    body += f"""
</table>

<h2 id="funding-sources">Funding Sources</h2>
<p class="wiki-sub">Where public library funding comes from: local, state, and federal dollars.</p>
<div class="funding-bars">"""

    max_fund = max((s['total'] for s in stats['funding_sources']), default=1) or 1
    for src in stats['funding_sources']:
        fund_str = f"${src['total']/1e9:,.1f}B" if src['total'] >= 1e9 else f"${src['total']/1e6:,.0f}M"
        pct_w = (src['total'] / max_fund) * 100
        body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(src["source"])}</span>
    <span class="svc-bar"><span class="svc-fill" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{fund_str} ({src["pct"]})</span>
  </div>"""

    # Poverty stats
    pov = stats['poverty_stats']
    body += f"""
</div>

<h2 id="poverty">Poverty & Age Demographics</h2>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{pov["avg"]:.1f}%</div><div class="label">Avg poverty rate</div></div>
  <div class="stat-card"><div class="num">{pov["min"]:.1f}%</div><div class="label">Lowest poverty rate</div></div>
  <div class="stat-card"><div class="num">{pov["max"]:.1f}%</div><div class="label">Highest poverty rate</div></div>
  <div class="stat-card"><div class="num">{pov["high_poverty"]:,}</div><div class="label">Libraries in high-poverty areas (>30%)</div></div>
  <div class="stat-card"><div class="num">{pov["count"]:,}</div><div class="label">Areas with poverty data</div></div>
</div>
<p class="rsrc">Poverty rates from Census ACS (pct_below_poverty column). {pov["high_poverty"]:,} libraries serve communities where over 30% of residents live below the poverty line.</p>

<h2 id="operations">Library Operations — National Scale</h2>"""

    ops = stats.get('pls_operations', {})
    if ops:
        def _fmt_total(key, suffix=''):
            d = ops.get(key)
            if not d: return '—'
            v = d['total']
            if v >= 1e9: return f"{v/1e9:.1f}B{suffix}"
            if v >= 1e6: return f"{v/1e6:.1f}M{suffix}"
            if v >= 1e3: return f"{v/1e3:.1f}K{suffix}"
            return f"{v:,}{suffix}"

        body += f"""
<div class="stats-grid">
  <div class="stat-card"><div class="num">{_fmt_total('visits')}</div><div class="label">Annual visits</div></div>
  <div class="stat-card"><div class="num">{_fmt_total('circulation')}</div><div class="label">Items circulated/yr</div></div>
  <div class="stat-card"><div class="num">{_fmt_total('ecirc')}</div><div class="label">E-material circulation</div></div>
  <div class="stat-card"><div class="num">{_fmt_total('pcir')}</div><div class="label">Physical circulation</div></div>
  <div class="stat-card"><div class="num">{_fmt_total('attendance')}</div><div class="label">Program attendance</div></div>
  <div class="stat-card"><div class="num">{_fmt_total('programs')}</div><div class="label">Programs offered</div></div>
  <div class="stat-card"><div class="num">{_fmt_total('wifi')}</div><div class="label">WiFi sessions</div></div>
  <div class="stat-card"><div class="num">{_fmt_total('borrowers')}</div><div class="label">Registered borrowers</div></div>
  <div class="stat-card"><div class="num">{_fmt_total('ill_to')}</div><div class="label">ILL — loaned out</div></div>
  <div class="stat-card"><div class="num">{_fmt_total('ill_from')}</div><div class="label">ILL — borrowed in</div></div>
  <div class="stat-card"><div class="num">{_fmt_total('branches')}</div><div class="label">Branch libraries</div></div>
  <div class="stat-card"><div class="num">{_fmt_total('bookmobiles')}</div><div class="label">Bookmobiles</div></div>
</div>
<p class="rsrc">Operational data from IMLS Public Libraries Survey FY2024 (AE/system level). Averages are per library system. Totals are national sums across {ops.get('visits',{}).get('count','—'):,} reporting systems.</p>"""

    # Most visited libraries
    most_vis = stats.get('most_visited', [])
    if most_vis:
        body += """
<h2 id="most-visited">Most-Visited Libraries</h2>
<table class="wikitable biggest-table">
  <tr><th>#</th><th>Library</th><th>City</th><th>State</th><th>Annual Visits</th></tr>"""
        for i, lib in enumerate(most_vis, 1):
            body += f"""
  <tr><td>{i}</td><td>{esc(lib['name'])}</td><td>{esc(lib['city']) or '—'}</td><td>{esc(lib['state'])}</td><td>{lib['visits']:,}</td></tr>"""
        body += "</table>"

    # Most circulated
    most_circ = stats.get('most_circulated', [])
    if most_circ:
        body += """
<h2 id="most-circulated">Most-Active Libraries by Circulation</h2>
<table class="wikitable biggest-table">
  <tr><th>#</th><th>Library</th><th>City</th><th>State</th><th>Annual Circulation</th></tr>"""
        for i, lib in enumerate(most_circ, 1):
            body += f"""
  <tr><td>{i}</td><td>{esc(lib['name'])}</td><td>{esc(lib['city']) or '—'}</td><td>{esc(lib['state'])}</td><td>{lib['circulation']:,}</td></tr>"""
        body += "</table>"

    # Extended ACS demographics
    acs_ext = stats.get('acs_extended', {})
    if acs_ext:
        body += f"""
<h2 id="community-context">Community Context — Education, Technology & Language</h2>
<div class="stats-grid">"""
        if 'bachelors' in acs_ext:
            body += f'<div class="stat-card"><div class="num">{acs_ext["bachelors"]["avg"]:.1f}%</div><div class="label">Avg bachelor\'s+ (25+)</div></div>'
        if 'computer' in acs_ext:
            body += f'<div class="stat-card"><div class="num">{acs_ext["computer"]["avg"]:.1f}%</div><div class="label">Homes with a computer</div></div>'
        if 'internet' in acs_ext:
            body += f'<div class="stat-card"><div class="num">{acs_ext["internet"]["avg"]:.1f}%</div><div class="label">Homes with internet</div></div>'
        if 'non_english' in acs_ext:
            body += f'<div class="stat-card"><div class="num">{acs_ext["non_english"]["avg"]:.1f}%</div><div class="label">Non-English at home</div></div>'
        body += """</div>
<p class="rsrc">Extended demographics from Census ACS 2023 5-year estimates (county-level for education/computer/internet, state-level for language).</p>"""

    # ---- Community Broadband Access ----
    bb = stats.get('broadband', {})
    if bb:
        body += f"""
<h2 id="broadband">Community Broadband Access</h2>
<p class="wiki-sub">How connected are the communities that libraries serve? Broadband subscription rates, digital divide metrics, and the communities most in need of library internet access — from Census ACS 2023 5-year estimates (B28003, B28004, B28008).</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{bb.get('broadband',{}).get('avg',0):.1f}%</div><div class="label">Avg broadband subscription</div></div>
  <div class="stat-card"><div class="num">{bb.get('fixed',{}).get('avg',0):.1f}%</div><div class="label">Avg fixed broadband</div></div>
  <div class="stat-card"><div class="num">{bb.get('cellular',{}).get('avg',0):.1f}%</div><div class="label">Avg cellular data plan</div></div>
  <div class="stat-card"><div class="num">{bb.get('no_internet',{}).get('avg',0):.1f}%</div><div class="label">Avg no internet at home</div></div>
  <div class="stat-card"><div class="num">{bb.get('no_computer',{}).get('avg',0):.1f}%</div><div class="label">Avg no computer at home</div></div>
  <div class="stat-card"><div class="num">{bb.get('dialup',{}).get('avg',0):.1f}%</div><div class="label">Avg dial-up only</div></div>
  <div class="stat-card"><div class="num">{bb.get('li_no_internet',{}).get('avg',0):.1f}%</div><div class="label">Low-income no internet</div></div>
  <div class="stat-card"><div class="num">{bb.get('broadband',{}).get('count',0):,}</div><div class="label">Communities with data</div></div>
</div>
<p class="rsrc">The digital divide: low-income households (under $10K/yr) are far less likely to have internet. Across reporting communities, {bb.get('li_no_internet',{}).get('avg',0):.1f}% of low-income households lack internet vs {bb.get('no_internet',{}).get('avg',0):.1f}% overall. Libraries bridge this gap with public WiFi and computer terminals.</p>"""

        # Worst digital divide table
        worst_div = stats.get('worst_digital_divide', [])
        if worst_div:
            body += """
<h3>Worst Digital Divide — Communities Where Libraries Are Most Critical</h3>
<p class="wiki-sub">Communities where the gap between low-income and overall internet access is largest. A divide ratio of 5.0× means low-income households are 5 times more likely to lack internet than the general population.</p>
<table class="wikitable biggest-table">
  <tr><th>#</th><th>Library</th><th>City</th><th>State</th><th>Divide Ratio</th><th>No Internet (overall)</th><th>No Internet (low-income)</th></tr>"""
            for i, lib in enumerate(worst_div, 1):
                body += f"""
  <tr>
    <td>{i}</td>
    <td><a href="search.html?q={esc(lib["name"])}">{esc(lib["name"])}</a></td>
    <td>{esc(lib["city"]) or "—"}</td>
    <td>{esc(lib["state"]) or "—"}</td>
    <td class="pct">{lib["divide"]:.1f}×</td>
    <td>{lib["no_internet"]:.1f}%</td>
    <td>{lib["li_no_internet"]:.1f}%</td>
  </tr>"""
            body += "</table>"

        # Lowest broadband access table
        low_bb = stats.get('lowest_broadband', [])
        if low_bb:
            body += """
<h3>Lowest Broadband Access — America's Least-Connected Communities</h3>
<p class="wiki-sub">Public libraries serving communities where fewer than half of households have broadband internet. These libraries are often the only source of free internet access.</p>
<table class="wikitable biggest-table">
  <tr><th>#</th><th>Library</th><th>City</th><th>State</th><th>Broadband %</th><th>No Internet</th><th>No Computer</th></tr>"""
            for i, lib in enumerate(low_bb, 1):
                body += f"""
  <tr>
    <td>{i}</td>
    <td><a href="search.html?q={esc(lib["name"])}">{esc(lib["name"])}</a></td>
    <td>{esc(lib["city"]) or "—"}</td>
    <td>{esc(lib["state"]) or "—"}</td>
    <td class="pct">{lib["broadband"]:.1f}%</td>
    <td>{lib["no_internet"]:.1f}%</td>
    <td>{lib["no_computer"]:.1f}%</td>
  </tr>"""
            body += "</table>"

    # ---- FCC Broadband Infrastructure Availability ----
    fcc = stats.get('fcc_broadband', {})
    if fcc and fcc.get('count'):
        body += f"""

<h2 id="fcc-broadband">FCC Broadband Infrastructure Availability</h2>
<p class="wiki-sub">The supply side: what broadband infrastructure ISPs have actually deployed in each community, from the FCC National Broadband Map (Dec 2025, BDC data). While the ACS data above shows what households <em>subscribe to</em>, this shows what's <em>available</em> — fiber, gigabit, and rural coverage rates.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{fcc['gigabit_avg']:.1f}%</div><div class="label">Avg gigabit availability</div></div>
  <div class="stat-card"><div class="num">{fcc['fiber_avg']:.1f}%</div><div class="label">Avg fiber availability</div></div>
  <div class="stat-card"><div class="num">{fcc['rural_avg']:.1f}%</div><div class="label">Avg rural locations</div></div>
  <div class="stat-card"><div class="num">{fcc['count']:,}</div><div class="label">Counties with FCC data</div></div>
</div>
<p class="rsrc">FCC BDC deployment data (Dec 31, 2025 filing). Gigabit = 1000/100 Mbps available; Fiber = any-speed fiber to the premises. "Any Technology" broadband (25/3 Mbps, including satellite) is available to ~100% of locations nationwide — the real infrastructure gap is in gigabit and fiber deployment.</p>"""

        low_gig = stats.get('lowest_gigabit', [])
        if low_gig:
            body += """
<h3>Communities Without Gigabit Infrastructure — The Infrastructure Gap</h3>
<p class="wiki-sub">Public libraries serving communities where fewer than 25% of locations have gigabit broadband available. These are places where the library may be the fastest internet connection available.</p>
<table class="wikitable biggest-table">
  <tr><th>#</th><th>Library</th><th>City</th><th>State</th><th>Gigabit Avail</th><th>Fiber Avail</th><th>Rural %</th></tr>"""
            for i, lib in enumerate(low_gig, 1):
                body += f"""
  <tr>
    <td>{i}</td>
    <td><a href="search.html?q={esc(lib["name"])}">{esc(lib["name"])}</a></td>
    <td>{esc(lib["city"]) or "—"}</td>
    <td>{esc(lib["state"]) or "—"}</td>
    <td class="pct">{lib["gigabit"]:.1f}%</td>
    <td>{lib["fiber"]:.1f}%</td>
    <td>{lib["rural"]:.1f}%</td>
  </tr>"""
            body += "</table>"

    # ---- FCC Census Place (town-level) Broadband ----
    fccp = stats.get('fcc_place', {})
    if fccp and fccp.get('count'):
        body += f"""

<h2 id="fcc-place-broadband">Town-Level Broadband Availability (FCC Census Place)</h2>
<p class="wiki-sub">The most precise broadband picture available — measured at the <strong>town/city level</strong> (Census Place), not county. Matched to each library by city + state using the FCC National Broadband Map's per-state Census Place files (Dec 2025 BDC deployment data). This reveals the true infrastructure gap libraries face, since broadband can vary dramatically between towns within a single county.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{fccp['gigabit_avg']:.1f}%</div><div class="label">Avg town gigabit availability</div></div>
  <div class="stat-card"><div class="num">{fccp['bb100_avg']:.1f}%</div><div class="label">Avg town 100/20 Mbps</div></div>
  <div class="stat-card"><div class="num">{fccp['fiber_avg']:.1f}%</div><div class="label">Avg town fiber availability</div></div>
  <div class="stat-card"><div class="num">{fccp['count']:,}</div><div class="label">Library towns with data</div></div>
  <div class="stat-card"><div class="num">{fccp['under25_gigabit']:,}</div><div class="label">Towns &lt;25% gigabit</div></div>
  <div class="stat-card"><div class="num">{fccp['no_fiber']:,}</div><div class="label">Towns with &lt;5% fiber</div></div>
</div>
<p class="rsrc">FCC BDC deployment data at Census Place (incorporated town/city) granularity, Dec 31 2025 filing. "Gigabit" = 1000/100 Mbps available to serviceable locations; "100/20" = the FCC's current broadband definition; "Fiber" = fiber-to-the-premises at any speed. These figures are independent of the county-level FCC data above — they reflect the specific town each library sits in.</p>"""

        place_low = stats.get('lowest_place_gigabit', [])
        if place_low:
            body += """
<h3>Library Towns Without Gigabit Infrastructure — Town-Level View</h3>
<p class="wiki-sub">Public libraries in towns where fewer than 25% of serviceable locations have gigabit broadband available. Because this is town-level, it catches underserved communities that county averages hide — a single well-connected city can mask a dozen rural towns in the same county.</p>
<table class="wikitable biggest-table">
  <tr><th>#</th><th>Library</th><th>City</th><th>State</th><th>Gigabit Avail</th><th>Fiber Avail</th><th>Serviceable Locations</th></tr>"""
            for i, lib in enumerate(place_low, 1):
                locs_str = f"{lib['locations']:,}" if lib['locations'] else '—'
                body += f"""
  <tr>
    <td>{i}</td>
    <td><a href="search.html?q={esc(lib["name"])}">{esc(lib["name"])}</a></td>
    <td>{esc(lib["city"]) or "—"}</td>
    <td>{esc(lib["state"]) or "—"}</td>
    <td class="pct">{lib["gigabit"]:.1f}%</td>
    <td>{lib["fiber"]:.1f}%</td>
    <td>{locs_str}</td>
  </tr>"""
            body += "</table>"

    body += f"""
<h2 id="top-rated">Top-Rated Libraries</h2>
<table class="wikitable top-rated-table">
  <tr><th>#</th><th>Library</th><th>City</th><th>State</th><th>Rating</th><th>Reviews</th></tr>"""

    for i, lib in enumerate(stats['top_rated'], 1):
        city = esc(lib['city']) or '—'
        state = esc(lib['state']) or '—'
        name_html = f'<a href="search.html?q={esc(lib["name"])}">{esc(lib["name"])}</a>'
        if lib.get('website'):
            name_html += f' <a href="{esc(lib["website"])}" target="_blank" rel="noopener" class="ext-link" title="Website"></a>'
        body += f"""
  <tr>
    <td>{i}</td>
    <td>{name_html}</td>
    <td>{city}</td>
    <td>{state}</td>
    <td class="rating">&#9733; {lib['rating']:.1f}</td>
    <td>{lib['rcount']:,}</td>
  </tr>"""

    body += f"""
</table>
<p class="rsrc">Libraries with a 5.0 average rating and at least 5 reviews, ranked by review count.</p>

<h2 id="services">Most Common Library Services</h2>
<div class="services-bars">"""

    max_svc = stats['services_breakdown'][0]['count'] if stats['services_breakdown'] else 1
    for svc in stats['services_breakdown']:
        pct_w = (svc['count'] / max_svc) * 100
        body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(svc['name'])}</span>
    <span class="svc-bar"><span class="svc-fill" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{svc['count']:,}</span>
  </div>"""

    body += f"""
</div>
<p class="rsrc">Service keywords extracted from {stats['services']:,} library service descriptions. Longer bars = more libraries offer this service.</p>

<h2 id="consortia">Library Consortia</h2>"""

    cons = stats.get('consortia', {})
    cons_list = stats.get('consortia_list', [])
    if cons_list:
        body += f"""
<p>{cons['us_total']:,} US library consortia — cooperative networks that share catalogs, interlibrary loan, and joint purchasing. Data from Wikipedia + ICOLC.</p>
<table class="wikitable consortia-table">
  <tr><th>Consortium</th><th>Abbreviation</th><th>Website</th><th>Region</th><th>Source</th></tr>"""
        for c in cons_list:
            name = esc(c.get('consortium_name',''))
            abbr = esc(c.get('abbreviation','')) or '—'
            web = (c.get('website','') or '').strip()
            web_html = f'<a href="{esc(web)}" target="_blank" rel="noopener">{esc(web)}</a>' if web else '—'
            region = esc(c.get('region','') or 'US')
            source = esc(c.get('source','') or '')
            body += f'\n  <tr><td>{name}</td><td>{abbr}</td><td>{web_html}</td><td>{region}</td><td>{source}</td></tr>'
        body += f"""
</table>
<p class="rsrc">{cons['total']:,} total consortia ({cons['us_total']:,} US-based, {cons['with_website']:,} with websites). Sources: {", ".join(cons['sources'])}.</p>"""
    else:
        body += "\n<p>No consortia data available.</p>"

    # ---- State Library Agencies (SLAA FY2024) ----
    sl = stats.get('slaa', {})
    if sl and sl.get('agencies'):
        sb = sl['total_budget']
        sl_budget_str = f"${sb/1e9:,.2f}B" if sb >= 1e9 else f"${sb/1e6:,.0f}M"
        sl_lsta_str = f"${sl['total_lsta']/1e6:,.0f}M" if sl['total_lsta'] >= 1e6 else f"${sl['total_lsta']:,}"
        sl_exp_str = f"${sl['total_expenditures']/1e9:,.2f}B" if sl['total_expenditures'] >= 1e9 else f"${sl['total_expenditures']/1e6:,.0f}M"
        sl_aid_str = f"${sl['total_aid']/1e6:,.0f}M" if sl['total_aid'] >= 1e6 else f"${sl['total_aid']:,}"
        sl_avg_str = f"${sl['avg_budget']/1e6:,.1f}M" if sl['avg_budget'] >= 1e6 else f"${sl['avg_budget']:,}"

        body += f"""

<h2 id="slaa">State Library Agencies (SLAA FY2024)</h2>
<p class="wiki-sub">The 50 state library agencies + DC — the bodies that administer federal LSTA funds, set statewide standards, and run aid programs. From the IMLS State Library Administrative Agency Survey, FY2024.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{sl_budget_str}</div><div class="label">Total agency income</div></div>
  <div class="stat-card"><div class="num">{sl_lsta_str}</div><div class="label">Federal LSTA funds</div></div>
  <div class="stat-card"><div class="num">{sl['total_staff']:,}</div><div class="label">Total agency staff (FTE)</div></div>
  <div class="stat-card"><div class="num">${sl['per_capita']:.2f}</div><div class="label">Per-capita spending</div></div>
  <div class="stat-card"><div class="num">{sl['agencies']}</div><div class="label">State agencies</div></div>
  <div class="stat-card"><div class="num">{sl['population_served']:,}</div><div class="label">Population served</div></div>
  <div class="stat-card"><div class="num">{sl['independent']}</div><div class="label">Independent agencies</div></div>
  <div class="stat-card"><div class="num">{sl['with_archive']}</div><div class="label">With state archive</div></div>
  <div class="stat-card"><div class="num">{sl['with_museum']}</div><div class="label">With state museum</div></div>
  <div class="stat-card"><div class="num">{sl['with_website']}</div><div class="label">With website</div></div>
</div>
<p class="rsrc">SLAA income = state + federal (LSTA) + other sources. Expenditures: {sl_exp_str} total ({sl_aid_str} as aid to libraries). Average agency budget: {sl_avg_str}. Data: IMLS SLAA FY2024.</p>
<table class="wikitable slaa-table">
  <tr><th>State</th><th>Agency</th><th>Budget</th><th>LSTA</th><th>Staff</th><th>Services</th><th>Website</th></tr>"""

        slaa_rows = sorted(data.get('slaa', []), key=lambda r: float(r.get('budget_total') or 0), reverse=True)
        for r in slaa_rows:
            st_code = esc((r.get('state') or '').upper())
            name = esc(r.get('agency_name') or '')
            bt = (r.get('budget_total') or '').strip()
            bt_str = f"${int(float(bt)):,}" if bt else '—'
            lt = (r.get('budget_federal_lsta') or '').strip()
            lt_str = f"${int(float(lt)):,}" if lt else '—'
            st_val = (r.get('staff_total') or '').strip()
            st_str = f"{float(st_val):.0f}" if st_val else '—'
            sc = (r.get('services_count') or '').strip()
            sc_str = f"{sc} programs" if sc else '—'
            web = (r.get('website') or '').strip()
            web_html = f'<a href="{esc(web)}" target="_blank" rel="noopener">site</a>' if web else '—'
            body += f'\n  <tr><td><a href="states/{st_code}.html">{st_code}</a></td><td>{name}</td><td class="pct">{bt_str}</td><td>{lt_str}</td><td>{st_str}</td><td>{sc_str}</td><td>{web_html}</td></tr>'

        body += '\n</table>'

    # ---- SLAA State Agency Services (summer reading, literacy, digitization, accessibility) ----
    slaa_svc = stats.get('slaa_services', {})
    if slaa_svc and slaa_svc.get('services'):
        body += f"""

<h3>What state library agencies actually do — services offered (FY2024)</h3>
<p class="wiki-sub">Beyond funding, state library agencies provide direct services: summer reading coordination, literacy programs, digitization, continuing education, and accessibility. This shows what percentage of the 51 state agencies offer each service.</p>
<div class="services-bars">"""
        max_svc = max(s.get('states', 0) for s in slaa_svc['services']) or 51
        for s in slaa_svc['services']:
            cnt = s.get('states', 0)
            pct_w = (cnt / max_svc) * 100
            body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(s["service"])}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{cnt} states ({s.get("pct", 0)}%)</span>
  </div>"""
        body += '\n</div>'

        # Summer reading by age group
        sra = slaa_svc.get('summer_reading_by_age', {})
        if sra:
            age_labels = {'early_childhood': 'Early Childhood', 'middle_childhood': 'Middle Childhood',
                          'young_adult': 'Young Adult', 'adult': 'Adult', 'older_adult': 'Older Adult'}
            body += """
<h4>Summer reading programs by age group</h4>
<div class="services-bars">"""
            max_sra = max(sra.values()) or 51
            for age, cnt in sorted(sra.items(), key=lambda x: -x[1]):
                pct_w = (cnt / max_sra) * 100
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{age_labels.get(age, age)}</span>
    <span class="svc-bar"><span class="svc-fill" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{cnt} states</span>
  </div>"""
            body += '\n</div>'

        # Numeric metrics
        nm = slaa_svc.get('numeric', {})
        if nm:
            body += f"""
<div class="stats-grid">
  <div class="stat-card"><div class="num">{nm.get('circulation',{}).get('total',0):,}</div><div class="label">Agency circulation</div></div>
  <div class="stat-card"><div class="num">{nm.get('library_visits',{}).get('total',0):,}</div><div class="label">Agency library visits</div></div>
  <div class="stat-card"><div class="num">{nm.get('events',{}).get('total',0):,}</div><div class="label">Events held</div></div>
  <div class="stat-card"><div class="num">{nm.get('event_attendance',{}).get('total',0):,}</div><div class="label">Event attendance</div></div>
</div>"""

        body += '<p class="rsrc">Data: IMLS State Library Administrative Agency Survey (SLAA) FY2024. Service fields indicate whether the state agency provides or supports each service type. A-E suffixes denote library types: A=Public, B=Academic, C=School, D=Special, E=Other.</p>'

    # ---- SLAA Historical Trends (FY2018-FY2024) ----
    slaa_tr = stats.get('slaa_trends', {})
    if slaa_tr and slaa_tr.get('trend_years'):
        sty = slaa_tr['trend_years']
        sty_n = len(sty)
        slaa_first_yr = sty[0]
        slaa_last_yr = sty[-1]
        def _val(trend_list, idx):
            v = trend_list[idx][1] if idx < len(trend_list) else ''
            try: return float(v) if v else 0
            except: return 0
        slaa_budget_first = _val(slaa_tr['trend_budget'], 0)
        slaa_budget_last = _val(slaa_tr['trend_budget'], -1)
        slaa_staff_first = _val(slaa_tr['trend_staff'], 0)
        slaa_staff_last = _val(slaa_tr['trend_staff'], -1)
        slaa_exp_last = _val(slaa_tr['trend_expenditures'], -1)
        slaa_aid_last = _val(slaa_tr['trend_aid'], -1)
        slaa_lsta_last = _val(slaa_tr['trend_lsta'], -1)
        def _chg(f, l):
            return ((l - f) / f * 100) if f else 0
        budget_chg = _chg(slaa_budget_first, slaa_budget_last)
        staff_chg = _chg(slaa_staff_first, slaa_staff_last)

        body += f"""

<h2 id="slaa-trends">State Agency Trends (SLAA FY{slaa_first_yr}–FY{slaa_last_yr})</h2>
<p class="wiki-sub">How state library agencies' funding and staffing have changed over {sty_n} vintages. State agencies are the conduit for federal LSTA dollars — their budgets reveal whether state-level library investment is keeping pace with inflation and growing responsibilities.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${slaa_budget_last/1e9:,.2f}B</div><div class="label">Latest total income (FY{slaa_last_yr})</div></div>
  <div class="stat-card"><div class="num">{'+' if budget_chg >= 0 else ''}{budget_chg:.1f}%</div><div class="label">Income change FY{slaa_first_yr}→{slaa_last_yr}</div></div>
  <div class="stat-card"><div class="num">{slaa_staff_last:,.0f}</div><div class="label">Staff FTE (FY{slaa_last_yr})</div></div>
  <div class="stat-card"><div class="num">{'+' if staff_chg >= 0 else ''}{staff_chg:.1f}%</div><div class="label">Staff change FY{slaa_first_yr}→{slaa_last_yr}</div></div>
  <div class="stat-card"><div class="num">${slaa_lsta_last/1e6:,.0f}M</div><div class="label">Federal LSTA (FY{slaa_last_yr})</div></div>
  <div class="stat-card"><div class="num">${slaa_aid_last/1e6:,.0f}M</div><div class="label">Aid to libraries (FY{slaa_last_yr})</div></div>
</div>"""
        # Trend table
        body += """
<table class="wikitable trend-table">
  <tr><th>Fiscal Year</th><th>Total Income</th><th>LSTA Income</th><th>Expenditures</th><th>Aid to Libraries</th><th>Staff FTE</th></tr>"""
        for i in range(sty_n):
            yr = sty[i]
            b = _val(slaa_tr['trend_budget'], i)
            l = _val(slaa_tr['trend_lsta'], i)
            e = _val(slaa_tr['trend_expenditures'], i)
            a = _val(slaa_tr['trend_aid'], i)
            s = _val(slaa_tr['trend_staff'], i)
            body += f'\n  <tr><td>FY{yr}</td><td class="pct">${b/1e6:,.0f}M</td><td>${l/1e6:,.0f}M</td><td>${e/1e6:,.0f}M</td><td>${a/1e6:,.0f}M</td><td>{s:,.0f}</td></tr>'
        body += "\n</table>"
        body += f'\n<p class="rsrc">Data: IMLS SLAA vintages FY{slaa_first_yr}, FY{sty[1] if sty_n > 2 else ""}, FY{sty[-2] if sty_n > 2 else ""}, FY{slaa_last_yr}. Income grew {budget_chg:+.1f}% while staffing grew only {staff_chg:+.1f}% — a widening gap between resources and capacity.</p>'

    # ---- Federal Depository Libraries (GPO FDLP) ----
    fdlp_s = stats.get('fdlp', {})
    if fdlp_s and fdlp_s.get('total'):
        body += f"""

<h2 id="fdlp">Federal Depository Libraries (GPO FDLP)</h2>
<p class="wiki-sub">The Federal Depository Library Program — {fdlp_s['total']} libraries that receive and provide public access to U.S. government documents. Of these, <strong>{fdlp_s['regional']} are Regional depositories</strong> (comprehensive collections, one or more per state) and {fdlp_s['selective']} are Selective (choosing specific titles). {fdlp_s['preservation_stewards']} are designated Preservation Stewards, committing to retain government publications long-term.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{fdlp_s['total']}</div><div class="label">Depository libraries</div></div>
  <div class="stat-card"><div class="num">{fdlp_s['regional']}</div><div class="label">Regional depositories</div></div>
  <div class="stat-card"><div class="num">{fdlp_s['selective']}</div><div class="label">Selective depositories</div></div>
  <div class="stat-card"><div class="num">{fdlp_s['preservation_stewards']}</div><div class="label">Preservation Stewards</div></div>
</div>"""

        # Regional depositories table
        if fdlp_s.get('regional_list'):
            body += """
<h3>Regional Depository Libraries</h3>
<p class="wiki-sub">Regional depositories receive and retain ALL government publications distributed through the FDLP — the comprehensive government-document collections, one or more per state.</p>
<table class="wikitable">
  <tr><th>Library</th><th>State</th><th>Parent Institution</th><th>Library Type</th></tr>"""
            for r in fdlp_s['regional_list']:
                body += f'\n  <tr><td>{esc(r["name"])}</td><td><a href="states/{r["state"]}.html">{r["state"]}</a></td><td>{esc(r["parent"]) or "—"}</td><td>{esc(r["type"]) or "—"}</td></tr>'
            body += "\n</table>"

        # Largest by titles selected
        if fdlp_s.get('largest'):
            body += """
<h3>Largest Selective Depositories by Titles Selected</h3>
<p class="wiki-sub">Selective depositories that receive the most individual government-document titles — the most comprehensive selective collections.</p>
<table class="wikitable">
  <tr><th>#</th><th>Library</th><th>State</th><th>Parent Institution</th><th>Type</th><th>Titles Selected</th></tr>"""
            for i, r in enumerate(fdlp_s['largest'], 1):
                body += f'\n  <tr><td>{i}</td><td>{esc(r["name"])}</td><td><a href="states/{r["state"]}.html">{r["state"]}</a></td><td>{esc(r["parent"]) or "—"}</td><td>{esc(r["dtype"]) or "—"}</td><td class="pct">{r["titles"]:,}</td></tr>'
            body += "\n</table>"
        body += f'\n<p class="rsrc">Data: U.S. Government Publishing Office (GPO) Federal Depository Library Program. Retrieved from GPO\'s FDLP Print Distribution Dashboard ArcGIS Feature Service (Dec 2025). Note: the FDLP comprises ~1,093 libraries total; this dataset covers the {fdlp_s["total"]} that select Print Distribution Titles. The full directory is maintained in GPO\'s FDLD application.</p>'

    # ---- IMLS Grant Awards (1996-2025) ----
    ig = stats.get('imls_grants', {})
    if ig and ig.get('total_count'):
        ig_n = ig['total_count']
        ig_amt = ig['total_amount']
        ig_yr = ig['year_range']
        # Find the ARPA/COVID spike year
        spike_year = ''
        spike_amt = 0
        if ig.get('trend_amounts') and ig.get('trend_years'):
            for i, yr in enumerate(ig['trend_years']):
                amt = ig['trend_amounts'][i] if i < len(ig['trend_amounts']) else 0
                if amt > spike_amt:
                    spike_amt = amt
                    spike_year = yr
        body += f"""

<h2 id="imls-grants">IMLS Grant Awards ({ig_yr})</h2>
<p class="wiki-sub">The Institute of Museum and Library Services is the primary federal funder of the nation's libraries and museums. Over {ig_yr}, IMLS awarded <strong>{ig_n:,} grants</strong> totaling <strong>${ig_amt/1e9:.2f} billion</strong> to libraries, museums, and Native American organizations across all 50 states and territories.{' FY' + str(spike_year) + ' saw a surge to $' + f'{spike_amt/1e6:.0f}' + 'M — the American Rescue Plan Act (ARPA) pandemic relief.' if spike_amt > 300e6 else ''}</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{ig_n:,}</div><div class="label">Total grants awarded</div></div>
  <div class="stat-card"><div class="num">${ig_amt/1e9:.2f}B</div><div class="label">Total federal investment</div></div>
  <div class="stat-card"><div class="num">${ig_amt/ig_n:,.0f}</div><div class="label">Average award</div></div>
  <div class="stat-card"><div class="num">{len(ig.get('top_programs', []))}</div><div class="label">Program types (pre-2014)</div></div>
  <div class="stat-card"><div class="num">{len(ig.get('top_states', []))}</div><div class="label">States & territories</div></div>
</div>"""

        # Grants by program type — bar chart
        if ig.get('top_programs'):
            body += """
<h3>Grant programs — where the money went</h3>
<div class="services-bars">"""
            max_prog = max(int(p.get('grants', 0) or 0) for p in ig['top_programs']) or 1
            for p in ig['top_programs']:
                cnt = int(p.get('grants', 0) or 0)
                amt = int(p.get('total_awarded', 0) or 0)
                pct_w = (cnt / max_prog) * 100
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(p["program"])}</span>
    <span class="svc-bar"><span class="svc-fill" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{cnt:,} (${amt/1e6:.0f}M)</span>
  </div>"""
            body += '\n</div>'

        # Top states by total awarded
        if ig.get('top_states'):
            body += """
<h3>Top states by total IMLS funding</h3>
<table class="wikitable">
  <tr><th>#</th><th>State</th><th>Grants</th><th>Total Awarded</th><th>Avg Award</th><th>Institutions</th></tr>"""
            for i, r in enumerate(ig['top_states'], 1):
                st_code = esc((r.get('state') or '').upper())
                st_grants = int(r.get('grants', 0) or 0)
                st_total = int(r.get('total_awarded', 0) or 0)
                st_avg = int(r.get('avg_award', 0) or 0)
                st_inst = int(r.get('institutions', 0) or 0)
                body += f'\n  <tr><td>{i}</td><td><a href="states/{st_code}.html">{st_code}</a></td><td>{st_grants:,}</td><td class="pct">${st_total/1e6:.1f}M</td><td>${st_avg:,}</td><td>{st_inst:,}</td></tr>'
            body += '\n</table>'

        # Largest individual awards
        if ig.get('largest'):
            body += """
<h3>Largest single IMLS awards</h3>
<table class="wikitable">
  <tr><th>#</th><th>Institution</th><th>City</th><th>State</th><th>Program</th><th>Award</th><th>Year</th></tr>"""
            for i, r in enumerate(ig['largest'], 1):
                amt = int(r.get('amount', 0) or 0)
                body += f'\n  <tr><td>{i}</td><td>{esc(r["institution"])}</td><td>{esc(r["city"]) or "—"}</td><td><a href="states/{esc((r["state"] or "").upper())}.html">{esc(r["state"])}</a></td><td>{esc(r["program"])}</td><td class="pct">${amt/1e6:.1f}M</td><td>{r.get("year", "—")}</td></tr>'
            body += '\n</table>'

        # Annual awards trend chart
        if ig.get('trend_years') and len(ig['trend_years']) >= 2:
            yrs = ig['trend_years']
            amts = ig['trend_amounts']
            n_yrs = len(yrs)
            chart_w = 700
            chart_h = 180
            bar_w = (chart_w - 60) / n_yrs
            max_amt = max(amts) if amts else 1
            g_bars = []
            for i, yr in enumerate(yrs):
                v = amts[i] if i < len(amts) else 0
                h = (v / max_amt) * (chart_h - 40) if v else 0
                x = 40 + i * bar_w
                y = chart_h - 30 - h
                g_bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(bar_w*0.7,1):.1f}" height="{h:.1f}" fill="#8b5cf6" rx="2"/>')
                if i % 3 == 0 or i == n_yrs - 1:
                    g_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{chart_h - 12:.1f}" text-anchor="middle" font-size="9" fill="#666">{yr}</text>')
                    if v:
                        g_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{y - 3:.1f}" text-anchor="middle" font-size="8" fill="#333">${v/1e6:.0f}M</text>')
            body += f"""
<h3>Annual IMLS award funding</h3>
<svg viewBox="0 0 {chart_w} {chart_h + 20}" class="trend-chart" xmlns="http://www.w3.org/2000/svg">
  <line x1="40" y1="{chart_h - 30}" x2="{chart_w - 20}" y2="{chart_h - 30}" stroke="#ccc" stroke-width="1"/>
  {''.join(g_bars)}
</svg>"""

        body += f'<p class="rsrc">Data: IMLS Discretionary Grant Awards, FY{ig_yr}. Individual grant records (FY1996–FY2013) from IMLS Administrative Discretionary Grant Data; aggregate state totals (FY2014–FY2025) from the IMLS Grants to States API. Award amounts include matching funds where applicable. IMLS is an independent federal agency and the primary source of federal support for the nation\'s libraries and museums.</p>'

    # ---- IMLS Grants to States (G2S) — formula funding ----
    g2s = stats.get('imls_g2s', {})
    if g2s and g2s.get('total_amount'):
        g2s_amt = g2s['total_amount']
        g2s_yr = g2s['year_range']
        g2s_latest = g2s['trend_amounts'][-1] if g2s.get('trend_amounts') else 0
        g2s_first = g2s['trend_amounts'][0] if g2s.get('trend_amounts') else 0
        g2s_chg = ((g2s_latest - g2s_first) / g2s_first * 100) if g2s_first else 0
        body += f"""

<h2 id="imls-g2s">IMLS Grants to States (G2S) — Formula Funding ({g2s_yr})</h2>
<p class="wiki-sub">While discretionary grants are awarded competitively, Grants to States (G2S) are <strong>formula-based funding</strong> distributed annually to every state library agency under the Library Services and Technology Act (LSTA). This is the backbone of federal library funding — it flows through the state agencies tracked in the SLAA section above to support local library services, technology, and outreach.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${g2s_amt/1e6:.0f}M</div><div class="label">Total G2S funding ({g2s_yr})</div></div>
  <div class="stat-card"><div class="num">${g2s_latest/1e6:.1f}M</div><div class="label">Latest year award</div></div>
  <div class="stat-card"><div class="num">{g2s_chg:+.1f}%</div><div class="label">Funding change over period</div></div>
  <div class="stat-card"><div class="num">{len(g2s.get('top_states', []))}</div><div class="label">States & territories</div></div>
</div>"""

        # G2S trend chart
        if g2s.get('trend_years') and len(g2s['trend_years']) >= 2:
            yrs = g2s['trend_years']
            amts = g2s['trend_amounts']
            n_yrs = len(yrs)
            chart_w = 600
            chart_h = 160
            bar_w = (chart_w - 60) / n_yrs
            max_amt = max(amts) if amts else 1
            g_bars = []
            for i, yr in enumerate(yrs):
                v = amts[i] if i < len(amts) else 0
                h = (v / max_amt) * (chart_h - 40) if v else 0
                x = 40 + i * bar_w
                y = chart_h - 30 - h
                g_bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(bar_w*0.7,1):.1f}" height="{h:.1f}" fill="#10b981" rx="2"/>')
                g_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{chart_h - 12:.1f}" text-anchor="middle" font-size="9" fill="#666">{yr}</text>')
                if v:
                    g_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{y - 3:.1f}" text-anchor="middle" font-size="8" fill="#333">${v/1e6:.0f}M</text>')
            body += f"""
<h3>Annual Grants to States funding</h3>
<svg viewBox="0 0 {chart_w} {chart_h + 20}" class="trend-chart" xmlns="http://www.w3.org/2000/svg">
  <line x1="40" y1="{chart_h - 30}" x2="{chart_w - 20}" y2="{chart_h - 30}" stroke="#ccc" stroke-width="1"/>
  {''.join(g_bars)}
</svg>"""

        # Top states by G2S amount
        if g2s.get('top_states'):
            body += """
<h3>Top states by total G2S funding</h3>
<table class="wikitable">
  <tr><th>#</th><th>State</th><th>Total G2S Awarded</th><th>Latest Per-Capita</th></tr>"""
            for i, r in enumerate(g2s['top_states'], 1):
                st_code = esc((r.get('state') or '').upper())
                amt = int(r.get('amount', 0) or 0)
                pc = float(r.get('per_capita', 0) or 0)
                pc_str = f"${pc:.2f}" if pc else '—'
                body += f'\n  <tr><td>{i}</td><td><a href="states/{st_code}.html">{st_code}</a></td><td class="pct">${amt/1e6:.1f}M</td><td>{pc_str}</td></tr>'
            body += '\n</table>'

        # Top states by per-capita funding
        if g2s.get('top_percapita'):
            body += """
<h3>Highest per-capita G2S funding — small states & territories get more per resident</h3>
<table class="wikitable">
  <tr><th>#</th><th>State</th><th>Per-Capita Funding</th><th>Total G2S</th></tr>"""
            for i, r in enumerate(g2s['top_percapita'], 1):
                st_code = esc((r.get('state') or '').upper())
                pc = float(r.get('per_capita', 0) or 0)
                amt = int(r.get('amount', 0) or 0)
                body += f'\n  <tr><td>{i}</td><td><a href="states/{st_code}.html">{st_code}</a></td><td class="pct">${pc:.2f}</td><td>${amt/1e6:.1f}M</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">Data: IMLS Grants to States (G2S) program, FY{g2s_yr}. G2S awards are formula-based under the Library Services and Technology Act (LSTA), distributed through state library administrative agencies. Per-capita figures show which states receive the most federal library funding per resident — small population states and territories consistently rank highest due to minimum-funding provisions in the LSTA formula.</p>'

    # ---- Public Library Historical Trends (IMLS PLS 2000-2024) ----
    pls = stats.get('pls_trends', {})
    if pls and pls.get('trend_years'):
        pls_years = pls['trend_years']
        pls_n = len(pls_years)
        pls_yr_labels = f"{pls_years[0]}–{pls_years[-1]}"
        # Pre-COVID peak vs COVID trough vs latest
        pre_covid_peak_visits = max(pls['trend_visits'][:pls_n-5]) if pls_n > 5 else max(pls['trend_visits'])
        covid_trough_visits = min(pls['trend_visits'][-5:]) if pls_n >= 5 else min(pls['trend_visits'])
        latest_visits = pls['trend_visits'][-1]
        latest_circ = pls['trend_circulation'][-1]
        latest_staff = pls['trend_staff_fte'][-1]
        latest_exp = pls['trend_expenditures'][-1]
        latest_pop = pls['trend_population'][-1]
        latest_sys = pls['trend_systems'][-1]
        latest_outlets = pls['trend_outlets'][-1]
        latest_lib_fte = pls['trend_librarian_fte'][-1]

        # % changes
        def _pchg(first, last):
            if first and last:
                return ((last - first) / first) * 100
            return 0
        visits_chg = _pchg(pls['trend_visits'][0], latest_visits)
        circ_chg = _pchg(pls['trend_circulation'][0], latest_circ)
        staff_chg = _pchg(pls['trend_staff_fte'][0], latest_staff)
        exp_chg = _pchg(pls['trend_expenditures'][0], latest_exp)
        covid_drop = ((covid_trough_visits - pre_covid_peak_visits) / pre_covid_peak_visits) * 100 if pre_covid_peak_visits else 0

        body += f"""

<h2 id="pls-trends">Public Library Historical Trends (IMLS PLS {pls_yr_labels})</h2>
<p class="wiki-sub">The IMLS Public Libraries Survey has been conducted every year since 1988, making it the longest-running national library dataset. Here we present {pls_n} consecutive vintages ({pls_yr_labels}) showing how America's ~9,200 public library systems have evolved across a quarter century — through the Great Recession, the COVID-19 pandemic, and the digital transition.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{latest_sys:,}</div><div class="label">Library systems ({pls_years[-1]})</div></div>
  <div class="stat-card"><div class="num">{latest_outlets:,}</div><div class="label">Total outlets</div></div>
  <div class="stat-card"><div class="num">{latest_pop/1e6:.0f}M</div><div class="label">Population served</div></div>
  <div class="stat-card"><div class="num">{latest_staff:,}</div><div class="label">Total staff (FTE)</div></div>
  <div class="stat-card"><div class="num">{latest_visits/1e6:.0f}M</div><div class="label">Annual visits</div></div>
  <div class="stat-card"><div class="num">{latest_circ/1e6:.0f}M</div><div class="label">Items circulated</div></div>
  <div class="stat-card"><div class="num">${latest_exp/1e9:.2f}B</div><div class="label">Operating expenditures</div></div>
  <div class="stat-card"><div class="num">{covid_drop:+.0f}%</div><div class="label">COVID visits drop (peak→trough)</div></div>
</div>"""

        # Trend table — every 3rd year to keep it compact
        body += """
<h3>Temporal trend data (selected years)</h3>
<table class="wikitable trend-table">
  <tr><th>Fiscal Year</th><th>Systems</th><th>Outlets</th><th>Pop. served</th><th>Staff FTE</th><th>Visits</th><th>Circulation</th><th>Expenditures</th></tr>"""
        step = max(1, pls_n // 10)  # ~10 rows max
        for i in range(0, pls_n, step):
            yr = pls_years[i]
            body += f"""
  <tr>
    <td class="yr">{yr}</td>
    <td>{pls['trend_systems'][i]:,}</td>
    <td>{pls['trend_outlets'][i]:,}</td>
    <td>{pls['trend_population'][i]/1e6:.0f}M</td>
    <td>{pls['trend_staff_fte'][i]:,}</td>
    <td>{pls['trend_visits'][i]/1e6:.0f}M</td>
    <td>{pls['trend_circulation'][i]/1e6:.0f}M</td>
    <td class="pct">${pls['trend_expenditures'][i]/1e9:.2f}B</td>
  </tr>"""
        # Always include the latest year
        if (pls_n - 1) % step != 0:
            i = pls_n - 1
            body += f"""
  <tr>
    <td class="yr">{pls_years[i]}</td>
    <td>{pls['trend_systems'][i]:,}</td>
    <td>{pls['trend_outlets'][i]:,}</td>
    <td>{pls['trend_population'][i]/1e6:.0f}M</td>
    <td>{pls['trend_staff_fte'][i]:,}</td>
    <td>{pls['trend_visits'][i]/1e6:.0f}M</td>
    <td>{pls['trend_circulation'][i]/1e6:.0f}M</td>
    <td class="pct">${pls['trend_expenditures'][i]/1e9:.2f}B</td>
  </tr>"""
        body += '\n</table>'

        # SVG chart: visits over time — the COVID cliff is the story
        chart_w = 750
        chart_h = 220
        bar_w = (chart_w - 60) / pls_n
        max_visits = max(pls['trend_visits']) if pls['trend_visits'] else 1
        v_bars = []
        for i, yr in enumerate(pls_years):
            v = pls['trend_visits'][i]
            h = (v / max_visits) * (chart_h - 40) if v else 0
            x = 40 + i * bar_w
            y = chart_h - 30 - h
            # Color: blue pre-COVID, red for 2020-2021 (trough), green for recovery
            if yr >= 2020 and yr <= 2021:
                fill = '#ef4444'
            elif yr >= 2022:
                fill = '#10b981'
            else:
                fill = '#3b82f6'
            v_bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(bar_w*0.7,1):.1f}" height="{h:.1f}" fill="{fill}" rx="1"/>')
            if i % 3 == 0 or i == pls_n - 1:
                v_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{chart_h - 12:.1f}" text-anchor="middle" font-size="9" fill="#666">{yr}</text>')
                if v:
                    v_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{y - 3:.1f}" text-anchor="middle" font-size="8" fill="#333">{v/1e6:.0f}M</text>')
        svg = f'''<h3>Annual library visits — the COVID-19 cliff and partial recovery</h3>
<svg viewBox="0 0 {chart_w} {chart_h + 20}" class="trend-chart" xmlns="http://www.w3.org/2000/svg">
  <line x1="40" y1="{chart_h - 30}" x2="{chart_w - 10}" y2="{chart_h - 30}" stroke="#ccc" stroke-width="1"/>
  {''.join(v_bars)}
  <text x="{chart_w - 10}" y="15" text-anchor="end" font-size="10" fill="#999">🔴 COVID trough 🟢 Recovery</text>
</svg>'''
        body += svg

        # Circulation chart
        max_circ = max(pls['trend_circulation']) if pls['trend_circulation'] else 1
        c_bars = []
        for i, yr in enumerate(pls_years):
            v = pls['trend_circulation'][i]
            h = (v / max_circ) * (chart_h - 40) if v else 0
            x = 40 + i * bar_w
            y = chart_h - 30 - h
            if yr >= 2020 and yr <= 2021:
                fill = '#ef4444'
            elif yr >= 2022:
                fill = '#10b981'
            else:
                fill = '#8b5cf6'
            c_bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(bar_w*0.7,1):.1f}" height="{h:.1f}" fill="{fill}" rx="1"/>')
            if i % 3 == 0 or i == pls_n - 1:
                c_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{chart_h - 12:.1f}" text-anchor="middle" font-size="9" fill="#666">{yr}</text>')
                if v:
                    c_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{y - 3:.1f}" text-anchor="middle" font-size="8" fill="#333">{v/1e6:.0f}M</text>')
        svg2 = f'''<h3>Total circulation — peak in 2010, decline through digital transition + COVID</h3>
<svg viewBox="0 0 {chart_w} {chart_h + 20}" class="trend-chart" xmlns="http://www.w3.org/2000/svg">
  <line x1="40" y1="{chart_h - 30}" x2="{chart_w - 10}" y2="{chart_h - 30}" stroke="#ccc" stroke-width="1"/>
  {''.join(c_bars)}
</svg>'''
        body += svg2

        # ---- Extended PLS trend metrics: digital transition, children's services, ILL ----
        latest_capex = pls['trend_capital_exp'][-1] if pls.get('trend_capital_exp') else 0
        latest_elmat = pls['trend_elmat_exp'][-1] if pls.get('trend_elmat_exp') else 0
        latest_bkvol = pls['trend_book_volumes'][-1] if pls.get('trend_book_volumes') else 0
        latest_kid_att = pls['trend_children_attendance'][-1] if pls.get('trend_children_attendance') else 0
        latest_kid_cir = pls['trend_children_circ'][-1] if pls.get('trend_children_circ') else 0
        latest_ref = pls['trend_reference'][-1] if pls.get('trend_reference') else 0
        latest_ill_to = pls['trend_ill_to'][-1] if pls.get('trend_ill_to') else 0
        latest_ill_from = pls['trend_ill_from'][-1] if pls.get('trend_ill_from') else 0
        first_elmat = pls['trend_elmat_exp'][0] if pls.get('trend_elmat_exp') else 0
        elmat_chg = _pchg(first_elmat, latest_elmat) if first_elmat else 0

        body += f"""
<h3>The digital transition — beyond visits & circulation</h3>
<p class="wiki-sub">The PLS captures more than foot traffic. These metrics reveal how libraries have shifted spending toward electronic materials, how capital investment fluctuates, and how interlibrary loan has changed in the age of e-books.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${latest_elmat/1e6:.0f}M</div><div class="label">E-material expenditures ({pls_years[-1]})</div></div>
  <div class="stat-card"><div class="num">{elmat_chg:+.0f}%</div><div class="label">E-material spend change {pls_years[0]}→{pls_years[-1]}</div></div>
  <div class="stat-card"><div class="num">${latest_capex/1e6:.0f}M</div><div class="label">Capital expenditures</div></div>
  <div class="stat-card"><div class="num">{latest_bkvol/1e6:.0f}M</div><div class="label">Book volumes held</div></div>
  <div class="stat-card"><div class="num">{latest_kid_att/1e6:.0f}M</div><div class="label">Children's program attendance</div></div>
  <div class="stat-card"><div class="num">{latest_kid_cir/1e6:.0f}M</div><div class="label">Children's materials circulated</div></div>
  <div class="stat-card"><div class="num">{latest_ref/1e6:.0f}M</div><div class="label">Reference transactions</div></div>
  <div class="stat-card"><div class="num">{latest_ill_to/1e6:.1f}M</div><div class="label">ILL lent to other libraries</div></div>
  <div class="stat-card"><div class="num">{latest_ill_from/1e6:.1f}M</div><div class="label">ILL borrowed from others</div></div>
</div>"""

        # E-material expenditure chart — the digital spending surge
        if pls.get('trend_elmat_exp') and any(v > 0 for v in pls['trend_elmat_exp']):
            max_elmat = max(pls['trend_elmat_exp']) if pls['trend_elmat_exp'] else 1
            e_bars = []
            for i, yr in enumerate(pls_years):
                v = pls['trend_elmat_exp'][i]
                h = (v / max_elmat) * (chart_h - 40) if v else 0
                x = 40 + i * bar_w
                y = chart_h - 30 - h
                e_bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(bar_w*0.7,1):.1f}" height="{h:.1f}" fill="#f59e0b" rx="1"/>')
                if i % 3 == 0 or i == pls_n - 1:
                    e_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{chart_h - 12:.1f}" text-anchor="middle" font-size="9" fill="#666">{yr}</text>')
                    if v:
                        e_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{y - 3:.1f}" text-anchor="middle" font-size="8" fill="#333">${v/1e6:.0f}M</text>')
            svg3 = f'''<h3>Electronic material expenditures — the shift to digital spending</h3>
<svg viewBox="0 0 {chart_w} {chart_h + 20}" class="trend-chart" xmlns="http://www.w3.org/2000/svg">
  <line x1="40" y1="{chart_h - 30}" x2="{chart_w - 10}" y2="{chart_h - 30}" stroke="#ccc" stroke-width="1"/>
  {''.join(e_bars)}
</svg>'''
            body += svg3

        # ILL chart — interlibrary loan trends (lending vs borrowing)
        if pls.get('trend_ill_to') and pls.get('trend_ill_from'):
            max_ill = max(max(pls['trend_ill_to']), max(pls['trend_ill_from'])) or 1
            ill_bars = []
            for i, yr in enumerate(pls_years):
                vt = pls['trend_ill_to'][i]
                vf = pls['trend_ill_from'][i]
                ht = (vt / max_ill) * (chart_h - 40) if vt else 0
                hf = (vf / max_ill) * (chart_h - 40) if vf else 0
                x = 40 + i * bar_w
                ill_bars.append(f'<rect x="{x:.1f}" y="{chart_h - 30 - ht:.1f}" width="{max(bar_w*0.35,1):.1f}" height="{ht:.1f}" fill="#3b82f6" rx="1"/>')
                ill_bars.append(f'<rect x="{x + bar_w*0.35:.1f}" y="{chart_h - 30 - hf:.1f}" width="{max(bar_w*0.35,1):.1f}" height="{hf:.1f}" fill="#ec4899" rx="1"/>')
                if i % 3 == 0 or i == pls_n - 1:
                    ill_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{chart_h - 12:.1f}" text-anchor="middle" font-size="9" fill="#666">{yr}</text>')
            svg4 = f'''<h3>Interlibrary loan — lending (blue) vs borrowing (pink), in millions</h3>
<svg viewBox="0 0 {chart_w} {chart_h + 20}" class="trend-chart" xmlns="http://www.w3.org/2000/svg">
  <line x1="40" y1="{chart_h - 30}" x2="{chart_w - 10}" y2="{chart_h - 30}" stroke="#ccc" stroke-width="1"/>
  {''.join(ill_bars)}
  <text x="{chart_w - 10}" y="15" text-anchor="end" font-size="10" fill="#999">Lending=blue, Borrowing=pink</text>
</svg>'''
            body += svg4

        # Extended trend data table
        body += """
<h3>Detailed trend data — digital spending, collections & interlibrary loan</h3>
<table class="wikitable trend-table">
  <tr><th>Year</th><th>Book volumes</th><th>E-material $</th><th>Capital $</th><th>Children's attend.</th><th>Children's circ.</th><th>Reference</th><th>ILL lent</th><th>ILL borrowed</th></tr>"""
        for i in range(0, pls_n, step):
            yr = pls_years[i]
            bkvol_v = pls['trend_book_volumes'][i] if pls.get('trend_book_volumes') else 0
            elmat_v = pls['trend_elmat_exp'][i] if pls.get('trend_elmat_exp') else 0
            capex_v = pls['trend_capital_exp'][i] if pls.get('trend_capital_exp') else 0
            kid_att_v = pls['trend_children_attendance'][i] if pls.get('trend_children_attendance') else 0
            kid_cir_v = pls['trend_children_circ'][i] if pls.get('trend_children_circ') else 0
            ref_v = pls['trend_reference'][i] if pls.get('trend_reference') else 0
            ill_to_v = pls['trend_ill_to'][i] if pls.get('trend_ill_to') else 0
            ill_from_v = pls['trend_ill_from'][i] if pls.get('trend_ill_from') else 0
            body += f"""
  <tr>
    <td class="yr">{yr}</td>
    <td>{bkvol_v/1e6:.0f}M</td>
    <td class="pct">${elmat_v/1e6:.0f}M</td>
    <td>${capex_v/1e6:.0f}M</td>
    <td>{kid_att_v/1e6:.0f}M</td>
    <td>{kid_cir_v/1e6:.0f}M</td>
    <td>{ref_v/1e6:.0f}M</td>
    <td>{ill_to_v/1e6:.1f}M</td>
    <td>{ill_from_v/1e6:.1f}M</td>
  </tr>"""
        # Always include latest year
        if (pls_n - 1) % step != 0:
            i = pls_n - 1
            yr = pls_years[i]
            bkvol_v = pls['trend_book_volumes'][i] if pls.get('trend_book_volumes') else 0
            elmat_v = pls['trend_elmat_exp'][i] if pls.get('trend_elmat_exp') else 0
            capex_v = pls['trend_capital_exp'][i] if pls.get('trend_capital_exp') else 0
            kid_att_v = pls['trend_children_attendance'][i] if pls.get('trend_children_attendance') else 0
            kid_cir_v = pls['trend_children_circ'][i] if pls.get('trend_children_circ') else 0
            ref_v = pls['trend_reference'][i] if pls.get('trend_reference') else 0
            ill_to_v = pls['trend_ill_to'][i] if pls.get('trend_ill_to') else 0
            ill_from_v = pls['trend_ill_from'][i] if pls.get('trend_ill_from') else 0
            body += f"""
  <tr>
    <td class="yr">{yr}</td>
    <td>{bkvol_v/1e6:.0f}M</td>
    <td class="pct">${elmat_v/1e6:.0f}M</td>
    <td>${capex_v/1e6:.0f}M</td>
    <td>{kid_att_v/1e6:.0f}M</td>
    <td>{kid_cir_v/1e6:.0f}M</td>
    <td>{ref_v/1e6:.0f}M</td>
    <td>{ill_to_v/1e6:.1f}M</td>
    <td>{ill_from_v/1e6:.1f}M</td>
  </tr>"""
        body += '\n</table>'

        body += f'<p class="rsrc">Source: IMLS Public Libraries Survey (PLS), FY{pls_years[0]}–FY{pls_years[-1]} ({pls_n} vintages). Visits peaked at {max(pls["trend_visits"])/1e6:.0f}M in {pls_years[pls["trend_visits"].index(max(pls["trend_visits"]))]}, then fell {covid_drop:.0f}% during COVID-19. E-material expenditures include e-books, e-serials, and electronic databases. Capital expenditures cover building construction/renovation. Expenditure figures are nominal (not inflation-adjusted). Per-system detail is available on state pages.</p>'

    # ---- PLS FY2024 Digital Services & Programs ----
    pd = stats.get('pls_digital', {})
    if pd and pd.get('total_systems'):
        ec = pd.get('elmat_circ_total', {})
        eb = pd.get('ebook_circ', {})
        ea = pd.get('eaudio_circ', {})
        ev = pd.get('evideo_circ', {})
        wifi = pd.get('wifi_sessions', {})
        pitu = pd.get('public_internet_users', {})
        gpt = pd.get('public_internet_terminals', {})
        protot = pd.get('programs_total', {})
        proon = pd.get('programs_online', {})
        provir = pd.get('programs_virtual', {})
        atttot = pd.get('attendance_total', {})
        att05 = pd.get('attendance_0_5', {})
        att611 = pd.get('attendance_6_11', {})
        attya = pd.get('attendance_young_adult', {})
        attad = pd.get('attendance_adult', {})
        capex = pd.get('capital_expenditures', {})
        caploc = pd.get('cap_rev_local', {})
        capst = pd.get('cap_rev_state', {})
        capfed = pd.get('cap_rev_federal', {})
        capoth = pd.get('cap_rev_other', {})
        caprev = pd.get('cap_rev_total', {})
        bkvol = pd.get('book_volumes', {})

        body += f"""

<h2 id="pls-digital">Digital Services & Programs — FY2024 Snapshot</h2>
<p class="wiki-sub">The FY2024 Public Libraries Survey captures the modern library's digital footprint with unprecedented detail: e-circulation by format, programs by age group and delivery mode, WiFi usage, public internet access, and capital revenue broken out by source. This is the most current picture of how America's 9,249 public library systems serve their communities in the post-pandemic era.</p>

<h3>E-circulation — the digital collection in action</h3>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{ec.get('total',0)/1e6:.0f}M</div><div class="label">Total e-material circulations</div></div>
  <div class="stat-card"><div class="num">{eb.get('total',0)/1e6:.0f}M</div><div class="label">E-book circulations</div></div>
  <div class="stat-card"><div class="num">{ea.get('total',0)/1e6:.0f}M</div><div class="label">E-audio circulations</div></div>
  <div class="stat-card"><div class="num">{ev.get('total',0)/1e6:.0f}M</div><div class="label">E-video circulations</div></div>
  <div class="stat-card"><div class="num">{bkvol.get('total',0)/1e6:.0f}M</div><div class="label">Physical book volumes held</div></div>
</div>"""

        # E-circulation vs physical pie/bar
        body += f"""
<div class="services-bars">
  <div class="svc-row"><span class="svc-name">E-book circulation</span><span class="svc-bar"><span class="svc-fill" style="width:{eb.get('total',0)/ec.get('total',1)*100:.1f}%"></span></span><span class="svc-count">{eb.get('total',0)/1e6:.0f}M</span></div>
  <div class="svc-row"><span class="svc-name">E-audio circulation</span><span class="svc-bar"><span class="svc-fill" style="width:{ea.get('total',0)/ec.get('total',1)*100:.1f}%"></span></span><span class="svc-count">{ea.get('total',0)/1e6:.0f}M</span></div>
  <div class="svc-row"><span class="svc-name">E-video circulation</span><span class="svc-bar"><span class="svc-fill" style="width:{ev.get('total',0)/ec.get('total',1)*100:.1f}%"></span></span><span class="svc-count">{ev.get('total',0)/1e6:.0f}M</span></div>
</div>"""

        body += f"""

<h3>Programs & attendance — by age group</h3>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{protot.get('total',0)/1e6:.1f}M</div><div class="label">Total programs offered</div></div>
  <div class="stat-card"><div class="num">{atttot.get('total',0)/1e6:.0f}M</div><div class="label">Total program attendance</div></div>
  <div class="stat-card"><div class="num">{att05.get('total',0)/1e6:.0f}M</div><div class="label">Ages 0–5 attendance</div></div>
  <div class="stat-card"><div class="num">{att611.get('total',0)/1e6:.0f}M</div><div class="label">Ages 6–11 attendance</div></div>
  <div class="stat-card"><div class="num">{attya.get('total',0)/1e6:.0f}M</div><div class="label">Young adult attendance</div></div>
  <div class="stat-card"><div class="num">{attad.get('total',0)/1e6:.0f}M</div><div class="label">Adult attendance</div></div>
</div>"""

        # Programs by delivery mode
        body += f"""
<h3>Program delivery — online vs offsite vs virtual</h3>
<p class="wiki-sub">The pandemic permanently changed library programming. In FY2024, <strong>{proon.get('total',0)/1e6:.1f}M programs were delivered online</strong> — a fundamental shift from the pre-COVID in-person model.</p>
<div class="services-bars">
  <div class="svc-row"><span class="svc-name">Online programs</span><span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{proon.get('total',0)/protot.get('total',1)*100:.1f}%"></span></span><span class="svc-count">{proon.get('total',0)/1e6:.1f}M</span></div>
  <div class="svc-row"><span class="svc-name">Offsite programs</span><span class="svc-bar"><span class="svc-fill" style="width:{pd.get('programs_offsite',{}).get('total',0)/protot.get('total',1)*100:.1f}%"></span></span><span class="svc-count">{pd.get('programs_offsite',{}).get('total',0)/1e3:.0f}K</span></div>
  <div class="svc-row"><span class="svc-name">Virtual programs</span><span class="svc-bar"><span class="svc-fill" style="width:{provir.get('total',0)/protot.get('total',1)*100:.1f}%"></span></span><span class="svc-count">{provir.get('total',0)/1e3:.0f}K</span></div>
</div>"""

        body += f"""

<h3>Internet access — libraries as connectivity hubs</h3>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{wifi.get('total',0)/1e6:.0f}M</div><div class="label">WiFi sessions</div></div>
  <div class="stat-card"><div class="num">{pitu.get('total',0)/1e6:.0f}M</div><div class="label">Public internet users</div></div>
  <div class="stat-card"><div class="num">{gpt.get('total',0)/1e3:.0f}K</div><div class="label">Public internet terminals</div></div>
  <div class="stat-card"><div class="num">{pd.get('views',{}).get('total',0)/1e6:.0f}M</div><div class="label">Virtual program views</div></div>
</div>"""

        # Capital funding by source
        cap_total = caprev.get('total', 0) or 1
        body += f"""

<h3>Capital funding — where the money comes from</h3>
<p class="wiki-sub">Capital revenue funds building construction, renovation, and major equipment. {capex.get('total',0)/1e9:.1f}B in capital expenditures in FY2024, funded by local, state, federal, and other sources.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${caploc.get('total',0)/1e6:.0f}M</div><div class="label">Local capital revenue</div></div>
  <div class="stat-card"><div class="num">${capst.get('total',0)/1e6:.0f}M</div><div class="label">State capital revenue</div></div>
  <div class="stat-card"><div class="num">${capfed.get('total',0)/1e6:.0f}M</div><div class="label">Federal capital revenue</div></div>
  <div class="stat-card"><div class="num">${capoth.get('total',0)/1e6:.0f}M</div><div class="label">Other capital revenue</div></div>
  <div class="stat-card"><div class="num">${capex.get('total',0)/1e9:.1f}B</div><div class="label">Total capital expenditures</div></div>
</div>
<div class="services-bars">
  <div class="svc-row"><span class="svc-name">Local</span><span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{caploc.get('total',0)/cap_total*100:.1f}%"></span></span><span class="svc-count">${caploc.get('total',0)/1e6:.0f}M</span></div>
  <div class="svc-row"><span class="svc-name">State</span><span class="svc-bar"><span class="svc-fill" style="width:{capst.get('total',0)/cap_total*100:.1f}%"></span></span><span class="svc-count">${capst.get('total',0)/1e6:.0f}M</span></div>
  <div class="svc-row"><span class="svc-name">Federal</span><span class="svc-bar"><span class="svc-fill" style="width:{capfed.get('total',0)/cap_total*100:.1f}%"></span></span><span class="svc-count">${capfed.get('total',0)/1e6:.0f}M</span></div>
  <div class="svc-row"><span class="svc-name">Other</span><span class="svc-bar"><span class="svc-fill" style="width:{capoth.get('total',0)/cap_total*100:.1f}%"></span></span><span class="svc-count">${capoth.get('total',0)/1e6:.0f}M</span></div>
</div>

<p class="rsrc">Data: IMLS Public Libraries Survey FY2024 (PLS_FY24_AE_pud24i), 9,249 library systems. E-circulation counts e-book, e-audio, and e-video checkouts separately. Program delivery modes: "online" = live-streamed/scheduled online, "virtual" = on-demand/recorded, "offsite" = at external locations. Capital revenue sources: local, state, federal, and other (donations, grants from non-government sources).</p>"""

    # ---- Historical Academic Library Trends (NCES ALS 2000-2012 + IPEDS 2023) ----
    als = stats.get('academic', {})
    if als and als.get('trend_years'):
        years = als['trend_years']
        n_yrs = len(years)
        yr_labels = ', '.join(str(y) for y in years)
        last_inst = als['trend_institutions'][-1] if n_yrs else 0
        last_exp = als['trend_expenditures'][-1] if n_yrs else 0
        last_coll = als['trend_collections'][-1] if n_yrs else 0
        last_staff = als['trend_staff_fte'][-1] if n_yrs else 0
        last_pres = als['trend_presentations'][-1] if n_yrs else 0
        last_sal = als['trend_salaries'][-1] if n_yrs else 0
        last_sfte = als['trend_student_fte'][-1] if n_yrs else 0
        latest_year = years[-1] if n_yrs else 0

        # Compute percentage changes from first available to last
        def _pct_change(first, last):
            if first and last:
                return ((last - first) / first) * 100
            return None

        inst_chg = _pct_change(als['trend_institutions'][0], last_inst)
        exp_chg = _pct_change(als['trend_expenditures'][0], last_exp)
        # Staff FTE: first valid value (2000 was 0) to last
        first_staff = next((v for v in als['trend_staff_fte'] if v > 0), 0)
        staff_chg = _pct_change(first_staff, last_staff)
        pres_chg = _pct_change(als['trend_presentations'][0], last_pres)

        # Format collection number (2023 counts include e-resources — much larger)
        coll_display = f"{last_coll/1e6:.1f}M" if last_coll < 1e9 else f"{last_coll/1e9:.2f}B"

        body += f"""

<h2 id="als-trends">Academic Library Trends (NCES ALS/IPEDS 2000–2023)</h2>
<p class="wiki-sub">The NCES Academic Library Survey collected data from degree-granting postsecondary institutions across {n_yrs} survey vintages ({yr_labels}). After 2012 the standalone ALS was discontinued and data collection was folded into IPEDS as the Academic Libraries component, continuing annually from 2014 onward (staffing was not collected 2014–2019). This is the only national census of college &amp; university libraries, capturing staffing, collections, expenditures, and services over a 23-year span.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{last_inst:,}</div><div class="label">Institutions ({latest_year})</div></div>
  <div class="stat-card"><div class="num">${last_exp/1e9:.2f}B</div><div class="label">Total expenditures</div></div>
  <div class="stat-card"><div class="num">{coll_display}</div><div class="label">Total collection items</div></div>
  <div class="stat-card"><div class="num">{last_staff:,}</div><div class="label">Total staff (FTE)</div></div>
  <div class="stat-card"><div class="num">${last_sal/1e9:.2f}B</div><div class="label">Total salaries</div></div>
  <div class="stat-card"><div class="num">{last_pres:,}</div><div class="label">Presentations (2012)</div></div>
  <div class="stat-card"><div class="num">{last_sfte/1e6:.1f}M</div><div class="label">Student FTE</div></div>
  <div class="stat-card"><div class="num">{inst_chg:+.1f}%</div><div class="label">Institution growth 2000→{latest_year}</div></div>
</div>"""

        # 2023-specific digital resource stats (only available in IPEDS 2023)
        if als.get('ebooks_2023'):
            eb = als['ebooks_2023']
            es = als['eserials_2023']
            ed = als['edatabase_2023']
            illp = als['ill_provided_2023']
            illr = als['ill_received_2023']
            tcirc = als['tcirc_2023']
            body += f"""
<h3>Digital resources & interlibrary loan (IPEDS 2023 only)</h3>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{eb/1e6:.1f}M</div><div class="label">E-books</div></div>
  <div class="stat-card"><div class="num">{es/1e6:.1f}M</div><div class="label">E-serials</div></div>
  <div class="stat-card"><div class="num">{ed/1e3:.0f}K</div><div class="label">E-databases</div></div>
  <div class="stat-card"><div class="num">{tcirc/1e6:.1f}M</div><div class="label">Total circulation</div></div>
  <div class="stat-card"><div class="num">{illp/1e6:.1f}M</div><div class="label">ILL provided</div></div>
  <div class="stat-card"><div class="num">{illr/1e3:.0f}K</div><div class="label">ILL received</div></div>
</div>"""

        # Build trend data table (year × metric)
        body += """
<h3>Temporal trend data</h3>
<table class="wikitable trend-table">
  <tr><th>Year</th><th>Institutions</th><th>Staff FTE</th><th>Expenditures</th><th>Collections</th><th>Salaries</th><th>Presentations</th><th>Student FTE</th></tr>"""
        for i, yr in enumerate(years):
            exp_v = als['trend_expenditures'][i]
            sal_v = als['trend_salaries'][i]
            sfte_v = als['trend_student_fte'][i]
            coll_v = als['trend_collections'][i]
            # Format collection: millions for old ALS, billions for 2023
            coll_str = f"{coll_v/1e6:.1f}M" if coll_v < 1e9 else f"{coll_v/1e9:.2f}B"
            body += f"""
  <tr>
    <td class="yr">{yr}</td>
    <td>{als['trend_institutions'][i]:,}</td>
    <td>{als['trend_staff_fte'][i]:,}</td>
    <td class="pct">${exp_v/1e6:,.0f}M</td>
    <td>{coll_str}</td>
    <td>${sal_v/1e6:,.0f}M</td>
    <td>{als['trend_presentations'][i]:,}</td>
    <td>{sfte_v:,}</td>
  </tr>"""
        body += '\n</table>'
        body += '<p class="rsrc">Note: From 2014 onward (IPEDS), collection counts include e-books, e-serials, and e-databases, which the pre-2012 ALS counted only as physical items — this explains the apparent discontinuity in collection totals after 2012. Staffing (FTE) was not collected in 2014–2019. Expenditure figures are nominal (not inflation-adjusted).</p>'

        # Inline SVG bar chart for expenditures over time
        if n_yrs >= 2:
            exp_vals = als['trend_expenditures']
            max_exp = max(exp_vals) if max(exp_vals) > 0 else 1
            bars = []
            chart_w = 700
            chart_h = 200
            bar_w = (chart_w - 60) / n_yrs
            for i, yr in enumerate(years):
                h = (exp_vals[i] / max_exp) * (chart_h - 40) if exp_vals[i] else 0
                x = 40 + i * bar_w
                y = chart_h - 30 - h
                fill = '#3b82f6' if yr <= 2012 else '#ef4444'  # red for IPEDS years (2014+)
                bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w*0.7:.1f}" height="{h:.1f}" fill="{fill}" rx="2"/>')
                bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{chart_h - 15:.1f}" text-anchor="middle" font-size="11" fill="#666">{yr}</text>')
                if exp_vals[i]:
                    bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{y - 5:.1f}" text-anchor="middle" font-size="10" fill="#333">${exp_vals[i]/1e9:.1f}B</text>')
            svg = f'''<h3>Total expenditures by year</h3>
<svg viewBox="0 0 {chart_w} {chart_h + 20}" class="trend-chart" xmlns="http://www.w3.org/2000/svg">
  <line x1="40" y1="{chart_h - 30}" x2="{chart_w - 20}" y2="{chart_h - 30}" stroke="#ccc" stroke-width="1"/>
  {''.join(bars)}
  <text x="{chart_w - 20}" y="15" text-anchor="end" font-size="10" fill="#999">🔴 = IPEDS (2014+, post-survey transfer)</text>
</svg>'''
            body += svg

        # Staff FTE decline chart
        staff_vals = als['trend_staff_fte']
        if any(v > 0 for v in staff_vals):
            max_staff = max(v for v in staff_vals if v > 0)
            s_bars = []
            for i, yr in enumerate(years):
                sv = staff_vals[i]
                h = (sv / max_staff) * (chart_h - 40) if sv > 0 else 0
                x = 40 + i * bar_w
                y = chart_h - 30 - h
                fill = '#10b981' if yr <= 2012 else '#ef4444'  # red for IPEDS years
                s_bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w*0.7:.1f}" height="{h:.1f}" fill="{fill}" rx="2"/>')
                s_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{chart_h - 15:.1f}" text-anchor="middle" font-size="11" fill="#666">{yr}</text>')
                if sv > 0:
                    s_bars.append(f'<text x="{x + bar_w*0.35:.1f}" y="{y - 5:.1f}" text-anchor="middle" font-size="10" fill="#333">{sv:,}</text>')
            svg2 = f'''<h3>Total staff FTE by year — the long decline</h3>
<svg viewBox="0 0 {chart_w} {chart_h + 20}" class="trend-chart" xmlns="http://www.w3.org/2000/svg">
  <line x1="40" y1="{chart_h - 30}" x2="{chart_w - 20}" y2="{chart_h - 30}" stroke="#ccc" stroke-width="1"/>
  {''.join(s_bars)}
</svg>'''
            body += svg2

        # Largest academic libraries table
        if stats.get('academic_largest'):
            body += f"""
<h3>Largest academic library collections ({latest_year})</h3>
<table class="wikitable als-largest-table">
  <tr><th>#</th><th>Institution</th><th>City</th><th>State</th><th>Collection</th><th>Expenditures</th><th>Staff FTE</th><th>Year</th></tr>"""
            for i, lib in enumerate(stats['academic_largest'], 1):
                exp_str = f"${lib['expenditure']:,}" if lib['expenditure'] else '—'
                staff_str = f"{lib['staff_fte']:.0f}" if lib['staff_fte'] else '—'
                yr_label = lib.get('year', '2012')
                coll_str = f"{lib['collection']:,}" if lib['collection'] < 1e9 else f"{lib['collection']/1e9:.2f}B"
                body += f"""
  <tr>
    <td>{i}</td>
    <td><a href="search.html?q={esc(lib['name'])}">{esc(lib['name'])}</a></td>
    <td>{esc(lib['city']) or '—'}</td>
    <td>{esc(lib['state']) or '—'}</td>
    <td class="pct">{coll_str}</td>
    <td>{exp_str}</td>
    <td>{staff_str}</td>
    <td>{yr_label}</td>
  </tr>"""
            body += '\n</table>'

        body += f'<p class="rsrc">Source: NCES Academic Library Survey (ALS) 2000–2012 (biennial) + IPEDS Academic Libraries 2014–2023 (annual). {als.get("institutions_2023", 0):,} institutions in 2023, {als.get("institutions_2012", 0):,} in 2012. Academic libraries are browsable via search (filter by type "academic").</p>'

    # ---- Institutional Characteristics (IPEDS HD2023 + EF2023A) ----
    ic = stats.get('institution_characteristics', {})
    if ic and ic.get('total_institutions'):
        ic_n = ic['total_institutions']
        ic_enr = ic.get('total_enrollment', 0)
        ic_hbcu = ic.get('hbcu', 0)
        ic_tribal = ic.get('tribal', 0)
        ic_land = ic.get('land_grant', 0)
        ic_med = ic.get('medical', 0)

        body += f"""

<h2 id="institution-profiles">Institutional Landscape — Who Has a Library?</h2>
<p class="wiki-sub">Not all colleges are alike. The IPEDS institutional characteristics survey classifies every degree-granting institution by Carnegie Classification, governance (public/private), and locale — providing context for the {ic_n:,} institutions whose libraries are tracked above. Understanding the institutional landscape reveals which types of colleges invest most in their libraries.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{ic_n:,}</div><div class="label">Total institutions</div></div>
  <div class="stat-card"><div class="num">{ic_enr/1e6:.1f}M</div><div class="label">Total enrollment</div></div>
  <div class="stat-card"><div class="num">{ic_hbcu}</div><div class="label">HBCUs</div></div>
  <div class="stat-card"><div class="num">{ic_tribal}</div><div class="label">Tribal colleges</div></div>
  <div class="stat-card"><div class="num">{ic_land}</div><div class="label">Land-grant institutions</div></div>
  <div class="stat-card"><div class="num">{ic_med}</div><div class="label">Medical schools</div></div>
</div>"""

        # Carnegie classification breakdown
        if ic.get('by_carnegie_broad'):
            body += """
<h3>By Carnegie Classification — institutional type</h3>
<div class="services-bars">"""
            max_cc = max(c.get('count', 0) for c in ic['by_carnegie_broad']) or 1
            for c in ic['by_carnegie_broad']:
                cnt = c.get('count', 0)
                pct_w = (cnt / max_cc) * 100
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(c["category"])}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{cnt:,}</span>
  </div>"""
            body += '\n</div>'

        # Control breakdown table
        if ic.get('by_control'):
            body += """
<h3>By governance — public vs private</h3>
<table class="wikitable">
  <tr><th>Type</th><th>Institutions</th><th>Share</th></tr>"""
            ic_total = ic_n or 1
            for c in ic['by_control']:
                cnt = c.get('count', 0)
                body += f'\n  <tr><td>{esc(c["type"])}</td><td>{cnt:,}</td><td class="pct">{100*cnt/ic_total:.1f}%</td></tr>'
            body += '\n</table>'

        # Locale breakdown
        if ic.get('by_locale'):
            body += """
<h3>By locale — where institutions are located</h3>
<table class="wikitable">
  <tr><th>Locale</th><th>Institutions</th><th>Share</th></tr>"""
            for c in ic['by_locale']:
                cnt = c.get('count', 0)
                body += f'\n  <tr><td>{esc(c["locale"])}</td><td>{cnt:,}</td><td class="pct">{100*cnt/ic_n:.1f}%</td></tr>'
            body += '\n</table>'

        body += '<p class="rsrc">Data: NCES IPEDS Institutional Characteristics (HD2023) and Fall Enrollment (EF2023A). Carnegie Classification uses the 2021 update. HBCU = Historically Black College or University. Land-grant institutions are designated under the Morrill Act. Enrollment figures are fall 2023 12-month total.</p>'

    # ---- Book Censorship Database (EveryLibrary Institute / Magnusson) ----
    bc = stats.get('book_censorship', {})
    if bc and bc.get('total_challenges'):
        bc_n = bc['total_challenges']
        bc_banned = bc.get('banned_removed', 0)
        bc_dr = bc.get('date_range', '')
        bc_top_state = bc.get('by_state', [{}])[0] if bc.get('by_state') else {}

        body += f"""

<h2 id="book-censorship">Book Challenges & Bans ({bc_dr})</h2>
<p class="wiki-sub">The EveryLibrary Institute's <a href="https://bookcensorship.net/" target="_blank" rel="noopener">Book Censorship Database</a>, maintained by Dr. Tasslyn Magnusson, tracks every reported attempt to restrict, remove, or ban books in U.S. schools and libraries. {bc_n:,} challenges documented across {len(bc.get('by_state',[]))} states — {bc_banned:,} resulting in removals or bans. This is the most comprehensive crowdsourced record of the wave of book censorship that accelerated in 2021.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{bc_n:,}</div><div class="label">Total challenges</div></div>
  <div class="stat-card"><div class="num">{bc_banned:,}</div><div class="label">Banned / removed</div></div>
  <div class="stat-card"><div class="num">{bc_top_state.get('count', 0):,}</div><div class="label">Most challenges ({esc(bc_top_state.get('state', ''))})</div></div>
  <div class="stat-card"><div class="num">{len(bc.get('by_year', []))}</div><div class="label">Years tracked</div></div>
</div>"""

        # Challenges by year SVG bar chart
        if bc.get('by_year'):
            by_yr = bc['by_year']
            max_yr = max(r.get('count', 0) for r in by_yr) or 1
            yr_n = len(by_yr)
            bw = 32
            chart_w = yr_n * bw + 60
            chart_h = 220
            body += f'\n<h3>Challenges per year</h3>\n<svg class="trend-chart" viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Book challenges by year">'
            for i, r in enumerate(by_yr):
                yr = r.get('year', '')
                cnt = r.get('count', 0)
                h = (cnt / max_yr) * (chart_h - 50) if max_yr else 0
                x = 40 + i * bw
                body += f'<rect x="{x}" y="{chart_h - 30 - h:.1f}" width="{bw - 6}" height="{h:.1f}" fill="var(--accent-red)" rx="3"/>'
                body += f'<text x="{x + (bw - 6)/2:.0f}" y="{chart_h - 12}" text-anchor="middle" class="axis-text">{yr}</text>'
                body += f'<text x="{x + (bw - 6)/2:.0f}" y="{chart_h - 35 - h:.1f}" text-anchor="middle" class="bar-label">{cnt:,}</text>'
            body += '</svg>'

        # Top states table
        if bc.get('by_state'):
            body += """
<h3>Top states by number of challenges</h3>
<table class="wikitable">
  <tr><th>State</th><th>Challenges</th><th>Share</th></tr>"""
            for r in bc['by_state'][:15]:
                cnt = r.get('count', 0)
                body += f'\n  <tr><td><a href="states/{esc(r["state"])}.html">{esc(r["state"])}</a></td><td>{cnt:,}</td><td class="pct">{100*cnt/bc_n:.1f}%</td></tr>'
            body += '\n</table>'

        # Most challenged books
        if bc.get('top_books'):
            body += """
<h3>Most challenged books</h3>
<table class="wikitable">
  <tr><th>Book</th><th>Challenges</th></tr>"""
            for r in bc['top_books'][:15]:
                body += f'\n  <tr><td>{esc(r["title"])}</td><td>{r.get("count", 0):,}</td></tr>'
            body += '\n</table>'

        # Outcomes table
        if bc.get('by_decision'):
            body += """
<h3>Outcomes — what happened to the challenges</h3>
<table class="wikitable">
  <tr><th>Decision</th><th>Count</th><th>Share</th></tr>"""
            for r in bc['by_decision'][:8]:
                cnt = r.get('count', 0)
                body += f'\n  <tr><td>{esc(r["decision"])}</td><td>{cnt:,}</td><td class="pct">{100*cnt/bc_n:.1f}%</td></tr>'
            body += '\n</table>'

        # Library type breakdown
        if bc.get('by_library_type'):
            body += """
<h3>By library type</h3>
<div class="services-bars">"""
            max_lt = max(r.get('count', 0) for r in bc['by_library_type']) or 1
            for r in bc['by_library_type']:
                cnt = r.get('count', 0)
                pct_w = (cnt / max_lt) * 100
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(r["type"])}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{cnt:,}</span>
  </div>"""
            body += '\n</div>'

        body += '<p class="rsrc">Source: EveryLibrary Institute Book Censorship Database (bookcensorship.net), maintained by Dr. Tasslyn Magnusson. Data is crowdsourced from public reports, news articles, and FOIA requests. "Banned/Removed" includes decisions where the book was removed from shelves or access was restricted. Challenge counts include repeated challenges of the same title in different jurisdictions.</p>'

    # ---- NTIA Tribal Broadband Connectivity Program (TBCP) ----
    tb = stats.get('tribal_broadband', {})
    if tb and tb.get('total_awards'):
        tb_n = tb['total_awards']
        tb_fund = tb.get('total_funding', 0)
        tb_avg = tb.get('avg_award', 0)
        tb_states = tb.get('states_covered', 0)

        body += f"""

<h2 id="tribal-broadband">Tribal Broadband Connectivity Program (TBCP)</h2>
<p class="wiki-sub">The NTIA's Tribal Broadband Connectivity Program, funded by the Infrastructure Investment and Jobs Act (IIJA), awarded <strong>${tb_fund/1e9:.2f} billion</strong> across {tb_n} Tribal projects. Awards support broadband infrastructure deployment, digital adoption, and planning on Tribal lands — directly serving libraries and communities that have historically lacked adequate internet access. States are derived from award ZIP codes.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${tb_fund/1e9:.2f}B</div><div class="label">Total awarded</div></div>
  <div class="stat-card"><div class="num">{tb_n}</div><div class="label">Tribal awards</div></div>
  <div class="stat-card"><div class="num">${tb_avg/1e6:.1f}M</div><div class="label">Average award</div></div>
  <div class="stat-card"><div class="num">{tb_states}</div><div class="label">States covered</div></div>
</div>"""

        # BIA Region breakdown
        if tb.get('by_bia_region'):
            body += """
<h3>Funding by BIA Region</h3>
<div class="services-bars">"""
            max_r = max(r.get('total', 0) for r in tb['by_bia_region']) or 1
            for r in tb['by_bia_region']:
                amt = r.get('total', 0)
                pct_w = (amt / max_r) * 100
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(r["region"])}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">${amt/1e6:,.0f}M</span>
  </div>"""
            body += '\n</div>'

        # Largest awards table
        if tb.get('top_awards'):
            body += """
<h3>Largest awards</h3>
<table class="wikitable">
  <tr><th>Recipient</th><th>State</th><th>BIA Region</th><th>Amount</th><th>Project Type</th></tr>"""
            for r in tb['top_awards'][:15]:
                body += f'\n  <tr><td>{esc(r["recipient"])}</td><td>{esc(r["state"]) or "—"}</td><td>{esc(r.get("bia_region",""))}</td><td class="pct">${r["amount"]/1e6:,.1f}M</td><td>{esc(r.get("project_type",""))}</td></tr>'
            body += '\n</table>'

        # Award size distribution
        if tb.get('size_distribution'):
            body += """
<h3>Award size distribution</h3>
<div class="services-bars">"""
            max_s = max(r.get('count', 0) for r in tb['size_distribution']) or 1
            for r in tb['size_distribution']:
                cnt = r.get('count', 0)
                pct_w = (cnt / max_s) * 100
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(r["bucket"])}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{cnt}</span>
  </div>"""
            body += '\n</div>'

        # By project type
        if tb.get('by_project_type'):
            body += """
<h3>By project type</h3>
<table class="wikitable">
  <tr><th>Project Type</th><th>Awards</th><th>Total Funding</th></tr>"""
            for r in tb['by_project_type']:
                body += f'\n  <tr><td>{esc(r["type"])}</td><td>{r.get("count", 0)}</td><td class="pct">${r.get("total", 0)/1e6:,.1f}M</td></tr>'
            body += '\n</table>'

        body += '<p class="rsrc">Source: NTIA Tribal Broadband Connectivity Program (TBCP) award data via ArcGIS REST API. Funded by the Infrastructure Investment and Jobs Act (IIJA). BIA = Bureau of Indian Affairs regional offices. States are derived from award ZIP codes (3-digit prefix mapping).</p>'

    # ---- USAC Emergency Connectivity Fund (ECF) ----
    ecf = stats.get('ecf', {})
    if ecf and ecf.get('total_records'):
        ecf_n = ecf['total_records']
        ecf_fund = ecf.get('total_funding', 0)
        ecf_dr = ecf.get('date_range', '')
        ecf_lib = ecf.get('library', {})
        ecf_lib_n = ecf_lib.get('total_records', 0)
        ecf_lib_fund = ecf_lib.get('total_funding', 0)

        body += f"""

<h2 id="ecf">Emergency Connectivity Fund (ECF) — Device Distribution</h2>
<p class="wiki-sub">The FCC's Emergency Connectivity Fund, a pandemic-era program ({ecf_dr}), distributed <strong>${ecf_fund/1e9:.2f} billion</strong> to help schools and libraries provide laptops, tablets, Wi-Fi hotspots, and broadband connections to students and patrons. Libraries received ${ecf_lib_fund/1e6:,.0f}M across {ecf_lib_n:,} funding requests — a massive one-time federal investment in digital access equipment that directly addressed the homework gap.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${ecf_fund/1e9:.2f}B</div><div class="label">Total ECF funding</div></div>
  <div class="stat-card"><div class="num">{ecf_n:,}</div><div class="label">Funding requests</div></div>
  <div class="stat-card"><div class="num">${ecf_lib_fund/1e6:,.0f}M</div><div class="label">Library funding</div></div>
  <div class="stat-card"><div class="num">{ecf_lib_n:,}</div><div class="label">Library requests</div></div>
</div>"""

        # Product type breakdown
        if ecf.get('by_product_type'):
            body += """
<h3>What was purchased — by product type</h3>
<div class="services-bars">"""
            max_p = max(r.get('funding', 0) for r in ecf['by_product_type']) or 1
            for r in ecf['by_product_type'][:10]:
                amt = r.get('funding', 0)
                pct_w = (amt / max_p) * 100
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(r["type"])}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">${amt/1e6:,.0f}M</span>
  </div>"""
            body += '\n</div>'

        # Applicant type table
        if ecf.get('by_applicant_type'):
            body += """
<h3>By applicant type</h3>
<table class="wikitable">
  <tr><th>Applicant Type</th><th>Records</th><th>Funding</th><th>Share</th></tr>"""
            for r in ecf['by_applicant_type']:
                cnt = r.get('count', 0)
                fund = r.get('funding', 0)
                body += f'\n  <tr><td>{esc(r["type"])}</td><td>{cnt:,}</td><td class="pct">${fund/1e6:,.0f}M</td><td>{100*fund/ecf_fund:.1f}%</td></tr>'
            body += '\n</table>'

        # Library-specific section
        if ecf_lib and ecf_lib.get('by_state'):
            body += f"""
<h3>Library ECF funding by state</h3>
<p class="wiki-sub">Of the ${ecf_fund/1e9:.2f}B total, libraries received ${ecf_lib_fund/1e6:,.0f}M ({100*ecf_lib_fund/ecf_fund:.1f}%) across {ecf_lib.get('unique_libraries', 0):,} unique library applicants.</p>
<table class="wikitable">
  <tr><th>State</th><th>Library requests</th><th>Library funding</th></tr>"""
            for r in ecf_lib['by_state'][:15]:
                cnt = r.get('count', 0)
                fund = r.get('funding', 0)
                body += f'\n  <tr><td><a href="states/{esc(r["state"])}.html">{esc(r["state"])}</a></td><td>{cnt:,}</td><td class="pct">${fund/1e6:,.0f}M</td></tr>'
            body += '\n</table>'

        # Library product breakdown
        if ecf_lib and ecf_lib.get('by_product_type'):
            body += """
<h3>What libraries purchased</h3>
<table class="wikitable">
  <tr><th>Product Type</th><th>Records</th><th>Funding</th></tr>"""
            for r in ecf_lib['by_product_type']:
                cnt = r.get('count', 0)
                fund = r.get('funding', 0)
                body += f'\n  <tr><td>{esc(r["type"])}</td><td>{cnt:,}</td><td class="pct">${fund/1e6:,.0f}M</td></tr>'
            body += '\n</table>'

        body += '<p class="rsrc">Source: USAC Emergency Connectivity Fund (ECF) FCC Form 471 data via Socrata API (opendata.usac.org). ECF was funded by the American Rescue Plan Act (2021) and operated 2021–2024. Funding amounts are approved (committed) values. "Blank/services" rows represent broadband connection FRNs rather than device purchases.</p>'

    # ---- BLS Librarian Salaries (OES May 2024) ----
    bls = stats.get('bls_salaries', {})
    if bls and bls.get('occupations'):
        body += f"""

<h2 id="librarian-salaries">Library Worker Salaries (BLS OES 2024)</h2>
<p class="wiki-sub">The Bureau of Labor Statistics' Occupational Employment and Wage Statistics survey tracks employment and wages for every occupation by state — including library workers. These figures reveal how much the people who run libraries actually earn, and the wide geographic variation in library worker compensation.</p>"""

        for soc, occ in bls['occupations'].items():
            title = occ.get('title', soc)
            emp = occ.get('total_employment', 0)
            avg_wage = occ.get('avg_mean_wage', 0)
            high_wage = occ.get('highest_mean_wage', 0)
            low_wage = occ.get('lowest_mean_wage', 0)
            states_n = occ.get('states_with_data', 0)

            body += f"""
<h3>{esc(title)} <span class="soc-code">({esc(soc)})</span></h3>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{emp:,.0f}</div><div class="label">Total employed</div></div>
  <div class="stat-card"><div class="num">${avg_wage:,.0f}</div><div class="label">Avg mean wage</div></div>
  <div class="stat-card"><div class="num">${high_wage:,.0f}</div><div class="label">Highest (any state)</div></div>
  <div class="stat-card"><div class="num">${low_wage:,.0f}</div><div class="label">Lowest (any state)</div></div>
</div>"""

            # Top states by wage
            if occ.get('top_by_wage'):
                body += """
<table class="wikitable">
  <tr><th>State</th><th>Mean Annual Wage</th><th>Median Annual Wage</th><th>Employment</th></tr>"""
                for r in occ['top_by_wage'][:10]:
                    body += f'\n  <tr><td><a href="states/{esc(r["state"])}.html">{esc(r["state"])}</a></td><td class="pct">${r["mean_wage"]:,.0f}</td><td>${r["median_wage"]:,.0f}</td><td>{r["employment"]:,.0f}</td></tr>'
                body += '\n</table>'

            # Lowest-paying states
            if occ.get('lowest_by_wage'):
                body += """
<h4>Lowest-paying states</h4>
<table class="wikitable">
  <tr><th>State</th><th>Mean Annual Wage</th><th>Employment</th></tr>"""
                for r in occ['lowest_by_wage'][:5]:
                    body += f'\n  <tr><td><a href="states/{esc(r["state"])}.html">{esc(r["state"])}</a></td><td class="pct">${r["mean_wage"]:,.0f}</td><td>{r["employment"]:,.0f}</td></tr>'
                body += '\n</table>'

        body += f'<p class="rsrc">Source: BLS Occupational Employment and Wage Statistics (OES), May 2024 survey. SOC = Standard Occupational Classification code. Wages are annual, before taxes. Employment counts include full-time and part-time workers. Library occupations include Librarians and Media Collections Specialists (25-4022), Library Technicians (25-4031), Library Assistants (43-4111), and Library Science Teachers (25-1082).</p>'

    # ---- FCC Affordable Connectivity Program (ACP) ----
    acp = stats.get('acp', {})
    if acp and acp.get('total_national_claims'):
        acp_total = acp['total_national_claims']
        acp_enrolled = acp.get('total_national_enrolled', 0)
        acp_dr = acp.get('date_range', '')
        acp_months = acp.get('months_active', 0)
        acp_top = acp.get('top_by_enrollment', [{}])[0] if acp.get('top_by_enrollment') else {}

        body += f"""

<h2 id="acp">Affordable Connectivity Program (ACP)</h2>
<p class="wiki-sub">The Affordable Connectivity Program was a $14.2 billion federal broadband subsidy that helped low-income households pay for internet service. Before the program ended in June 2024, <strong>{acp_enrolled/1e6:.1f} million households</strong> had enrolled. This data reveals the enormous unmet demand for affordable internet - the very demand that libraries help address through free WiFi, public computers, and hotspot lending. Over {acp_months} months, ${acp_total/1e9:.1f}B in claims were processed.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{acp_enrolled/1e6:.1f}M</div><div class="label">Households enrolled</div></div>
  <div class="stat-card"><div class="num">${acp_total/1e9:.1f}B</div><div class="label">Total claims paid</div></div>
  <div class="stat-card"><div class="num">{acp_months}</div><div class="label">Months active</div></div>
  <div class="stat-card"><div class="num">{acp_top.get('state', '')}</div><div class="label">Top state by enrollment</div></div>
</div>"""

        # Monthly claims trend SVG chart
        if acp.get('monthly_trend'):
            mt = acp['monthly_trend']
            max_amt = max(m.get('amount', 0) for m in mt) or 1
            n = len(mt)
            bw = 18
            chart_w = n * bw + 60
            chart_h = 220
            body += f'\n<h3>Monthly claims trend ({acp_months} months)</h3>\n<svg class="trend-chart" viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="ACP monthly claims trend">'
            for i, m in enumerate(mt):
                amt = m.get('amount', 0)
                h = (amt / max_amt) * (chart_h - 50) if max_amt else 0
                x = 40 + i * bw
                body += f'<rect x="{x}" y="{chart_h - 30 - h:.1f}" width="{bw - 3}" height="{h:.1f}" fill="var(--accent-blue)" rx="2"/>'
                if i % 3 == 0:
                    label = m['month'][:3]
                    body += f'<text x="{x + (bw - 3)/2:.0f}" y="{chart_h - 12}" text-anchor="middle" class="axis-text">{label}</text>'
                if i == n - 1 or i % 6 == 0:
                    body += f'<text x="{x + (bw - 3)/2:.0f}" y="{chart_h - 35 - h:.1f}" text-anchor="middle" class="bar-label">${amt/1e6:.0f}M</text>'
            body += '</svg>'

        # Top states by enrollment
        if acp.get('top_by_enrollment'):
            body += """
<h3>Top states by household enrollment</h3>
<table class="wikitable">
  <tr><th>State</th><th>Households enrolled</th><th>Total claims</th></tr>"""
            for r in acp['top_by_enrollment'][:15]:
                body += f'\n  <tr><td><a href="states/{esc(r["state"])}.html">{esc(r["state"])}</a></td><td class="pct">{r["households_enrolled"]:,}</td><td>${r["total_claims"]/1e6:,.0f}M</td></tr>'
            body += '\n</table>'

        body += '<p class="rsrc">Source: FCC Affordable Connectivity Program data via USAC ACP Enrollment & Claims Tracker. Enrollment figures are unique households as of the Feb 8, 2024 enrollment freeze. Claims figures are cumulative gross claim amounts certified across 29 monthly data months (Jan 2022 - May 2024). The ACP was created by the Infrastructure Investment and Jobs Act (IIJA) and succeeded the Emergency Broadband Benefit (EBB) program. The program ended June 1, 2024 when funding was exhausted.</p>'

    # ---- USAC E-Rate (library telecommunications funding) ----
    er = stats.get('erate', {})
    if er and er.get('total_records'):
        er_n = er['total_records']
        er_cost = er.get('total_cost', 0)
        er_yr = er.get('year_range', '')
        er_apps = er.get('unique_applicants', 0)
        er_bens = er.get('unique_bens', 0)

        body += f"""

<h2 id="erate">E-Rate: Library Telecommunications Funding ({er_yr})</h2>
<p class="wiki-sub">The Universal Service E-Rate program is the largest ongoing federal program funding library and school telecommunications and internet access. Libraries apply for discounts on broadband, fiber, and internal connections via FCC Form 471. <strong>{er_apps:,} library applicants</strong> submitted {er_n:,} funding requests totaling ${er_cost/1e6:,.0f}M in pre-discount eligible costs across {er_yr}. This is the quiet, steady infrastructure funding that keeps libraries connected year after year.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${er_cost/1e6:,.0f}M</div><div class="label">Total eligible costs</div></div>
  <div class="stat-card"><div class="num">{er_n:,}</div><div class="label">Funding requests</div></div>
  <div class="stat-card"><div class="num">{er_apps:,}</div><div class="label">Unique library applicants</div></div>
  <div class="stat-card"><div class="num">{er_bens:,}</div><div class="label">Unique billed entities</div></div>
</div>"""

        # Top states by library E-Rate funding
        if er.get('by_state'):
            body += """
<h3>Top states by library E-Rate funding</h3>
<table class="wikitable">
  <tr><th>State</th><th>Records</th><th>Eligible Costs</th></tr>"""
            for r in er['by_state'][:15]:
                body += f'\n  <tr><td><a href="states/{esc(r["state"])}.html">{esc(r["state"])}</a></td><td>{r["count"]:,}</td><td class="pct">${r["cost"]/1e6:,.0f}M</td></tr>'
            body += '\n</table>'

        # By funding year
        if er.get('by_year'):
            body += """
<h3>Annual library E-Rate funding</h3>
<table class="wikitable">
  <tr><th>Funding Year</th><th>Records</th><th>Eligible Costs</th></tr>"""
            for r in er['by_year']:
                body += f'\n  <tr><td>FY{esc(r["year"])}</td><td>{r["count"]:,}</td><td class="pct">${r["cost"]/1e6:,.0f}M</td></tr>'
            body += '\n</table>'

        # By service type
        if er.get('by_function_type'):
            body += """
<h3>What E-Rate funds in libraries — by service type</h3>
<div class="services-bars">"""
            max_f = max(r.get('cost', 0) for r in er['by_function_type']) or 1
            for r in er['by_function_type'][:12]:
                amt = r.get('cost', 0)
                pct_w = (amt / max_f) * 100
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(r["type"])}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">${amt/1e6:,.0f}M</span>
  </div>"""
            body += '\n</div>'

        body += '<p class="rsrc">Source: USAC E-Rate FCC Form 471 FRN line-item data via Socrata API (opendata.usac.org, dataset hbj5-2bpj). Library subset filtered on applicant_type IN ("Library", "Library System"). Figures are pre-discount extended eligible costs (the basis for funding), not post-discount disbursements. Funding Year (FY) runs July 1 to June 30. E-Rate discounts range from 20% to 90% based on poverty level and urban/rural status.</p>'

    # ---- NTIA BEAD Broadband Allocations ----
    bead = stats.get('bead', {})
    if bead and bead.get('total_distributed'):
        bead_total = bead['total_distributed']
        bead_approp = bead.get('total_appropriated', 0)
        bead_admin = bead.get('admin_reserve', 0)
        bead_states = bead.get('states_count', 0)
        bead_top = bead.get('largest', [{}])[0] if bead.get('largest') else {}

        body += f"""

<h2 id="bead">Broadband Equity Access & Deployment (BEAD)</h2>
<p class="wiki-sub">The BEAD program is the largest broadband investment in U.S. history: <strong>${bead_total/1e9:.2f} billion</strong> allocated across {bead_states} states and territories from the Infrastructure Investment and Jobs Act. Each state received a minimum of $100M (territories $25M) plus additional funding based on their share of unserved locations. While BEAD primarily funds broadband infrastructure deployment, libraries benefit as community anchor institutions that provide public internet access in newly connected areas.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${bead_total/1e9:.2f}B</div><div class="label">Distributed to states</div></div>
  <div class="stat-card"><div class="num">${bead_approp/1e9:.2f}B</div><div class="label">Total appropriated</div></div>
  <div class="stat-card"><div class="num">${bead_admin/1e6:.0f}M</div><div class="label">NTIA admin reserve (2%)</div></div>
  <div class="stat-card"><div class="num">{bead_states}</div><div class="label">States & territories</div></div>
</div>"""

        # Top states by allocation
        if bead.get('largest'):
            body += """
<h3>Top states by BEAD allocation</h3>
<table class="wikitable">
  <tr><th>State</th><th>Allocation</th><th>Minimum</th><th>Above Minimum</th></tr>"""
            for r in bead['largest'][:15]:
                body += f'\n  <tr><td><a href="states/{esc(r["state"])}.html">{esc(r["state"])}</a></td><td class="pct">${r["allocation"]/1e9:,.2f}B</td><td>${r["minimum"]/1e6:,.0f}M</td><td>${r["above_minimum"]/1e6:,.0f}M</td></tr>'
            body += '\n</table>'

        # Smallest allocations
        if bead.get('smallest'):
            body += """
<h3>Smallest allocations (territories & small states)</h3>
<table class="wikitable">
  <tr><th>State / Territory</th><th>Allocation</th></tr>"""
            for r in bead['smallest'][:10]:
                body += f'\n  <tr><td>{esc(r["state"])}</td><td class="pct">${r["allocation"]/1e6:,.0f}M</td></tr>'
            body += '\n</table>'

        body += '<p class="rsrc">Source: NTIA Broadband Equity Access and Deployment (BEAD) Program. Allocations announced June 2023. Formula: Minimum ($100M states/$25M territories) + High-Cost Allocation (share of unserved in high-cost areas x $4.245B) + Remaining Funds (share of total unserved x balance). Unserved locations identified from FCC Broadband DATA Maps. 2% ($849M) reserved for NTIA administration.</p>'

    # ---- Library Workforce Demographics ----
    wf = stats.get('library_workforce', {})
    if wf and wf.get('total_employed'):
        wf_total = wf['total_employed']
        wf_occupations = wf.get('by_occupation', [])
        wf_gender = wf.get('gender_breakdown', {})
        wf_race = wf.get('racial_ethnic', {})
        wf_age = wf.get('age_distribution', [])
        wf_union = wf.get('union_membership', {})
        wf_education = wf.get('education', {})
        wf_facts = wf.get('key_facts', [])
        wf_challenges = wf.get('workforce_challenges', [])

        body += f"""

<h2 id="workforce">The Library Workforce: Who Works in Libraries</h2>
<p class="wiki-sub">The US library workforce comprises approximately {wf_total:,} workers across four BLS occupational categories. Librarianship is one of the most female-dominated professions in America ({wf_gender.get('female_pct',83):.0f}% women) and has a persistent racial diversity gap ({wf_race.get('white_pct',84):.0f}% white). The workforce is aging - 42% of librarians were over 55 in 2014 - signaling a wave of impending retirements. Yet education, training, and library occupations have the highest unionization rate of any professional occupation group ({wf_union.get('all_education_training_library_occupations_pct',35.5):.1f}%).</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{wf_total:,}</div><div class="label">Total library workers</div></div>
  <div class="stat-card"><div class="num">{wf_gender.get('female_pct',83):.0f}%</div><div class="label">Female (librarians)</div></div>
  <div class="stat-card"><div class="num">{wf_race.get('white_pct',84):.0f}%</div><div class="label">White (librarians)</div></div>
  <div class="stat-card"><div class="num">{wf_union.get('librarians_pct',20.5):.1f}%</div><div class="label">Librarian union rate</div></div>
  <div class="stat-card"><div class="num">{wf_union.get('all_education_training_library_occupations_pct',35.5):.1f}%</div><div class="label">All ed/library union rate (highest of any profession)</div></div>
</div>"""

        # By occupation table
        if wf_occupations:
            body += """
<h3>Library occupations (BLS OEWS 2023)</h3>
<table class="wikitable">
  <tr><th>Occupation</th><th>SOC code</th><th>Employed</th><th>Median salary</th></tr>"""
            for o in wf_occupations:
                body += f'\n  <tr><td>{esc(o.get("occupation",""))}</td><td>{esc(o.get("soc_code",""))}</td><td class="pct">{o.get("employed",0):,}</td><td>${o.get("median_salary",0):,}</td></tr>'
            body += '\n</table>'

        # Gender breakdown bars
        if wf_gender:
            body += f"""
<h3>Gender breakdown of librarians</h3>
<div class="services-bars">
  <div class="svc-row"><span class="svc-label">Female</span><span class="svc-bar"><span class="svc-fill svc-fill-people" style="width:{wf_gender.get("female_pct",83):.1f}%"></span></span><span class="svc-val">{wf_gender.get("female_pct",83):.1f}%</span></div>
  <div class="svc-row"><span class="svc-label">Male</span><span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{wf_gender.get("male_pct",16):.1f}%"></span></span><span class="svc-val">{wf_gender.get("male_pct",16):.1f}%</span></div>
  <div class="svc-row"><span class="svc-label">Nonbinary / gender nonconforming</span><span class="svc-bar"><span class="svc-fill svc-fill-green" style="width:{wf_gender.get("nonbinary_pct",0.6)*10:.1f}%"></span></span><span class="svc-val">{wf_gender.get("nonbinary_pct",0.6):.1f}%</span></div>
</div>"""

        # Racial/ethnic breakdown
        if wf_race:
            body += """
<h3>Racial / ethnic breakdown of librarians</h3>
<div class="services-bars">"""
            for label, key in [('White', 'white_pct'), ('Black/African American', 'black_pct'), ('Hispanic/Latine', 'hispanic_pct'), ('Asian', 'asian_pct')]:
                pct = wf_race.get(key, 0)
                body += f'\n  <div class="svc-row"><span class="svc-label">{label}</span><span class="svc-bar"><span class="svc-fill svc-fill-people" style="width:{pct:.1f}%"></span></span><span class="svc-val">{pct:.1f}%</span></div>'
            body += '\n</div>'

        # Union membership
        if wf_union:
            body += """
<h3>Union membership rates</h3>
<table class="wikitable">
  <tr><th>Occupation</th><th>Union rate</th></tr>"""
            for label, key in [('Librarians', 'librarians_pct'), ('Library technicians', 'library_technicians_pct'), ('Library assistants', 'library_assistants_pct'), ('All education/training/library occupations', 'all_education_training_library_occupations_pct')]:
                body += f'\n  <tr><td>{label}</td><td class="pct">{wf_union.get(key,0):.1f}%</td></tr>'
            body += '\n</table>'
            if wf_union.get('union_wage_premium'):
                body += f'<p class="wiki-sub"><strong>Union wage premium:</strong> {esc(str(wf_union.get("union_wage_premium","")))}</p>'

        # Key facts
        if wf_facts:
            body += """
<h3>Key findings</h3>
<ul class="wiki-list">"""
            for f in wf_facts[:10]:
                body += f'\n  <li>{esc(f)}</li>'
            body += '\n</ul>'

        body += f'<p class="rsrc">Source: BLS Occupational Employment and Wage Statistics (OEWS) May 2023 for employment counts and salaries; AFL-CIO Department for Professional Employees "Library Workers: Facts & Figures 2016" for gender/racial/union data; Library Journal 2023 Placements & Salaries Survey for new MLIS graduate demographics. The {wf_total:,} total includes 133K librarians/media collections specialists, 160K library assistants, 74K library technicians, and 3.7K library science teachers. Librarianship has been majority-female since ~1930. The racial diversity gap is narrowing among new MLIS graduates (white share fell from 84% in 2021 to 74% in 2022). Education, training, and library occupations have the highest unionization rate (35.5%) of any professional occupation group.</p>'

    # ---- Library Ballot Measures (EveryLibrary) ----
    ballot = stats.get('ballot', {})
    if ballot and ballot.get('total_measures'):
        bm_n = ballot['total_measures']
        bm_pass = ballot.get('total_pass', 0)
        bm_fail = ballot.get('total_fail', 0)
        bm_rate = ballot.get('pass_rate', 0)
        bm_amount = ballot.get('total_amount_requested', 0)
        bm_yr = ballot.get('year_range', '')

        body += f"""

<h2 id="ballot-measures">Library Ballot Measures ({bm_yr})</h2>
<p class="wiki-sub">When libraries need new buildings, expanded operations, or renewed tax levies, they often must ask voters directly through ballot measures. EveryLibrary tracks these elections across the country. Of {bm_n} library ballot measures recorded, <strong>{bm_pass} passed ({bm_rate:.0f}%)</strong> and {bm_fail} failed, with ${bm_amount/1e6:,.0f}M in funding requested. This is democracy at its most local - communities voting directly on whether to fund their libraries.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{bm_n}</div><div class="label">Ballot measures</div></div>
  <div class="stat-card"><div class="num">{bm_pass}</div><div class="label">Passed</div></div>
  <div class="stat-card"><div class="num">{bm_fail}</div><div class="label">Failed</div></div>
  <div class="stat-card"><div class="num">{bm_rate:.0f}%</div><div class="label">Pass rate</div></div>
  <div class="stat-card"><div class="num">${bm_amount/1e6:,.0f}M</div><div class="label">Funding requested</div></div>
</div>"""

        # By year chart
        if ballot.get('by_year'):
            by_yr = ballot['by_year']
            max_y = max(r.get('count', 0) for r in by_yr) or 1
            n_yrs = len(by_yr)
            bw = 36
            chart_w = n_yrs * bw + 60
            chart_h = 200
            body += f'\n<h3>Library ballot measures per year</h3>\n<svg class="trend-chart" viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Library ballot measures per year">'
            for i, r in enumerate(by_yr):
                cnt = r.get('count', 0)
                h = (cnt / max_y) * (chart_h - 50) if max_y else 0
                x = 40 + i * bw
                body += f'<rect x="{x}" y="{chart_h - 30 - h:.1f}" width="{bw - 6}" height="{h:.1f}" fill="var(--accent-green)" rx="3"/>'
                body += f'<text x="{x + (bw - 6)/2:.0f}" y="{chart_h - 12}" text-anchor="middle" class="axis-text">{r["year"]}</text>'
                body += f'<text x="{x + (bw - 6)/2:.0f}" y="{chart_h - 35 - h:.1f}" text-anchor="middle" class="bar-label">{cnt}</text>'
            body += '</svg>'

        # Top states table
        if ballot.get('by_state'):
            body += """
<h3>States with most library ballot measures</h3>
<table class="wikitable">
  <tr><th>State</th><th>Total</th><th>Passed</th><th>Failed</th><th>Pass Rate</th><th>Amount Requested</th></tr>"""
            for r in ballot['by_state'][:15]:
                pr = (r['pass'] / r['total'] * 100) if r['total'] else 0
                amt = r.get('amount', 0)
                body += f'\n  <tr><td><a href="states/{esc(r["state"])}.html">{esc(r["state"])}</a></td><td>{r["total"]}</td><td>{r["pass"]}</td><td>{r["fail"]}</td><td class="pct">{pr:.0f}%</td><td>${amt/1e6:,.0f}M</td></tr>'
            body += '\n</table>'

        body += '<p class="rsrc">Source: EveryLibrary campaign history (everylibrary.org/campaign_history). Includes library bond measures, operating levy renewals, tax increases, library district formations, and anti-privatization measures. Amount figures are for measures where dollar amounts were specified; many operating levy renewals do not list a specific dollar amount.</p>'

    # ---- State Library Funding Analysis ----
    sf = stats.get('state_funding', {})
    if sf and sf.get('national_totals'):
        sf_nat = sf['national_totals']
        sf_total = sf_nat.get('total_income', 0)
        sf_local = sf_nat.get('local_government_income', 0)
        sf_state = sf_nat.get('state_government_income', 0)
        sf_fed = sf_nat.get('federal_government_income', 0)
        sf_other = sf_nat.get('other_income', 0)
        sf_local_pct = sf_nat.get('local_pct', 0)
        sf_state_pct = sf_nat.get('state_pct', 0)
        sf_fed_pct = sf_nat.get('federal_pct', 0)
        sf_other_pct = sf_nat.get('other_pct', 0)
        sf_pc = sf_nat.get('total_income_per_capita', 0)
        sf_slaa = sf_nat.get('slaa_total_income', 0)
        sf_slaa_aid = sf_nat.get('slaa_state_aid_to_libraries', 0)
        sf_pop = sf_nat.get('population_served', 0)
        sf_n_states = sf_nat.get('count_states', 51)
        sf_n_terr = sf_nat.get('count_territories', 5)
        sf_rankings = sf.get('rankings', {})
        sf_fmd = sf.get('funding_mix_dependency', {})
        sf_top10 = sf.get('top_10', {})
        sf_bot10 = sf.get('bottom_10', {})

        body += f"""

<h2 id="state-funding">State Library Funding: Where the Money Comes From</h2>
<p class="wiki-sub">America's {sf_n_states} state library systems (plus {sf_n_terr} territories) received ${sf_total/1e9:.1f}B in total income in FY2024 serving a population of {sf_pop/1e6:.0f}M - that's ${sf_pc:.2f} per person. But the funding model varies dramatically by state: most rely overwhelmingly on local property taxes, a handful depend on state government appropriations, and federal funding is a tiny fraction everywhere. Understanding this funding mix is essential to understanding why libraries in different states face very different political and budgetary pressures.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${sf_total/1e9:.1f}B</div><div class="label">Total library income (FY2024)</div></div>
  <div class="stat-card"><div class="num">${sf_pc:.2f}</div><div class="label">Per capita (national avg)</div></div>
  <div class="stat-card"><div class="num">{sf_local_pct:.1f}%</div><div class="label">From local government</div></div>
  <div class="stat-card"><div class="num">{sf_state_pct:.1f}%</div><div class="label">From state government</div></div>
  <div class="stat-card"><div class="num">{sf_fed_pct:.1f}%</div><div class="label">From federal government</div></div>
  <div class="stat-card"><div class="num">${sf_slaa/1e6:.0f}M</div><div class="label">SLAA agency income (state libraries)</div></div>
</div>"""

        # Funding source breakdown bars
        body += f"""
<h3>National funding mix</h3>
<div class="services-bars">
  <div class="svc-row"><span class="svc-label">Local government</span><span class="svc-bar"><span class="svc-fill svc-fill-money" style="width:{sf_local_pct:.1f}%"></span></span><span class="svc-val">${sf_local/1e9:.1f}B ({sf_local_pct:.1f}%)</span></div>
  <div class="svc-row"><span class="svc-label">Other income</span><span class="svc-bar"><span class="svc-fill svc-fill-green" style="width:{sf_other_pct:.1f}%"></span></span><span class="svc-val">${sf_other/1e6:.0f}M ({sf_other_pct:.1f}%)</span></div>
  <div class="svc-row"><span class="svc-label">State government</span><span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{sf_state_pct:.1f}%"></span></span><span class="svc-val">${sf_state/1e6:.0f}M ({sf_state_pct:.1f}%)</span></div>
  <div class="svc-row"><span class="svc-label">Federal government</span><span class="svc-bar"><span class="svc-fill svc-fill-red" style="width:{sf_fed_pct*10:.1f}%"></span></span><span class="svc-val">${sf_fed/1e6:.0f}M ({sf_fed_pct:.1f}%)</span></div>
</div>"""

        # Top 10 by total funding
        if sf_top10.get('total_funding'):
            body += """
<h3>Top 10 states by total library funding</h3>
<table class="wikitable">
  <tr><th>State</th><th>Total income</th><th>Per capita</th><th>Local %</th><th>State %</th><th>Federal %</th></tr>"""
            for s in sf_top10['total_funding'][:10]:
                body += f'\n  <tr><td><a href="states/{s["state"]}.html">{esc(s["state_name"])}</a></td><td class="pct">${s["total_income"]/1e6:.0f}M</td><td>${s.get("total_income_per_capita",0):.2f}</td><td>{s.get("local_pct",0):.1f}%</td><td>{s.get("state_pct",0):.1f}%</td><td>{s.get("federal_pct",0):.1f}%</td></tr>'
            body += '\n</table>'

        # Top 10 by per capita funding
        if sf_top10.get('total_per_capita'):
            body += """
<h3>Top 10 states by per-capita library funding</h3>
<table class="wikitable">
  <tr><th>State</th><th>Per capita</th><th>Total income</th><th>Population served</th></tr>"""
            for s in sf_top10['total_per_capita'][:10]:
                body += f'\n  <tr><td><a href="states/{s["state"]}.html">{esc(s["state_name"])}</a></td><td class="pct">${s.get("total_income_per_capita",0):.2f}</td><td>${s["total_income"]/1e6:.0f}M</td><td>{s.get("population_served",0):,}</td></tr>'
            body += '\n</table>'

        # State government funding leaders
        if sf_top10.get('state_government_income'):
            body += """
<h3>Top 10 states by state government funding</h3>
<table class="wikitable">
  <tr><th>State</th><th>State gov't income</th><th>State % of total</th><th>Per capita (state)</th></tr>"""
            for s in sf_top10['state_government_income'][:10]:
                body += f'\n  <tr><td><a href="states/{s["state"]}.html">{esc(s["state_name"])}</a></td><td class="pct">${s["state_government_income"]/1e6:.0f}M</td><td>{s.get("state_pct",0):.1f}%</td><td>${s.get("state_income_per_capita",0):.2f}</td></tr>'
            body += '\n</table>'

        # Funding mix dependency - most dependent on state funding
        if sf_fmd.get('most_dependent_on_state_funding'):
            body += """
<h3>Most dependent on state government funding</h3>
<p class="wiki-sub">These states rely on state government as the primary funder rather than local property taxes - the opposite of the national norm.</p>
<table class="wikitable">
  <tr><th>State</th><th>Total income</th><th>State %</th><th>Local %</th><th>Federal %</th></tr>"""
            for s in sf_fmd['most_dependent_on_state_funding'][:10]:
                body += f'\n  <tr><td><a href="states/{s["state"]}.html">{esc(s["state_name"])}</a></td><td class="pct">${s["total_income"]/1e6:.1f}M</td><td>{s["state_pct"]:.1f}%</td><td>{s["local_pct"]:.1f}%</td><td>{s["federal_pct"]:.1f}%</td></tr>'
            body += '\n</table>'

        # Least dependent on state funding
        if sf_fmd.get('least_dependent_on_state_funding'):
            body += """
<h3>Least dependent on state funding (most locally self-reliant)</h3>
<p class="wiki-sub">These states fund libraries almost entirely through local government - state aid is effectively zero.</p>
<table class="wikitable">
  <tr><th>State</th><th>State %</th><th>Local %</th><th>Total income</th></tr>"""
            for s in sf_fmd['least_dependent_on_state_funding'][:10]:
                body += f'\n  <tr><td><a href="states/{s["state"]}.html">{esc(s["state_name"])}</a></td><td class="pct">{s["state_pct"]:.1f}%</td><td>{s["local_pct"]:.1f}%</td><td>${s["total_income"]/1e6:.0f}M</td></tr>'
            body += '\n</table>'

        # Federal funding leaders
        if sf_top10.get('federal_income'):
            body += """
<h3>Top 10 states by federal funding</h3>
<table class="wikitable">
  <tr><th>State</th><th>Federal income</th><th>Federal %</th><th>Per capita (federal)</th></tr>"""
            for s in sf_top10['federal_income'][:10]:
                body += f'\n  <tr><td><a href="states/{s["state"]}.html">{esc(s["state_name"])}</a></td><td class="pct">${s["federal_government_income"]/1e6:.1f}M</td><td>{s.get("federal_pct",0):.1f}%</td><td>${s.get("federal_income_per_capita",0):.2f}</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">Source: IMLS Public Libraries Survey (PLS) FY2024 and State Library Agency Survey (SLAA) FY2024, compiled via ALA State of America\'s Libraries data. National totals: ${sf_total/1e9:.1f}B total income across {sf_n_states} states + DC and {sf_n_terr} territories, serving {sf_pop/1e6:.0f}M people (${sf_pc:.2f}/capita). The {sf_local_pct:.1f}% local / {sf_state_pct:.1f}% state / {sf_fed_pct:.1f}% federal split reveals that America\'s public libraries are overwhelmingly a local government function. Ohio is a striking outlier: its state government provides $482M (42.9% of library income) through the dedicated Library and Local Government Support Fund - more than all other states combined. Hawaii runs the opposite model with 93.5% state funding and no local library districts. IMLS uses negative sentinels (-1, -3, -40) for suppressed/unreported values, normalized to 0 here.</p>'

    # ---- USDA Rural Development Library Grants ----
    usda = stats.get('usda_grants', {})
    if usda and usda.get('totals'):
        ut = usda['totals']
        u_total = ut.get('total_dollars', 0)
        u_awards = ut.get('library_awards', 0)
        u_grants = ut.get('library_grants', 0)
        u_loans = ut.get('library_loans', 0)
        u_recip = ut.get('distinct_recipients', 0)
        u_states = ut.get('states_covered', 0)
        u_top = usda.get('top_states', [])
        u_recip_top = usda.get('top_recipients', [])
        u_years = usda.get('by_year', [])
        u_sizes = usda.get('award_size_distribution', [])
        yr_range = ut.get('fiscal_year_range', {})

        body += f"""

<h2 id="usda-grants">USDA Rural Development Library Grants &amp; Loans</h2>
<p class="wiki-sub">The USDA Rural Development Community Facilities program (CFDA 10.766) provides grants and loans to rural areas under 20,000 population for essential community facilities - and public libraries are explicitly eligible. From FY{yr_range.get('start', 2007)} to FY{yr_range.get('end', 2025)}, the program awarded {u_awards} grants and loans totaling ${u_total/1e6:.1f}M to {u_recip} library recipients across {u_states} states. While modest compared to IMLS or E-Rate funding, these USDA awards are often transformative for small rural communities that lack other capital sources.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${u_total/1e6:.1f}M</div><div class="label">Total awards to libraries</div></div>
  <div class="stat-card"><div class="num">{u_awards}</div><div class="label">Total awards (grants + loans)</div></div>
  <div class="stat-card"><div class="num">{u_grants}</div><div class="label">Grants</div></div>
  <div class="stat-card"><div class="num">{u_loans}</div><div class="label">Loans</div></div>
  <div class="stat-card"><div class="num">{u_recip}</div><div class="label">Distinct recipients</div></div>
  <div class="stat-card"><div class="num">{u_states}</div><div class="label">States</div></div>
</div>"""

        # Top states table
        if u_top:
            body += """
<h3>Top states by USDA library funding</h3>
<table class="wikitable">
  <tr><th>State</th><th>Awards</th><th>Grants</th><th>Loans</th><th>Total $</th></tr>"""
            for s in u_top[:10]:
                body += f'\n  <tr><td><a href="states/{esc(s["state"])}.html">{esc(s["state"])}</a></td><td class="pct">{s.get("awards",0)}</td><td>{s.get("grants",0)}</td><td>{s.get("loans",0)}</td><td>${s.get("total_dollars",0)/1e6:.1f}M</td></tr>'
            body += '\n</table>'

        # Top recipients
        if u_recip_top:
            body += """
<h3>Largest USDA library awards</h3>
<table class="wikitable">
  <tr><th>Library</th><th>State</th><th>City</th><th>Type</th><th>Amount</th></tr>"""
            for r in u_recip_top[:10]:
                atype = "Loan" if r.get('loans', 0) > 0 and r.get('grants', 0) == 0 else ("Grant" if r.get('grants', 0) > 0 and r.get('loans', 0) == 0 else "Grant+Loan")
                body += f'\n  <tr><td>{esc(r.get("recipient","").title())}</td><td>{esc(r.get("state",""))}</td><td>{esc(r.get("city",""))}</td><td>{atype}</td><td>${r.get("total_dollars",0)/1e6:.1f}M</td></tr>'
            body += '\n</table>'

        # By year trend
        if u_years:
            body += """
<h3>USDA library awards by fiscal year</h3>
<table class="wikitable">
  <tr><th>FY</th><th>Grants</th><th>Loans</th><th>Grant $</th><th>Loan $</th><th>Total $</th></tr>"""
            for y in u_years:
                body += f'\n  <tr><td>FY{y.get("fiscal_year","")}</td><td>{y.get("grants",0)}</td><td>{y.get("loans",0)}</td><td>${y.get("grant_dollars",0)/1e3:.0f}K</td><td>${y.get("loan_dollars",0)/1e6:.1f}M</td><td>${y.get("total_dollars",0)/1e6:.1f}M</td></tr>'
            body += '\n</table>'

        body += '<p class="rsrc">Source: USASpending.gov API, filtered to USDA Rural Housing Service / Community Programs awards under CFDA 10.766 (Community Facilities Loans and Grants) where the recipient name contains "library" or "libraries." USDA loan obligations report as $0 in USASpending (they are recorded as loan face value); loan subsidy cost and grant outlays are tracked separately. The program serves rural areas with populations under 20,000. Libraries represent approximately 1% of all Community Facilities awards but receive critical infrastructure funding for buildings, equipment, and technology.</p>'

    # ---- NEH Grants to Libraries ----
    neh = stats.get('neh_grants', {})
    if neh and neh.get('total_grants'):
        n_total = neh['total_grants']
        n_dollars = neh.get('total_awarded', neh.get('total_dollars', 0))
        n_states = len(neh.get('grants_by_state', []))
        n_top_recipients = neh.get('top_recipients', [])
        n_by_state = neh.get('grants_by_state', [])
        n_by_year = neh.get('grants_by_year', [])
        n_by_program = neh.get('grants_by_program', [])
        n_largest = neh.get('largest_awards', neh.get('largest_grants', []))
        n_yr_range = neh.get('year_range', {})
        n_yr_min = n_yr_range.get('min', '')
        n_yr_max = n_yr_range.get('max', '')
        n_avg = n_dollars / n_total if n_total else 0
        n_largest_amt = n_largest[0]['amount'] if n_largest else 0

        body += f"""

<h2 id="neh-grants">National Endowment for the Humanities: Library Grants</h2>
<p class="wiki-sub">The National Endowment for the Humanities (NEH) is an independent federal agency that funds humanities research, education, preservation, and public programs. Libraries are major NEH recipients - from the American Library Association's national reading programs to state newspaper digitization projects. From FY{n_yr_min} to FY{n_yr_max}, NEH awarded {n_total} grants totaling ${n_dollars/1e6:.1f}M to library recipients across {n_states} states, with an average grant of ${n_avg/1e3:.0f}K. The largest single award was ${n_largest_amt/1e6:.2f}M to the American Library Association in 2021 for American Rescue Plan humanities relief.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${n_dollars/1e6:.1f}M</div><div class="label">Total NEH library grants</div></div>
  <div class="stat-card"><div class="num">{n_total}</div><div class="label">Awards to libraries</div></div>
  <div class="stat-card"><div class="num">${n_avg/1e3:.0f}K</div><div class="label">Average grant</div></div>
  <div class="stat-card"><div class="num">${n_largest_amt/1e6:.2f}M</div><div class="label">Largest single grant</div></div>
  <div class="stat-card"><div class="num">{n_states}</div><div class="label">States reached</div></div>
  <div class="stat-card"><div class="num">{len(n_by_program)}</div><div class="label">NEH funding programs</div></div>
</div>"""

        # Top recipients bar chart
        if n_top_recipients:
            body += """
<h3>Top NEH library recipients</h3>
<div class="services-bars">"""
            max_amt = n_top_recipients[0].get('total_awarded', n_top_recipients[0].get('amount', 0)) or 1
            for r in n_top_recipients[:12]:
                name = r.get('recipient', r.get('name', '')).title().replace('Llc', 'LLC')
                amt = r.get('total_awarded', r.get('amount', 0))
                grnts = r.get('grants', 1)
                pct = (amt / max_amt) * 100 if max_amt else 0
                body += f'\n  <div class="svc-row"><span class="svc-label">{esc(name)} ({grnts} grants)</span><span class="svc-bar"><span class="svc-fill svc-fill-money" style="width:{pct:.1f}%"></span></span><span class="svc-val">${amt/1e6:.2f}M</span></div>'
            body += '\n</div>'

        # NEH programs breakdown
        if n_by_program:
            body += """
<h3>NEH library grants by program (CFDA)</h3>
<table class="wikitable">
  <tr><th>Program</th><th>Grants</th><th>Total awarded</th><th>Average award</th></tr>"""
            for p in n_by_program:
                body += f'\n  <tr><td>{esc(p.get("program",""))}</td><td>{p.get("grants",0)}</td><td class="pct">${p.get("total_awarded",0)/1e6:.1f}M</td><td>${p.get("avg_award",0)/1e3:.0f}K</td></tr>'
            body += '\n</table>'

        # Top states
        if n_by_state:
            body += """
<h3>NEH library grants by state</h3>
<table class="wikitable">
  <tr><th>State</th><th>Grants</th><th>Total awarded</th><th>Avg award</th><th>Recipients</th></tr>"""
            for s in n_by_state[:15]:
                body += f'\n  <tr><td><a href="states/{s["state"]}.html">{s["state"]}</a></td><td>{s.get("grants",0)}</td><td class="pct">${s.get("total_awarded",0)/1e6:.1f}M</td><td>${s.get("avg_award",0)/1e3:.0f}K</td><td>{s.get("recipients",0)}</td></tr>'
            body += '\n</table>'

        # By year SVG
        if n_by_year and len(n_by_year) >= 2:
            labels = [str(y['year']) for y in n_by_year]
            amounts = [y.get('total_awarded', y.get('amount', 0)) for y in n_by_year]
            max_amt = max(amounts) or 1
            n = len(n_by_year)
            bw = 38
            chart_w = n * bw + 60
            chart_h = 220
            body += f'\n<h3>NEH library grants by year</h3>\n<svg class="trend-chart" viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="NEH library grants by year">'
            for i in range(n):
                x = 40 + i * bw
                h = (amounts[i] / max_amt) * (chart_h - 60) if max_amt else 0
                body += f'<rect x="{x}" y="{chart_h - 40 - h:.1f}" width="{bw - 6}" height="{h:.1f}" fill="var(--accent-yellow)" rx="3"/>'
                body += f'<text x="{x + (bw-6)/2:.0f}" y="{chart_h - 22}" text-anchor="middle" class="axis-text">{labels[i]}</text>'
                body += f'<text x="{x + (bw-6)/2:.0f}" y="{chart_h - 45 - h:.1f}" text-anchor="middle" class="bar-label">${amounts[i]/1e6:.1f}M</text>'
            body += '</svg>'

        # Largest individual grants
        if n_largest:
            body += """
<h3>Largest individual NEH library grants</h3>
<table class="wikitable">
  <tr><th>Recipient</th><th>State</th><th>Program</th><th>Description</th><th>Amount</th><th>Year</th></tr>"""
            for g in n_largest[:15]:
                body += f'\n  <tr><td>{esc(g.get("recipient","").title())}</td><td>{g.get("state","") or "&mdash;"}</td><td>{esc(g.get("program",""))}</td><td>{esc(g.get("description","")[:120])}{"..." if len(g.get("description",""))>120 else ""}</td><td class="pct">${g.get("amount",0)/1e6:.2f}M</td><td>{g.get("year","")}</td></tr>'
            body += '\n</table>'

        ala_note = ''
        if n_top_recipients:
            ala_amt = n_top_recipients[0].get('total_awarded', n_top_recipients[0].get('amount', 0))
            ala_pct = (ala_amt / n_dollars * 100) if n_dollars else 0
            ala_note = f' The American Library Association alone received ${ala_amt/1e6:.1f}M ({ala_pct:.0f}% of all NEH library funding) for national programs including the Great American Read, Big Read, We the People bookshelf, and American Rescue Plan humanities relief.'
        prog_note = ''
        if n_by_program:
            prog_note = f' The top NEH program for libraries is {n_by_program[0].get("program","")} ({n_by_program[0].get("grants",0)} grants, ${n_by_program[0].get("total_awarded",0)/1e6:.1f}M).'
        body += f'<p class="rsrc">Source: USASpending.gov API, filtered to awards from the National Endowment for the Humanities (toptier agency code 418) where the recipient name contains "library" and award type codes 02-05 (grants). The {n_total} awards span FY{n_yr_min}-FY{n_yr_max} and total ${n_dollars/1e6:.1f}M. Records cover awards with action dates on or after 2007-10-01 (USASpending search limit); NEH\'s own public query (securegrants.neh.gov) covers full history back to 1965 but was unreachable.{ala_note}{prog_note}</p>'

    # ---- IMLS Library Grants (all programs) ----
    ig = stats.get('imls_library_grants', {})
    if ig and ig.get('total_grants'):
        ig_total = ig['total_grants']
        ig_dollars = ig.get('total_awarded', 0)
        ig_avg = ig_dollars / ig_total if ig_total else 0
        ig_states = ig.get('states_reached', 0)
        ig_yr = ig.get('year_range', {})
        ig_yr_min = ig_yr.get('min', '')
        ig_yr_max = ig_yr.get('max', '')
        ig_by_state = ig.get('grants_by_state', [])
        ig_by_year = ig.get('grants_by_year', [])
        ig_top_recipients = ig.get('top_recipients', [])
        ig_largest = ig.get('largest_awards', [])
        ig_by_program = ig.get('grants_by_program', [])
        ig_largest_amt = ig_largest[0]['amount'] if ig_largest else 0

        body += f"""

<h2 id="imls-grants">IMLS Grants to Libraries: All Programs</h2>
<p class="wiki-sub">The Institute of Museum and Library Services is the primary federal funder of the nation's libraries. Through the Grants to States program (LSTA), National Leadership Grants, Laura Bush 21st Century Librarian Program, and other initiatives, IMLS awarded {ig_total} grants totaling ${ig_dollars/1e9:.1f}B to library recipients from FY{ig_yr_min} to FY{ig_yr_max}. These grants flow primarily to state library agencies, which redistribute funds to local libraries, but also fund direct grants for research, professional development, and digital inclusion initiatives.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${ig_dollars/1e9:.1f}B</div><div class="label">Total IMLS library grants</div></div>
  <div class="stat-card"><div class="num">{ig_total}</div><div class="label">Awards to libraries</div></div>
  <div class="stat-card"><div class="num">${ig_avg/1e6:.1f}M</div><div class="label">Average grant</div></div>
  <div class="stat-card"><div class="num">${ig_largest_amt/1e6:.1f}M</div><div class="label">Largest single grant</div></div>
  <div class="stat-card"><div class="num">{ig_states}</div><div class="label">States reached</div></div>
  <div class="stat-card"><div class="num">{ig_yr_max - ig_yr_min + 1}</div><div class="label">Years of data</div></div>
</div>"""

        # Top recipients
        if ig_top_recipients:
            body += """
<h3>Top IMLS library grant recipients</h3>
<div class="services-bars">"""
            max_amt = ig_top_recipients[0].get('total_awarded', 0) or 1
            for r in ig_top_recipients[:12]:
                name = r.get('recipient', '').title().replace('Llc', 'LLC')
                amt = r.get('total_awarded', 0)
                grnts = r.get('grant_count', 1)
                pct = (amt / max_amt) * 100 if max_amt else 0
                body += f'\n  <div class="svc-row"><span class="svc-label">{esc(name)} ({grnts} grants)</span><span class="svc-bar"><span class="svc-fill svc-fill-money" style="width:{pct:.1f}%"></span></span><span class="svc-val">${amt/1e6:.1f}M</span></div>'
            body += '\n</div>'

        # IMLS programs breakdown
        if ig_by_program:
            body += """
<h3>IMLS library grants by program (CFDA)</h3>
<table class="wikitable">
  <tr><th>Program</th><th>Grants</th><th>Total awarded</th><th>Avg award</th></tr>"""
            for p in ig_by_program:
                body += f'\n  <tr><td>{esc(p.get("program",""))}</td><td>{p.get("grants",0)}</td><td class="pct">${p.get("total_awarded",0)/1e6:.1f}M</td><td>${p.get("avg_award",0)/1e3:.0f}K</td></tr>'
            body += '\n</table>'

        # Top states
        if ig_by_state:
            body += """
<h3>IMLS library grants by state</h3>
<table class="wikitable">
  <tr><th>State</th><th>Grants</th><th>Total awarded</th></tr>"""
            for s in ig_by_state[:15]:
                body += f'\n  <tr><td><a href="states/{s["state"]}.html">{s["state"]}</a></td><td>{s.get("grant_count",0)}</td><td class="pct">${s.get("total_awarded",0)/1e6:.1f}M</td></tr>'
            body += '\n</table>'

        # By year SVG
        if ig_by_year and len(ig_by_year) >= 2:
            labels = [str(y['year']) for y in ig_by_year]
            amounts = [y.get('total_awarded', 0) for y in ig_by_year]
            max_amt = max(amounts) or 1
            n = len(ig_by_year)
            bw = 38
            chart_w = n * bw + 60
            chart_h = 220
            body += f'\n<h3>IMLS library grants by year</h3>\n<svg class="trend-chart" viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="IMLS library grants by year">'
            for i in range(n):
                x = 40 + i * bw
                h = (amounts[i] / max_amt) * (chart_h - 60) if max_amt else 0
                body += f'<rect x="{x}" y="{chart_h - 40 - h:.1f}" width="{bw - 6}" height="{h:.1f}" fill="var(--accent-green)" rx="3"/>'
                body += f'<text x="{x + (bw-6)/2:.0f}" y="{chart_h - 22}" text-anchor="middle" class="axis-text">{labels[i]}</text>'
                body += f'<text x="{x + (bw-6)/2:.0f}" y="{chart_h - 45 - h:.1f}" text-anchor="middle" class="bar-label">${amounts[i]/1e6:.0f}M</text>'
            body += '</svg>'

        # Largest individual grants
        if ig_largest:
            body += """
<h3>Largest individual IMLS library grants</h3>
<table class="wikitable">
  <tr><th>Recipient</th><th>State</th><th>Description</th><th>Amount</th><th>Year</th></tr>"""
            for g in ig_largest[:15]:
                body += f'\n  <tr><td>{esc(g.get("recipient","").title())}</td><td>{g.get("state","") or "&mdash;"}</td><td>{esc(g.get("description","")[:120])}{"..." if len(g.get("description",""))>120 else ""}</td><td class="pct">${g.get("amount",0)/1e6:.1f}M</td><td>{g.get("year","")}</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">Source: USASpending.gov API, filtered to awards from the Institute of Museum and Library Services (toptier agency) where the recipient name contains "library" and award type codes 02-05 (grants). The {ig_total} awards span FY{ig_yr_min}-FY{ig_yr_max} and total ${ig_dollars/1e9:.1f}B. The Grants to States program (LSTA) is the largest component, flowing through state library agencies. The spike in FY2021 (${max(y.get("total_awarded",0) for y in ig_by_year)/1e6:.0f}M) reflects American Rescue Plan supplemental funding. State extraction from recipient name may undercount some states where the recipient name does not include a state identifier.</p>'

    # ---- Federal Funding Totals (comprehensive overview) ----
    fft = stats.get('federal_funding_totals', {})
    if fft and fft.get('total_federal_funding'):
        fft_total = fft['total_federal_funding']
        fft_sources = fft.get('sources', [])

        body += f"""

<h2 id="federal-funding-totals">Federal Funding for Libraries: The Complete Picture</h2>
<p class="wiki-sub">When you add up every federal program that funds libraries - from IMLS grants to broadband subsidies to emergency COVID relief - the total reaches ${fft_total/1e9:.1f}B across {fft.get('source_count',0)} distinct programs. The largest programs are broadband infrastructure (BEAD, ACP, ECF, E-Rate) rather than direct library grants. IMLS, the agency most people associate with library funding, accounts for just ${1_465_541_788/fft_total*100:.1f}% of the total federal investment in libraries.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${fft_total/1e9:.1f}B</div><div class="label">Total federal library funding</div></div>
  <div class="stat-card"><div class="num">{fft.get('source_count',0)}</div><div class="label">Federal funding programs</div></div>
  <div class="stat-card"><div class="num">${42.45}</div><div class="label">B: BEAD (largest)</div></div>
  <div class="stat-card"><div class="num">${1.47}</div><div class="label">B: IMLS grants</div></div>
</div>"""

        # Bar chart of all programs
        if fft_sources:
            body += """
<h3>All federal library funding programs, ranked</h3>
<div class="services-bars">"""
            max_amt = fft_sources[0].get('amount', 1) if fft_sources else 1
            for s in fft_sources:
                amt = s.get('amount', 0)
                pct = (amt / max_amt) * 100 if max_amt else 0
                body += f'\n  <div class="svc-row"><span class="svc-label">{esc(s.get("name",""))}</span><span class="svc-bar"><span class="svc-fill svc-fill-money" style="width:{pct:.1f}%"></span></span><span class="svc-val">${amt/1e9:.2f}B</span></div>'
            body += '\n</div>'

            # Detailed table
            body += """
<table class="wikitable">
  <tr><th>Program</th><th>Amount</th><th>Awards</th><th>Period</th><th>Description</th></tr>"""
            for s in fft_sources:
                body += f'\n  <tr><td>{esc(s.get("name",""))}</td><td class="pct">${s.get("amount",0)/1e9:.2f}B</td><td>{s.get("grants",0):,}</td><td>{esc(s.get("period",""))}</td><td>{esc(s.get("description",""))}</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">{esc(fft.get("note",""))} BEAD ($42.45B) and ACP ($29.8B) are broadband programs that benefit libraries as anchor institutions but are not library-specific grants. E-Rate ($2.28B) is the largest ongoing library-specific federal program, providing telecommunications and internet access discounts. The $10B Emergency Connectivity Fund (ECF) was a one-time COVID-era program that has ended. IMLS ($1.47B) is the primary direct grant-making agency for libraries. Together, these programs represent the most significant federal investment in library infrastructure, access, and services in American history.</p>'

    # ---- Other Federal Agency Grants to Libraries ----
    ofg = stats.get('other_federal_grants', {})
    if ofg and ofg.get('total_grants'):
        ofg_total = ofg['total_grants']
        ofg_dollars = ofg.get('total_awarded', 0)
        ofg_agencies = ofg.get('agencies_count', 0)
        ofg_by_agency = ofg.get('by_agency', [])
        ofg_by_state = ofg.get('by_state', [])
        ofg_largest = ofg.get('largest_awards', [])

        body += f"""

<h2 id="other-federal-grants">Other Federal Grants to Libraries</h2>
<p class="wiki-sub">Beyond IMLS, NEH, and USDA, several other federal agencies award grants to libraries. From USASpending data, {ofg_agencies} federal agencies collectively awarded {ofg_total} grants totaling ${ofg_dollars/1e6:.1f}M to library recipients. The Department of Housing and Urban Development (HUD) is the largest non-library-specific funder, using Community Development Block Grants to support library construction in distressed communities. The Department of the Interior funds libraries on tribal lands and historic preservation projects.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">${ofg_dollars/1e6:.1f}M</div><div class="label">Total other federal grants</div></div>
  <div class="stat-card"><div class="num">{ofg_total}</div><div class="label">Awards to libraries</div></div>
  <div class="stat-card"><div class="num">{ofg_agencies}</div><div class="label">Federal agencies</div></div>
  <div class="stat-card"><div class="num">${ofg_dollars/ofg_total/1e3:.0f}K</div><div class="label">Average grant</div></div>
</div>"""

        # By agency bars
        if ofg_by_agency:
            body += """
<h3>Grants by federal agency</h3>
<div class="services-bars">"""
            max_amt = ofg_by_agency[0].get('total_awarded', 0) or 1
            for a in ofg_by_agency:
                amt = a.get('total_awarded', 0)
                pct = (amt / max_amt) * 100 if max_amt else 0
                body += f'\n  <div class="svc-row"><span class="svc-label">{esc(a.get("agency",""))} ({a.get("grants",0)} grants)</span><span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct:.1f}%"></span></span><span class="svc-val">${amt/1e6:.1f}M</span></div>'
            body += '\n</div>'

            # Agency table with full names
            body += """
<table class="wikitable">
  <tr><th>Agency</th><th>Full name</th><th>Grants</th><th>Total awarded</th></tr>"""
            for a in ofg_by_agency:
                body += f'\n  <tr><td>{esc(a.get("agency",""))}</td><td>{esc(a.get("agency_name",""))}</td><td>{a.get("grants",0)}</td><td class="pct">${a.get("total_awarded",0)/1e6:.1f}M</td></tr>'
            body += '\n</table>'

        # Top states
        if ofg_by_state:
            body += """
<h3>Top states receiving other federal library grants</h3>
<table class="wikitable">
  <tr><th>State</th><th>Total awarded</th></tr>"""
            for s in ofg_by_state[:15]:
                body += f'\n  <tr><td><a href="states/{s["state"]}.html">{s["state"]}</a></td><td class="pct">${s.get("total_awarded",0)/1e6:.1f}M</td></tr>'
            body += '\n</table>'

        # Largest grants
        if ofg_largest:
            body += """
<h3>Largest other federal library grants</h3>
<table class="wikitable">
  <tr><th>Recipient</th><th>Agency</th><th>State</th><th>Description</th><th>Amount</th><th>Year</th></tr>"""
            for g in ofg_largest[:15]:
                body += f'\n  <tr><td>{esc(g.get("recipient","").title())}</td><td>{g.get("agency","")}</td><td>{g.get("state","") or "&mdash;"}</td><td>{esc(g.get("description","")[:100])}{"..." if len(g.get("description",""))>100 else ""}</td><td class="pct">${g.get("amount",0)/1e6:.1f}M</td><td>{g.get("year","")}</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">Source: USASpending.gov API, filtered to awards from 7 federal agencies (HUD, DOI, HHS, ED, CNCS, NSF, EPA) where the recipient name contains "library" and award type codes 02-05 (grants). Total: {ofg_total} awards, ${ofg_dollars/1e6:.1f}M. HUD Community Development Block Grants (CDBG) support library construction in low-income communities. DOI grants fund tribal libraries and historic library preservation. HHS grants support library-based health literacy programs. NSF grants fund STEM education at libraries. These are distinct from IMLS, NEH, and USDA awards which are covered in their own sections.</p>'

    # ---- Library Usage Survey Data (Pew Research + Gallup) ----
    lu = stats.get('library_usage', {})
    if lu and lu.get('overall_usage'):
        ou = lu['overall_usage']
        cv = lu.get('community_value', {})
        si = lu.get('service_importance', {})
        dem = lu.get('demographic_usage', {})
        survey_yr = lu.get('survey_year', '')

        nea = lu.get('nea_sppa_2022', {})
        nea_pct = nea.get('adults_visited_public_library_pct', 23)
        nea_n = nea.get('sample_size', 19100)

        body += f"""

<h2 id="library-usage">How Americans Use Libraries (Survey Data)</h2>
<p class="wiki-sub">Beyond the administrative data, public opinion surveys reveal how Americans actually interact with libraries and what they value. The Pew Research Center surveyed {lu.get('sample_size', 6224):,} Americans in {survey_yr}, finding that {ou.get('used_library_past_year', 54)}% had used a library in the past year. Gallup's 2019 poll found Americans visit libraries an average of {dem.get('gallup_2019_visits_per_year_avg', 10.5)} times per year - more frequent than any other cultural activity measured. In 2022, the NEA added a library-visit question to its Survey of Public Participation in the Arts for the first time: {nea_pct}% of adults reported visiting a public library.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{ou.get('used_library_past_year', 54)}%</div><div class="label">Used a library (past year, Pew)</div></div>
  <div class="stat-card"><div class="num">{ou.get('library_household', 72)}%</div><div class="label">Live in a "library household"</div></div>
  <div class="stat-card"><div class="num">{ou.get('website_visit', 30)}%</div><div class="label">Visited library website</div></div>
  <div class="stat-card"><div class="num">{cv.get('libraries_improve_quality_of_life', 94)}%</div><div class="label">Say libraries improve community</div></div>
  <div class="stat-card"><div class="num">{cv.get('closure_would_impact_community', 90)}%</div><div class="label">Closure would impact community</div></div>
  <div class="stat-card"><div class="num">{dem.get('gallup_2019_visits_per_year_avg', 10.5)}</div><div class="label">Avg visits per year (Gallup)</div></div>
  <div class="stat-card"><div class="num">{nea_pct}%</div><div class="label">Adults visited public library (NEA 2022)</div></div>
</div>"""

        # Community value bars
        if cv:
            body += """
<h3>How Americans value libraries in their communities</h3>
<div class="services-bars">"""
            max_v = max(cv.values()) if cv else 1
            for label, val in cv.items():
                pct_w = (val / max_v) * 100 if isinstance(val, (int, float)) and max_v else 0
                display = label.replace("_", " ").title()
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(display)}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{val}%</span>
  </div>"""
            body += '\n</div>'

        # Service importance bars
        if si:
            body += """
<h3>Who depends on library services most</h3>
<div class="services-bars">"""
            max_s = max(si.values()) if si else 1
            for label, val in si.items():
                if isinstance(val, (int, float)):
                    pct_w = (val / max_s) * 100 if max_s else 0
                    display = label.replace("_", " ").title()
                    body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(display)}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{val}%</span>
  </div>"""
            body += '\n</div>'

        # Usage trend
        if ou:
            body += f"""
<h3>Usage trends</h3>
<table class="wikitable">
  <tr><th>Metric</th><th>2012</th><th>{survey_yr}</th><th>Change</th></tr>"""
            metrics = [
                ("Overall library usage", ou.get('used_library_2012', 59), ou.get('used_library_past_year', 54)),
                ("In-person visit", ou.get('in_person_visit_2012', 53), ou.get('in_person_visit', 48)),
                ("Website visit", ou.get('website_visit_2012', 25), ou.get('website_visit', 30)),
            ]
            for label, v1, v2 in metrics:
                chg = v2 - v1
                body += f'\n  <tr><td>{label}</td><td class="pct">{v1}%</td><td class="pct">{v2}%</td><td>{"+" if chg >= 0 else ""}{chg}pp</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">Source: Pew Research Center Internet & American Life Project ({survey_yr} survey, n={lu.get("sample_size", 6224):,}), Gallup ({dem.get("survey_year", 2019)} poll), and NEA Survey of Public Participation in the Arts (2022, n={nea_n:,}). Pew surveyed Americans aged 16+ on library use and attitudes. In-person visits declined {ou.get("in_person_visit_2012", 53) - ou.get("in_person_visit", 48)}pp from 2012 to {survey_yr} while website visits increased {ou.get("website_visit", 30) - ou.get("website_visit_2012", 25)}pp - a shift toward digital access that the PLS data confirms. The NEA SPPA 2022 library-visit question is not directly comparable to Pew due to different wording (in-person public library visits by adults 18+) and methodology.</p>'

    # ---- Library User Demographics and Usage Patterns ----
    demo = stats.get('library_demographics', {})
    if demo and demo.get('demographics'):
        demo_data = demo.get('demographics', {}).get('summary_by_source', {})
        reasons = demo.get('reasons_for_use', {})
        services = demo.get('services_offered', {})
        nces = demo.get('nces_school_libraries', {})

        gallup_demo = demo_data.get('gallup_2019_frequency', {})
        pew_demo = demo_data.get('pew_2016_visit_rate_by_demographic', {})
        pew_hisp = demo_data.get('pew_2015_hispanic_use', {})
        visitor_reasons = reasons.get('among_library_visitors_past_12_months', {})

        body += f"""

<h2 id="demographics">Who Uses Libraries & Why</h2>
<p class="wiki-sub">Survey data reveals stark demographic patterns in library use. Gallup's 2019 poll found that women visit libraries nearly twice as often as men (13.4 vs 7.5 visits/year), young adults aged 18-29 visit most frequently (15.5/year), and low-income households use libraries more than high-income ones (12.2 vs 8.5 visits/year). Pew's 2016 survey found that college graduates (59%) and parents (55%) visit libraries at higher rates - suggesting libraries serve both the educated and those caring for children.</p>"""

        # Demographic stat cards
        if gallup_demo:
            body += f"""
<div class="stats-grid">
  <div class="stat-card"><div class="num">{gallup_demo.get('women', 13.4)}</div><div class="label">Women: avg visits/year</div></div>
  <div class="stat-card"><div class="num">{gallup_demo.get('men', 7.5)}</div><div class="label">Men: avg visits/year</div></div>
  <div class="stat-card"><div class="num">{gallup_demo.get('ages_18_29', 15.5)}</div><div class="label">Ages 18-29 visits/year</div></div>
  <div class="stat-card"><div class="num">{gallup_demo.get('ages_65_plus', 8.2)}</div><div class="label">Ages 65+ visits/year</div></div>
  <div class="stat-card"><div class="num">{gallup_demo.get('income_less_than_40000', 12.2)}</div><div class="label">Low-income visits/year</div></div>
  <div class="stat-card"><div class="num">{gallup_demo.get('income_100000_plus', 8.5)}</div><div class="label">High-income visits/year</div></div>
</div>"""

        # Gallup demographic bars
        if gallup_demo:
            body += """
<h3>Library visits per year by demographic group (Gallup 2019)</h3>
<div class="services-bars">"""
            demo_pairs = [
                ("Women", "women"), ("Men", "men"),
                ("Ages 18-29", "ages_18_29"), ("Ages 30-49", "ages_30_49"),
                ("Ages 50-64", "ages_50_64"), ("Ages 65+", "ages_65_plus"),
                ("Income <$40K", "income_less_than_40000"),
                ("Income $40-100K", "income_40000_99999"),
                ("Income $100K+", "income_100000_plus"),
                ("Midwest", "midwest"), ("East", "east"),
                ("West", "west"), ("South", "south"),
            ]
            max_d = max(gallup_demo.get(k, 0) for _, k in demo_pairs) or 1
            for label, key in demo_pairs:
                val = gallup_demo.get(key, 0)
                pct_w = (val / max_d) * 100 if max_d else 0
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{label}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-people" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{val}</span>
  </div>"""
            body += '\n</div>'

        # Pew visit rate by demographic
        if pew_demo:
            body += """
<h3>Library visit rate by demographic (Pew 2016, % who visited in past year)</h3>
<div class="services-bars">"""
            max_p = max(pew_demo.values()) or 1
            for label, val in sorted(pew_demo.items(), key=lambda x: -x[1]):
                pct_w = (val / max_p) * 100 if max_p else 0
                display = label.replace("_", " ").title()
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(display)}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{val}%</span>
  </div>"""
            body += '\n</div>'

        # Reasons for use
        if visitor_reasons:
            body += """
<h3>Why library visitors use the library (Pew 2016, % of past-year visitors)</h3>
<div class="services-bars">"""
            reason_pairs = [
                ("Checked out a printed book", "checked_out_printed_book_percent"),
                ("Sat, read, studied, or engaged with media", "sat_read_studied_engaged_with_media_percent"),
                ("Got help from a librarian", "got_help_from_librarians_percent"),
                ("Attended classes, programs, or lectures", "attended_classes_programs_lectures_percent"),
                ("Used 3D printers or new technology", "used_3d_printers_or_new_tech_percent"),
            ]
            max_r = max(visitor_reasons.get(k, 0) for _, k in reason_pairs) or 1
            for label, key in reason_pairs:
                val = visitor_reasons.get(key, 0)
                pct_w = (val / max_r) * 100 if max_r else 0
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{label}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-money" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{val}%</span>
  </div>"""
            body += '\n</div>'

        # Library services offered (ALA Digital Inclusion Survey)
        if services:
            body += """
<h3>Services offered by public libraries (ALA Digital Inclusion Survey 2014)</h3>
<div class="services-bars">"""
            svc_pairs = [
                ("Free public WiFi", "free_public_wifi_percent"),
                ("Summer reading programs", "summer_reading_programs_percent"),
                ("Digital literacy training", "basic_digital_literacy_training_percent"),
                ("Assist with gov services online", "assist_online_government_services_percent"),
                ("Help apply for jobs", "help_apply_for_jobs_percent"),
                ("Online job resources", "online_job_resources_percent"),
                ("Host adult events", "host_adult_events_percent"),
                ("Host teen events", "host_teen_events_percent"),
                ("Training on new devices", "training_new_devices_percent"),
                ("Safe online practices training", "training_safe_online_practices_percent"),
                ("Social media training", "training_social_media_percent"),
                ("Early learning tech (Pre-K)", "early_learning_tech_prek_percent"),
                ("Business information resources", "business_information_resources_percent"),
            ]
            max_s = max(services.get(k, 0) for _, k in svc_pairs) or 1
            for label, key in svc_pairs:
                val = services.get(key, 0)
                pct_w = (val / max_s) * 100 if max_s else 0
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{label}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-green" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{val}%</span>
  </div>"""
            body += '\n</div>'

        # NCES School Libraries
        if nces and nces.get('number_of_schools_with_libraries_media_centers'):
            sl = nces['number_of_schools_with_libraries_media_centers']
            staff = nces.get('average_staff_per_library_media_center', {})
            cat = nces.get('percent_with_automated_catalog', {})
            books = nces.get('books_per_100_students', {})
            workstations = nces.get('computer_workstations_per_100_students', {})
            internet = nces.get('percent_with_internet_connection', {})

            body += f"""

<h3>School Libraries / Media Centers (NCES, 2011-12)</h3>
<p class="wiki-sub">The NCES Schools and Staffing Survey (SASS) - since discontinued - provides the most recent comprehensive data on school libraries. In 2011-12, {sl.get('2011_12_total', 81200):,} public schools had library media centers ({sl.get('2011_12_elementary', 58000):,} elementary, {sl.get('2011_12_secondary', 17100):,} secondary). Each center averaged {staff.get('2011_12', 1.77)} staff and {cat.get('2011_12', 88.3)}% had automated catalogs.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{sl.get('2011_12_total', 81200):,}</div><div class="label">Schools with libraries (2011-12)</div></div>
  <div class="stat-card"><div class="num">{staff.get('2011_12', 1.77)}</div><div class="label">Avg staff per media center</div></div>
  <div class="stat-card"><div class="num">{cat.get('2011_12', 88.3)}%</div><div class="label">With automated catalog</div></div>
  <div class="stat-card"><div class="num">{books.get('2011_12', 2188):,}</div><div class="label">Books per 100 students</div></div>
  <div class="stat-card"><div class="num">{workstations.get('2011_12', 3.1)}</div><div class="label">Computers per 100 students</div></div>
  <div class="stat-card"><div class="num">{internet.get('2011_12', 95.9)}%</div><div class="label">With internet connection</div></div>
</div>"""

            # School library trend table
            body += """
<h3>School library trends over time</h3>
<table class="wikitable">
  <tr><th>Metric</th><th>1999-2000</th><th>2003-04</th><th>2007-08</th><th>2011-12</th></tr>"""
            trend_rows = [
                ("Schools with libraries", sl.get("1999_2000_total"), sl.get("2003_04_total"), sl.get("2007_08_total"), sl.get("2011_12_total")),
                ("Avg staff per center", staff.get("1999_2000"), staff.get("2003_04"), staff.get("2007_08"), staff.get("2011_12")),
                ("% with automated catalog", cat.get("1999_2000"), cat.get("2003_04"), cat.get("2007_08"), cat.get("2011_12")),
                ("% with internet", internet.get("1999_2000"), internet.get("2003_04"), internet.get("2007_08"), internet.get("2011_12")),
                ("Books per 100 students", books.get("1999_2000"), books.get("2003_04"), books.get("2007_08"), books.get("2011_12")),
                ("Computers per 100 students", None, workstations.get("2003_04"), workstations.get("2007_08"), workstations.get("2011_12")),
            ]
            for label, v1, v2, v3, v4 in trend_rows:
                def fmt(v):
                    if v is None: return "-"
                    if isinstance(v, float): return f"{v:.1f}"
                    return f"{v:,}"
                body += f'\n  <tr><td>{label}</td><td class="pct">{fmt(v1)}</td><td class="pct">{fmt(v2)}</td><td class="pct">{fmt(v3)}</td><td class="pct">{fmt(v4)}</td></tr>'
            body += '\n</table>'

            body += '<p class="rsrc">Source: NCES Digest of Education Statistics, Table 701.10, from the Schools and Staffing Survey (SASS). The SASS was discontinued after 2011-12, making this the most recent comprehensive national school library data available. School library expenditure per pupil declined from $23.37 (1999-2000) to $16.00 (2011-12) in current dollars - a real-terms cut of over 50%.</p>'

        body += '<p class="rsrc">Demographics source: Gallup (Dec 2019 poll), Pew Research Center (2016 Libraries survey, 2015 Hispanic media survey), and NEA SPPA 2022. Reasons for use from Pew 2016. Library services from ALA Digital Inclusion Survey 2014. Library attendance at programs increased 10 points from 2015 to 2016 (17% to 27%), the largest gain of any usage category.</p>'

        # NEA 2022 reading trends
        nea_reading = demo.get('nea_reading_trends', {})
        if nea_reading and nea_reading.get('books_read_any_2017_2022_by_demographic'):
            br = nea_reading['books_read_any_2017_2022_by_demographic']
            lit = nea_reading.get('literature_read_2017_2022_by_demographic', {})
            novels = nea_reading.get('novels_or_short_stories_2017_2022', {})
            poetry = nea_reading.get('poetry_2017_2022', {})

            all_books = br.get('all_adults', {})
            all_lit = lit.get('all_adults', {})
            all_novels = novels.get('all_adults', {})
            all_poetry = poetry.get('all_adults', {})

            body += f"""

<h2 id="reading-trends">Reading Trends: The Decline of Book Reading (NEA 2017-2022)</h2>
<p class="wiki-sub">The NEA's 2022 Survey of Public Participation in the Arts reveals a significant decline in book reading among American adults. From 2017 to 2022, the share of adults who read books fell from {all_books.get('2017', 0)*100:.1f}% to {all_books.get('2022', 0)*100:.1f}% - a {abs(all_books.get('pp_change', 0)):.1f} percentage point drop. Literature reading (novels, poetry, plays) fell even more sharply, from {all_lit.get('2017', 0)*100:.1f}% to {all_lit.get('2022', 0)*100:.1f}%. Novel reading hit a record low of {all_novels.get('2022', 0)*100:.1f}%. This decline has direct implications for libraries, which exist to serve a population that is reading less.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{all_books.get('2022', 0)*100:.1f}%</div><div class="label">Adults who read books (2022)</div></div>
  <div class="stat-card"><div class="num">{all_books.get('pp_change', 0):.1f}pp</div><div class="label">Change from 2017</div></div>
  <div class="stat-card"><div class="num">{all_lit.get('2022', 0)*100:.1f}%</div><div class="label">Read literature (2022)</div></div>
  <div class="stat-card"><div class="num">{all_novels.get('2022', 0)*100:.1f}%</div><div class="label">Read novels (record low)</div></div>
  <div class="stat-card"><div class="num">{all_poetry.get('2022', 0)*100:.1f}%</div><div class="label">Read poetry (2022)</div></div>
  <div class="stat-card"><div class="num">{br.get('female',{}).get('2022',0)*100:.1f}%</div><div class="label">Women reading books</div></div>
</div>"""

            # Reading by gender and age bars
            body += """
<h3>Book reading rate by demographic (2017 vs 2022, % who read any books)</h3>
<table class="wikitable">
  <tr><th>Demographic group</th><th>2017</th><th>2022</th><th>Change</th><th>Significant?</th></tr>"""
            demo_labels = [
                ("All adults", "all_adults"),
                ("Male", "male"), ("Female", "female"),
                ("Hispanic", "hispanic"), ("White", "white"),
                ("African American", "african_american"), ("Asian", "asian"),
                ("Ages 18-24", "age_18_24"), ("Ages 25-34", "age_25_34"),
                ("Ages 35-44", "age_35_44"), ("Ages 45-54", "age_45_54"),
                ("Ages 55-64", "age_55_64"), ("Ages 65-74", "age_65_74"),
                ("Ages 75+", "age_75_plus"),
                ("Grade school", "education_grade_school"),
                ("Some high school", "education_some_high_school"),
                ("High school diploma", "education_high_school_diploma"),
                ("Some college", "education_some_college"),
                ("Bachelor's", "education_bachelors"),
                ("Graduate/professional", "education_graduate_professional"),
            ]
            for label, key in demo_labels:
                grp = br.get(key, {})
                v17 = grp.get('2017', 0)
                v22 = grp.get('2022', 0)
                chg = grp.get('pp_change', 0)
                sig = "Yes" if grp.get('significant', False) else "No"
                body += f'\n  <tr><td>{label}</td><td class="pct">{v17*100:.1f}%</td><td class="pct">{v22*100:.1f}%</td><td class="pct">{"+" if chg >= 0 else ""}{chg:.1f}pp</td><td>{sig}</td></tr>'
            body += '\n</table>'

            # Literature reading comparison
            if lit:
                body += """
<h3>Literature reading (novels, poetry, plays) by demographic</h3>
<table class="wikitable">
  <tr><th>Group</th><th>2017</th><th>2022</th><th>Change</th></tr>"""
                lit_groups = [("All adults", "all_adults"), ("Male", "male"), ("Female", "female"),
                              ("Ages 18-24", "age_18_24"), ("Ages 55-64", "age_55_64"),
                              ("Ages 65-74", "age_65_74"), ("Graduate/professional", "education_graduate_professional")]
                for label, key in lit_groups:
                    grp = lit.get(key, {})
                    v17 = grp.get('2017', 0)
                    v22 = grp.get('2022', 0)
                    chg = grp.get('pp_change', 0)
                    body += f'\n  <tr><td>{label}</td><td class="pct">{v17*100:.1f}%</td><td class="pct">{v22*100:.1f}%</td><td class="pct">{"+" if chg >= 0 else ""}{chg:.1f}pp</td></tr>'
                body += '\n</table>'

            body += '<p class="rsrc">Source: NEA Survey of Public Participation in the Arts (SPPA) 2022, a supplement to the U.S. Census Bureau Current Population Survey (n=40,718). Reading rates are the share of U.S. adults who read books (excluding work/school reading) in the prior 12 months. The 2022 U.S. adult population was 255.4 million. The decline in book reading from 52.7% to 48.5% represents approximately 10.7 million fewer adult readers. Older adults (55+) saw the steepest declines, while young adults (18-34) held steady. Poetry reading fell to a record low of 9.2%.</p>'

    # ---- COVID-19 Impact and Recovery ----
    cov = stats.get('covid_recovery', {})
    if cov and cov.get('recovery'):
        rec = cov['recovery']
        trends = cov.get('year_trends', [])
        bl_yr = rec.get('baseline_year', 'FY2019')
        tr_yr = rec.get('trough_year', 'FY2020')
        lt_yr = rec.get('latest_year', 'FY2024')
        v_decline = rec.get('visits_decline_pct', 0)
        v_recovery = rec.get('visits_recovery_pct', 0)
        c_decline = rec.get('circ_decline_pct', 0)
        c_recovery = rec.get('circ_recovery_pct', 0)
        p_decline = rec.get('programs_decline_pct', 0)
        p_recovery = rec.get('programs_recovery_pct', 0)
        inc_chg = rec.get('income_change_pct', 0)
        stf_chg = rec.get('staff_change_pct', 0)

        body += f"""

<h2 id="covid-recovery">COVID-19 Impact and Recovery</h2>
<p class="wiki-sub">The COVID-19 pandemic was the most disruptive event in the history of American public libraries. Using multi-year IMLS Public Libraries Survey data, we can trace the full arc: in {bl_yr}, American libraries recorded {rec.get('visits_baseline', 0)/1e6:.0f}M visits. By {tr_yr}, that had collapsed to {rec.get('visits_trough', 0)/1e6:.0f}M - a {v_decline:.0f}% decline. As of {lt_yr}, visits have recovered to {rec.get('visits_latest', 0)/1e6:.0f}M, still only {v_recovery:.0f}% of pre-pandemic levels. Yet funding actually grew {inc_chg:+.0f}%, suggesting libraries pivoted to digital services rather than closing for good.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">-{v_decline:.0f}%</div><div class="label">Visits lost in COVID trough</div></div>
  <div class="stat-card"><div class="num">{v_recovery:.0f}%</div><div class="label">Visits recovered (vs {bl_yr})</div></div>
  <div class="stat-card"><div class="num">{c_recovery:.0f}%</div><div class="label">Circulation recovered</div></div>
  <div class="stat-card"><div class="num">{p_recovery:.0f}%</div><div class="label">Programs recovered</div></div>
  <div class="stat-card"><div class="num">{inc_chg:+.0f}%</div><div class="label">Income change</div></div>
  <div class="stat-card"><div class="num">{stf_chg:+.1f}%</div><div class="label">Staff change</div></div>
</div>"""

        # Multi-year trend SVG chart
        if trends and len(trends) >= 2:
            yrs = [t["year"].replace("FY", "") for t in trends]
            visits = [t.get("visits", 0) for t in trends]
            circ = [t.get("circulation", 0) for t in trends]
            max_v = max(max(visits), max(circ)) or 1
            n = len(trends)
            bw = 50
            chart_w = n * bw * 2 + 70
            chart_h = 260
            body += f'\n<h3>Visits vs circulation: {bl_yr} to {lt_yr}</h3>\n<svg class="trend-chart" viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Library visits and circulation trend FY2019-FY2024">'
            for i in range(n):
                x = 50 + i * bw * 2
                # Visits bar
                hv = (visits[i] / max_v) * (chart_h - 60) if max_v else 0
                body += f'<rect x="{x}" y="{chart_h - 40 - hv:.1f}" width="{bw - 5}" height="{hv:.1f}" fill="var(--accent-blue)" rx="3"/>'
                body += f'<text x="{x + (bw-5)/2:.0f}" y="{chart_h - 25}" text-anchor="middle" class="axis-text">{yrs[i]}</text>'
                body += f'<text x="{x + (bw-5)/2:.0f}" y="{chart_h - 45 - hv:.1f}" text-anchor="middle" class="bar-label">{visits[i]/1e6:.0f}M</text>'
                # Circulation bar
                hc = (circ[i] / max_v) * (chart_h - 60) if max_v else 0
                body += f'<rect x="{x + bw}" y="{chart_h - 40 - hc:.1f}" width="{bw - 5}" height="{hc:.1f}" fill="var(--accent-green)" rx="3"/>'
                body += f'<text x="{x + bw + (bw-5)/2:.0f}" y="{chart_h - 45 - hc:.1f}" text-anchor="middle" class="bar-label">{circ[i]/1e6:.0f}M</text>'
            body += f'\n<text x="10" y="20" class="axis-text" fill="var(--accent-blue)">Visits</text>'
            body += f'\n<text x="10" y="38" class="axis-text" fill="var(--accent-green)">Circulation</text>'
            body += '</svg>'

        # Year-by-year table
        if trends:
            body += f"""
<h3>Year-by-year national library statistics</h3>
<table class="wikitable">
  <tr><th>Year</th><th>States</th><th>Visits</th><th>Visits/capita</th><th>Circulation</th><th>Programs</th><th>Income</th><th>Staff</th><th>Visits YoY</th></tr>"""
            for t in trends:
                body += f'\n  <tr><td>{t["year"]}</td><td>{t.get("states_reporting",0)}</td><td>{t.get("visits",0):,}</td><td class="pct">{t.get("visits_per_capita",0):.2f}</td><td>{t.get("circulation",0):,}</td><td>{t.get("programs",0):,}</td><td>${t.get("income",0)/1e9:.1f}B</td><td>{t.get("staff",0):,}</td><td class="pct">{"+" if t.get("visits_yoy",0) >= 0 else ""}{t.get("visits_yoy",0):.1f}%</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">Source: IMLS Public Libraries Survey (PLS) multi-year data compiled via ALA State of America\'s Libraries. The baseline year is {bl_yr} (pre-pandemic), the trough is {tr_yr} (pandemic low), and latest is {lt_yr}. Note: FY2021 data is missing from this compilation as many states received reporting waivers during the pandemic. Visits have not fully recovered - as of {lt_yr}, they remain {100 - v_recovery:.0f}% below {bl_yr} levels - but circulation and programs have recovered more quickly, and income actually increased, reflecting expanded digital services and federal pandemic relief funding.</p>'

    # ---- State Per-Capita Library Rankings (PLS FY2024) ----
    pc = stats.get('state_per_capita', {})
    if pc and pc.get('rankings'):
        rankings = pc['rankings']
        tot_pop = pc.get('total_population', 0)
        tot_visits = pc.get('total_visits', 0)
        tot_circ = pc.get('total_circulation', 0)
        tot_income = pc.get('total_income', 0)
        tot_buildings = pc.get('total_buildings', 0)
        n_states = pc.get('total_states', 56)

        body += f"""

<h2 id="per-capita-rankings">State Per-Capita Library Rankings (FY2024)</h2>
<p class="wiki-sub">Normalizing library statistics by population reveals which states invest most heavily in library services relative to their size. These per-capita rankings, computed from IMLS Public Libraries Survey FY2024 data across {n_states} states and territories serving {tot_pop/1e6:.0f}M residents, show a different picture than raw totals. The District of Columbia consistently tops per-capita measures, reflecting its urban density and concentrated library investment. Below are the top 10 states across {len(rankings)} key metrics.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{tot_visits/1e6:.0f}M</div><div class="label">Total library visits (FY2024)</div></div>
  <div class="stat-card"><div class="num">{tot_circ/1e9:.1f}B</div><div class="label">Total circulation</div></div>
  <div class="stat-card"><div class="num">${tot_income/1e9:.1f}B</div><div class="label">Total library income</div></div>
  <div class="stat-card"><div class="num">{tot_buildings:,}</div><div class="label">Library buildings</div></div>
  <div class="stat-card"><div class="num">{tot_visits/tot_pop:.1f}</div><div class="label">National visits per capita</div></div>
  <div class="stat-card"><div class="num">${tot_income/tot_pop:.0f}</div><div class="label">National $ per capita</div></div>
</div>"""

        # Top 10 visits per capita
        vc = rankings.get('visits_per_capita', [])
        if vc:
            body += """
<h3>Top 10 states: library visits per capita</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Visits per capita</th><th>Total visits</th><th>Population</th></tr>"""
            for i, r in enumerate(vc[:10], 1):
                body += f'\n  <tr><td class="pct">{i}</td><td><a href="states/{esc(r["state"])}.html">{esc(r["state_name"])}</a></td><td class="pct">{r["visits_per_capita"]:.2f}</td><td>{r["visits"]:,}</td><td>{r["population"]:,}</td></tr>'
            body += '\n</table>'

        # Top 10 spending per capita
        sc = rankings.get('spending_per_capita', [])
        if sc:
            body += """
<h3>Top 10 states: library spending per capita</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>$ per capita</th><th>Total income</th><th>Local share</th></tr>"""
            for i, r in enumerate(sc[:10], 1):
                body += f'\n  <tr><td class="pct">{i}</td><td><a href="states/{esc(r["state"])}.html">{esc(r["state_name"])}</a></td><td class="pct">${r["spending_per_capita"]:.0f}</td><td>${r["income"]/1e6:.0f}M</td><td class="pct">{r["local_pct"]:.0f}%</td></tr>'
            body += '\n</table>'

        # Top 10 circulation per capita
        cc = rankings.get('circ_per_capita', [])
        if cc:
            body += """
<h3>Top 10 states: circulation per capita</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Circ per capita</th><th>Digital circ %</th><th>Total circulation</th></tr>"""
            for i, r in enumerate(cc[:10], 1):
                body += f'\n  <tr><td class="pct">{i}</td><td><a href="states/{esc(r["state"])}.html">{esc(r["state_name"])}</a></td><td class="pct">{r["circ_per_capita"]:.1f}</td><td class="pct">{r["digital_circ_pct"]:.0f}%</td><td>{r["circulation"]:,}</td></tr>'
            body += '\n</table>'

        # Top 10 librarians per 10K population
        lc = rankings.get('librarians_per_10k', [])
        if lc:
            body += """
<h3>Top 10 states: librarians per 10,000 residents</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Librarians per 10K</th><th>Total librarians</th><th>Population</th></tr>"""
            for i, r in enumerate(lc[:10], 1):
                body += f'\n  <tr><td class="pct">{i}</td><td><a href="states/{esc(r["state"])}.html">{esc(r["state_name"])}</a></td><td class="pct">{r["librarians_per_10k"]:.2f}</td><td>{r["librarians"]:,}</td><td>{r["population"]:,}</td></tr>'
            body += '\n</table>'

        # Top 10 books per capita
        bc = rankings.get('books_per_capita', [])
        if bc:
            body += """
<h3>Top 10 states: book volumes per capita</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Books per capita</th><th>Total volumes</th><th>Population</th></tr>"""
            for i, r in enumerate(bc[:10], 1):
                body += f'\n  <tr><td class="pct">{i}</td><td><a href="states/{esc(r["state"])}.html">{esc(r["state_name"])}</a></td><td class="pct">{r["books_per_capita"]:.2f}</td><td>{r["books"]:,}</td><td>{r["population"]:,}</td></tr>'
            body += '\n</table>'

        # Top 10 WiFi sessions per capita
        wc = rankings.get('wifi_per_capita', [])
        if wc:
            body += """
<h3>Top 10 states: WiFi sessions per capita</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>WiFi per capita</th><th>Total sessions</th><th>Population</th></tr>"""
            for i, r in enumerate(wc[:10], 1):
                body += f'\n  <tr><td class="pct">{i}</td><td><a href="states/{esc(r["state"])}.html">{esc(r["state_name"])}</a></td><td class="pct">{r["wifi_per_capita"]:.1f}</td><td>{r["wifi_sessions"]:,}</td><td>{r["population"]:,}</td></tr>'
            body += '\n</table>'

        # Top 10 digital circulation percentage
        dc = rankings.get('digital_circ_pct', [])
        if dc:
            body += """
<h3>Top 10 states: digital circulation as % of total</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Digital circ %</th><th>E-circulation</th><th>Total circulation</th></tr>"""
            for i, r in enumerate(dc[:10], 1):
                body += f'\n  <tr><td class="pct">{i}</td><td><a href="states/{esc(r["state"])}.html">{esc(r["state_name"])}</a></td><td class="pct">{r["digital_circ_pct"]:.0f}%</td><td>{r.get("ecirc_per_capita", 0) * r["population"]:,.0f}</td><td>{r["circulation"]:,}</td></tr>'
            body += '\n</table>'

        # Top 10 programs per 10K
        pc10 = rankings.get('programs_per_10k', [])
        if pc10:
            body += """
<h3>Top 10 states: programs per 10,000 residents</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Programs per 10K</th><th>Total programs</th><th>Attendance</th></tr>"""
            for i, r in enumerate(pc10[:10], 1):
                body += f'\n  <tr><td class="pct">{i}</td><td><a href="states/{esc(r["state"])}.html">{esc(r["state_name"])}</a></td><td class="pct">{r["programs_per_10k"]:.1f}</td><td>{r["programs"]:,}</td><td>{r["program_attendance"]:,}</td></tr>'
            body += '\n</table>'

        # Top 10 registered borrowers %
        rb = rankings.get('registered_pct', [])
        if rb:
            body += """
<h3>Top 10 states: registered borrowers as % of population</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Registered %</th><th>Registered borrowers</th><th>Population</th></tr>"""
            for i, r in enumerate(rb[:10], 1):
                body += f'\n  <tr><td class="pct">{i}</td><td><a href="states/{esc(r["state"])}.html">{esc(r["state_name"])}</a></td><td class="pct">{r["registered_pct"]:.0f}%</td><td>{r["registered_borrowers"]:,}</td><td>{r["population"]:,}</td></tr>'
            body += '\n</table>'

        # Lowest spending per capita
        low_spend = pc.get('lowest', {}).get('spending_per_capita', [])
        if low_spend:
            body += """
<h3>Lowest library spending per capita</h3>
<table class="wikitable">
  <tr><th>State</th><th>$ per capita</th><th>Total income</th><th>Population</th></tr>"""
            for r in low_spend:
                body += f'\n  <tr><td><a href="states/{esc(r["state"])}.html">{esc(r["state_name"])}</a></td><td class="pct">${r["spending_per_capita"]:.0f}</td><td>${r["income"]/1e6:.0f}M</td><td>{r["population"]:,}</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">Source: IMLS Public Libraries Survey (PLS) FY2024, compiled via ALA State of America\'s Libraries data. Per-capita metrics are computed by dividing each state\'s aggregate library statistic by its total population served. Rankings include all {n_states} states and territories with population &ge; 1,000. Some territories show extreme ratios (e.g., 100% digital circulation) due to small library systems with specialized collections.</p>'

    # ---- PLS Extended Metrics: Bookmobiles, ILL, WiFi, etc. ----
    plse = stats.get('pls_extended', {})
    if plse and plse.get('national_totals'):
        pe_nat = plse['national_totals']
        pe_n_states = plse.get('state_count', 56)
        pe_rankings = plse.get('rankings', {})

        pe_bookmobiles = pe_nat.get('bookmobiles', 0)
        pe_ill_from = pe_nat.get('interlibrary_loan_from', 0)
        pe_ill_to = pe_nat.get('interlibrary_loan_to', 0)
        pe_ref = pe_nat.get('reference_transactions', 0)
        pe_registered = pe_nat.get('registered_borrowers', 0)
        pe_wifi = pe_nat.get('wifi_sessions', 0)
        pe_internet = pe_nat.get('public_internet_users', 0)
        pe_books = pe_nat.get('book_volumes', 0)
        pe_ebook_circ = pe_nat.get('ebook_circulation', 0)
        pe_program_att = pe_nat.get('total_program_attendance', 0)

        body += f"""

<h2 id="pls-extended">Beyond the Basics: Bookmobiles, WiFi, and ILL</h2>
<p class="wiki-sub">The IMLS Public Libraries Survey captures dozens of metrics beyond the headline numbers. This section surfaces the less-discussed but equally important dimensions of library service: the {pe_bookmobiles:,} bookmobiles still operating across America, {pe_registered/1e6:.0f}M registered borrowers, {pe_ill_from/1e6:.0f}M interlibrary loans received, {pe_wifi/1e6:.0f}M WiFi sessions, and {pe_books/1e6:.0f}M book volumes on shelves.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{pe_registered/1e6:.0f}M</div><div class="label">Registered borrowers</div></div>
  <div class="stat-card"><div class="num">{pe_books/1e6:.0f}M</div><div class="label">Book volumes on shelves</div></div>
  <div class="stat-card"><div class="num">{pe_ill_from/1e6:.0f}M</div><div class="label">ILL items received</div></div>
  <div class="stat-card"><div class="num">{pe_ill_to/1e6:.0f}M</div><div class="label">ILL items lent</div></div>
  <div class="stat-card"><div class="num">{pe_wifi/1e6:.0f}M</div><div class="label">WiFi sessions</div></div>
  <div class="stat-card"><div class="num">{pe_bookmobiles:,}</div><div class="label">Bookmobiles</div></div>
  <div class="stat-card"><div class="num">{pe_internet/1e6:.0f}M</div><div class="label">Public internet users</div></div>
  <div class="stat-card"><div class="num">{pe_ref/1e6:.0f}M</div><div class="label">Reference transactions</div></div>
  <div class="stat-card"><div class="num">{pe_ebook_circ/1e6:.0f}M</div><div class="label">E-book circulation</div></div>
  <div class="stat-card"><div class="num">{pe_program_att/1e6:.0f}M</div><div class="label">Program attendance</div></div>
</div>"""

        # Bookmobiles top states
        bm_rank = pe_rankings.get('bookmobiles', [])
        if bm_rank:
            body += """
<h3>States with the most bookmobiles</h3>
<p class="wiki-sub">Bookmobiles remain a vital service for reaching rural communities, homebound patrons, and childcare centers.</p>
<table class="wikitable">
  <tr><th>State</th><th>Bookmobiles</th></tr>"""
            for r in bm_rank[:10]:
                body += f'\n  <tr><td><a href="states/{r["state"]}.html">{esc(r.get("state_name", r["state"]))}</a></td><td class="pct">{r["value"]}</td></tr>'
            body += '\n</table>'

        # ILL top states
        ill_rank = pe_rankings.get('interlibrary_loan_from', [])
        if ill_rank:
            body += """
<h3>Top states by interlibrary loan items received</h3>
<table class="wikitable">
  <tr><th>State</th><th>ILL items received</th></tr>"""
            for r in ill_rank[:10]:
                body += f'\n  <tr><td><a href="states/{r["state"]}.html">{esc(r.get("state_name", r["state"]))}</a></td><td class="pct">{r["value"]:,}</td></tr>'
            body += '\n</table>'

        # WiFi top states
        wifi_rank = pe_rankings.get('wifi_sessions', [])
        if wifi_rank:
            body += """
<h3>Top states by WiFi sessions</h3>
<table class="wikitable">
  <tr><th>State</th><th>WiFi sessions</th></tr>"""
            for r in wifi_rank[:10]:
                body += f'\n  <tr><td><a href="states/{r["state"]}.html">{esc(r.get("state_name", r["state"]))}</a></td><td class="pct">{r["value"]:,}</td></tr>'
            body += '\n</table>'

        # Reference transactions top states
        ref_rank = pe_rankings.get('reference_transactions', [])
        if ref_rank:
            body += """
<h3>Top states by reference transactions</h3>
<table class="wikitable">
  <tr><th>State</th><th>Reference transactions</th></tr>"""
            for r in ref_rank[:10]:
                body += f'\n  <tr><td><a href="states/{r["state"]}.html">{esc(r.get("state_name", r["state"]))}</a></td><td class="pct">{r["value"]:,}</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">Source: IMLS Public Libraries Survey (PLS) FY2024, compiled via ALA State of America\'s Libraries data. All {pe_n_states} states and territories are included. IMLS uses negative sentinels (-1, -3, -40) for suppressed/unreported values, normalized to 0. The {pe_bookmobiles:,} bookmobiles represent a often-overlooked dimension of library service - Kentucky leads with 74 bookmobiles. Interlibrary loan totals ({pe_ill_from/1e6:.0f}M received vs {pe_ill_to/1e6:.0f}M lent) show a rough balance, though individual states vary widely. Reference transactions ({pe_ref/1e6:.0f}M nationally) have been declining as patrons shift to self-service digital resources.</p>'

    # ---- Interlibrary Loan and Resource Sharing ----
    ill = stats.get('ill', {})
    if ill and ill.get('national_totals'):
        ill_nat = ill['national_totals']
        ill_borrowed = ill_nat.get('loans_borrowed', 0)
        ill_lent = ill_nat.get('loans_lent', 0)
        ill_total = ill_nat.get('total_ill_activity', 0)
        ill_ratio = ill_nat.get('borrowed_lent_ratio', 1.0)
        ill_systems = ill_nat.get('reporting_systems_fy2024', 0)
        ill_trends = ill.get('trends', [])
        ill_oclc = ill.get('oclc_stats', {})
        ill_by_state = ill.get('by_state', {})
        ill_networks = ill.get('networks', [])
        ill_facts = ill.get('key_facts', [])

        body += f"""

<h2 id="ill">Interlibrary Loan: The Hidden Sharing Network</h2>
<p class="wiki-sub">Interlibrary loan (ILL) is the system that allows libraries to borrow items from other libraries on behalf of their patrons - making the collective holdings of all US libraries available to every individual library user. In FY2024, US public libraries processed {ill_total/1e6:.0f}M ILL transactions ({ill_borrowed/1e6:.0f}M borrowed, {ill_lent/1e6:.0f}M lent) across {ill_systems:,} reporting systems. The borrowed-to-lent ratio of {ill_ratio:.2f} shows the system is roughly balanced nationally, though individual states vary widely.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{ill_total/1e6:.0f}M</div><div class="label">Total ILL transactions (FY2024)</div></div>
  <div class="stat-card"><div class="num">{ill_borrowed/1e6:.0f}M</div><div class="label">Items borrowed</div></div>
  <div class="stat-card"><div class="num">{ill_lent/1e6:.0f}M</div><div class="label">Items lent</div></div>
  <div class="stat-card"><div class="num">{ill_systems:,}</div><div class="label">Reporting library systems</div></div>
  <div class="stat-card"><div class="num">{ill_ratio:.2f}</div><div class="label">Borrowed/lent ratio</div></div>
</div>"""

        # 25-year trend chart
        if ill_trends and len(ill_trends) >= 2:
            labels = [str(t['year']) for t in ill_trends]
            totals = [t.get('total', 0) for t in ill_trends]
            max_total = max(totals) or 1
            n = len(ill_trends)
            bw = 32
            chart_w = n * bw + 60
            chart_h = 240
            body += f'\n<h3>ILL volume over 25 years (FY2000-FY2024)</h3>\n<svg class="trend-chart" viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="ILL volume trend 2000-2024">'
            for i in range(n):
                x = 35 + i * bw
                h = (totals[i] / max_total) * (chart_h - 60) if max_total else 0
                body += f'<rect x="{x}" y="{chart_h - 40 - h:.1f}" width="{bw - 5}" height="{h:.1f}" fill="var(--accent-blue)" rx="3"/>'
                if i % 5 == 0 or i == n - 1:
                    body += f'<text x="{x + (bw-5)/2:.0f}" y="{chart_h - 22}" text-anchor="middle" class="axis-text">{labels[i]}</text>'
                    body += f'<text x="{x + (bw-5)/2:.0f}" y="{chart_h - 45 - h:.1f}" text-anchor="middle" class="bar-label">{totals[i]/1e6:.0f}M</text>'
            body += '</svg>'

        # Top states by ILL borrowed
        ill_states = ill_by_state.get('states', [])
        if ill_states:
            body += """
<h3>Top states by ILL items borrowed</h3>
<table class="wikitable">
  <tr><th>State</th><th>Borrowed</th><th>Lent</th><th>Total</th></tr>"""
            for s in ill_states[:15]:
                body += f'\n  <tr><td><a href="states/{s.get("state","")}.html">{esc(s.get("state_name", s.get("state","")))}</a></td><td class="pct">{s.get("borrowed",0):,}</td><td>{s.get("lent",0):,}</td><td>{s.get("total",0):,}</td></tr>'
            body += '\n</table>'

        # OCLC resource sharing
        if ill_oclc:
            body += f"""
<h3>OCLC Resource Sharing Network</h3>
<p>{esc(ill_oclc.get("organization",""))}</p>
<table class="wikitable">
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Total OCLC member libraries</td><td class="pct">{esc(str(ill_oclc.get("member_libraries","")))}</td></tr>
  <tr><td>Resource sharing network</td><td class="pct">{esc(str(ill_oclc.get("resource_sharing_network_size","")))}</td></tr>
  <tr><td>E-resource ILL requests/year</td><td class="pct">{esc(str(ill_oclc.get("e_resource_requests_year","")))}</td></tr>
  <tr><td>Express program (fast fulfillment)</td><td class="pct">{esc(str(ill_oclc.get("express_program","")))}</td></tr>
  <tr><td>Founded</td><td class="pct">{esc(str(ill_oclc.get("founded","")))}</td></tr>
</table>"""

        # Resource sharing networks
        if ill_networks:
            body += """
<h3>Major resource sharing networks</h3>
<table class="wikitable">
  <tr><th>Network</th><th>Description</th></tr>"""
            for net in ill_networks:
                body += f'\n  <tr><td>{esc(net.get("name",""))}</td><td>{esc(net.get("description","")[:150])}{"..." if len(net.get("description",""))>150 else ""}</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">Source: IMLS Public Libraries Survey (PLS) FY2024 fields LOANFM (borrowed) and LOANTO (lent), aggregated from {ill_systems:,} public library systems. Trend data covers FY2000-FY2024 (25 years). OCLC statistics from OCLC at-a-glance and resource sharing pages. Note: PLS data covers public libraries only - academic, school, special, and medical library ILL are not included, so the true national ILL volume is higher. The FY2024 total of {ill_total/1e6:.0f}M represents a recovery from the COVID-era low; FY2024 set the all-time record for items borrowed ({ill_borrowed/1e6:.0f}M). For context, FY2024 e-circulation (~{316+245}M items) is ~4x the ILL volume, showing how direct e-licensing now substitutes for some returnable book ILL.</p>'

    # ---- ALA State of America's Libraries Report 2024 ----
    ala = stats.get('ala_report', {})
    if ala and ala.get('key_statistics'):
        ks = ala['key_statistics']
        top_books = ala.get('top_10_challenged_books', [])
        state_leg = ala.get('state_legislation', [])
        fed_leg = ala.get('federal_legislation', [])
        titles_23 = ks.get('unique_titles_challenged_2023', 4240)
        titles_22 = ks.get('unique_titles_challenged_2022', 2571)
        pct_inc = ks.get('percent_increase_challenged_titles', 65)
        attempts = ks.get('censorship_attempts_documented_2023', 1247)
        bills = ks.get('state_censorship_bills_introduced_2023', 151)
        avg_pre = ks.get('average_unique_titles_challenged_2001_2020', 273)
        pub_pct_22 = ks.get('public_library_challenges_percent_2022', 16)
        pub_pct_23 = ks.get('public_library_challenges_percent_2023', 32)

        body += f"""

<h2 id="ala-report">State of America's Libraries (ALA 2024)</h2>
<p class="wiki-sub">The American Library Association's annual State of America's Libraries Report is the field's most authoritative year-in-review. The 2024 edition (covering 2023 data) documents a censorship crisis: {titles_23:,} unique titles were challenged in {attempts:,} documented censorship attempts - a {pct_inc:.0f}% increase from {titles_22:,} in 2022. For context, the average year from 2001-2020 saw only {avg_pre} unique titles challenged. Meanwhile, {bills} state censorship bills were introduced across the country, and public library challenges doubled from {pub_pct_22}% to {pub_pct_23}% of all challenges.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{titles_23:,}</div><div class="label">Unique titles challenged (2023)</div></div>
  <div class="stat-card"><div class="num">+{pct_inc:.0f}%</div><div class="label">Increase from 2022</div></div>
  <div class="stat-card"><div class="num">{attempts:,}</div><div class="label">Censorship attempts documented</div></div>
  <div class="stat-card"><div class="num">{bills}</div><div class="label">State censorship bills introduced</div></div>
  <div class="stat-card"><div class="num">{avg_pre}</div><div class="label">Avg titles/year (2001-2020)</div></div>
  <div class="stat-card"><div class="num">{pub_pct_23}%</div><div class="label">Public library share of challenges</div></div>
</div>"""

        # Pre-2023 vs 2023 comparison bar chart
        body += f"""
<h3>The censorship surge: 2023 in historical context</h3>
<svg class="trend-chart" viewBox="0 0 480 220" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Challenged titles historical comparison">
  <rect x="40" y="120" width="80" height="70" fill="var(--accent-blue)" rx="4"/>
  <text x="80" y="205" text-anchor="middle" class="axis-text">2001-2020 avg</text>
  <text x="80" y="112" text-anchor="middle" class="bar-label">{avg_pre}</text>
  <rect x="180" y="92" width="80" height="98" fill="var(--accent-yellow)" rx="4"/>
  <text x="220" y="205" text-anchor="middle" class="axis-text">2022</text>
  <text x="220" y="84" text-anchor="middle" class="bar-label">{titles_22:,}</text>
  <rect x="320" y="20" width="80" height="170" fill="var(--accent-red)" rx="4"/>
  <text x="360" y="205" text-anchor="middle" class="axis-text">2023</text>
  <text x="360" y="12" text-anchor="middle" class="bar-label">{titles_23:,}</text>
</svg>"""

        # Top 10 most challenged books
        if top_books:
            body += """
<h3>Top 10 most challenged books of 2023</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>Title</th><th>Author</th><th>Reasons cited</th></tr>"""
            for b in top_books:
                body += f'\n  <tr><td class="pct">{b.get("rank", "")}</td><td><em>{esc(b.get("title", ""))}</em></td><td>{esc(b.get("author", ""))}</td><td>{esc(b.get("reasons", ""))}</td></tr>'
            body += '\n</table>'

        # State legislation highlights
        if state_leg:
            body += """
<h3>State legislation highlights</h3>
<table class="wikitable">
  <tr><th>State</th><th>Development</th></tr>"""
            for s in state_leg:
                body += f'\n  <tr><td><a href="states/{esc(s["state"])}.html">{esc(s["state"])}</a></td><td>{esc(s["description"])}</td></tr>'
            body += '\n</table>'

        # Federal legislation highlights
        if fed_leg:
            body += """
<h3>Federal legislation & policy highlights</h3>
<ul class="wiki-list">"""
            for f in fed_leg:
                body += f'\n  <li>{esc(f["description"])}</li>'
            body += '\n</ul>'

        body += f'<p class="rsrc">Source: American Library Association, <em>State of America\'s Libraries Report 2024</em> (covering 2023 data). The ALA tracks censorship attempts in partnership with the ALA Office for Intellectual Freedom. Challenge data may undercount actual incidents as reporting is voluntary. The {titles_23 - titles_22:,} additional titles challenged in 2023 vs 2022 represent the largest single-year increase ever recorded.</p>'

    # ---- Digital Public Library of America (DPLA) ----
    dpla = stats.get('dpla', {})
    if dpla and (dpla.get('collection_growth_over_time') or dpla.get('growth_timeline')):
        dpla_items = dpla.get('total_items_sum_of_hubs', dpla.get('estimated_items_current', 50000000))
        dpla_timeline = dpla.get('collection_growth_over_time', dpla.get('growth_timeline', []))
        dpla_hubs = dpla.get('all_hubs', [])
        dpla_top_hubs = dpla.get('top_hubs_by_item_count', [])
        dpla_hubs_by_state = dpla.get('hubs_by_state', [])
        dpla_svc = dpla.get('service_hub_count', 0)
        dpla_content = dpla.get('content_hub_count', 0)
        dpla_states = dpla.get('distinct_states_with_hub', dpla.get('states_represented', 40))
        dpla_institutions = dpla.get('contributing_institutions', '8,700+')
        growth_x = (dpla_items / dpla_timeline[0]['items']) if dpla_timeline and dpla_timeline[0].get('items') else 20

        body += f"""

<h2 id="dpla">Digital Public Library of America (DPLA)</h2>
<p class="wiki-sub">The Digital Public Library of America, founded April 18, 2013 and headquartered in Boston, is the nation's aggregator of digital cultural heritage. Rather than holding its own collections, DPLA brings together metadata from thousands of libraries, archives, museums, and historical societies through a network of {dpla_svc} Service Hubs and {dpla_content} Content Hubs. Since launching with 2.4 million items, DPLA has grown to {dpla_items/1e6:.0f}M+ items from {dpla_institutions} contributing institutions - a {growth_x:.0f}x increase in just over a decade.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{dpla_items/1e6:.0f}M+</div><div class="label">Items aggregated</div></div>
  <div class="stat-card"><div class="num">{dpla_institutions}</div><div class="label">Contributing institutions</div></div>
  <div class="stat-card"><div class="num">{dpla_svc + dpla_content}</div><div class="label">Partner hubs ({dpla_svc} service + {dpla_content} content)</div></div>
  <div class="stat-card"><div class="num">{dpla_states}</div><div class="label">States with hubs</div></div>
  <div class="stat-card"><div class="num">2013</div><div class="label">Founded (Boston, MA)</div></div>
  <div class="stat-card"><div class="num">{growth_x:.0f}x</div><div class="label">Growth since launch</div></div>
</div>"""

        # Growth chart SVG
        if dpla_timeline and len(dpla_timeline) >= 2:
            labels = [t.get("date", t.get("label", "")) for t in dpla_timeline]
            items = [t["items"] for t in dpla_timeline]
            max_items = max(items) or 1
            n = len(dpla_timeline)
            bw = 55
            chart_w = n * bw + 60
            chart_h = 240
            body += f'\n<h3>DPLA collection growth: items over time</h3>\n<svg class="trend-chart" viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="DPLA collection growth over time">'
            for i in range(n):
                x = 45 + i * bw
                h = (items[i] / max_items) * (chart_h - 60) if max_items else 0
                body += f'<rect x="{x}" y="{chart_h - 40 - h:.1f}" width="{bw - 8}" height="{h:.1f}" fill="var(--accent-green)" rx="3"/>'
                body += f'<text x="{x + (bw-8)/2:.0f}" y="{chart_h - 22}" text-anchor="middle" class="axis-text">{labels[i]}</text>'
                body += f'<text x="{x + (bw-8)/2:.0f}" y="{chart_h - 45 - h:.1f}" text-anchor="middle" class="bar-label">{items[i]/1e6:.0f}M</text>'
            body += '</svg>'

        # Growth timeline table
        body += """
<h3>DPLA growth timeline</h3>
<table class="wikitable">
  <tr><th>Date</th><th>Items</th><th>Notes</th></tr>"""
        for t in dpla_timeline:
            body += f'\n  <tr><td>{t.get("date", "")} {esc(t.get("label", ""))}</td><td class="pct">{t["items"]:,}</td><td>{esc(t.get("note", ""))}</td></tr>'
        body += '\n</table>'

        # Top hubs by item count
        if dpla_top_hubs:
            body += """
<h3>Top DPLA hubs by item count</h3>
<table class="wikitable">
  <tr><th>Hub</th><th>Type</th><th>States</th><th>Items</th></tr>"""
            for h in dpla_top_hubs[:15]:
                body += f'\n  <tr><td>{esc(h.get("name", ""))}</td><td>{esc(h.get("hub_type", "").title())}</td><td>{esc(h.get("states", ""))}</td><td class="pct">{h.get("item_count", 0):,}</td></tr>'
            body += '\n</table>'

        # Hubs by state
        if dpla_hubs_by_state:
            body += """
<h3>DPLA hubs by state</h3>
<table class="wikitable">
  <tr><th>State</th><th>Hubs</th><th>Items</th><th>Hub names</th></tr>"""
            for s in dpla_hubs_by_state[:20]:
                hub_names = ', '.join(s.get('hubs', []))
                body += f'\n  <tr><td>{esc(s.get("state", ""))}</td><td>{s.get("hub_count", 0)}</td><td class="pct">{s.get("item_count", 0):,}</td><td>{esc(hub_names)}</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">Source: DPLA website (dp.la and pro.dp.la), DPLA WordPress REST API (dpla.wpengine.com/wp-json/wp/v2/), DPLA GitHub ingestion3 repository, and Wikipedia. DPLA launched April 18, 2013 with ~2.4M items from 6 Service Hubs and 10 Content Hubs representing over 400 institutions. Current item count of {dpla_items/1e6:.0f}M+ is the sum of individual hub counts; DPLA self-reports "{esc(dpla.get("total_items_reported", "53M+"))}". The DPLA API at api.dp.la/v2 requires a registered API key (request via apps@dp.la). DPLA is a 501(c)(3) nonprofit (EIN 46-1160948) headquartered in Boston, MA.</p>'

    # ---- School Libraries: State-Level Certified Librarian Access ----
    nces_full = stats.get('nces_school_full', {})
    if nces_full and nces_full.get('national_totals_2011_12'):
        nat = nces_full['national_totals_2011_12']
        sr = nces_full.get('state_rankings_2011_12', {})
        sv = nces_full.get('state_level_variation_2011_12', {})
        trends_nces = nces_full.get('trends_over_time', [])
        breakdown = nces_full.get('breakdown_by_school_characteristic_2011_12', {})

        body += f"""

<h2 id="school-librarians">School Libraries: Certified Librarian Access by State</h2>
<p class="wiki-sub">While public libraries get most attention, the nation's 81,200 school library media centers are where most Americans first encounter libraries. NCES data from 2011-12 (the most recent available, as the SASS survey was discontinued) reveals stark state-level disparities: Tennessee has certified librarians in 97.6% of school libraries, while California has them in only 25.2% - a 72 percentage-point gap. Nationwide, only 66.4% of school libraries have a full-time certified librarian, meaning roughly 1 in 5 school libraries (16,990) have no certified librarian at all.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{nat.get('school_libraries', 81200):,}</div><div class="label">School libraries (2011-12)</div></div>
  <div class="stat-card"><div class="num">{nat.get('pct_schools_with_library', 90.2)}%</div><div class="label">Schools with a library</div></div>
  <div class="stat-card"><div class="num">{nat.get('pct_lmc_with_fulltime_certified', 66.4)}%</div><div class="label">With full-time certified librarian</div></div>
  <div class="stat-card"><div class="num">{nat.get('pct_lmc_with_no_certified', 20.9)}%</div><div class="label">With NO certified librarian</div></div>
  <div class="stat-card"><div class="num">{nat.get('total_paid_professional_specialists', 88520):,}</div><div class="label">Paid library specialists</div></div>
  <div class="stat-card"><div class="num">{nat.get('total_volunteers', 273260):,}</div><div class="label">Volunteers in school libraries</div></div>
</div>"""

        # Highest certified librarian states
        highest = sr.get('highest_pct_fulltime_certified', [])
        if highest:
            body += """
<h3>States with the highest certified librarian rates</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>% full-time certified librarian</th></tr>"""
            for i, s in enumerate(highest[:10], 1):
                st_name = s.get('state', '')
                body += f'\n  <tr><td class="pct">{i}</td><td>{esc(st_name)}</td><td class="pct">{s.get("pct_fulltime_certified", 0):.1f}%</td></tr>'
            body += '\n</table>'

        # Lowest certified librarian states
        lowest = sr.get('lowest_pct_fulltime_certified', [])
        if lowest:
            body += """
<h3>States with the lowest certified librarian rates</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>% full-time certified librarian</th></tr>"""
            for i, s in enumerate(lowest[:10], 1):
                st_name = s.get('state', '')
                body += f'\n  <tr><td class="pct">{i}</td><td>{esc(st_name)}</td><td class="pct">{s.get("pct_fulltime_certified", 0):.1f}%</td></tr>'
            body += '\n</table>'

        # States with most school libraries with NO certified librarian
        no_cert = sr.get('highest_pct_no_certified', [])
        if no_cert:
            body += """
<h3>States where school libraries have NO certified librarian (highest rates)</h3>
<table class="wikitable">
  <tr><th>State</th><th>% with no certified librarian</th></tr>"""
            for s in no_cert[:10]:
                body += f'\n  <tr><td>{esc(s.get("state", ""))}</td><td class="pct">{s.get("pct_no_certified", 0):.1f}%</td></tr>'
            body += '\n</table>'

        # Most school libraries by state
        most_sl = sr.get('most_school_libraries', [])
        if most_sl:
            body += """
<h3>States with the most school libraries</h3>
<table class="wikitable">
  <tr><th>State</th><th>School libraries</th></tr>"""
            for s in most_sl[:10]:
                body += f'\n  <tr><td>{esc(s.get("state", ""))}</td><td>{s.get("school_libraries", 0):,}</td></tr>'
            body += '\n</table>'

        # State variation stats
        if sv:
            body += f"""
<h3>National variation in school librarian access</h3>
<table class="wikitable">
  <tr><th>Metric</th><th>Value</th></tr>"""
            for k, v in sv.items():
                display = k.replace("_", " ").title()
                if isinstance(v, float):
                    val = f"{v:.1f}"
                else:
                    val = str(v)
                body += f'\n  <tr><td>{esc(display)}</td><td class="pct">{val}</td></tr>'
            body += '\n</table>'

        # Trends table
        if trends_nces:
            body += """
<h3>School library trends over time</h3>
<table class="wikitable">
  <tr><th>Year</th><th>Schools</th><th>Libraries</th><th>% with library</th><th>% full-time certified</th></tr>"""
            for t in trends_nces:
                pct_cert = t.get('pct_lmc_with_fulltime_certified') or t.get('pct_with_fulltime_certified_librarian')
                body += f'\n  <tr><td>{t.get("year", "")}</td><td>{t.get("total_public_schools", 0):,}</td><td>{t.get("school_libraries", 0):,}</td><td class="pct">{t.get("pct_schools_with_library", 0):.1f}%</td><td class="pct">{f"{pct_cert:.1f}%" if pct_cert else "N/A"}</td></tr>'
            body += '\n</table>'

        body += '<p class="rsrc">Source: NCES Schools and Staffing Survey (SASS), Table Library. Data from 2011-12 is the most recent available because the SASS was replaced by the National Teacher and Principal Survey (NTPS) in 2015-16, which does not include a school library component. The 72.4 percentage-point spread between Tennessee (97.6%) and California (25.2%) represents one of the largest state-level disparities in any educational metric. Charter schools have dramatically lower staffing: 32.8% full-time certified vs 67.4% for traditional public schools. Data currency note: this data is over a decade old; current school librarian access rates are likely lower due to budget cuts and the SASS/NTPS discontinuation has created a data gap.</p>'

    # ---- ALA-Accredited LIS Degree Programs ----
    lis = stats.get('lis_programs', {})
    if lis and lis.get('totals'):
        lt = lis['totals']
        l_us = lt.get('total_us_accredited_programs', 56)
        l_all = lt.get('total_accredited_programs_all_countries', 65)
        l_states = lt.get('us_states_and_territories_with_programs', 35)
        l_canada = lt.get('canada_programs', 8)
        l_by_state = lis.get('programs_by_state', {})
        l_by_type = lis.get('programs_by_institution_type', {})
        l_delivery = lis.get('delivery_options', {})
        l_programs = lis.get('programs', [])

        pub_count = l_by_type.get('public', {}).get('count', 0) if isinstance(l_by_type.get('public'), dict) else 0
        priv_count = l_by_type.get('private', {}).get('count', 0) if isinstance(l_by_type.get('private'), dict) else 0
        online_count = l_delivery.get('us_programs_with_online_option', 0)
        fully_online = l_delivery.get('us_programs_fully_online_only', 0)
        no_distance = l_delivery.get('us_programs_with_no_distance_education', 0)

        body += f"""

<h2 id="lis-programs">Library Science Degree Programs (ALA-Accredited)</h2>
<p class="wiki-sub">To become a professional librarian, most positions require a Master's degree from an ALA-accredited Library and Information Studies program. There are currently {l_us} such programs in the United States (plus {l_canada} in Canada), spread across only {l_states} states and territories. This means 15 states have NO ALA-accredited library school within their borders. The profession is increasingly accessible online: {fully_online} programs are fully online-only, and {online_count} of {l_us} offer some distance education option.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{l_us}</div><div class="label">US ALA-accredited programs</div></div>
  <div class="stat-card"><div class="num">{l_all}</div><div class="label">Total (all countries)</div></div>
  <div class="stat-card"><div class="num">{l_states}</div><div class="label">States with a program</div></div>
  <div class="stat-card"><div class="num">{pub_count}</div><div class="label">Public institutions</div></div>
  <div class="stat-card"><div class="num">{priv_count}</div><div class="label">Private institutions</div></div>
  <div class="stat-card"><div class="num">{fully_online}</div><div class="label">Fully online programs</div></div>
</div>"""

        # Programs by state
        if l_by_state:
            body += """
<h3>ALA-accredited LIS programs by state</h3>
<table class="wikitable">
  <tr><th>State</th><th>Programs</th><th>Institution(s)</th></tr>"""
            for code, s in sorted(l_by_state.items(), key=lambda x: -x[1].get('count', 0)):
                insts = ", ".join(s.get('institutions', []))
                body += f'\n  <tr><td><a href="states/{esc(code)}.html">{esc(s.get("state_name", code))}</a></td><td class="pct">{s.get("count", 0)}</td><td>{esc(insts)}</td></tr>'
            body += '\n</table>'

        # Public vs private
        body += f"""
<h3>Public vs private institutions</h3>
<div class="services-bars">
  <div class="svc-row">
    <span class="svc-name">Public institutions</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pub_count/max(l_us,1)*100:.1f}%"></span></span>
    <span class="svc-count">{pub_count}</span>
  </div>
  <div class="svc-row">
    <span class="svc-name">Private institutions</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-money" style="width:{priv_count/max(l_us,1)*100:.1f}%"></span></span>
    <span class="svc-count">{priv_count}</span>
  </div>
</div>"""

        # Delivery options
        body += f"""
<h3>Distance education options</h3>
<div class="services-bars">
  <div class="svc-row">
    <span class="svc-name">Fully online only</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-green" style="width:{fully_online/max(l_us,1)*100:.1f}%"></span></span>
    <span class="svc-count">{fully_online}</span>
  </div>
  <div class="svc-row">
    <span class="svc-name">Any online/hybrid option</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-people" style="width:{online_count/max(l_us,1)*100:.1f}%"></span></span>
    <span class="svc-count">{online_count}</span>
  </div>
  <div class="svc-row">
    <span class="svc-name">No distance education</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-red" style="width:{no_distance/max(l_us,1)*100:.1f}%"></span></span>
    <span class="svc-count">{no_distance}</span>
  </div>
</div>"""

        body += f'<p class="rsrc">Source: ALA Office for Accreditation, Directory of ALA-Accredited and Candidate Programs in Library and Information Studies (ala.org/educationcareers/accreditedprograms). The directory includes {l_all} programs total: {l_us} in the US, {l_canada} in Canada, and 1 in the UK. Only {l_states} US states/territories have an accredited program, leaving 15 states without one. Programs are reviewed every 7 years under the 2014 Standards for Accreditation of Master\'s Programs in Library and Information Studies. The shift toward online education is striking: {fully_online} programs are fully online-only, making library science one of the most accessible professional degrees.</p>'

    # ---- State-level book censorship breakdown ----
    stcens = stats.get('state_censorship', {})
    if stcens and stcens.get('states'):
        sc_states = stcens['states']
        sc_total = stcens.get('total_challenges', 0)
        sc_banned = stcens.get('total_banned_removed', 0)
        sc_school = stcens.get('total_school_challenges', 0)
        sc_public = stcens.get('total_public_library_challenges', 0)
        sc_n = stcens.get('total_states_with_challenges', 0)

        body += f"""

<h2 id="state-censorship">Book Bans by State: The Censorship Map</h2>
<p class="wiki-sub">Book censorship is not evenly distributed across America. Of {sc_n} states with documented challenges, just five account for the vast majority of all book bans. Florida alone recorded {sc_states[0]['total_challenges']:,} challenges with {sc_states[0]['banned_removed']:,} books banned or removed. {sc_school:,} of all challenges occurred in school libraries versus {sc_public:,} in public libraries - making K-12 education the primary battleground for intellectual freedom in America.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{sc_total:,}</div><div class="label">Total challenges (all states)</div></div>
  <div class="stat-card"><div class="num">{sc_banned:,}</div><div class="label">Books banned or removed</div></div>
  <div class="stat-card"><div class="num">{sc_school:,}</div><div class="label">School library challenges</div></div>
  <div class="stat-card"><div class="num">{sc_public:,}</div><div class="label">Public library challenges</div></div>
  <div class="stat-card"><div class="num">{sc_n}</div><div class="label">States with challenges</div></div>
  <div class="stat-card"><div class="num">{sc_school / max(sc_total, 1) * 100:.0f}%</div><div class="label">Challenges in schools</div></div>
</div>"""

        # Top 15 states table
        body += """
<h3>Top 15 states by total book challenges</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Challenges</th><th>Banned/Removed</th><th>Restricted</th><th>School</th><th>Public Lib</th><th>Unique Titles</th></tr>"""
        for i, s in enumerate(sc_states[:15], 1):
            body += f'\n  <tr><td class="pct">{i}</td><td><a href="states/{esc(s["state"])}.html">{esc(s["state_name"])}</a></td><td class="pct">{s["total_challenges"]:,}</td><td>{s["banned_removed"]:,}</td><td>{s["restricted"]}</td><td>{s["school_challenges"]:,}</td><td>{s["public_library_challenges"]}</td><td>{s["unique_titles"]}</td></tr>'
        body += '\n</table>'

        # School vs public library challenges bar chart for top 10
        body += """
<h3>School vs public library challenges (top 10 states)</h3>
<svg class="trend-chart" viewBox="0 0 520 260" preserveAspectRatio="xMidYMid meet" role="img" aria-label="School vs public library challenges by state">
  <text x="10" y="20" class="axis-text" fill="var(--accent-red)">School</text>
  <text x="10" y="38" class="axis-text" fill="var(--accent-blue)">Public</text>"""
        max_sc = max((s["school_challenges"] for s in sc_states[:10]), default=1) or 1
        for i, s in enumerate(sc_states[:10]):
            x = 50 + i * 47
            # School bar
            hs = (s["school_challenges"] / max_sc) * 180 if max_sc else 0
            body += f'<rect x="{x}" y="{230 - hs:.1f}" width="20" height="{hs:.1f}" fill="var(--accent-red)" rx="2"/>'
            # Public bar
            hp = (s["public_library_challenges"] / max_sc) * 180 if max_sc else 0
            body += f'<rect x="{x + 22}" y="{230 - hp:.1f}" width="20" height="{hp:.1f}" fill="var(--accent-blue)" rx="2"/>'
            body += f'<text x="{x + 21}" y="245" text-anchor="middle" class="axis-text">{esc(s["state"])}</text>'
        body += '</svg>'

        body += '<p class="rsrc">Source: ALA Office for Intellectual Freedom and EveryLibrary Institute Magnusson database, compiled via ALA State of America\'s Libraries 2024 state-level data. "Challenges" include formal and informal attempts to remove or restrict books. "Banned/Removed" means the book was actually pulled from shelves. School library challenges overwhelmingly dominate the data, reflecting the concentration of censorship efforts in K-12 education. States with zero challenges may reflect lack of reporting rather than absence of censorship.</p>'

    # ---- Federal Depository Library Program (FDLP) ----
    fdlp = stats.get('fdlp_summary', {})
    if fdlp and fdlp.get('total_libraries'):
        ftot = fdlp['total_libraries']
        freg = fdlp.get('regional_count', 0)
        fsel = fdlp.get('selective_count', 0)
        fstates = fdlp.get('states_covered', 0)
        foldest = fdlp.get('oldest_designation_year', 0)
        fnewest = fdlp.get('newest_designation_year', 0)
        ftypes = fdlp.get('library_types', {})
        fregions = fdlp.get('regions', {})
        fera = fdlp.get('era_buckets', {})
        fby_state = fdlp.get('by_state', [])

        body += f"""

<h2 id="fdlp-directory">Federal Depository Library Program: Full Directory</h2>
<p class="wiki-sub">The Federal Depository Library Program, established by Congress in 1813, ensures that the American public has free access to government information. Today, {ftot:,} libraries across {fstates} states and territories participate - {freg} regional depositories (which retain all publications) and {fsel:,} selective depositories (which choose materials relevant to their communities). The oldest participating library was designated in {foldest}, making this one of the oldest federal information programs still in operation.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{ftot:,}</div><div class="label">Total depository libraries</div></div>
  <div class="stat-card"><div class="num">{freg}</div><div class="label">Regional depositories</div></div>
  <div class="stat-card"><div class="num">{fsel:,}</div><div class="label">Selective depositories</div></div>
  <div class="stat-card"><div class="num">{fstates}</div><div class="label">States/territories</div></div>
  <div class="stat-card"><div class="num">{foldest}</div><div class="label">Oldest designation</div></div>
  <div class="stat-card"><div class="num">{fnewest}</div><div class="label">Newest designation</div></div>
</div>"""

        # Library type bars
        if ftypes:
            body += """
<h3>Depository libraries by type</h3>
<div class="services-bars">"""
            max_t = max(ftypes.values()) if ftypes else 1
            for label, cnt in sorted(ftypes.items(), key=lambda x: -x[1]):
                pct_w = (cnt / max_t) * 100 if max_t else 0
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(label)}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{cnt:,}</span>
  </div>"""
            body += '\n</div>'

        # Region distribution bars
        if fregions:
            body += """
<h3>Distribution by National Collection Service Area</h3>
<div class="services-bars">"""
            max_r = max(fregions.values()) if fregions else 1
            for label, cnt in sorted(fregions.items(), key=lambda x: -x[1]):
                pct_w = (cnt / max_r) * 100 if max_r else 0
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(label)}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-people" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{cnt:,}</span>
  </div>"""
            body += '\n</div>'

        # Era buckets bars
        if fera:
            body += """
<h3>When libraries joined the FDLP (by era)</h3>
<div class="services-bars">"""
            max_e = max(fera.values()) if fera else 1
            for label, cnt in fera.items():
                pct_w = (cnt / max_e) * 100 if max_e else 0
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(label)}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-money" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{cnt:,}</span>
  </div>"""
            body += '\n</div>'

        # Top states table
        if fby_state:
            body += """
<h3>Top 15 states by number of depository libraries</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Total</th><th>Regional</th><th>Selective</th><th>Academic</th><th>Public</th><th>Law</th><th>Oldest</th></tr>"""
            for i, s in enumerate(fby_state[:15], 1):
                body += f'\n  <tr><td class="pct">{i}</td><td><a href="states/{esc(s["state"])}.html">{esc(s["state_name"])}</a></td><td class="pct">{s["count"]}</td><td>{s["regional"]}</td><td>{s["selective"]}</td><td>{s["academic"]}</td><td>{s["public"]}</td><td>{s["law"]}</td><td>{s["oldest_year"] or ""}</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">Source: U.S. Government Publishing Office (GPO) Federal Depository Library Program Directory, via ask.gpo.gov/s/FDLD. Academic libraries make up the largest share of FDLP participants, followed by public libraries. Regional depositories (one or two per state) serve as permanent repositories for all federal publications, while selective depositories tailor their collections to community needs. The program traces back to the Act of December 27, 1813, which authorized the distribution of one copy of every House and Senate journal to universities and historical societies.</p>'

    # ---- IMLS Museum Data File ----
    museums = stats.get('museums', {})
    if museums and museums.get('total_museums'):
        m_total = museums['total_museums']
        m_types = museums.get('museums_by_type', [])
        m_top = museums.get('top_10_states', [])
        m_locale = museums.get('urban_vs_rural', {})
        m_lib = museums.get('museum_library_relationship', {})
        m_rev = museums.get('museums_by_revenue_size', [])

        body += f"""

<h2 id="museums">America's Museums (IMLS Museum Data File 2018)</h2>
<p class="wiki-sub">The IMLS oversees both libraries and museums, making it the only federal agency with this dual mandate. Its 2018 Museum Data File - the final edition, as IMLS has retired this dataset - identified {m_total:,} museums across all 50 states and DC. Nearly half ({m_types[0]['count']/m_total*100:.0f}%) are historical societies or historic preservation organizations, reflecting America's grassroots approach to local history. The IMLS funds museums and libraries through parallel grant programs, and {m_lib.get('academic_affiliated_with_ipeds', 2566):,} museums are affiliated with academic institutions that also host libraries.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{m_total:,}</div><div class="label">Total museums</div></div>
  <div class="stat-card"><div class="num">{m_locale.get('urban', 0):,}</div><div class="label">Urban museums</div></div>
  <div class="stat-card"><div class="num">{m_locale.get('rural', 0):,}</div><div class="label">Rural museums</div></div>
  <div class="stat-card"><div class="num">51</div><div class="label">States + DC</div></div>
  <div class="stat-card"><div class="num">{m_lib.get('academic_affiliated_with_ipeds', 0):,}</div><div class="label">Academic-affiliated (IPEDS)</div></div>
  <div class="stat-card"><div class="num">{m_lib.get('co_located_with_library', 0)}</div><div class="label">Co-located with a library</div></div>
</div>"""

        # Museum types bars
        if m_types:
            body += """
<h3>Museums by type</h3>
<div class="services-bars">"""
            max_t = max(t.get('count', 0) for t in m_types) or 1
            for t in m_types:
                cnt = t.get('count', 0)
                pct_w = (cnt / max_t) * 100 if max_t else 0
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(t.get('type', ''))}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{cnt:,}</span>
  </div>"""
            body += '\n</div>'

        # Top states
        if m_top:
            body += """
<h3>Top 10 states by number of museums</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Museums</th></tr>"""
            for i, s in enumerate(m_top[:10], 1):
                body += f'\n  <tr><td class="pct">{i}</td><td><a href="states/{esc(s["state"])}.html">{esc(s["state"])}</a></td><td class="pct">{s.get("count", 0):,}</td></tr>'
            body += '\n</table>'

        # Urban vs rural
        if m_locale:
            urban = m_locale.get('urban', 0)
            rural = m_locale.get('rural', 0)
            body += f"""
<h3>Urban vs rural distribution</h3>
<div class="services-bars">
  <div class="svc-row">
    <span class="svc-name">Urban (City + Suburb)</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-people" style="width:{urban/max(urban+rural,1)*100:.1f}%"></span></span>
    <span class="svc-count">{urban:,}</span>
  </div>
  <div class="svc-row">
    <span class="svc-name">Rural (Town + Rural)</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-green" style="width:{rural/max(urban+rural,1)*100:.1f}%"></span></span>
    <span class="svc-count">{rural:,}</span>
  </div>
</div>"""

        body += f'<p class="rsrc">Source: IMLS Museum Data File (MDF) 2018, the final edition of this dataset. IMLS has stated it has no plans to update the files. The MDF covers museums in all 50 states plus DC. Museum types follow IMLS discipline codes (ART, HST, HSC, GMU, SCI, NAT, CMU, ZAW, BOT). Urban/rural classification uses NCES locale codes. The museum-library relationship data shows {m_lib.get("academic_affiliated_with_ipeds", 0):,} museums are affiliated with postsecondary institutions (which host academic libraries) and {m_lib.get("co_located_with_library", 0)} museums are explicitly co-located with a named library.</p>'

    # ---- Prison Libraries ----
    prison = stats.get('prison_libraries', {})
    if prison and prison.get('prison_counts'):
        pc = prison['prison_counts']
        la = prison.get('library_access', {})
        leg = prison.get('legislation', {})
        ks = prison.get('key_statistics', {})
        std = prison.get('standards_and_guidance', {})

        body += f"""

<h2 id="prison-libraries">Prison Libraries: The Hidden Gap</h2>
<p class="wiki-sub">Over 1.25 million Americans are incarcerated in U.S. prisons, yet no federal agency tracks how many of those prisons have functioning libraries. The Bureau of Justice Statistics counts prisoners but not library services; the BOP does not publish a public inventory of facility libraries; and state departments of corrections report inconsistently. What we do know: the Prison Libraries Act of 2026 (H.R. 7247) would authorize $60M over 6 years for prison library services - the first federal legislation to specifically target this gap. ALA's 2025 report found many prison libraries are "little more than a few dusty shelves."</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{pc.get('total_prisoners_yearend_2023', 1254200):,}</div><div class="label">Total U.S. prisoners (2023)</div></div>
  <div class="stat-card"><div class="num">{pc.get('federal_bop_prisoners_2023', 143300):,}</div><div class="label">Federal (BOP)</div></div>
  <div class="stat-card"><div class="num">{pc.get('state_prisoners_2023_estimated', 1110900):,}</div><div class="label">State prisoners</div></div>
  <div class="stat-card"><div class="num">{ks.get('individuals_released_from_prisons_per_year', 600000):,}</div><div class="label">Released each year</div></div>
  <div class="stat-card"><div class="num">$60M</div><div class="label">Prison Libraries Act (proposed)</div></div>
  <div class="stat-card"><div class="num">None</div><div class="label">Official access rate</div></div>
</div>"""

        # Prison population table
        body += f"""
<h3>U.S. prison population (BJS, yearend 2023)</h3>
<table class="wikitable">
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Total prisoners</td><td class="pct">{pc.get('total_prisoners_yearend_2023', 0):,}</td></tr>
  <tr><td>Change from 2022</td><td class="pct">+{pc.get('year_over_year_change_pct', 2)}%</td></tr>
  <tr><td>Federal (BOP jurisdiction)</td><td class="pct">{pc.get('federal_bop_prisoners_2023', 0):,}</td></tr>
  <tr><td>State (estimated)</td><td class="pct">{pc.get('state_prisoners_2023_estimated', 0):,}</td></tr>
  <tr><td>Sentenced (1+ years)</td><td class="pct">{pc.get('sentenced_more_than_1_year_2023', 0):,}</td></tr>
  <tr><td>Male prisoners (sentenced)</td><td class="pct">{pc.get('male_prisoners_sentenced_2023', 0):,}</td></tr>
  <tr><td>Female prisoners (sentenced)</td><td class="pct">{pc.get('female_prisoners_sentenced_2023', 0):,}</td></tr>
  <tr><td>Male decline since 2013</td><td class="pct">{pc.get('male_pct_decline_since_2013', 0)}%</td></tr>
  <tr><td>Female decline since 2013</td><td class="pct">{pc.get('female_pct_decline_since_2013', 0)}%</td></tr>
</table>"""

        # Offense composition
        offenses = ks.get('offense_composition_of_prison_population_pct', {})
        if offenses:
            body += """
<h3>Offense composition of prison population</h3>
<div class="services-bars">"""
            max_o = max(offenses.values()) if offenses else 1
            for label, val in sorted(offenses.items(), key=lambda x: -x[1]):
                display = label.replace("_", " ").title()
                pct_w = (val / max_o) * 100 if max_o else 0
                body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(display)}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-red" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{val}%</span>
  </div>"""
            body += '\n</div>'

        # Legislation
        curr = leg.get('current_bill', {})
        if curr:
            body += f"""
<h3>Prison Libraries Act of 2026</h3>
<table class="wikitable">
  <tr><th>Field</th><th>Detail</th></tr>
  <tr><td>House bill</td><td>{esc(curr.get('house', ''))}</td></tr>
  <tr><td>Senate companion</td><td>{esc(curr.get('senate', ''))}</td></tr>
  <tr><td>Congress</td><td>{esc(curr.get('congress', ''))}</td></tr>
  <tr><td>Date introduced</td><td>{esc(curr.get('date_introduced', ''))}</td></tr>
  <tr><td>Status</td><td>{esc(curr.get('status', ''))}</td></tr>
</table>"""

        # Key context
        body += f"""
<h3>Key context</h3>
<ul class="wiki-list">
  <li>Pell Grant eligibility for incarcerated people reinstated July 1, 2023, ending the 1994 ban</li>
  <li>ALA benchmark: adequate prison library funding should be ~$13 per capita per incarcerated person</li>
  <li>ALA recidivism-savings ratio: every dollar invested in prison education saves ~5x in future incarceration costs</li>
  <li>ALA released "Investing in Prison Libraries" report in June 2025</li>
  <li>ALA Standards for Library Services for the Incarcerated or Detained: 2024 Revised Edition (first revision since 1992)</li>
</ul>"""

        body += '<p class="rsrc">Source: Bureau of Justice Statistics (BJS) yearend 2023 prison statistics, ALA "Investing in Prison Libraries" (2025), Congress.gov (H.R. 7247 / S. 4320), and Ithaka S+R (2024). The central data limitation: no comprehensive national dataset on prison libraries exists. BJS counts prisoners but not libraries; BOP facility-library inventories are not public; state DOCs vary widely. The facility census most recently collected was 2019. The Prison Libraries Act would be the first federal legislation to specifically establish and expand prison library services.</p>'

    # ---- Library of Congress ----
    loc = stats.get('loc', {})
    if loc and loc.get('fy2024'):
        fy24 = loc['fy2024']
        loc_items_text = fy24.get('total_collection_items', '181.1 million')
        loc_budget_dict = fy24.get('budget', {})
        loc_budget = loc_budget_dict.get('total_budget_authority_usd', 897749000)
        loc_approp = loc_budget_dict.get('appropriations_usd', 852158000)
        loc_visits = fy24.get('website_visits', '149.3 million')
        loc_pages = fy24.get('website_page_views', '505.3 million')
        loc_onsite = fy24.get('on_site_visitors', '880,000')
        loc_ref = fy24.get('reference_requests', '764,000')
        loc_staff = loc_budget_dict.get('permanent_employees', 3263)
        loc_female = loc_budget_dict.get('staff_female', 1871)
        loc_male = loc_budget_dict.get('staff_male', 1392)
        loc_buildings = loc.get('buildings', [])
        loc_growth = loc.get('historical_growth', [])
        loc_facts = loc.get('narrative_facts', [])
        loc_crs = fy24.get('congressional_research_service', {})
        loc_copyright = fy24.get('copyright_office', {})
        loc_nls = fy24.get('nls_blind_print_disabled', {})
        loc_coll_breakdown = fy24.get('collection_breakdown', [])

        body += f"""

<h2 id="loc">Library of Congress: The World's Largest Library</h2>
<p class="wiki-sub">Founded on April 24, 1800, the Library of Congress is the largest library in the world and the research arm of the U.S. Congress. From Thomas Jefferson's personal library of 6,487 books (purchased for $23,950 in 1815 after British troops burned the original collection) to {esc(loc_items_text)} items today, the LoC serves as both the national library of the United States and an international cultural repository. The Library operates across three buildings on Capitol Hill and employs {loc_staff:,} permanent staff.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{esc(loc_items_text)}</div><div class="label">Total items in collection</div></div>
  <div class="stat-card"><div class="num">${loc_budget/1e6:.0f}M</div><div class="label">FY2024 budget authority</div></div>
  <div class="stat-card"><div class="num">{esc(loc_visits)}</div><div class="label">Website visits (FY2024)</div></div>
  <div class="stat-card"><div class="num">{esc(loc_pages)}</div><div class="label">Website page views</div></div>
  <div class="stat-card"><div class="num">{esc(loc_onsite)}</div><div class="label">Onsite visitors</div></div>
  <div class="stat-card"><div class="num">{loc_staff:,}</div><div class="label">Permanent employees</div></div>
</div>"""

        # Historical growth timeline
        if loc_growth:
            body += """
<h3>Historical growth timeline</h3>
<table class="wikitable">
  <tr><th>Year</th><th>Event</th></tr>"""
            for g in loc_growth:
                body += f'\n  <tr><td class="pct">{g["year"]}</td><td>{esc(g["event"])}</td></tr>'
            body += '\n</table>'

        # NLS for the Blind and Print Disabled
        if loc_nls:
            body += f"""
<h3>National Library Service for the Blind and Print Disabled (NLS)</h3>
<p>The NLS provides free braille and talking-book services to eligible readers. In FY2024 it served {loc_nls.get("total_readers_served",0):,} readers and circulated {loc_nls.get("total_items_circulated",0):,} items.</p>
<table class="wikitable">
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Total items circulated</td><td class="pct">{loc_nls.get("total_items_circulated",0):,}</td></tr>
  <tr><td>Digital cartridge audio circulated</td><td class="pct">{loc_nls.get("digital_cartridge_audio_circulated",0):,}</td></tr>
  <tr><td>BARD audio downloads</td><td class="pct">{loc_nls.get("bard_audio_downloads",0):,}</td></tr>
  <tr><td>E-braille circulated</td><td class="pct">{loc_nls.get("ebraille_circulated",0):,}</td></tr>
  <tr><td>Total readers served</td><td class="pct">{loc_nls.get("total_readers_served",0):,}</td></tr>
  <tr><td>Total items in collection</td><td class="pct">{loc_nls.get("total_items_in_collection",0):,}</td></tr>
  <tr><td>Appropriation</td><td class="pct">${loc_nls.get("appropriation_usd",0)/1e6:.1f}M</td></tr>
</table>"""

        # Copyright Office
        if loc_copyright:
            body += f"""
<h3>U.S. Copyright Office (LoC)</h3>
<table class="wikitable">
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Total registrations</td><td class="pct">{loc_copyright.get("total_registrations_all",0):,}</td></tr>
  <tr><td>Basic registrations</td><td class="pct">{loc_copyright.get("basic_registrations",0):,}</td></tr>
  <tr><td>Visual arts registrations</td><td class="pct">{loc_copyright.get("visual_arts_total",0):,}</td></tr>
  <tr><td>Documents recorded</td><td class="pct">{loc_copyright.get("documents_recorded",0):,}</td></tr>
  <tr><td>Works in recorded documents</td><td class="pct">{loc_copyright.get("works_in_recorded_documents",0):,}</td></tr>
  <tr><td>Registration fees recorded</td><td class="pct">${loc_copyright.get("registration_fees_recorded_usd",0)/1e6:.1f}M</td></tr>
</table>"""

        # Congressional Research Service
        if loc_crs:
            body += f"""
<h3>Congressional Research Service (CRS)</h3>
<table class="wikitable">
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Congressional requests responded to</td><td class="pct">{esc(str(loc_crs.get("congressional_requests_responded","")))}</td></tr>
  <tr><td>New products published</td><td class="pct">{esc(str(loc_crs.get("new_products_published","")))}</td></tr>
  <tr><td>Product updates</td><td class="pct">{esc(str(loc_crs.get("product_updates","")))}</td></tr>
  <tr><td>Seminar attendees</td><td class="pct">{esc(str(loc_crs.get("seminar_attendees","")))}</td></tr>
  <tr><td>Seminars held</td><td class="pct">{loc_crs.get("seminars_held",0):,}</td></tr>
</table>"""

        # Narrative facts
        if loc_facts:
            body += """
<h3>Notable facts about the Library of Congress</h3>
<ul class="wiki-list">"""
            for f in loc_facts[:12]:
                body += f'\n  <li>{esc(f)}</li>'
            body += '\n</ul>'

        body += f'<p class="rsrc">Source: Library of Congress FY2024 Annual Report of the Librarian of Congress (loc.gov/about/reports-and-budgets/annual-reports/), loc.gov/about/fascinating-facts/, and Wikipedia. The Library operates with a total budget authority of ${loc_budget/1e6:.0f}M (${loc_approp/1e6:.0f}M appropriations + ${loc_budget_dict.get("offsetting_receipts_usd",0)/1e6:.0f}M offsetting receipts). The Library employs {loc_staff:,} permanent staff ({loc_female:,} female, {loc_male:,} male), with an average of {loc_budget_dict.get("avg_years_loc_service",0)} years of service. Collections span {loc_coll_breakdown and len(loc_coll_breakdown) or 13} categories including cataloged books, manuscripts, maps, photographs, audio materials, and moving images. The NLS served {loc_nls.get("total_readers_served",0):,} blind and print-disabled readers in FY2024.</p>'

    # ---- National Library of Medicine ----
    nlm = stats.get('nlm', {})
    if nlm and nlm.get('current_stats'):
        nlm_stats = nlm['current_stats']
        nlm_items = nlm_stats.get('collection_size_items', 0)
        nlm_budget = nlm_stats.get('annual_budget_usd', 0)
        nlm_staff = nlm_stats.get('employees', 0)
        nlm_databases = nlm.get('key_databases', [])
        nlm_nnlm = nlm.get('nnlm_network', {})
        nlm_facts = nlm.get('key_facts', [])
        nlm_timeline = nlm.get('historical_timeline', [])
        nlm_founded = nlm.get('founded', 1836)

        body += f"""

<h2 id="nlm">National Library of Medicine: The World's Largest Biomedical Library</h2>
<p class="wiki-sub">Founded in {nlm_founded} as the Library of the Office of the Surgeon General, the National Library of Medicine is the world's largest biomedical library and a vital component of the National Institutes of Health. Located on the NIH campus in Bethesda, MD, NLM serves researchers, healthcare professionals, and the public through its extensive digital databases - most notably PubMed, which indexes over 40 million biomedical citations. Unlike most libraries, NLM's impact is felt primarily through its digital services rather than its physical collection of {nlm_items/1e6:.1f}M items.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{nlm_items/1e6:.1f}M</div><div class="label">Collection items</div></div>
  <div class="stat-card"><div class="num">${nlm_budget/1e6:.0f}M</div><div class="label">Annual budget (FY2016)</div></div>
  <div class="stat-card"><div class="num">{nlm_staff:,}</div><div class="label">Employees</div></div>
  <div class="stat-card"><div class="num">{nlm_nnlm.get('member_organizations', 8000):,}+</div><div class="label">NNLM member organizations</div></div>
  <div class="stat-card"><div class="num">{nlm_nnlm.get('regions', 7)}</div><div class="label">NNLM regions</div></div>
  <div class="stat-card"><div class="num">{len(nlm_databases)}</div><div class="label">Major databases</div></div>
</div>"""

        # Key databases
        if nlm_databases:
            body += """
<h3>Key databases and digital services</h3>
<table class="wikitable">
  <tr><th>Database</th><th>Size / Scope</th><th>Description</th></tr>"""
            for db in nlm_databases:
                body += f'\n  <tr><td>{esc(db.get("name",""))}</td><td class="pct">{esc(db.get("size",""))}</td><td>{esc(db.get("description","")[:150])}{"..." if len(db.get("description",""))>150 else ""}</td></tr>'
            body += '\n</table>'

        # NNLM network
        if nlm_nnlm:
            body += f"""
<h3>Network of the National Library of Medicine (NNLM)</h3>
<p>{esc(nlm_nnlm.get("description",""))}</p>
<table class="wikitable">
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Member organizations</td><td class="pct">{nlm_nnlm.get("member_count_text","8,000+")}</td></tr>
  <tr><td>Regions</td><td class="pct">{nlm_nnlm.get("regions",7)}</td></tr>
  <tr><td>Coordinating institutions</td><td class="pct">{nlm_nnlm.get("coordinating_institutions",14)}</td></tr>
</table>"""

        # Historical timeline (first 10 key events)
        if nlm_timeline:
            body += """
<h3>Historical timeline</h3>
<table class="wikitable">
  <tr><th>Year</th><th>Event</th></tr>"""
            for t in nlm_timeline[:12]:
                body += f'\n  <tr><td class="pct">{t.get("year","")}</td><td>{esc(t.get("event",""))}</td></tr>'
            body += '\n</table>'

        # Key facts
        if nlm_facts:
            body += """
<h3>Notable facts</h3>
<ul class="wiki-list">"""
            for f in nlm_facts[:10]:
                body += f'\n  <li>{esc(f)}</li>'
            body += '\n</ul>'

        body += f'<p class="rsrc">Source: nlm.nih.gov/about/, en.wikipedia.org/wiki/United_States_National_Library_of_Medicine, ncbi.nlm.nih.gov (GenBank statistics), nnlm.gov. NLM was founded in {nlm_founded} and established as the National Library of Medicine by the National Library of Medicine Act of 1956 (Public Law 941). Collection size of {nlm_items/1e6:.1f}M items is from 2015; budget of ${nlm_budget/1e6:.0f}M is FY2016 appropriation — more recent figures were not available from live .gov budget pages. PubMed contains 40M+ citations (March 2025); PubMed Central holds 10.8M full-text articles; ClinicalTrials.gov lists 444K+ trials from 221 countries; GenBank contains 53.9 trillion bases in 6.27 billion sequence records. The NNLM network connects {nlm_nnlm.get("member_organizations",8000):,}+ member organizations across {nlm_nnlm.get("regions",7)} regions.</p>'

    # ---- Digital Libraries (HathiTrust, Internet Archive, etc.) ----
    dl = stats.get('digital_libraries', {})
    if dl and dl.get('hathitrust'):
        ht = dl.get('hathitrust', {})
        ia = dl.get('internet_archive', {})
        pg = dl.get('project_gutenberg', {})
        gb = dl.get('google_books', {})
        si = dl.get('smithsonian_open_access', {})
        clt = dl.get('cross_library_totals', {})
        ht_vols = ht.get('current_stats', {}).get('total_volumes', 0)
        ht_members = ht.get('current_stats', {}).get('member_institutions', 0)
        ia_pages = ia.get('current_stats', {}).get('web_pages_archived', 0)
        ia_books = ia.get('current_stats', {}).get('books_texts', 0)
        pg_books = pg.get('current_stats', {}).get('total_ebooks', 0)
        gb_titles = gb.get('current_stats', {}).get('total_titles_scanned', 0)
        si_images = si.get('current_stats', {}).get('cc0_images', 0)

        body += f"""

<h2 id="digital-libraries">Digital Libraries: HathiTrust, Internet Archive & Beyond</h2>
<p class="wiki-sub">Beyond the physical library system, a parallel digital infrastructure has emerged over the past two decades. These digital libraries collectively hold billions of items - from the Internet Archive's {ia_pages/1e9:.0f}+ billion archived web pages to HathiTrust's {ht_vols/1e6:.0f}M digitized book volumes. Together they represent a massive expansion of access to human knowledge, though one constrained by copyright law, funding sustainability, and ongoing legal challenges.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{ia_pages/1e9:.0f}B+</div><div class="label">IA Wayback web pages</div></div>
  <div class="stat-card"><div class="num">{ht_vols/1e6:.0f}M</div><div class="label">HathiTrust volumes</div></div>
  <div class="stat-card"><div class="num">{gb_titles/1e6:.0f}M+</div><div class="label">Google Books scanned</div></div>
  <div class="stat-card"><div class="num">{ia_books/1e6:.0f}M</div><div class="label">IA books & texts</div></div>
  <div class="stat-card"><div class="num">{si_images/1e6:.0f}M</div><div class="label">Smithsonian CC0 images</div></div>
  <div class="stat-card"><div class="num">{pg_books/1e3:.0f}K</div><div class="label">Project Gutenberg eBooks</div></div>
</div>"""

        # HathiTrust section
        body += f"""
<h3>HathiTrust Digital Library</h3>
<p>{esc(ht.get("description", ""))}</p>
<table class="wikitable">
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Total digitized volumes</td><td class="pct">{ht_vols:,}</td></tr>
  <tr><td>Public domain volumes (US)</td><td class="pct">{ht.get("current_stats",{}).get("public_domain_volumes",0):,}</td></tr>
  <tr><td>Member institutions</td><td class="pct">{ht_members}</td></tr>
  <tr><td>Shared print volumes (25-yr retention)</td><td class="pct">{ht.get("current_stats",{}).get("shared_print_volumes",0):,}</td></tr>
  <tr><td>Founded</td><td class="pct">{esc(ht.get("founded",""))}</td></tr>
</table>"""
        if ht.get('key_facts'):
            body += '<ul class="wiki-list">'
            for f in ht['key_facts']:
                body += f'\n  <li>{esc(f)}</li>'
            body += '\n</ul>'

        # Internet Archive section
        body += f"""
<h3>Internet Archive</h3>
<p>{esc(ia.get("description", ""))}</p>
<table class="wikitable">
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Web pages archived (Wayback Machine)</td><td class="pct">{ia_pages:,}</td></tr>
  <tr><td>Books & texts</td><td class="pct">{ia_books:,}</td></tr>
  <tr><td>Video recordings</td><td class="pct">{ia.get("current_stats",{}).get("video_items",0):,}</td></tr>
  <tr><td>Audio recordings</td><td class="pct">{ia.get("current_stats",{}).get("audio_items",0):,}</td></tr>
  <tr><td>Software programs</td><td class="pct">{ia.get("current_stats",{}).get("software_programs",0):,}</td></tr>
  <tr><td>Daily archiving rate</td><td class="pct">{ia.get("current_stats",{}).get("daily_archiving_rate",0):,} pages/day</td></tr>
  <tr><td>Founded</td><td class="pct">{ia.get("founded","")}</td></tr>
</table>"""
        if ia.get('key_facts'):
            body += '<ul class="wiki-list">'
            for f in ia['key_facts']:
                body += f'\n  <li>{esc(f)}</li>'
            body += '\n</ul>'

        # Other digital libraries table
        body += """
<h3>Other major digital libraries</h3>
<table class="wikitable">
  <tr><th>Library</th><th>Founded</th><th>Key figure</th><th>Description</th></tr>"""
        body += f'\n  <tr><td>Project Gutenberg</td><td>{pg.get("founded","")}</td><td class="pct">{pg_books:,} eBooks</td><td>{esc(pg.get("description",""))}</td></tr>'
        body += f'\n  <tr><td>Google Books</td><td>{gb.get("founded","")}</td><td class="pct">{gb_titles:,} titles scanned</td><td>{esc(gb.get("description",""))}</td></tr>'
        body += f'\n  <tr><td>Smithsonian Open Access</td><td>{si.get("founded","")}</td><td class="pct">{si_images:,} CC0 images</td><td>{esc(si.get("description",""))}</td></tr>'
        body += '\n</table>'

        # Founding timeline
        timeline = clt.get('founding_timeline', [])
        if timeline:
            body += """
<h3>Founding timeline of major digital libraries</h3>
<table class="wikitable">
  <tr><th>Year</th><th>Library</th></tr>"""
            for t in timeline:
                body += f'\n  <tr><td class="pct">{t["year"]}</td><td>{esc(t["library"])}</td></tr>'
            body += '\n</table>'

        body += f'<p class="rsrc">Source: Wikipedia articles for HathiTrust, Internet Archive, Project Gutenberg, Google Books, and Smithsonian Open Access (citing primary sources including annual reports, press releases, and court opinions). HathiTrust: {ht_vols/1e6:.0f}M volumes ({ht.get("current_stats",{}).get("public_domain_volumes",0)/1e6:.1f}M public domain) from {ht_members} member institutions. Internet Archive: {ia_pages/1e9:.0f}B+ archived web pages and {ia_books/1e6:.0f}M books/texts. Google Books scanned {gb_titles/1e6:.0f}M+ titles with {gb.get("current_stats",{}).get("library_partners",0)} library partners. Note: these collections overlap heavily (Google scans feed HathiTrust; IA and Open Library share titles). Cross-library totals are not disjoint.</p>'

    # ---- Library Philanthropy: Carnegie, Friends, Gates, Endowments ----
    phil = stats.get('philanthropy', {})
    if phil and phil.get('carnegie_libraries'):
        carn = phil.get('carnegie_libraries', {})
        friends = phil.get('friends_groups', {})
        ufl = phil.get('ala_united_for_libraries', {})
        gates = phil.get('gates_foundation', {})
        endow = phil.get('endowments', [])
        founds = phil.get('major_foundations', [])
        priv_giving = phil.get('private_giving_to_libraries', {})
        crowdfund = phil.get('crowdfunding_and_community_fundraising', {})
        adopt = phil.get('adopt_a_book_programs', {})
        key_facts = phil.get('key_facts', [])
        carn_by_state = carn.get('by_state', [])
        carn_us = carn.get('total_built_us', 0)
        carn_world = carn.get('total_built_worldwide', 0)
        carn_us_dollars = carn.get('total_dollars_us', 0) or carn.get('dollar_total_by_state_parsed', 0)
        carn_states_count = carn.get('states_with_carnegie_libraries', 0)
        nyc_grant = carn.get('new_york_city_grant', {}) or {}
        gates_amt = gates.get('total_committed_estimate_usd', '')

        # Friends group counts
        fg_counts = friends.get('known_historical_counts', [])
        fg_latest = fg_counts[-1] if fg_counts else {}
        fg_members = fg_latest.get('members', 0)
        fg_groups = fg_latest.get('groups', 0)
        fg_year = fg_latest.get('year', 0)

        # Compute Carnegie top states for bars
        carn_sorted = sorted(carn_by_state, key=lambda x: x.get('public_libraries', 0), reverse=True)
        carn_top = carn_sorted[:10]
        carn_max = max((s.get('public_libraries', 0) for s in carn_top), default=1) or 1
        # Compute dollar totals
        carn_dollar_sorted = sorted(carn_by_state, key=lambda x: x.get('total_amount_usd', 0), reverse=True)
        carn_dollar_top = carn_dollar_sorted[:10]
        carn_dollar_max = max((s.get('total_amount_usd', 0) for s in carn_dollar_top), default=1) or 1

        body += f"""

<h2 id="philanthropy">Library Philanthropy: Carnegie, Friends & the Gates Foundation</h2>
<p class="wiki-sub">Before government funding, there was philanthropy. Andrew Carnegie alone funded {carn_us:,} of the {carn_world:,} library buildings he built worldwide - nearly half of all American libraries in existence by 1919. A century later, the Gates Foundation committed over $1 billion to wire libraries into the digital age. Between these bookends sits a vast ecosystem of Friends of the Library groups (thousands nationally, raising millions annually through book sales and membership drives), library endowments worth billions, and modern foundations whose grant budgets quietly shape the direction of American humanities and literacy.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{carn_us:,}</div><div class="label">Carnegie libraries built in US</div></div>
  <div class="stat-card"><div class="num">{carn_world:,}</div><div class="label">Carnegie libraries worldwide</div></div>
  <div class="stat-card"><div class="num">${carn_us_dollars/1e6:.1f}M</div><div class="label">Carnegie US construction grants</div></div>
  <div class="stat-card"><div class="num">{carn_states_count}</div><div class="label">States with Carnegie libraries</div></div>
  <div class="stat-card"><div class="num">{fg_groups:,}</div><div class="label">Friends of the Library groups ({fg_year})</div></div>
  <div class="stat-card"><div class="num">{fg_members/1000:.0f}K</div><div class="label">Friends group members ({fg_year})</div></div>
  <div class="stat-card"><div class="num">&gt;$1B</div><div class="label">Gates Foundation commitment</div></div>
  <div class="stat-card"><div class="num">${nyc_grant.get("amount_usd_1901",0)/1e6:.1f}M</div><div class="label">Carnegie's NYPL grant (1901)</div></div>
</div>"""

        # Carnegie overview narrative + timeline
        body += f"""
<h3>Andrew Carnegie's Library Empire (1889-1919)</h3>
<p>{esc(carn.get("years_active", ""))}. {esc(carn.get("context", "")) if carn.get("context") else "Carnegie funded construction of 1,670 public library buildings across 1,412 American communities for approximately $40 million (~$1.5 billion in 2025 dollars). The program required communities to provide land and commit to annual maintenance &mdash; a matching-fund model that shaped how public libraries were governed for the next century."}</p>
<table class="wikitable">
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Libraries built worldwide</td><td class="pct">{carn_world:,}</td></tr>
  <tr><td>Libraries built in United States</td><td class="pct">{carn_us:,}</td></tr>
  <tr><td>States with Carnegie libraries</td><td class="pct">{carn_states_count}</td></tr>
  <tr><td>States with none</td><td class="pct">{esc(", ".join(carn.get("states_with_no_carnegie_libraries", []) or ["Alaska", "Delaware"]))}</td></tr>
  <tr><td>Total US grant dollars (by-state parsed)</td><td class="pct">${carn_us_dollars:,.0f}</td></tr>
  <tr><td>NYPL branch grant (1901)</td><td class="pct">${nyc_grant.get("amount_usd_1901",0)/1e6:.1f}M for {nyc_grant.get("branches",65)} branches</td></tr>
  <tr><td>Endowed libraries</td><td class="pct">{esc(carn.get("endowed_libraries", "") or "Braddock, Homestead, Duquesne (PA)")}</td></tr>
</table>"""

        # Top states by number of Carnegie libraries
        if carn_top:
            body += """
<h3>Top 10 states by number of Carnegie libraries</h3>
<div class="services-bars">"""
            for s in carn_top:
                cnt = s.get('public_libraries', 0)
                body += f"""
  <div class="svc-row">
    <span class="svc-label">{esc(s["state"])}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-blue" style="width:{cnt/carn_max*100:.1f}%"></span></span>
    <span class="svc-count">{cnt:,}</span>
  </div>"""
            body += '\n</div>'

        # Top states by Carnegie dollars
        if carn_dollar_top:
            body += """
<h3>Top 10 states by Carnegie grant dollars</h3>
<table class="wikitable">
  <tr><th>State</th><th>Public grants</th><th>Libraries built</th><th>Earliest grant</th><th>Latest grant</th><th>Total (USD)</th></tr>"""
            for s in carn_dollar_top:
                body += f"""
  <tr>
    <td>{esc(s["state"])}</td>
    <td class="pct">{s.get("public_grants",0):,}</td>
    <td>{s.get("public_libraries",0):,}</td>
    <td>{esc(s.get("earliest_grant",""))}</td>
    <td>{esc(s.get("latest_grant",""))}</td>
    <td class="pct">${s.get("total_amount_usd",0):,.0f}</td>
  </tr>"""
            body += '\n</table>'

        # Friends of the Library
        if friends:
            first_grp = friends.get('first_us_group', {}) or {}
            first_uni = friends.get('first_university_group', {}) or {}
            body += f"""
<h3>Friends of the Library: grassroots fundraising</h3>
<p>{esc(friends.get("description", "") or "Friends of the Library groups are volunteer-driven nonprofit support organizations that fund-raise on behalf of their local libraries. They are the most widespread form of library philanthropy in the United States, with thousands of groups operating at public library systems nationwide.")}</p>
<table class="wikitable">
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Estimated national count</td><td class="pct">{esc(str(friends.get("estimated_count_national","")).split(";")[0])}</td></tr>"""
            if first_grp:
                body += f'\n  <tr><td>First US Friends group</td><td class="pct">{first_grp.get("year","1922")} &mdash; {esc(first_grp.get("location","Glen Ellyn, Illinois"))}</td></tr>'
            if first_uni:
                body += f'\n  <tr><td>First university Friends group</td><td class="pct">{first_uni.get("year","1925")} &mdash; {esc(first_uni.get("location","Harvard University"))}</td></tr>'
            if fg_counts:
                body += '\n  <tr><td>Historical growth</td><td>'
                for hc in fg_counts:
                    body += f'{hc.get("year","")}: {hc.get("groups",0):,} groups / {hc.get("members",0):,} members; '
                body = body.rstrip('; ') + '</td></tr>'
            body += '\n</table>'

        # ALA United for Libraries
        if ufl:
            body += f"""
<h3>United for Libraries (ALA division)</h3>
<p>{esc(ufl.get("merger_history", ""))} {esc(ufl.get("serves", ""))}.</p>"""
            if ufl.get('key_programs'):
                body += '<ul class="wiki-list">'
                for p in ufl['key_programs']:
                    body += f'\n  <li>{esc(p)}</li>'
                body += '\n</ul>'

        # Gates Foundation
        if gates:
            notable = gates.get('notable_individual_grants', [])
            body += f"""
<h3>Bill &amp; Melinda Gates Foundation: wiring libraries (1997-2018)</h3>
<p>{esc(gates.get("description", "") or "The Gates Foundation's U.S. Libraries initiative, launched in 1997, aimed to ensure that anyone who could reach a public library could reach the internet. It installed computers, software, and training at library systems across all 50 states, then wound down the Global Libraries program around 2018 as internet access at libraries became near-universal.")}</p>
<table class="wikitable">
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Program</td><td class="pct">{esc(gates.get("program", ""))}</td></tr>
  <tr><td>US initiative launched</td><td class="pct">{gates.get("us_libraries_initiative_start_year", 1997)}</td></tr>
  <tr><td>US reach</td><td class="pct">{esc(gates.get("scope_us", ""))}</td></tr>
  <tr><td>Estimated total committed</td><td class="pct">{esc(gates.get("total_committed_estimate_usd", "Exceeds $1 billion"))}</td></tr>
  <tr><td>Program wound down</td><td class="pct">{esc(gates.get("program_end", "c. 2018"))}</td></tr>
</table>"""
            if notable:
                body += """
<h4>Notable individual Gates grants</h4>
<table class="wikitable">
  <tr><th>Grantee</th><th>Amount</th><th>Purpose</th></tr>"""
                for g in notable:
                    amt = g.get('amount_usd', 0)
                    body += f'\n  <tr><td>{esc(g.get("grantee",""))}</td><td class="pct">${amt/1e6:.1f}M</td><td>{esc(g.get("purpose", g.get("year","")))}</td></tr>'
                body += '\n</table>'

        # Major foundations
        if founds:
            body += """
<h3>Major library-supporting foundations</h3>
<table class="wikitable">
  <tr><th>Foundation</th><th>Founded</th><th>Endowment</th><th>Library focus</th></tr>"""
            for f in founds:
                endow_val = f.get('endowment_usd', 0)
                endow_str = f'${endow_val/1e9:.1f}B' if endow_val and endow_val >= 1e9 else (f'${endow_val/1e6:.0f}M' if endow_val else '&mdash;')
                founded = f.get('founded', '') or f.get('founded_year', '') or '&mdash;'
                focus = f.get('mission', '') or f.get('library_history', '') or f.get('description', '') or f.get('areas', '')
                # Trim focus
                if isinstance(focus, list):
                    focus = '; '.join(str(x) for x in focus)
                focus = esc(str(focus))[:240]
                body += f'\n  <tr><td>{esc(f.get("name",""))}</td><td class="pct">{esc(str(founded))}</td><td class="pct">{endow_str}</td><td>{focus}</td></tr>'
            body += '\n</table>'

        # Endowments table
        if endow:
            body += """
<h3>Library endowments: billions in the bank</h3>
<table class="wikitable">
  <tr><th>Institution</th><th>Endowment</th><th>Year</th><th>Source</th></tr>"""
            for e in sorted(endow, key=lambda x: x.get('endowment_size_usd', 0), reverse=True):
                body += f'\n  <tr><td>{esc(e.get("library",""))}</td><td class="pct">${e.get("endowment_size_usd",0)/1e9:.2f}B</td><td class="pct">{e.get("year","")}</td><td>{esc(e.get("source",""))}</td></tr>'
            body += '\n</table>'

        # Adopt-a-Book programs
        if adopt and adopt.get('examples'):
            body += f"""
<h3>Adopt-a-Book &amp; community programs</h3>
<p>{esc(adopt.get("description", "") or "Adopt-a-Book programs let donors sponsor the purchase or conservation of specific library books, often with bookplates recognizing the donor. Run by individual libraries, their Friends groups, and affiliated foundations.")}</p>
<table class="wikitable">
  <tr><th>Organization</th><th>Notes</th></tr>"""
            for ex in adopt.get('examples', []):
                body += f'\n  <tr><td>{esc(ex.get("organization",""))}</td><td>{esc(ex.get("note",""))}</td></tr>'
            body += '\n</table>'

        # Crowdfunding / community fundraising
        if crowdfund:
            body += """
<h3>Crowdfunding &amp; community fundraising</h3>
<ul class="wiki-list">"""
            for k, v in crowdfund.items():
                if isinstance(v, str) and v:
                    body += f'\n  <li><strong>{esc(k.replace("_", " ").title())}:</strong> {esc(v)}</li>'
            body += '\n</ul>'

        # Key facts
        if key_facts:
            body += """
<h3>Key facts</h3>
<ul class="wiki-list">"""
            for kf in key_facts:
                body += f'\n  <li>{esc(kf)}</li>'
            body += '\n</ul>'

        body += f'<p class="rsrc">Source: Wikipedia articles for Andrew Carnegie library grants, Friends of Libraries, Bill &amp; Melinda Gates Foundation, Carnegie Corporation of New York, Andrew W. Mellon Foundation, and New York Public Library (citing annual reports, the Carnegie Corporation history page, and FOLUSA/ALA United for Libraries materials). Carnegie built {carn_us:,} of {carn_world:,} worldwide libraries across {carn_states_count} states; by-state dollar total parsed from the Wikipedia detail table to ${carn_us_dollars:,.0f}. Friends group counts are historical snapshots (no single national registry exists). The Gates Foundation\'s cumulative library commitment is widely reported as exceeding $1 billion, though the foundation does not publish a single official total. Endowment figures are as of the year cited in each source.</p>'

    # ---- Circulation & Library Cards ----
    circ = stats.get('circulation', {})
    if circ and circ.get('national'):
        nat = circ.get('national', {})
        by_st = circ.get('by_state', [])
        top_circ = circ.get('top_by_circulation', [])
        top_percap = circ.get('top_by_per_capita_circulation', [])
        top_regs = circ.get('top_by_registered_borrowers', [])
        top_visits = circ.get('top_by_visits', [])
        top_child = circ.get('top_by_childrens_pct', [])
        top_ecirc = circ.get('top_by_electronic_pct', [])
        n_circ = nat.get('total_circulation', 0)
        n_ecirc = nat.get('total_ebook_circulation', 0)
        n_regs = nat.get('total_registered_borrowers', 0)
        n_visits = nat.get('total_visits', 0)
        n_child = nat.get('total_childrens_circulation', 0)
        n_progs = nat.get('total_programs', 0)
        n_attend = nat.get('total_program_attendance', 0)
        n_inet = nat.get('total_public_internet_users', 0)
        n_vols = nat.get('total_book_volumes', 0)
        n_pop = nat.get('total_population_served', 0)
        pct_e = nat.get('pct_electronic', 0)
        pct_c = nat.get('pct_childrens', 0)
        circ_pc = nat.get('circulation_per_capita', 0)
        visits_pc = nat.get('visits_per_capita', 0)
        borrows_pc = nat.get('borrowers_per_capita', 0)
        n_states = len([s for s in by_st if s.get('total_circulation', 0) > 0])

        # Max for bars
        max_circ = max((s.get('total_circulation', 0) for s in top_circ), default=1) or 1
        max_percap = max((s.get('circulation_per_capita', 0) for s in top_percap), default=1) or 1
        max_regs = max((s.get('registered_borrowers', 0) for s in top_regs), default=1) or 1

        body += f"""

<h2 id="circulation">Circulation &amp; Library Cards: What Americans Borrow</h2>
<p class="wiki-sub">Every year Americans check out {n_circ/1e9:.2f} billion items from public libraries &mdash; {circ_pc:.1f} items for every person in the country. {n_regs/1e6:.0f} million Americans hold library cards. Of all circulation, {pct_c:.0f}% is children's materials and {pct_e:.0f}% is electronic (e-books and e-audiobooks), a figure that was effectively zero just two decades ago. The library card &mdash; the most powerful free tool in America &mdash; is held by roughly {borrows_pc:.0f}% of the population served.</p>
<div class="stats-grid">
  <div class="stat-card"><div class="num">{n_circ/1e9:.2f}B</div><div class="label">Items circulated annually</div></div>
  <div class="stat-card"><div class="num">{n_regs/1e6:.0f}M</div><div class="label">Registered borrowers (card holders)</div></div>
  <div class="stat-card"><div class="num">{n_visits/1e6:.0f}M</div><div class="label">Annual library visits</div></div>
  <div class="stat-card"><div class="num">{n_ecirc/1e6:.0f}M</div><div class="label">Electronic (e-book) circulation</div></div>
  <div class="stat-card"><div class="num">{n_child/1e6:.0f}M</div><div class="label">Children's circulation</div></div>
  <div class="stat-card"><div class="num">{n_progs/1e6:.1f}M</div><div class="label">Programs hosted</div></div>
  <div class="stat-card"><div class="num">{n_attend/1e6:.0f}M</div><div class="label">Program attendance</div></div>
  <div class="stat-card"><div class="num">{n_inet/1e6:.0f}M</div><div class="label">Public internet users</div></div>
  <div class="stat-card"><div class="num">{n_vols/1e6:.0f}M</div><div class="label">Book volumes in collections</div></div>
  <div class="stat-card"><div class="num">{circ_pc:.1f}</div><div class="label">Circulation per capita</div></div>
</div>"""

        # Circulation mix bars (children's vs electronic share)
        body += f"""
<h3>The circulation mix: what gets checked out</h3>
<div class="services-bars">
  <div class="svc-row">
    <span class="svc-label">Physical materials</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{(100-pct_e):.1f}%"></span></span>
    <span class="svc-count">{100-pct_e:.0f}%</span>
  </div>
  <div class="svc-row">
    <span class="svc-label">Electronic (e-books/audio)</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-green" style="width:{pct_e:.1f}%"></span></span>
    <span class="svc-count">{pct_e:.0f}%</span>
  </div>
  <div class="svc-row">
    <span class="svc-label">Children's materials</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-yellow" style="width:{pct_c:.1f}%"></span></span>
    <span class="svc-count">{pct_c:.0f}%</span>
  </div>
</div>"""

        # Top states by total circulation
        if top_circ:
            body += """
<h3>Top 10 states by total circulation</h3>
<div class="services-bars">"""
            for s in top_circ[:10]:
                cnt = s.get('total_circulation', 0)
                body += f"""
  <div class="svc-row">
    <span class="svc-label">{esc(s["state"])}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-blue" style="width:{cnt/max_circ*100:.1f}%"></span></span>
    <span class="svc-count">{cnt:,}</span>
  </div>"""
            body += '\n</div>'

        # Top states by circulation per capita
        if top_percap:
            body += """
<h3>Top 10 states by circulation per capita</h3>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Population served</th><th>Total circulation</th><th>Per capita</th></tr>"""
            for i, s in enumerate(top_percap[:10], 1):
                body += f"""
  <tr>
    <td>{i}</td>
    <td>{esc(s["state"])}</td>
    <td>{s.get("population",0):,}</td>
    <td>{s.get("total_circulation",0):,}</td>
    <td class="pct">{s.get("circulation_per_capita",0):.2f}</td>
  </tr>"""
            body += '\n</table>'

        # Top states by registered borrowers
        if top_regs:
            body += """
<h3>Top 10 states by registered library card holders</h3>
<div class="services-bars">"""
            for s in top_regs[:10]:
                cnt = s.get('registered_borrowers', 0)
                body += f"""
  <div class="svc-row">
    <span class="svc-label">{esc(s["state"])}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-people" style="width:{cnt/max_regs*100:.1f}%"></span></span>
    <span class="svc-count">{cnt:,}</span>
  </div>"""
            body += '\n</div>'

        # Top states by children's circulation share
        if top_child:
            body += """
<h3>Where children's materials dominate circulation</h3>
<p>States where children's materials make up the largest share of total circulation (among states with &gt;100,000 total circulation):</p>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Total circulation</th><th>Children's circulation</th><th>Children's share</th></tr>"""
            for i, s in enumerate(top_child[:10], 1):
                body += f"""
  <tr>
    <td>{i}</td>
    <td>{esc(s["state"])}</td>
    <td>{s.get("total_circulation",0):,}</td>
    <td>{s.get("children_circulation",0):,}</td>
    <td class="pct">{s.get("pct_childrens_circulation",0):.1f}%</td>
  </tr>"""
            body += '\n</table>'

        # Top states by electronic circulation share
        if top_ecirc:
            body += """
<h3>Where digital borrowing leads</h3>
<p>States with the highest share of electronic (e-book/e-audio) circulation:</p>
<table class="wikitable">
  <tr><th>Rank</th><th>State</th><th>Total circulation</th><th>Electronic circulation</th><th>Electronic share</th></tr>"""
            for i, s in enumerate(top_ecirc[:10], 1):
                body += f"""
  <tr>
    <td>{i}</td>
    <td>{esc(s["state"])}</td>
    <td>{s.get("total_circulation",0):,}</td>
    <td>{s.get("electronic_circulation",0):,}</td>
    <td class="pct">{s.get("pct_electronic_circulation",0):.1f}%</td>
  </tr>"""
            body += '\n</table>'

        # Key facts
        kf = circ.get('key_facts', [])
        if kf:
            body += """
<h3>Key facts</h3>
<ul class="wiki-list">"""
            for f in kf:
                body += f'\n  <li>{esc(f)}</li>'
            body += '\n</ul>'

        body += f'<p class="rsrc">Source: IMLS Public Libraries Survey FY2022 (latest finalized PLS data), compiled via ALA State of America\'s Libraries 2024 report. Covers {n_states} states and territories with circulation data. Total circulation ({n_circ/1e9:.2f}B) includes physical and electronic materials; electronic circulation ({n_ecirc/1e6:.0f}M, {pct_e:.0f}%) is reported separately and may overlap with total_circulation depending on each state\'s reporting methodology. Registered borrowers ({n_regs/1e6:.0f}M) are active library card holders as reported by each state. IMLS uses negative sentinels (-1, -3, -40) for suppressed/unreported values, normalized to 0. Per-capita figures divide by population served (min 1,000). ALA designates September as Library Card Sign-Up Month.</p>'

    body += f"""
<h2 id="leaderboard">State Leaderboard</h2>
<table class="wikitable leaderboard-table">
  <tr><th>Rank</th><th>State</th><th>Public</th><th>Private</th><th>Gov</th><th>Total</th></tr>"""

    for i, st in enumerate(stats['state_ranking'], 1):
        total = st['pub'] + st['priv'] + st['gov']
        body += f"""
  <tr>
    <td>{i}</td>
    <td><a href="states/{st['code']}.html">{esc(st['name'])}</a></td>
    <td>{st['pub']:,}</td>
    <td>{st['priv']:,}</td>
    <td>{st['gov']:,}</td>
    <td class="pct">{total:,}</td>
  </tr>"""

    body += f"""
</table>

<h2 id="states">Browse by State</h2>
<div class="state-grid">"""

    for st in sorted(STATE_NAMES.keys()):
        st_data = stats['states'].get(st)
        if st_data:
            body += f'<a href="states/{st}.html">{st}</a>'

    body += f"""
</div>

<h2>Map Legend</h2>
<div class="rules-box">
  <ul>
    <li><span style="color:#2b7fff;font-weight:700">● Blue</span> — Public libraries ({pub['total']:,})</li>
    <li><span style="color:#e23b3b;font-weight:700">● Red</span> — Private/academic libraries ({priv['total']:,})</li>
    <li><span style="color:#8e44ff;font-weight:700">● Purple</span> — Government websites linked to locations ({gov['total']:,})</li>
  </ul>
</div>

<div class="catlinks"><span class="cat-title">Categories: </span><a href="search.html?type=public">Public</a> | <a href="search.html?type=private">Private</a> | <a href="search.html?type=gov">Government</a> | <a href="search.html?type=hours">Hours</a> | <a href="search.html?type=services">Services</a></div>
<div class="relatedbox">
  <h3>Keep exploring</h3>
  <ul>
    <li><a href="search.html">Search all records →</a></li>
    <li><a href="map.html">Full-page interactive map →</a></li>
    <li><a href="gov.html">Government sites overview →</a></li>
    <li><a href="about.html">Methodology & data sources →</a></li>
  </ul>
</div>
<p class="edit-note">Generated from CSV data by wiki/build_wiki.py on {now_str()}.</p>"""

    with open(os.path.join(WIKI, 'index.html'), 'w') as f:
        f.write(shell("US Library Census", body, panel("index"), active_tab="index"))

def build_gov(data, stats):
    print("[build] Building gov.html...")
    body = f"""
<p class="contentSub">Government websites</p>
<div class="wiki-sub">{stats['gov']['total']:,} federal, state, county, city, tribal, and special-district websites — {stats['gov']['live']:,} verified live ({stats['gov']['live_pct']}).</div>

<div class="stats-grid">
  <div class="stat-card"><div class="num">{stats['gov']['total']:,}</div><div class="label">Total gov sites</div></div>
  <div class="stat-card"><div class="num">{stats['gov']['live']:,}</div><div class="label">Verified live</div></div>
  <div class="stat-card"><div class="num">{stats['gov_services']:,}</div><div class="label">Service summaries</div></div>
</div>

<h2>Verification by Tier</h2>
<table class="data-table">
  <tr><th>Tier</th><th>Total</th><th>Live</th><th>Rate</th></tr>"""

    tier_labels = {
        'federal':'Federal','state':'State','county':'County',
        'city':'City','tribal':'Tribal','special':'Special/Interstate'
    }
    for tier in ['federal','state','county','city','tribal','special']:
        ts = stats['gov']['tiers'].get(tier, {'total':0,'live':0,'pct':'0%'})
        body += f'<tr><td><a href="search.html?type=gov&tier={tier}">{tier_labels[tier]}</a></td><td>{ts["total"]:,}</td><td class="live">{ts["live"]:,}</td><td class="pct">{ts["pct"]}</td></tr>'

    body += '</table>'

    # ---- What powers America's gov websites (server tech) ----
    gt = stats['gov_tech']
    body += f"""
<h2 id="tech">What Powers America's Government Websites</h2>
<p class="wiki-sub">Server software detected across {gt['total_checked']:,} verified government websites — a tech-stack census of .gov.</p>
<div class="tech-bars">"""

    max_tech = gt['servers'][0]['count'] if gt['servers'] else 1
    for srv in gt['servers']:
        pct_w = (srv['count'] / max_tech) * 100
        body += f"""
  <div class="svc-row">
    <span class="svc-name">{esc(srv["name"])}</span>
    <span class="svc-bar"><span class="svc-fill svc-fill-tech" style="width:{pct_w:.1f}%"></span></span>
    <span class="svc-count">{srv["count"]:,}</span>
  </div>"""

    body += f"""
</div>

<h2 id="health">Site Health — HTTP Status Breakdown</h2>
<table class="data-table health-table">
  <tr><th>HTTP Status</th><th>Meaning</th><th>Count</th><th>Share</th></tr>"""

    status_meanings = {
        '200': 'OK', '202': 'Accepted', '206': 'Partial Content',
        '301': 'Moved Permanently', '307': 'Temporary Redirect',
        '400': 'Bad Request', '401': 'Unauthorized', '402': 'Payment Required',
        '403': 'Forbidden', '404': 'Not Found', '409': 'Conflict',
        '410': 'Gone', '421': 'Misdirected Request', '429': 'Too Many Requests',
        '444': 'No Response (nginx)', '500': 'Internal Server Error',
        '502': 'Bad Gateway', '503': 'Service Unavailable',
        '504': 'Gateway Timeout', '508': 'Loop Detected',
        '520': 'Cloudflare Error', '521': 'Web Server Down',
        '523': 'Origin Unreachable', '525': 'SSL Handshake Failed',
        '526': 'Invalid SSL Cert', '530': 'Cloudflare',
        '999': 'Blocked/Error', '0': 'Connection Failed',
    }
    total_checked = gt['total_checked'] or 1
    for st in gt['statuses']:
        meaning = status_meanings.get(st['code'], 'Unknown')
        code_int = 0
        try: code_int = int(st['code'])
        except (ValueError, TypeError): pass
        if code_int == 0:
            cls = 'dead'
        elif code_int < 300:
            cls = 'live'
        elif code_int < 400:
            cls = 'rating'
        else:
            cls = 'dead'
        body += f'<tr><td><span class="{cls}">{esc(st["code"])}</span></td><td>{meaning}</td><td>{st["count"]:,}</td><td class="pct">{100*st["count"]/total_checked:.1f}%</td></tr>'

    body += '</table>'

    # ---- Oldest & newest agencies ----
    tl = stats['agency_timeline']
    body += """
<h2 id="timeline">Agency Timeline — Oldest & Newest</h2>
<table class="data-table">
  <tr><th>Year</th><th>Agency</th><th>Level</th><th>State</th></tr>"""

    for a in tl['oldest']:
        body += f'<tr><td class="pct">{a["year"]}</td><td><strong>{esc(a["name"])}</strong></td><td>{esc(a["level"])}</td><td>{esc(a["state"]) or "—"}</td></tr>'

    if tl['oldest'] and tl['newest']:
        body += '<tr><td colspan="4" style="text-align:center;font-style:italic;color:var(--wiki-text-muted)">— Newest agencies —</td></tr>'
        for a in tl['newest']:
            body += f'<tr><td class="pct">{a["year"]}</td><td><strong>{esc(a["name"])}</strong></td><td>{esc(a["level"])}</td><td>{esc(a["state"]) or "—"}</td></tr>'

    body += '</table>\n'

    # Gov services table — top agencies with summaries
    gs = data['gov_services']
    summarized = [r for r in gs if (r.get('services_summary') or '').strip()]
    body += f"""
<h2 id="services">Government Services — What Each Agency Does</h2>
<p>{len(summarized)} agencies with detailed service summaries out of {len(gs):,} total records.</p>
<table class="data-table">
  <tr><th>Agency</th><th>Level</th><th>State</th><th>Established</th><th>Services</th></tr>"""

    for r in summarized[:50]:
        agency = esc(r.get('agency_name',''))
        level = esc(r.get('level',''))
        state = esc(r.get('state',''))
        est = esc(r.get('established_year',''))
        summary = esc(r.get('services_summary','')[:120])
        body += f'<tr><td><strong>{agency}</strong></td><td>{level}</td><td>{state}</td><td>{est}</td><td>{summary}</td></tr>'

    body += f'</table>\n<p>Showing 50 of {len(summarized)} summarized agencies. <a href="search.html?type=govservices">Search all →</a></p>'

    body += f"""
<div class="catlinks"><span class="cat-title">Categories: </span><a href="search.html?type=gov&tier=federal">Federal</a> | <a href="search.html?type=gov&tier=state">State</a> | <a href="search.html?type=gov&tier=county">County</a> | <a href="search.html?type=gov&tier=city">City</a> | <a href="search.html?type=gov&tier=tribal">Tribal</a> | <a href="search.html?type=gov&tier=special">Special</a></div>
<p class="edit-note">Generated on {now_str()}.</p>"""

    with open(os.path.join(WIKI, 'gov.html'), 'w') as f:
        f.write(shell("Government Websites", body, panel("gov"), active_tab="gov"))

def build_about(data, stats):
    print("[build] Building about.html...")
    body = f"""
<p class="contentSub">About this wiki</p>
<div class="wiki-sub">How this dataset was built, where the data comes from, and what's still missing.</div>

<h2>Overview</h2>
<p>This is a living, automated-crawl dataset of every public and private library in the
United States, plus every federal, state, county, city, tribal, and special-district
government website. Each record carries address, geocoordinates, website URL, funding
information, contact details, review ratings, hours of operation, services offered, and
area demographics. Every link is verified live, and the dataset is continuously enriched
via a scheduled pipeline.</p>

<h2>Primary Data Sources</h2>
<table class="data-table">
  <tr><th>Source</th><th>What it provides</th><th>Records</th></tr>
  <tr><td><strong>IMLS PLS FY2024</strong></td><td>Public library outlets (outlet-level, includes address, funding, size, population served)</td><td>{stats['public']['total']:,}</td></tr>
  <tr><td><strong>NCES IPEDS AL 2023 + HD2023</strong></td><td>Academic libraries (degree-granting institutions)</td><td>{stats['private']['total']:,}</td></tr>
  <tr><td><strong>CISA dotgov-data + GSA govt-urls</strong></td><td>Federal/state/county/city/tribal/special .gov domain registry</td><td>{stats['gov']['total']:,}</td></tr>
  <tr><td><strong>Census ACS 2023 5-Year</strong></td><td>Demographics (median income, population, age, poverty rate)</td><td>{stats['public']['demographics']:,}</td></tr>
  <tr><td><strong>Google Places API v1</strong></td><td>Real review ratings (free daily quota, no billing needed)</td><td>{stats['public']['rated']:,}+{stats['private']['rated']:,}</td></tr>
  <tr><td><strong>Gemini LLM (gemini-flash-lite-latest)</strong></td><td>Estimated ratings for well-known libraries where Places API quota exhausted</td><td>~6,100</td></tr>
  <tr><td><strong>LibraryTechnology.org state directories</strong></td><td>Library website discovery (3,366 additional websites found)</td><td>7,912 systems</td></tr>
  <tr><td><strong>Library website scraping</strong></td><td>Emails, social media links, hours, services extracted from library homepages</td><td>{stats['hours']:,} hours, {stats['services']:,} services</td></tr>
</table>

<h2>Data Coverage</h2>
<table class="coverage-table">
  <tr><th>Field</th><th>Public libraries</th><th>Private libraries</th><th>Gov sites</th></tr>
  <tr><td>Total records</td><td>{stats['public']['total']:,}</td><td>{stats['private']['total']:,}</td><td>{stats['gov']['total']:,}</td></tr>
  <tr><td>Geocoded</td><td>100%</td><td>99.9%</td><td>Partial</td></tr>
  <tr><td>Websites</td><td>{stats['public']['web_pct']}</td><td>{stats['private']['web_pct']}</td><td>100%</td></tr>
  <tr><td>Ratings</td><td>{stats['public']['rated_pct']}</td><td>{stats['private']['rated_pct']}</td><td>—</td></tr>
  <tr><td>Emails</td><td>{stats['public']['email_pct']}</td><td>—</td><td>—</td></tr>
  <tr><td>Social media</td><td>{stats['public']['social_pct']}</td><td>—</td><td>—</td></tr>
  <tr><td>Demographics</td><td>{stats['public']['demo_pct']}</td><td>—</td><td>—</td></tr>
  <tr><td>Verified live</td><td>—</td><td>—</td><td>{stats['gov']['live_pct']}</td></tr>
</table>

<h2>Known Gaps (honest accounting)</h2>
<div class="rules-box">
  <ul>
    <li><strong>14.5% of public library systems</strong> (1,339) have no website — almost all are tiny rural/bookmobile libraries with no online presence.</li>
    <li><strong>54.1% of public libraries</strong> remain unrated — Google Places API daily quota limits accumulation; Gemini LLM fills in well-known libraries but correctly omits obscure branches.</li>
    <li><strong>25.6% of gov sites</strong> are not live — many are genuinely expired/dead .gov domains (DNS won't resolve).</li>
    <li><strong>Special libraries</strong> (law, medical, theological, corporate) are underrepresented — only 75 added beyond the 3,695 academic libraries.</li>
    <li><strong>Cron automation</strong> is set up but not yet active — run <code>bash automation/setup_cron.sh</code> to enable continuous enrichment.</li>
  </ul>
</div>

<h2>Scripts (21 Python scripts)</h2>
<table class="data-table">
  <tr><th>Script</th><th>Purpose</th></tr>
  <tr><td><code>fetch_imls.py</code></td><td>Download IMLS Public Libraries Survey FY2024</td></tr>
  <tr><td><code>fetch_academic.py</code></td><td>Download NCES IPEDS Academic Libraries 2023</td></tr>
  <tr><td><code>fetch_gov.py</code></td><td>Build gov-site spreadsheets from CISA/GSA registries</td></tr>
  <tr><td><code>fetch_special_libraries.py</code></td><td>Expand private libraries (law/medical/theological/corporate)</td></tr>
  <tr><td><code>find_library_websites.py</code></td><td>Heuristic website discovery for public libraries</td></tr>
  <tr><td><code>fetch_state_directories.py</code></td><td>Scrape LibraryTechnology.org state directories</td></tr>
  <tr><td><code>scrape_library_pages.py</code></td><td>Scrape library websites for emails, socials, ratings</td></tr>
  <tr><td><code>merge_enrichment.py</code></td><td>Merge scraped enrichment into public_libraries.csv</td></tr>
  <tr><td><code>fetch_reviews.py</code></td><td>Google Places API + Gemini LLM ratings</td></tr>
  <tr><td><code>fetch_library_hours.py</code></td><td>Scrape library websites for hours of operation</td></tr>
  <tr><td><code>fetch_library_services.py</code></td><td>Scrape library websites for services offered</td></tr>
  <tr><td><code>fetch_gov_services.py</code></td><td>Document what each federal/state agency does</td></tr>
  <tr><td><code>verify_links.py</code></td><td>Batched HTTP link checker for all URLs</td></tr>
  <tr><td><code>enrich_geocode.py</code></td><td>Fill lat/lng via Census Gazetteer</td></tr>
  <tr><td><code>enrich_demographics.py</code></td><td>Overlay Census ACS demographics</td></tr>
  <tr><td><code>build_map.py</code></td><td>Generate the interactive 2D map</td></tr>
  <tr><td><code>dns_bypass.py</code></td><td>Bypass macOS mDNS hangs (utility module)</td></tr>
</table>

<h2>Update Frequency</h2>
<p>The pipeline is designed to run every 30 minutes via cron (<code>automation/run_pipeline.sh</code>).
Each run is idempotent and resumable — it picks up where the last run left off, using
caches in <code>data/_cache/</code>. Google Places API quota resets daily at midnight PT,
so ratings accumulate across runs. The wiki can be rebuilt at any time by re-running
<code>python3 wiki/build_wiki.py</code>.</p>

<div class="catlinks"><span class="cat-title">Categories: </span><a href="index.html">Main page</a> | <a href="search.html">Search</a> | <a href="map.html">Map</a></div>
<p class="edit-note">Generated on {now_str()}.</p>"""

    with open(os.path.join(WIKI, 'about.html'), 'w') as f:
        f.write(shell("About / Methodology", body, panel("about"), active_tab="about"))

def build_search():
    print("[build] Building search.html...")
    body = """
<p class="contentSub">Search the census</p>
<div class="wiki-sub">Search across all 46,000+ records — libraries, government sites, hours, and services.</div>

<div class="search-controls">
  <input type="text" id="searchInput" placeholder="Search by name, city, or address…" oninput="doSearch()">
  <select id="stateFilter" onchange="doSearch()">
    <option value="">All states</option>
  </select>
  <select id="typeFilter" onchange="doSearch()">
    <option value="">All types</option>
    <option value="public">Public libraries</option>
    <option value="private">Private libraries</option>
    <option value="academic">Academic libraries</option>
    <option value="gov">Government sites</option>
  </select>
  <select id="sortFilter" onchange="doSearch()">
    <option value="name">Sort: Name</option>
    <option value="state">Sort: State</option>
    <option value="rating">Sort: Rating</option>
    <option value="city">Sort: City</option>
  </select>
  <label><input type="checkbox" id="hasWebsite" onchange="doSearch()"> Has website</label>
  <label><input type="checkbox" id="hasRating" onchange="doSearch()"> Has rating</label>
</div>

<div class="search-info" id="searchInfo">Loading data…</div>
<div class="search-results" id="searchResults"></div>
<div class="pagination" id="pagination"></div>

<div class="detail-overlay" id="detailPanel">
  <button class="close" onclick="closeDetail()">×</button>
  <div id="detailContent"></div>
</div>

<script src="app.js"></script>
"""

    # Search page — no sidebar, content spans full width (Bootstrap col-12)
    page = shell("Search & Filter", body, panel_html="", active_tab="search")
    with open(os.path.join(WIKI, 'search.html'), 'w') as f:
        f.write(page)

def build_state_pages(data, stats):
    print("[build] Building state pages...")
    os.makedirs(STATES_DIR, exist_ok=True)

    for st, st_info in stats['states'].items():
        st_name = st_info['name']
        st_pub = [r for r in data['public'] if r.get('state','') == st]
        st_priv = [r for r in data['private'] if r.get('state','') == st]
        st_gov = [r for r in data['gov'] if r.get('state','') == st]

        # Build hours lookup
        hours_map = {r.get('id',''): r for r in data['hours'] if r.get('id','')}

        st_rated = sum(1 for r in st_pub if (r.get('reviews_rating') or '').strip())
        st_web = sum(1 for r in st_pub if (r.get('website') or '').strip())
        st_gov_live = sum(1 for r in st_gov if (r.get('url_live','') or '').strip().lower() in ('true','1','yes'))

        body = f"""
<p class="contentSub">State: {esc(st_name)}</p>
<div class="wiki-sub">{st_info['pub']:,} public libraries · {st_info['priv']:,} private libraries · {st_info['gov']:,} government websites</div>

<div class="stats-grid">
  <div class="stat-card"><div class="num">{st_info['pub']:,}</div><div class="label">Public libraries</div></div>
  <div class="stat-card"><div class="num">{st_info['priv']:,}</div><div class="label">Private libraries</div></div>
  <div class="stat-card"><div class="num">{st_info['gov']:,}</div><div class="label">Gov sites</div></div>
  <div class="stat-card"><div class="num">{st_rated:,}</div><div class="label">Rated</div></div>
  <div class="stat-card"><div class="num">{st_gov_live:,}</div><div class="label">Gov live</div></div>
  <div class="stat-card"><div class="num">{st_web:,}</div><div class="label">With websites</div></div>
</div>"""

        # ---- State Library Agency info box (SLAA FY2024) ----
        st_slaa = stats.get('slaa_by_state', {}).get(st)
        if st_slaa:
            ag_name = esc(st_slaa.get('agency_name','') or '')
            ag_type = esc(st_slaa.get('agency_type','') or '')
            ag_web = (st_slaa.get('website','') or '').strip()
            ag_web_html = f'<a href="{esc(ag_web)}" target="_blank" rel="noopener">{esc(ag_web)}</a>' if ag_web else '—'
            bt = (st_slaa.get('budget_total','') or '').strip()
            bt_str = f"${int(float(bt)):,}" if bt else '—'
            lt = (st_slaa.get('budget_federal_lsta','') or '').strip()
            lt_str = f"${int(float(lt)):,}" if lt else '—'
            si = (st_slaa.get('budget_state','') or '').strip()
            si_str = f"${int(float(si)):,}" if si else '—'
            stf = (st_slaa.get('staff_total','') or '').strip()
            stf_str = f"{float(stf):.0f}" if stf else '—'
            mls = (st_slaa.get('staff_mls_librarians','') or '').strip()
            mls_str = f"{float(mls):.0f}" if mls else '—'
            pop_s = (st_slaa.get('population_served','') or '').strip()
            pop_str = f"{int(float(pop_s)):,}" if pop_s else '—'
            fy = esc(st_slaa.get('fiscal_year','') or '')
            svcs = esc(st_slaa.get('services_offered','') or '')
            arch = esc(st_slaa.get('has_state_archive','') or '')
            mus = esc(st_slaa.get('has_state_museum','') or '')
            body += f"""

<div class="slaa-box">
  <h2>State Library Agency — {esc(st_name)}</h2>
  <table class="data-table">
    <tr><th>Agency</th><td>{ag_name}</td><th>Type</th><td>{ag_type}</td></tr>
    <tr><th>Fiscal year</th><td>{fy}</td><th>Website</th><td>{ag_web_html}</td></tr>
    <tr><th>Total income</th><td>{bt_str}</td><th>Federal LSTA</th><td>{lt_str}</td></tr>
    <tr><th>State income</th><td>{si_str}</td><th>Staff (FTE)</th><td>{stf_str} ({mls_str} MLS librarians)</td></tr>
    <tr><th>Population served</th><td>{pop_str}</td><th>Archive / Museum</th><td>{arch} / {mus}</td></tr>"""
            if svcs:
                body += f'\n    <tr><th>Services offered</th><td colspan="3">{svcs}</td></tr>'
            body += '\n  </table>\n  <p class="rsrc">Data: IMLS State Library Administrative Agency Survey, FY2024.</p>\n</div>'

        # ---- Academic libraries in this state (NCES ALS 2012 / IPEDS 2023) ----
        st_acad = [r for r in data.get('academic', []) if (r.get('state', '') or '').strip() == st]
        st_acad_2023 = [r for r in data.get('academic_2023', []) if (r.get('state', '') or '').strip() == st]
        st_acad_agg = stats.get('academic_by_state_2012', {}).get(st, {})
        if st_acad or st_acad_agg or st_acad_2023:
            n_acad = st_acad_agg.get('institutions', len(st_acad_2023) or len(st_acad))
            exp_a = st_acad_agg.get('expenditures', 0)
            coll_a = st_acad_agg.get('collections', 0)
            staff_a = st_acad_agg.get('staff_fte', 0)
            pres_a = st_acad_agg.get('presentations', 0)
            sal_a = st_acad_agg.get('salaries', 0)
            sfte_a = st_acad_agg.get('student_fte', 0)
            als_year = st_acad_agg.get('year', 2012)
            coll_display = f"{coll_a/1e6:.1f}M" if coll_a < 1e9 else f"{coll_a/1e9:.2f}B"
            body += f"""

<div class="slaa-box academic-box">
  <h2>Academic Libraries — {esc(st_name)} (NCES {als_year})</h2>
  <div class="stats-grid">
    <div class="stat-card"><div class="num">{n_acad}</div><div class="label">Institutions</div></div>
    <div class="stat-card"><div class="num">{staff_a:,}</div><div class="label">Staff FTE</div></div>
    <div class="stat-card"><div class="num">${exp_a/1e6:,.0f}M</div><div class="label">Expenditures</div></div>
    <div class="stat-card"><div class="num">{coll_display}</div><div class="label">Collections</div></div>
    <div class="stat-card"><div class="num">${sal_a/1e6:,.0f}M</div><div class="label">Salaries</div></div>
    <div class="stat-card"><div class="num">{sfte_a:,}</div><div class="label">Student FTE</div></div>"""
            if pres_a:
                body += f'\n    <div class="stat-card"><div class="num">{pres_a:,}</div><div class="label">Presentations</div></div>'
            body += '\n  </div>'
            # Prefer 2023 institutions for the table (richer data), fall back to 2012
            st_acad_display = st_acad_2023 if st_acad_2023 else st_acad
            if st_acad_display:
                # Show top institutions by collection
                st_acad_sorted = sorted(st_acad_display, key=lambda r: -float(r.get('colbksa') or 0))
                body += """
  <table class="data-table">
    <tr><th>Institution</th><th>City</th><th>Collection</th><th>Expenditures</th><th>Staff FTE</th><th>Website</th></tr>"""
                for r in st_acad_sorted[:30]:
                    name = esc(r.get('name', '') or '')
                    city = esc(r.get('city', '') or '—')
                    coll_v = (r.get('colbksa') or '').strip()
                    coll_str = f"{int(float(coll_v)):,}" if coll_v else '—'
                    exp_v = (r.get('extot') or '').strip()
                    exp_str = f"${int(float(exp_v)):,}" if exp_v else '—'
                    stf_v = (r.get('sttot') or '').strip()
                    stf_str = f"{float(stf_v):.0f}" if stf_v else '—'
                    web = (r.get('website') or '').strip()
                    web_html = f'<a href="{esc(web)}" target="_blank" rel="noopener">site</a>' if web else '—'
                    body += f'\n    <tr><td>{name}</td><td>{city}</td><td class="pct">{coll_str}</td><td>{exp_str}</td><td>{stf_str}</td><td>{web_html}</td></tr>'
                body += '\n  </table>'
            body += f'\n  <p class="rsrc">Data: NCES {"IPEDS Academic Libraries 2023" if als_year == 2023 else "Academic Library Survey (ALS) 2012"}. Historical trends (2000–2023) available on the <a href="../index.html#als-trends">main page</a>.</p>\n</div>'

        # ---- Federal Depository Libraries in this state ----
        st_fdlp = [r for r in data.get('fdlp', []) if (r.get('state', '') or '').strip().upper() == st]
        if st_fdlp:
            st_regional = sum(1 for r in st_fdlp if (r.get('depository_type', '') or '').strip() == 'Regional')
            body += f"""

<div class="slaa-box">
  <h2>Federal Depository Libraries — {esc(st_name)} (GPO FDLP)</h2>
  <p class="wiki-sub">{len(st_fdlp)} federal depository librar{'y' if len(st_fdlp)==1 else 'ies'} in {esc(st_name)} ({st_regional} Regional, {len(st_fdlp)-st_regional} Selective) that receive U.S. government documents through the FDLP.</p>
  <table class="data-table">
    <tr><th>Library</th><th>Depository Type</th><th>Parent Institution</th><th>Library Type</th><th>Titles Selected</th><th>Preservation Steward</th></tr>"""
            for r in sorted(st_fdlp, key=lambda r: (r.get('depository_type','') != 'Regional', r.get('library_name',''))):
                name = esc(r.get('library_name', '') or '')
                dtype = esc(r.get('depository_type', '') or '—')
                parent = esc(r.get('parent_institution', '') or '—')
                ltype = esc(r.get('library_type', '') or '—')
                tc = (r.get('pdt_titles_count', '') or '').strip()
                tc_str = f"{int(tc):,}" if tc else '—'
                ps = esc(r.get('preservation_steward', '') or '—')
                body += f'\n    <tr><td>{name}</td><td>{dtype}</td><td>{parent}</td><td>{ltype}</td><td>{tc_str}</td><td>{ps}</td></tr>'
            body += '\n  </table>'
            body += '\n  <p class="rsrc">Data: U.S. Government Publishing Office (GPO) FDLP Print Distribution Dashboard. National overview on the <a href="../index.html#fdlp">main page</a>.</p>\n</div>'

        body += f"""

<h2>Public Libraries</h2>
<table class="data-table">
  <tr><th>Name</th><th>City</th><th>Website</th><th>Rating</th><th>Hours</th></tr>"""

        for r in st_pub[:200]:
            name = esc(r.get('name',''))
            city = esc(r.get('city',''))
            web = r.get('website','').strip()
            web_html = f'<a href="{esc(web)}" target="_blank">{esc(web[:40])}</a>' if web else ''
            rating = r.get('reviews_rating','').strip()
            rating_html = f'<span class="rating">★ {esc(rating)}</span>' if rating else ''
            lid = r.get('id','')
            hrs = hours_map.get(lid, {}).get('hours_raw', '').strip()
            hrs_html = esc(hrs[:50]) if hrs else ''
            body += f'<tr><td>{name}</td><td>{city}</td><td>{web_html}</td><td>{rating_html}</td><td>{hrs_html}</td></tr>'

        if len(st_pub) > 200:
            body += f'<tr><td colspan="5" style="text-align:center"><a href="search.html?state={st}&type=public">View all {len(st_pub)} →</a></td></tr>'

        body += '</table>'

        if st_priv:
            body += f"""
<h2>Private/Academic Libraries ({len(st_priv)})</h2>
<table class="data-table">
  <tr><th>Name</th><th>City</th><th>Website</th><th>Rating</th></tr>"""
            for r in st_priv[:50]:
                name = esc(r.get('name',''))
                city = esc(r.get('city',''))
                web = r.get('website','').strip()
                web_html = f'<a href="{esc(web)}" target="_blank">{esc(web[:40])}</a>' if web else ''
                rating = r.get('reviews_rating','').strip()
                rating_html = f'<span class="rating">★ {esc(rating)}</span>' if rating else ''
                body += f'<tr><td>{name}</td><td>{city}</td><td>{web_html}</td><td>{rating_html}</td></tr>'
            if len(st_priv) > 50:
                body += f'<tr><td colspan="4" style="text-align:center"><a href="search.html?state={st}&type=private">View all {len(st_priv)} →</a></td></tr>'
            body += '</table>'

        if st_gov:
            body += f"""
<h2>Government Websites ({len(st_gov)})</h2>
<table class="data-table">
  <tr><th>Name</th><th>Tier</th><th>Website</th><th>Status</th></tr>"""
            for r in st_gov[:100]:
                name = esc(r.get('name',''))
                tier = esc(r.get('_tier',''))
                web = r.get('website','').strip()
                web_html = f'<a href="{esc(web)}" target="_blank">{esc(web[:40])}</a>' if web else ''
                live = (r.get('url_live','') or '').strip().lower() in ('true','1','yes')
                status = '<span class="live">● Live</span>' if live else '<span class="dead">○ Down</span>'
                body += f'<tr><td>{name}</td><td>{tier}</td><td>{web_html}</td><td>{status}</td></tr>'
            if len(st_gov) > 100:
                body += f'<tr><td colspan="4" style="text-align:center"><a href="search.html?state={st}&type=gov">View all {len(st_gov)} →</a></td></tr>'
            body += '</table>'

        # ---- Town-level broadband availability for this state ----
        st_pgig, st_pfib, st_p100 = [], [], []
        st_low_gig = []
        for r in st_pub:
            g = (r.get('fcc_place_gigabit') or '').strip()
            if g:
                try:
                    gv = float(g)
                    st_pgig.append(gv)
                    fv = (r.get('fcc_place_fiber') or '0').strip()
                    ov = (r.get('fcc_place_100_20') or '0').strip()
                    st_pfib.append(float(fv) if fv else 0)
                    st_p100.append(float(ov) if ov else 0)
                    if gv < 25:
                        locs = (r.get('fcc_place_locations') or '').strip()
                        st_low_gig.append({
                            'name': r.get('name',''), 'city': r.get('city',''),
                            'gigabit': gv, 'fiber': float(fv) if fv else 0,
                            'locations': int(float(locs)) if locs else 0,
                        })
                except (ValueError, TypeError):
                    pass
        if st_pgig:
            avg_g = sum(st_pgig) / len(st_pgig)
            avg_f = sum(st_pfib) / len(st_pfib) if st_pfib else 0
            avg_o = sum(st_p100) / len(st_p100) if st_p100 else 0
            under25 = sum(1 for v in st_pgig if v < 25)
            body += f"""

<div class="slaa-box">
  <h2>Town-Level Broadband — {esc(st_name)} (FCC Census Place)</h2>
  <div class="stats-grid">
    <div class="stat-card"><div class="num">{avg_g:.1f}%</div><div class="label">Avg town gigabit</div></div>
    <div class="stat-card"><div class="num">{avg_o:.1f}%</div><div class="label">Avg town 100/20 Mbps</div></div>
    <div class="stat-card"><div class="num">{avg_f:.1f}%</div><div class="label">Avg town fiber</div></div>
    <div class="stat-card"><div class="num">{len(st_pgig):,}</div><div class="label">Library towns</div></div>
    <div class="stat-card"><div class="num">{under25:,}</div><div class="label">Towns &lt;25% gigabit</div></div>
  </div>"""
            st_low_gig.sort(key=lambda x: x['gigabit'])
            if st_low_gig:
                body += f"""
  <h3>Underserved Library Towns in {esc(st_name)}</h3>
  <p class="wiki-sub">Library communities in {esc(st_name)} where fewer than 25% of locations have gigabit broadband available.</p>
  <table class="data-table">
    <tr><th>Library</th><th>City</th><th>Gigabit Avail</th><th>Fiber Avail</th><th>Serviceable Locations</th></tr>"""
                for lib in st_low_gig[:20]:
                    locs_str = f"{lib['locations']:,}" if lib['locations'] else '—'
                    body += f'\n    <tr><td>{esc(lib["name"])}</td><td>{esc(lib["city"]) or "—"}</td><td class="pct">{lib["gigabit"]:.1f}%</td><td>{lib["fiber"]:.1f}%</td><td>{locs_str}</td></tr>'
                body += '\n  </table>'
            body += f'\n  <p class="rsrc">Data: FCC National Broadband Map, Census Place (town) granularity, Dec 2025 BDC deployment filing.</p>\n</div>'

        # ---- California-specific enriched stats (CA State Library FY2023-24) ----
        if st == 'CA':
            ca = data.get('ca_summary', {})
            if ca and ca.get('libraries'):
                body += f"""

<div class="slaa-box">
  <h2>California Public Libraries — Detailed State Statistics (FY2023-24)</h2>
  <p class="wiki-sub">The California State Library publishes richer per-library statistics than the national IMLS PLS survey, with unique breakouts for e-resources by format, programs by age group and delivery format, and capital revenue by source. Data covers {ca['libraries']} public library systems serving {ca['population_served']:,} Californians.</p>
  <div class="stats-grid">
    <div class="stat-card"><div class="num">${ca['income_total']/1e9:,.2f}B</div><div class="label">Total income</div></div>
    <div class="stat-card"><div class="num">${ca['income_local']/1e9:,.2f}B</div><div class="label">Local government funding</div></div>
    <div class="stat-card"><div class="num">${ca['expenditures_salaries']/1e6:,.0f}M</div><div class="label">Salaries</div></div>
    <div class="stat-card"><div class="num">${ca['expenditures_benefits']/1e6:,.0f}M</div><div class="label">Benefits</div></div>
    <div class="stat-card"><div class="num">{ca['total_staff']:,.0f}</div><div class="label">Staff FTE</div></div>
    <div class="stat-card"><div class="num">{ca['librarians']:,.0f}</div><div class="label">Librarians (MLS)</div></div>
    <div class="stat-card"><div class="num">{ca['visits']:,}</div><div class="label">Annual visits</div></div>
    <div class="stat-card"><div class="num">{ca['book_volumes']:,}</div><div class="label">Book volumes</div></div>
  </div>"""

                # E-resources breakdown (uniquely detailed in CA data)
                body += f"""
  <h3>Digital Collections &amp; E-Resource Usage</h3>
  <p class="wiki-sub">California uniquely reports e-resource circulation by format — a level of detail not available in the national IMLS PLS survey.</p>
  <div class="stats-grid">
    <div class="stat-card"><div class="num">{ca.get('ebook_circulation',0):,}</div><div class="label">E-book circulation</div></div>
    <div class="stat-card"><div class="num">{ca.get('eaudio_circulation',0):,}</div><div class="label">E-audio circulation</div></div>
    <div class="stat-card"><div class="num">{ca.get('evideo_circulation',0):,}</div><div class="label">E-video circulation</div></div>
    <div class="stat-card"><div class="num">{ca.get('eserial_circulation',0):,}</div><div class="label">E-serial circulation</div></div>
    <div class="stat-card"><div class="num">${ca.get('expenditures_electronic_materials',0)/1e6:,.0f}M</div><div class="label">E-materials spending</div></div>
    <div class="stat-card"><div class="num">${ca.get('expenditures_print_materials',0)/1e6:,.0f}M</div><div class="label">Print materials spending</div></div>
  </div>"""

                # Programs by age + format (uniquely detailed in CA data)
                body += f"""
  <h3>Programs by Age Group &amp; Delivery Format</h3>
  <p class="wiki-sub">California breaks out library programs by both age group and delivery format (on-site, off-site, virtual) — revealing the post-COVID shift to virtual programming.</p>
  <table class="data-table">
    <tr><th>Age Group</th><th>Programs</th><th>Attendance</th></tr>
    <tr><td>Ages 0–5</td><td>{ca.get('programs_0_5',0):,}</td><td>{ca.get('attendance_0_5',0):,}</td></tr>
    <tr><td>Ages 6–11</td><td>{ca.get('programs_6_11',0):,}</td><td>{ca.get('attendance_6_11',0):,}</td></tr>
    <tr><td>Young Adult</td><td>{ca.get('programs_ya',0):,}</td><td>{ca.get('attendance_ya',0):,}</td></tr>
    <tr><td>Adult</td><td>{ca.get('programs_adult',0):,}</td><td>{ca.get('attendance_adult',0):,}</td></tr>
    <tr><th>Total</th><th>{ca.get('programs_total',0):,}</th><th>{ca.get('attendance_total',0):,}</th></tr>
  </table>
  <table class="data-table">
    <tr><th>Delivery Format</th><th>Programs</th><th>Attendance</th></tr>
    <tr><td>On-site</td><td>{ca.get('programs_onsite',0):,}</td><td>—</td></tr>
    <tr><td>Off-site</td><td>{ca.get('programs_offsite',0):,}</td><td>—</td></tr>
    <tr><td>Virtual</td><td>{ca.get('programs_virtual',0):,}</td><td>{ca.get('attendance_virtual',0):,}</td></tr>
  </table>"""

                # Capital + technology
                body += f"""
  <h3>Capital Funding &amp; Technology Access</h3>
  <div class="stats-grid">
    <div class="stat-card"><div class="num">${ca.get('capital',0)/1e6:,.0f}M</div><div class="label">Capital expenditures</div></div>
    <div class="stat-card"><div class="num">${ca.get('capital_revenue_state',0)/1e6:,.0f}M</div><div class="label">State capital revenue</div></div>
    <div class="stat-card"><div class="num">${ca.get('capital_revenue_federal',0)/1e6:,.0f}M</div><div class="label">Federal capital revenue</div></div>
    <div class="stat-card"><div class="num">{ca.get('public_internet_terminals',0):,}</div><div class="label">Public internet terminals</div></div>
    <div class="stat-card"><div class="num">{ca.get('wifi_sessions',0):,}</div><div class="label">WiFi sessions</div></div>
    <div class="stat-card"><div class="num">{ca.get('pit_users',0):,}</div><div class="label">PIT users</div></div>
  </div>
  <p class="rsrc">Data: California State Library, Public Libraries Survey FY2023-24. Richer than the national IMLS PLS — includes e-resource breakouts by format, programs by age group and delivery format, and capital revenue by source. Source files: <a href="https://www.library.ca.gov/services/to-libraries/statistics/">California State Library Statistics</a>.</p>"""

                # LIPC broadband program tiers
                if ca.get('lipc_total'):
                    body += f"""
  <h3>Broadband Program Tiers (LIPC)</h3>
  <p class="wiki-sub">California's Library Improvement &amp; Construction Program (LIPC) classifies public libraries into three tiers by Local Income Per Capita (LIPC) to prioritize broadband infrastructure funding. <strong>Tier 1</strong> libraries have the lowest local funding per resident and receive priority for state broadband grants.</p>
  <div class="stats-grid">
    <div class="stat-card"><div class="num">{ca.get('lipc_tier1_count',0)}</div><div class="label">Tier 1 (lowest income/capita)</div></div>
    <div class="stat-card"><div class="num">{ca.get('lipc_tier2_count',0)}</div><div class="label">Tier 2 (moderate)</div></div>
    <div class="stat-card"><div class="num">{ca.get('lipc_tier3_count',0)}</div><div class="label">Tier 3 (highest income/capita)</div></div>
    <div class="stat-card"><div class="num">{ca.get('lipc_total',0)}</div><div class="label">Libraries classified</div></div>
  </div>"""
                    tier1_lowest = ca.get('lipc_tier1_lowest', [])
                    if tier1_lowest:
                        body += """
  <h4>Most Underserved Tier 1 Libraries (Lowest Income Per Capita)</h4>
  <table class="data-table">
    <tr><th>Library</th><th>Population Served</th><th>Local Income/Capita</th></tr>"""
                        for lib in tier1_lowest:
                            body += f'\n    <tr><td>{esc(lib["name"])}</td><td>{lib["population"]:,}</td><td class="pct">${lib["income_per_capita"]:.2f}</td></tr>'
                        body += '\n  </table>'
                    body += '\n  <p class="rsrc">Data: California State Library LIPC Broadband Program tiers, FY2022-23. Tier 1 = local operating income per capita under ~$50; Tier 2 = $50–$100; Tier 3 = $100+.</p>'

                body += '\n</div>'

        body += f"""
<div class="catlinks"><span class="cat-title">Categories: </span><a href="search.html?state={st}&type=public">Public in {st}</a> | <a href="search.html?state={st}&type=private">Private in {st}</a> | <a href="search.html?state={st}&type=gov">Gov in {st}</a></div>
<div class="relatedbox">
  <h3>Navigate</h3>
  <ul>
    <li><a href="../index.html">← Back to main page</a></li>
    <li><a href="../search.html?state={st}">Search {st} →</a></li>
    <li><a href="../map.html">View on map →</a></li>
  </ul>
</div>
<p class="edit-note">Generated on {now_str()}.</p>"""

        with open(os.path.join(STATES_DIR, f'{st}.html'), 'w') as f:
            st_panel = panel_state(stats['states'].keys(), st)
            page = shell(f"{st_name}", body, st_panel, root="../")
            f.write(page)

    print(f"  Built {len(stats['states'])} state pages")

def build_map_geojson(data):
    """Generate compact GeoJSON for MapLibre — only coordinates + essential properties."""
    print("[build] Generating map_points.geojson...")
    features = []
    for source, type_key in [(data['public'], 'public'), (data['private'], 'private'), (data['gov'], 'gov')]:
        for r in source:
            try:
                lat = float(r.get('latitude', ''))
                lng = float(r.get('longitude', ''))
                if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                    continue
            except (ValueError, TypeError):
                continue
            props = {
                't': type_key,
                'n': r.get('name', '')[:100],
                'c': r.get('city', '')[:50],
                's': r.get('state', ''),
            }
            rating = (r.get('reviews_rating') or '').strip()
            if rating:
                props['r'] = rating
            web = (r.get('website') or '').strip()
            if web:
                props['w'] = web[:120]
            if type_key == 'gov':
                props['tier'] = r.get('_tier', '')
            features.append({
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [lng, lat]},
                'properties': props,
            })
    geojson = {'type': 'FeatureCollection', 'features': features}
    path = os.path.join(DATA_OUT, 'map_points.geojson')
    with open(path, 'w') as f:
        json.dump(geojson, f, separators=(',', ':'))
    size_mb = os.path.getsize(path) / 1024 / 1024
    print(f"  map_points.geojson: {len(features)} features ({size_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# US state boundaries + 2024 election results for choropleth overlay
# ---------------------------------------------------------------------------

# 2024 presidential election results (Trump vs Harris)
# party: 'R' (Republican/Trump won) or 'D' (Democratic/Harris won)
# margin: approximate vote margin percentage
STATE_VOTES_2024 = {
    'AL': {'party': 'R', 'margin': 30.6}, 'AK': {'party': 'R', 'margin': 15.0},
    'AZ': {'party': 'R', 'margin': 5.5},  'AR': {'party': 'R', 'margin': 27.6},
    'CA': {'party': 'D', 'margin': 20.0}, 'CO': {'party': 'D', 'margin': 11.0},
    'CT': {'party': 'D', 'margin': 13.0}, 'DE': {'party': 'D', 'margin': 8.0},
    'FL': {'party': 'R', 'margin': 13.1}, 'GA': {'party': 'R', 'margin': 2.2},
    'HI': {'party': 'D', 'margin': 25.0}, 'ID': {'party': 'R', 'margin': 37.0},
    'IL': {'party': 'D', 'margin': 10.0}, 'IN': {'party': 'R', 'margin': 19.0},
    'IA': {'party': 'R', 'margin': 13.2}, 'KS': {'party': 'R', 'margin': 20.0},
    'KY': {'party': 'R', 'margin': 25.5}, 'LA': {'party': 'R', 'margin': 18.0},
    'ME': {'party': 'D', 'margin': 7.0},  'MD': {'party': 'D', 'margin': 20.0},
    'MA': {'party': 'D', 'margin': 25.0}, 'MI': {'party': 'R', 'margin': 1.4},
    'MN': {'party': 'D', 'margin': 4.0},  'MS': {'party': 'R', 'margin': 12.0},
    'MO': {'party': 'R', 'margin': 18.4}, 'MT': {'party': 'R', 'margin': 20.0},
    'NE': {'party': 'R', 'margin': 22.0}, 'NV': {'party': 'R', 'margin': 3.1},
    'NH': {'party': 'D', 'margin': 5.0},  'NJ': {'party': 'D', 'margin': 12.0},
    'NM': {'party': 'D', 'margin': 6.0},  'NY': {'party': 'D', 'margin': 13.0},
    'NC': {'party': 'R', 'margin': 3.3},  'ND': {'party': 'R', 'margin': 30.0},
    'OH': {'party': 'R', 'margin': 11.0}, 'OK': {'party': 'R', 'margin': 32.0},
    'OR': {'party': 'D', 'margin': 13.0}, 'PA': {'party': 'R', 'margin': 2.0},
    'RI': {'party': 'D', 'margin': 20.0}, 'SC': {'party': 'R', 'margin': 18.0},
    'SD': {'party': 'R', 'margin': 25.0},  'TN': {'party': 'R', 'margin': 26.0},
    'TX': {'party': 'R', 'margin': 14.0}, 'UT': {'party': 'R', 'margin': 30.0},
    'VT': {'party': 'D', 'margin': 20.0}, 'VA': {'party': 'D', 'margin': 5.0},
    'WA': {'party': 'D', 'margin': 15.0}, 'WV': {'party': 'R', 'margin': 30.0},
    'WI': {'party': 'R', 'margin': 0.9},  'WY': {'party': 'R', 'margin': 40.0},
    'DC': {'party': 'D', 'margin': 80.0},
}

STATES_GEOJSON_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_110m_admin_1_states_provinces_lakes.geojson"
)


def build_states_geojson():
    """Fetch US state boundaries from Natural Earth, compact to code+name,
    and write a voting data JSON for the map choropleth overlay."""
    print("[build] Building state boundaries + voting data...")
    path = os.path.join(DATA_OUT, 'us_states.geojson')
    votes_path = os.path.join(DATA_OUT, 'state_votes.json')

    # Try fetching fresh; fall back to existing file if offline
    raw = None
    try:
        print(f"  Fetching from Natural Earth...")
        req = urllib.request.Request(STATES_GEOJSON_URL, headers={'User-Agent': 'wiki-build/1.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"  Warning: could not fetch ({e}), using existing file if available")
        if os.path.exists(path):
            print(f"  Using cached {path}")
            return
        print(f"  ERROR: No cached states geojson and fetch failed")
        return

    # Filter to US states, compact properties
    us_features = []
    for f in raw.get('features', []):
        props = f.get('properties', {})
        if props.get('admin', '') in ('United States of America', 'United States'):
            code = props.get('postal', '')
            if code:
                us_features.append({
                    'type': 'Feature',
                    'properties': {'code': code, 'name': props.get('name', '')},
                    'geometry': f['geometry'],
                })

    geojson = {'type': 'FeatureCollection', 'features': us_features}
    with open(path, 'w') as f:
        json.dump(geojson, f, separators=(',', ':'))
    print(f"  us_states.geojson: {len(us_features)} states ({os.path.getsize(path)/1024:.0f} KB)")

    # Write voting data
    with open(votes_path, 'w') as f:
        json.dump(STATE_VOTES_2024, f, separators=(',', ':'))
    print(f"  state_votes.json: {len(STATE_VOTES_2024)} states")


def build_map_page():
    print("[build] Building map.html (MapLibre GL JS)...")
    # Map page is standalone — NOT wrapped in the Bootstrap grid shell.
    # The map container is position:fixed to fill the viewport below the navbar.
    nav_items = [
        ("index.html",  "Main page"),
        ("search.html", "Search"),
        ("map.html",    "Map"),
        ("gov.html",    "Government"),
        ("about.html",   "About"),
    ]
    nav_html = "\n".join(
        f'      <li class="nav-item"><a class="nav-link {"active" if label=="Map" else ""}" href="{href}">{label}</a></li>'
        for href, label in nav_items
    )
    page = f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Interactive Map — US Library Census Wiki</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<link rel="stylesheet" href="wiki.css">
<script>
(function(){{var t=localStorage.getItem('wiki-theme')||'light';document.documentElement.setAttribute('data-theme',t);}})();
</script>
</head>
<body class="wiki-body map-page">
<nav class="navbar navbar-expand-lg border-bottom fixed-top wiki-nav">
  <div class="container-fluid">
    <a class="navbar-brand" href="index.html"><b>US Library Census</b> <small class="text-muted fw-normal">AGI</small></a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#wikiNav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="wikiNav">
      <ul class="navbar-nav me-auto">
{nav_html}
      </ul>
      <form class="d-flex me-2" action="search.html" method="get">
        <input class="form-control form-control-sm" name="q" type="search" placeholder="Search" aria-label="Search">
      </form>
    </div>
    <button class="btn btn-sm btn-outline-secondary theme-toggle ms-2" onclick="toggleTheme()" title="Toggle dark mode" aria-label="Toggle dark mode">🌓</button>
  </div>
</nav>
<div id="map-container">
  <div id="map"></div>
  <div class="map-search-bar">
    <input type="text" id="mapSearchInput" class="form-control form-control-sm" placeholder="Search by name or city…" onkeydown="if(event.key==='Enter')mapSearch()">
    <select id="mapStateFilter" class="form-select form-select-sm" onchange="zoomToState(this)">
      <option value="">All states</option>
    </select>
  </div>
  <div class="map-overlay-card" id="mapControls">
    <div class="d-flex align-items-center mb-1"><input type="checkbox" class="form-check-input me-1" id="chkPublic" checked onchange="toggleLayer('public')"> <span class="legend-dot" style="background:#2b7fff"></span> <label class="form-check-label small ms-1" for="chkPublic">Public</label></div>
    <div class="d-flex align-items-center mb-1"><input type="checkbox" class="form-check-input me-1" id="chkPrivate" checked onchange="toggleLayer('private')"> <span class="legend-dot" style="background:#e23b3b"></span> <label class="form-check-label small ms-1" for="chkPrivate">Private</label></div>
    <div class="d-flex align-items-center"><input type="checkbox" class="form-check-input me-1" id="chkGov" checked onchange="toggleLayer('gov')"> <span class="legend-dot" style="background:#8e44ff"></span> <label class="form-check-label small ms-1" for="chkGov">Government</label></div>
  </div>
  <div class="map-overlay-card map-voting-card" id="mapVoting">
    <div class="voting-title">🗳️ Voting Blocks (2024)</div>
    <div class="d-flex align-items-center mb-2">
      <button class="btn btn-sm btn-outline-secondary voting-toggle-btn" onclick="toggleVotingOverlay()" id="votingBtn">Show overlay <span class="voting-state" id="votingLabel">OFF</span></button>
    </div>
    <div class="voting-legend">
      <span class="legend-dot" style="background:rgba(226,59,59,0.5)"></span> Republican
      <span class="legend-dot ms-2" style="background:rgba(51,102,204,0.5)"></span> Democratic
    </div>
  </div>
  <div class="map-overlay-card map-stats-card" id="mapStats">Loading…</div>
  <div class="map-loading" id="mapLoading"><div class="spinner-border text-primary"></div><p class="mt-2 mb-0">Loading 46k points…</p></div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<script>function toggleTheme(){{var h=document.documentElement;var c=h.getAttribute('data-theme')||'light';var n=c==='light'?'dark':'light';h.setAttribute('data-theme',n);localStorage.setItem('wiki-theme',n);if(typeof applyTheme==='function'){{applyTheme(n);}}}}</script>
<script src="map.js"></script>
</body>
</html>"""
    with open(os.path.join(WIKI, 'map.html'), 'w') as f:
        f.write(page)
    print("  map.html generated (MapLibre GL JS, standalone)")

def main():
    print(f"=== US Library Census Wiki build — {now_str()} ===")
    data = load_all()
    stats = build_json(data)
    build_map_geojson(data)
    build_states_geojson()
    build_index(data, stats)
    build_gov(data, stats)
    build_about(data, stats)
    build_search()
    build_state_pages(data, stats)
    build_map_page()
    print(f"\n=== Build complete — {now_str()} ===")
    print(f"  Output: {WIKI}")
    print(f"  Pages: index.html, search.html, gov.html, about.html, map.html, states/*.html")
    print(f"  Data: data/*.json")
    print(f"\n  To serve: cd wiki && python3 -m http.server 8124")
    print(f"  Then open: http://localhost:8124")

if __name__ == "__main__":
    main()
