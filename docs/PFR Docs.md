# Welcome to pro-football-reference-web-scraper's documentation!

[![](https://img.shields.io/github/license/mjk2244/pro-football-reference-web-scraper)](https://opensource.org/licenses/Apache-2.0) ![](https://img.shields.io/github/issues/mjk2244/pro-football-reference-web-scraper) [![](https://codecov.io/gh/mjk2244/pro-football-reference-web-scraper/branch/main/graph/badge.svg?token=OTGOR2M0CY)](https://codecov.io/gh/mjk2244/pro-football-reference-web-scraper) [![](https://img.shields.io/github/actions/workflow/status/mjk2244/pro-football-reference-web-scraper/build.yml)](https://github.com/mjk2244/pro-football-reference-web-scraper/) [![](https://img.shields.io/pypi/v/pro-football-reference-web-scraper)](https://pypi.org/project/pro-football-reference-web-scraper/)
## Overview
pro-football-reference-web-scraper is a Python library that helps developers take advantage of the plethora of free data provided by [Pro Football Reference](https://www.pro-football-reference.com/). It is intended primarily to help fantasy sports players and sports bettors gain an edge in their NFL sports gaming endeavors. However, it can be used for any project that requires team- and player-specific data.

```eval_rst

.. toctree::
   :maxdepth: 10
   :caption: Contents:

   README.md
   get_player_game_log.md
   get_team_game_log.md
   player_splits.md
   team_splits.md
   CONTRIBUTING.md
   source/modules

```

# Quick Guide
Web scraper to retrieve player and team data from Pro Football Reference.  

[![](https://img.shields.io/github/license/mjk2244/pro-football-reference-web-scraper)](https://opensource.org/licenses/Apache-2.0) ![](https://img.shields.io/github/issues/mjk2244/pro-football-reference-web-scraper) [![](https://codecov.io/gh/mjk2244/pro-football-reference-web-scraper/branch/main/graph/badge.svg?token=OTGOR2M0CY)](https://codecov.io/gh/mjk2244/pro-football-reference-web-scraper) [![](https://img.shields.io/github/actions/workflow/status/mjk2244/pro-football-reference-web-scraper/build.yml)](https://github.com/mjk2244/pro-football-reference-web-scraper/) [![](https://img.shields.io/pypi/v/pro-football-reference-web-scraper)](https://pypi.org/project/pro-football-reference-web-scraper/)
## Overview
pro-football-reference-web-scraper is a Python library that helps developers take advantage of the plethora of free data provided by [Pro Football Reference](https://www.pro-football-reference.com/). It is intended primarily to help fantasy sports players and sports bettors gain an edge in their NFL sports gaming endeavors. However, it can be used for any project that requires team- and player-specific data.

## Installation
To install, run the following:
```
pip install pro-football-reference-web-scraper
```

## Usage
### Player Game Logs
The following code will retrieve and print Josh Allen's game log during the 2022 season as a pandas DataFrame.  

`player`: a player's full name, as it appears on [Pro Football Reference](https://www.pro-football-reference.com/)  
`position`: 'QB', 'RB', 'TE', or 'WR'  
`season`: the season you are looking for (int)  

```python
from pro_football_reference_web_scraper import player_game_log as p

game_log = p.get_player_game_log(player = 'Josh Allen', position = 'QB', season = 2022)
print(game_log)
```

### Team Game Logs
The following code will retrieve and print the Kansas City Chiefs' game log during the 1995 season as a pandas DataFrame.  

`team`: a team's full name (city and mascot), as it appears on [Pro Football Reference](https://www.pro-football-reference.com/)  
`season`: the season you are looking for (int)  

```python
from pro_football_reference_web_scraper import team_game_log as t

game_log = t.get_team_game_log(team = 'Kansas City Chiefs', season = 1995)
print(game_log)
```

# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)


@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
set SOURCEDIR=.
set BUILDDIR=_build

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Make sure you have Sphinx
	echo.installed, then set the SPHINXBUILD environment variable to point
	echo.to the full path of the 'sphinx-build' executable. Alternatively you
	echo.may add the Sphinx directory to PATH.
	echo.
	echo.If you don't have Sphinx installed, grab it from
	echo.https://www.sphinx-doc.org/
	exit /b 1
)

if "%1" == "" goto help

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%

:end
popd

import sphinx_rtd_theme
from recommonmark.transform import AutoStructify
import os
import sys
sys.path.insert(0, os.path.abspath('../pro_football_reference_web_scraper'))

def setup(app):
    app.add_config_value('recommonmark_config', {
        'auto_toc_tree_section': 'Contents',
    }, True)
    app.add_transform(AutoStructify)

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'pro-football-reference-web-scraper'
copyright = '2023, Matthew Kim'
author = 'Matthew Kim'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['recommonmark', 'sphinx.ext.napoleon', 'sphinx.ext.autodoc']
source_suffix = ['.rst', '.md']

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
html_static_path = ['_static']

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Getting a Player's Game Log

In order to retrieve a player's game log in a given season, you will first need to know the name of the player you are interested in. The spelling of the player's name must exactly match its spelling on [Pro Football Reference](https://www.pro-football-reference.com/). You will also need to specify the season you are interested in as well as the player's position. We currently only support game logs for quarterbacks, running backs, wide receivers, and tight ends.

## QB Game Log

The following code will output Patrick Mahomes' game log from the 2022 season.

```eval_rst

.. note:: The `position` parameter must be 'QB' exactly. 'Quarterback' or 'qb' will not work.

```

```python

from pro_football_reference_web_scraper import player_game_log as p

print(p.get_player_game_log(player = 'Patrick Mahomes', position = 'QB', season = 2022))

```

Output:

```

|    | date       |   week | team   | game_location   | opp   | result   |   team_pts |   opp_pts |   cmp |   att |   pass_yds |   pass_td |   int |   rating |   sacked |   rush_att |   rush_yds |   rush_td |
|---:|:-----------|-------:|:-------|:----------------|:------|:---------|-----------:|----------:|------:|------:|-----------:|----------:|------:|---------:|---------:|-----------:|-----------:|----------:|
|  0 | 2022-09-11 |      1 | KAN    | @               | ARI   | W        |         44 |        21 |    30 |    39 |        360 |         5 |     0 |    144.2 |        0 |          3 |          5 |         0 |
|  1 | 2022-09-15 |      2 | KAN    |                 | LAC   | W        |         27 |        24 |    24 |    35 |        235 |         2 |     0 |    106.2 |        1 |          2 |         -1 |         0 |
|  2 | 2022-09-25 |      3 | KAN    | @               | IND   | L        |         17 |        20 |    20 |    35 |        262 |         1 |     1 |     78.5 |        1 |          4 |         26 |         0 |
|  3 | 2022-10-02 |      4 | KAN    | @               | TAM   | W        |         41 |        31 |    23 |    37 |        249 |         3 |     1 |     97.7 |        3 |          4 |         34 |         0 |
|  4 | 2022-10-10 |      5 | KAN    |                 | LVR   | W        |         30 |        29 |    29 |    43 |        292 |         4 |     0 |    117.6 |        3 |          4 |         28 |         0 |
|  5 | 2022-10-16 |      6 | KAN    |                 | BUF   | L        |         20 |        24 |    25 |    40 |        338 |         2 |     2 |     85.2 |        3 |          4 |         21 |         0 |
|  6 | 2022-10-23 |      7 | KAN    | @               | SFO   | W        |         44 |        23 |    25 |    34 |        423 |         3 |     1 |    132.4 |        1 |          0 |          0 |         0 |
|  7 | 2022-11-06 |      9 | KAN    |                 | TEN   | W        |         20 |        17 |    43 |    68 |        446 |         1 |     1 |     80.9 |        4 |          6 |         63 |         1 |
|  8 | 2022-11-13 |     10 | KAN    |                 | JAX   | W        |         27 |        17 |    26 |    35 |        331 |         4 |     1 |    129.6 |        0 |          7 |         39 |         0 |
|  9 | 2022-11-20 |     11 | KAN    | @               | LAC   | W        |         30 |        27 |    20 |    34 |        329 |         3 |     0 |    120.8 |        1 |          4 |         23 |         0 |
| 10 | 2022-11-27 |     12 | KAN    |                 | LAR   | W        |         26 |        10 |    27 |    42 |        320 |         1 |     1 |     85.4 |        0 |          4 |         36 |         0 |
| 11 | 2022-12-04 |     13 | KAN    | @               | CIN   | L        |         24 |        27 |    16 |    27 |        223 |         1 |     0 |     98.2 |        2 |          2 |          9 |         1 |
| 12 | 2022-12-11 |     14 | KAN    | @               | DEN   | W        |         34 |        28 |    28 |    42 |        352 |         3 |     3 |     86.6 |        2 |          3 |         -3 |         0 |
| 13 | 2022-12-18 |     15 | KAN    | @               | HOU   | W        |         30 |        24 |    36 |    41 |        336 |         2 |     0 |    117.1 |        2 |          5 |         33 |         1 |
| 14 | 2022-12-24 |     16 | KAN    |                 | SEA   | W        |         24 |        10 |    16 |    28 |        224 |         2 |     0 |    106.8 |        1 |          2 |          8 |         1 |
| 15 | 2023-01-01 |     17 | KAN    |                 | DEN   | W        |         27 |        24 |    29 |    42 |        328 |         3 |     1 |    106.1 |        0 |          4 |          8 |         0 |
| 16 | 2023-01-07 |     18 | KAN    | @               | LVR   | W        |         31 |        13 |    18 |    26 |        202 |         1 |     0 |    105   |        2 |          3 |         29 |         0 |

```

## RB Game Log

The following code will output Christian McCaffrey's game log from the 2019 season.

```eval_rst

.. note:: The `position` parameter must be 'RB' exactly. 'Running back' or 'rb' will not work.

```

```python

from pro_football_reference_web_scraper import player_game_log as p

print(p.get_player_game_log(player = 'Christian McCaffrey', position = 'RB', season = 2019))

```

Output:

```

|    | date       |   week | team   | game_location   | opp   | result   |   team_pts |   opp_pts |   rush_att |   rush_yds |   rush_td |   tgt |   rec |   rec_yds |   rec_td |
|---:|:-----------|-------:|:-------|:----------------|:------|:---------|-----------:|----------:|-----------:|-----------:|----------:|------:|------:|----------:|---------:|
|  0 | 2019-09-08 |      1 | CAR    |                 | LAR   | L        |         27 |        30 |         19 |        128 |         2 |    11 |    10 |        81 |        0 |
|  1 | 2019-09-12 |      2 | CAR    |                 | TAM   | L        |         14 |        20 |         16 |         37 |         0 |     6 |     2 |        16 |        0 |
|  2 | 2019-09-22 |      3 | CAR    | @               | ARI   | W        |         38 |        20 |         24 |        153 |         1 |     4 |     3 |        35 |        0 |
|  3 | 2019-09-29 |      4 | CAR    | @               | HOU   | W        |         16 |        10 |         27 |         93 |         1 |    10 |    10 |        86 |        0 |
|  4 | 2019-10-06 |      5 | CAR    |                 | JAX   | W        |         34 |        27 |         19 |        176 |         2 |     8 |     6 |        61 |        1 |
|  5 | 2019-10-13 |      6 | CAR    | @               | TAM   | W        |         37 |        26 |         22 |         31 |         1 |     5 |     4 |        26 |        1 |
|  6 | 2019-10-27 |      8 | CAR    | @               | SFO   | L        |         13 |        51 |         14 |        117 |         1 |     5 |     4 |        38 |        0 |
|  7 | 2019-11-03 |      9 | CAR    |                 | TEN   | W        |         30 |        20 |         24 |        146 |         2 |     3 |     3 |        20 |        1 |
|  8 | 2019-11-10 |     10 | CAR    | @               | GNB   | L        |         16 |        24 |         20 |        108 |         1 |     7 |     6 |        33 |        0 |
|  9 | 2019-11-17 |     11 | CAR    |                 | ATL   | L        |          3 |        29 |         14 |         70 |         0 |    15 |    11 |       121 |        0 |
| 10 | 2019-11-24 |     12 | CAR    | @               | NOR   | L        |         31 |        34 |         22 |         64 |         1 |     9 |     9 |        69 |        1 |
| 11 | 2019-12-01 |     13 | CAR    |                 | WAS   | L        |         21 |        29 |         14 |         44 |         0 |    12 |     7 |        58 |        0 |
| 12 | 2019-12-08 |     14 | CAR    | @               | ATL   | L        |         20 |        40 |         11 |         53 |         0 |    12 |    11 |        82 |        0 |
| 13 | 2019-12-15 |     15 | CAR    |                 | SEA   | L        |         24 |        30 |         19 |         87 |         2 |    10 |     8 |        88 |        0 |
| 14 | 2019-12-22 |     16 | CAR    | @               | IND   | L        |          6 |        38 |         13 |         54 |         0 |    15 |    15 |       119 |        0 |
| 15 | 2019-12-29 |     17 | CAR    |                 | NOR   | L        |         10 |        42 |          9 |         26 |         1 |    10 |     7 |        72 |        0 |

```

## WR Game Log

The following code will output Jordy Nelson's game log from the 2014 season.

```eval_rst

.. note:: The `position` parameter must be 'WR' exactly. 'Wide receiver' or 'wr' will not work.

```

```python

from pro_football_reference_web_scraper import player_game_log as p

print(p.get_player_game_log(player = 'Jordy Nelson', position = 'WR', season = 2014))

```

Output:

```

|    | date       |   week | team   | game_location   | opp   | result   |   team_pts |   opp_pts |   tgt |   rec |   rec_yds |   rec_td |   snap_pct |
|---:|:-----------|-------:|:-------|:----------------|:------|:---------|-----------:|----------:|------:|------:|----------:|---------:|-----------:|
|  0 | 2014-09-04 |      1 | GNB    | @               | SEA   | L        |         16 |        36 |    14 |     9 |        83 |        0 |       0.98 |
|  1 | 2014-09-14 |      2 | GNB    |                 | NYJ   | W        |         31 |        24 |    16 |     9 |       209 |        1 |       0.97 |
|  2 | 2014-09-21 |      3 | GNB    | @               | DET   | L        |          7 |        19 |     7 |     5 |        59 |        0 |       1    |
|  3 | 2014-09-28 |      4 | GNB    | @               | CHI   | W        |         38 |        17 |    12 |    10 |       108 |        2 |       1    |
|  4 | 2014-10-02 |      5 | GNB    |                 | MIN   | W        |         42 |        10 |     3 |     1 |        66 |        1 |       0.7  |
|  5 | 2014-10-12 |      6 | GNB    | @               | MIA   | W        |         27 |        24 |    16 |     9 |       107 |        1 |       1    |
|  6 | 2014-10-19 |      7 | GNB    |                 | CAR   | W        |         38 |        17 |     5 |     4 |        80 |        1 |       0.84 |
|  7 | 2014-10-26 |      8 | GNB    | @               | NOR   | L        |         23 |        44 |     5 |     3 |        25 |        0 |       0.93 |
|  8 | 2014-11-09 |     10 | GNB    |                 | CHI   | W        |         55 |        14 |     6 |     6 |       152 |        2 |       0.63 |
|  9 | 2014-11-16 |     11 | GNB    |                 | PHI   | W        |         53 |        20 |    10 |     4 |       109 |        1 |       0.76 |
| 10 | 2014-11-23 |     12 | GNB    | @               | MIN   | W        |         24 |        21 |    12 |     8 |        68 |        0 |       0.95 |
| 11 | 2014-11-30 |     13 | GNB    |                 | NWE   | W        |         26 |        21 |     6 |     2 |        53 |        1 |       1    |
| 12 | 2014-12-08 |     14 | GNB    |                 | ATL   | W        |         43 |        37 |    10 |     8 |       146 |        2 |       0.99 |
| 13 | 2014-12-14 |     15 | GNB    | @               | BUF   | L        |         13 |        21 |    12 |     5 |        55 |        0 |       0.99 |
| 14 | 2014-12-21 |     16 | GNB    | @               | TAM   | W        |         20 |         3 |     9 |     9 |       113 |        1 |       0.89 |
| 15 | 2014-12-28 |     17 | GNB    |                 | DET   | W        |         30 |        20 |     8 |     6 |        86 |        0 |       0.94 |

```

## TE Game Log

The following code will output Jimmy Graham's game log from the 2013 season.

```eval_rst

.. note:: The `position` parameter must be 'TE' exactly. 'Tight end' or 'te' will not work.

```

```python

from pro_football_reference_web_scraper import player_game_log as p

print(p.get_player_game_log(player = 'Jimmy Graham', position = 'TE', season = 2013))

```

Output:

```

|    | date       |   week | team   | game_location   | opp   | result   |   team_pts |   opp_pts |   tgt |   rec |   rec_yds |   rec_td |   snap_pct |
|---:|:-----------|-------:|:-------|:----------------|:------|:---------|-----------:|----------:|------:|------:|----------:|---------:|-----------:|
|  0 | 2013-09-08 |      1 | NOR    |                 | ATL   | W        |         23 |        17 |     7 |     4 |        45 |        1 |       0.83 |
|  1 | 2013-09-15 |      2 | NOR    | @               | TAM   | W        |         16 |        14 |    16 |    10 |       179 |        1 |       0.81 |
|  2 | 2013-09-22 |      3 | NOR    |                 | ARI   | W        |         31 |         7 |    15 |     9 |       134 |        2 |       0.8  |
|  3 | 2013-09-30 |      4 | NOR    |                 | MIA   | W        |         38 |        17 |     4 |     4 |       100 |        2 |       0.78 |
|  4 | 2013-10-06 |      5 | NOR    | @               | CHI   | W        |         26 |        18 |    11 |    10 |       135 |        0 |       0.55 |
|  5 | 2013-10-13 |      6 | NOR    | @               | NWE   | L        |         27 |        30 |     6 |     0 |         0 |        0 |       0.69 |
|  6 | 2013-10-27 |      8 | NOR    |                 | BUF   | W        |         35 |        17 |     3 |     3 |        37 |        2 |       0.26 |
|  7 | 2013-11-03 |      9 | NOR    | @               | NYJ   | L        |         20 |        26 |    12 |     9 |       116 |        2 |       0.76 |
|  8 | 2013-11-10 |     10 | NOR    |                 | DAL   | W        |         49 |        17 |     5 |     5 |        59 |        0 |       0.39 |
|  9 | 2013-11-17 |     11 | NOR    |                 | SFO   | W        |         23 |        20 |    11 |     6 |        41 |        0 |       0.74 |
| 10 | 2013-11-21 |     12 | NOR    | @               | ATL   | W        |         17 |        13 |     7 |     5 |       100 |        1 |       0.63 |
| 11 | 2013-12-02 |     13 | NOR    | @               | SEA   | L        |          7 |        34 |     9 |     3 |        42 |        1 |       0.88 |
| 12 | 2013-12-08 |     14 | NOR    |                 | CAR   | W        |         31 |        13 |    11 |     6 |        58 |        2 |       0.72 |
| 13 | 2013-12-15 |     15 | NOR    | @               | STL   | L        |         16 |        27 |     6 |     2 |        25 |        0 |       0.84 |
| 14 | 2013-12-22 |     16 | NOR    | @               | CAR   | L        |         13 |        17 |    11 |     5 |        73 |        1 |       0.54 |
| 15 | 2013-12-29 |     17 | NOR    |                 | TAM   | W        |         42 |        17 |     8 |     5 |        71 |        1 |       0.52 |

```

# Getting a Team's Game Log

In order to retrieve a team's game log in a given season, you will first need to know the name of the team you are interested in. The spelling of the team's name must exactly match its spelling on [Pro Football Reference](https://www.pro-football-reference.com/). You will also need to specify the season you are interested in. The following code will print the Los Angeles Rams' game log during the 2021 season. The bye week is omitted. In addition to more traditional stats, the game log also includes stats on distance traveled (if an away game) and number of rest days.

```eval_rst
.. note:: Please capitalize every word in the team's name. For example, 'los angeles rams' will not work, but 'Los Angeles Rams' will. Additionally, ensure that you are writing the team's entire name (e.g. 'Los Angeles Rams' instead of 'Rams').

```

```python

from pro_football_reference import team_game_log as t

print(t.get_team_game_log(team = 'Los Angeles Rams', season = 2021))

```

Output:

```
|    |   week | day   | rest_days        | home_team   |   distance_travelled | opp                  | result   |   points_for |   points_allowed |   tot_yds |   pass_yds |   rush_yds |   opp_tot_yds |   opp_pass_yds |   opp_rush_yds |
|---:|-------:|:------|:-----------------|:------------|---------------------:|:---------------------|:---------|-------------:|-----------------:|----------:|-----------:|-----------:|--------------:|---------------:|---------------:|
|  0 |      1 | Sun   | 10 days 00:00:00 | True        |                0     | Chicago Bears        | W        |           34 |               14 |       386 |        312 |         74 |           322 |            188 |            134 |
|  1 |      2 | Sun   | 7 days 00:00:00  | False       |             1809.97  | Indianapolis Colts   | W        |           27 |               24 |       371 |        270 |        101 |           354 |            245 |            109 |
|  2 |      3 | Sun   | 7 days 00:00:00  | True        |                0     | Tampa Bay Buccaneers | W        |           34 |               24 |       407 |        331 |         76 |           446 |            411 |             35 |
|  3 |      4 | Sun   | 7 days 00:00:00  | True        |                0     | Arizona Cardinals    | L        |           20 |               37 |       401 |        280 |        121 |           465 |            249 |            216 |
|  4 |      5 | Thu   | 4 days 00:00:00  | False       |              954.979 | Seattle Seahawks     | W        |           26 |               17 |       476 |        358 |        118 |           354 |            262 |             92 |
|  5 |      6 | Sun   | 10 days 00:00:00 | False       |             2448.6   | New York Giants      | W        |           38 |               11 |       365 |        234 |        131 |           261 |            201 |             60 |
|  6 |      7 | Sun   | 7 days 00:00:00  | True        |                0     | Detroit Lions        | W        |           28 |               19 |       374 |        327 |         47 |           415 |            278 |            137 |
|  7 |      8 | Sun   | 7 days 00:00:00  | False       |             1376.55  | Houston Texans       | W        |           38 |               22 |       467 |        302 |        165 |           323 |            279 |             44 |
|  8 |      9 | Sun   | 7 days 00:00:00  | True        |                0     | Tennessee Titans     | L        |           16 |               28 |       347 |        253 |         94 |           194 |            125 |             69 |
|  9 |     10 | Mon   | 8 days 00:00:00  | False       |              308.127 | San Francisco 49ers  | L        |           10 |               31 |       278 |        226 |         52 |           335 |            179 |            156 |
| 10 |     12 | Sun   | 13 days 00:00:00 | False       |             1764.03  | Green Bay Packers    | L        |           28 |               36 |       353 |        285 |         68 |           399 |            307 |             92 |
| 11 |     13 | Sun   | 7 days 00:00:00  | True        |                0     | Jacksonville Jaguars | W        |           37 |                7 |       418 |        290 |        128 |           197 |            136 |             61 |
| 12 |     14 | Mon   | 8 days 00:00:00  | False       |              369.445 | Arizona Cardinals    | W        |           30 |               23 |       356 |        267 |         89 |           447 |            344 |            103 |
| 13 |     15 | Tue   | 8 days 00:00:00  | True        |                0     | Seattle Seahawks     | W        |           20 |               10 |       332 |        209 |        123 |           214 |            134 |             80 |
| 14 |     16 | Sun   | 5 days 00:00:00  | False       |             1533.21  | Minnesota Vikings    | W        |           30 |               23 |       356 |        197 |        159 |           361 |            295 |             66 |
| 15 |     17 | Sun   | 7 days 00:00:00  | False       |             2323.91  | Baltimore Ravens     | W        |           20 |               19 |       373 |        300 |         73 |           327 |            162 |            165 |
| 16 |     18 | Sun   | 7 days 00:00:00  | True        |                0     | San Francisco 49ers  | L        |           24 |               27 |       265 |        201 |         64 |           449 |            314 |            135 |
```

## Teams That Changed Names

Some teams have changed names throughout the course of NFL history. For example, the Phoenix Cardinals became the Arizona Cardinals in 1984. If you are unsure of when a team changed its name, you can either use any of its historical names or its current name. For example, the following code blocks will give the same output.

```python

from pro_football_reference_web_scraper import team_game_log as t

print(t.get_team_game_log(team = 'Phoenix Cardinals', season = 1994))

```

```python

from pro_football_reference_web_scraper import team_game_log as t

print(t.get_team_game_log(team = 'Arizona Cardinals', season = 1994))

```

Output:

```

|    |   week | day   | rest_days        | home_team   |   distance_travelled | opp                 | result   |   points_for |   points_allowed |   tot_yds |   pass_yds |   rush_yds |   opp_tot_yds |   opp_pass_yds |   opp_rush_yds |
|---:|-------:|:------|:-----------------|:------------|---------------------:|:--------------------|:---------|-------------:|-----------------:|----------:|-----------:|-----------:|--------------:|---------------:|---------------:|
|  0 |      1 | Sun   | 10 days 00:00:00 | False       |              369.445 | Los Angeles Rams    | L        |           12 |               14 |       234 |        128 |        106 |           152 |            102 |             50 |
|  1 |      2 | Sun   | 7 days 00:00:00  | True        |                0     | New York Giants     | L        |           17 |               20 |       174 |        135 |         39 |           206 |             88 |            118 |
|  2 |      3 | Sun   | 7 days 00:00:00  | False       |             1733.7   | Cleveland Browns    | L        |            0 |               32 |       318 |        255 |         63 |           322 |            243 |             79 |
|  3 |      5 | Sun   | 14 days 00:00:00 | True        |                0     | Minnesota Vikings   | W        |           17 |                7 |       309 |        200 |        109 |           358 |            340 |             18 |
|  4 |      6 | Sun   | 7 days 00:00:00  | False       |              865.842 | Dallas Cowboys      | L        |            3 |               38 |       221 |        168 |         53 |           351 |            273 |             78 |
|  5 |      7 | Sun   | 7 days 00:00:00  | False       |             1951.93  | Washington Redskins | W        |           19 |               16 |       324 |        173 |        151 |           234 |            149 |             85 |
|  6 |      8 | Sun   | 7 days 00:00:00  | True        |                0     | Dallas Cowboys      | L        |           21 |               28 |       315 |        208 |        107 |           312 |            237 |             75 |
|  7 |      9 | Sun   | 7 days 00:00:00  | True        |                0     | Pittsburgh Steelers | W        |           20 |               17 |       335 |        236 |         99 |           317 |            232 |             85 |
|  8 |     10 | Sun   | 7 days 00:00:00  | False       |             2074.89  | Philadelphia Eagles | L        |            7 |               17 |       254 |        181 |         73 |           322 |            172 |            150 |
|  9 |     11 | Sun   | 7 days 00:00:00  | False       |             2127.99  | New York Giants     | W        |           10 |                9 |       239 |        173 |         66 |           231 |             81 |            150 |
| 10 |     12 | Sun   | 7 days 00:00:00  | True        |                0     | Philadelphia Eagles | W        |           12 |                6 |       281 |        123 |        158 |           185 |            110 |             75 |
| 11 |     13 | Sun   | 7 days 00:00:00  | True        |                0     | Chicago Bears       | L        |           16 |               19 |       244 |        177 |         67 |           318 |            186 |            132 |
| 12 |     14 | Sun   | 7 days 00:00:00  | False       |             1007.26  | Houston Oilers      | W        |           30 |               12 |       332 |        171 |        161 |           198 |            161 |             37 |
| 13 |     15 | Sun   | 7 days 00:00:00  | True        |                0     | Washington Redskins | W        |           17 |               15 |       278 |        194 |         84 |           406 |            283 |            123 |
| 14 |     16 | Sun   | 7 days 00:00:00  | True        |                0     | Cincinnati Bengals  | W        |           28 |                7 |       364 |        212 |        152 |           189 |            125 |             64 |
| 15 |     17 | Sat   | 6 days 00:00:00  | False       |             1583.8   | Atlanta Falcons     | L        |            6 |               10 |       385 |        313 |         72 |           307 |            256 |             51 |

```

# Player Splits

In order to retrieve a player's splits in a given season, you will first need to know the name of the player you are interested in. The spelling of the player's name must exactly match its spelling on [Pro Football Reference](https://www.pro-football-reference.com/). You will also need to specify the season you are interested in, as well as if you want the stats as averages or sums.

## Home-Road Splits

You can retrieve a player's stats in home vs. road games either as averages or sums.

### Averages

The following code will output Saquon Barkley's stats in home vs. road games in the 2018 season as averages.

```python

from pro_football_reference_web_scraper import player_splits as p

print(p.home_road(player = 'Saquon Barkley', position = 'RB', season = 2018, avg = True))

```

Output:

```

| game_location   |   games |   team_pts |   opp_pts |   rush_att |   rush_yds |   rush_td |   tgt |   rec_yds |   rec_td |
|:----------------|--------:|-----------:|----------:|-----------:|-----------:|----------:|------:|----------:|---------:|
| home            |       8 |     20.25  |     27.75 |     17     |     90.625 |     0.75  | 7.625 |    42.375 |    0.125 |
| away            |       8 |     25.875 |     23.75 |     15.625 |     72.75  |     0.625 | 7.5   |    47.75  |    0.375 |

```

### Sums

The following code will output Saquon Barkley's stats in home vs. road games in the 2018 season as sums.

```python

from pro_football_reference_web_scraper import player_splits as p

print(p.home_road(player = 'Saquon Barkley', position = 'RB', season = 2018, avg = False))

```

Output:

```

| game_location   |   games |   team_pts |   opp_pts |   rush_att |   rush_yds |   rush_td |   tgt |   rec_yds |   rec_td |
|:----------------|--------:|-----------:|----------:|-----------:|-----------:|----------:|------:|----------:|---------:|
| home            |       8 |        162 |       222 |        136 |        725 |         6 |    61 |       339 |        1 |
| away            |       8 |        207 |       190 |        125 |        582 |         5 |    60 |       382 |        3 |

```

## Win-Loss Splits

You can also retrieve a player's stats in wins vs. losses either as averages or sums.

### Averages

The following code will output Saquon Barkley's stats in wins vs. losses in the 2018 season as averages.


```python

from pro_football_reference_web_scraper import player_splits as p

print(p.win_loss(player = 'Saquon Barkley', position = 'RB', season = 2018, avg = True))

```

Output:

```

| result   |   games |   team_pts |   opp_pts |   rush_att |   rush_yds |   rush_td |   tgt |   rec_yds |   rec_td |
|:---------|--------:|-----------:|----------:|-----------:|-----------:|----------:|------:|----------:|---------:|
| W        |       5 |    32.4    |   24.6    |    20.4    |   117.2    |  0.8      |   4.4 |   25.2    | 0.2      |
| L        |      11 |    18.8182 |   26.2727 |    14.4545 |    65.5455 |  0.636364 |   9   |   54.0909 | 0.272727 |

```

### Sums

The following code will output Saquon Barkley's stats in wins vs. losses in the 2018 season as sums.

```python

from pro_football_reference_web_scraper import player_splits as p

print(p.win_loss(player = 'Saquon Barkley', position = 'RB', season = 2018, avg = False))

```

Output:

```

| result   |   games |   team_pts |   opp_pts |   rush_att |   rush_yds |   rush_td |   tgt |   rec_yds |   rec_td |
|:---------|--------:|-----------:|----------:|-----------:|-----------:|----------:|------:|----------:|---------:|
| W        |       5 |        162 |       123 |        102 |        586 |         4 |    22 |       126 |        1 |
| L        |      11 |        207 |       289 |        159 |        721 |         7 |    99 |       595 |        3 |

```

# Team Splits

In order to retrieve a team's splits in a given season, you will first need to know the name of the team you are interested in. The spelling of the team's name must exactly match its spelling on [Pro Football Reference](https://www.pro-football-reference.com/). You will also need to specify the season you are interested in, as well as if you want the stats as averages or sums.

## Home-Road Splits

You can retrieve a team's stats in home vs. road games either as averages or sums.

### Averages

The following code will output the Philadelphia Eagles stats in home vs. road games in the 2018 season as averages.

```eval_rst

.. note:: The 'team' parameter is case sensitive. 'Philadelphia eagles' will not work, but 'Philadelphia Ealges' will.

```

```python

from pro_football_reference_web_scraper import team_splits as t

print(t.home_road(team = 'Philadelphia Eagles', season = 2018, avg = True))

```

Output:

```

| game_location   |   games |   wins |   ties |   losses |   points_for |   points_allowed |   tot_yds |   pass_yds |   rush_yds |   opp_tot_yds |   opp_pass_yds |   opp_rush_yds |
|:----------------|--------:|-------:|-------:|---------:|-------------:|-----------------:|----------:|-----------:|-----------:|--------------:|---------------:|---------------:|
| home            |       8 |      5 |      0 |        3 |       22.625 |             20.5 |   379.25  |    280.625 |     98.625 |       334     |        233.625 |        100.375 |
| away            |       8 |      4 |      0 |        4 |       23.25  |             23   |   351.375 |    253.75  |     97.625 |       398.375 |        304.875 |         93.5   |

```

### Sums

The following code will output the Philadelphia Eagles stats in home vs. road games in the 2018 season as sums.

```eval_rst

.. note:: The 'team' parameter is case sensitive. 'Philadelphia eagles' will not work, but 'Philadelphia Ealges' will.

```

```python

from pro_football_reference_web_scraper import team_splits as t

print(t.home_road(team = 'Philadelphia Eagles', season = 2018, avg = False))

```

Output:

```

| game_location   |   games |   wins |   ties |   losses |   points_for |   points_allowed |   tot_yds |   pass_yds |   rush_yds |   opp_tot_yds |   opp_pass_yds |   opp_rush_yds |
|:----------------|--------:|-------:|-------:|---------:|-------------:|-----------------:|----------:|-----------:|-----------:|--------------:|---------------:|---------------:|
| home            |       8 |      5 |      0 |        3 |          181 |              164 |      3034 |       2245 |        789 |          2672 |           1869 |            803 |
| away            |       8 |      4 |      0 |        4 |          186 |              184 |      2811 |       2030 |        781 |          3187 |           2439 |            748 |

```

## Win-Loss Splits

You can also retrieve a team's stats in wins vs. losses either as averages or sums.

### Averages

The following code will output the Philadelphia Eagles stats in wins vs. losses games in the 2018 season as averages.

```eval_rst

.. note:: The 'team' parameter is case sensitive. 'Philadelphia eagles' will not work, but 'Philadelphia Ealges' will.

```

```python

from pro_football_reference_web_scraper import team_splits as t

print(t.win_loss(team = 'Philadelphia Eagles', season = 2018, avg = True))

```

Output:

```

| result   |   games |   points_for |   points_allowed |   tot_yds |   pass_yds |   rush_yds |   opp_tot_yds |   opp_pass_yds |   opp_rush_yds |
|:---------|--------:|-------------:|-----------------:|----------:|-----------:|-----------:|--------------:|---------------:|---------------:|
| W        |       9 |      26.1111 |          16.3333 |   380.222 |    262.444 |   117.778  |       305.333 |        221.556 |        83.7778 |
| L        |       7 |      18.8571 |          28.7143 |   346.143 |    273.286 |    72.8571 |       444.429 |        330.571 |       113.857  |

```

### Sums

The following code will output the Philadelphia Eagles stats in wins vs. lossees in the 2018 season as sums.

```eval_rst

.. note:: The 'team' parameter is case sensitive. 'Philadelphia eagles' will not work, but 'Philadelphia Ealges' will.

```

```python

from pro_football_reference_web_scraper import team_splits as t

print(t.win_loss(team = 'Philadelphia Eagles', season = 2018, avg = False))

```

Output:

```

| result   |   games |   points_for |   points_allowed |   tot_yds |   pass_yds |   rush_yds |   opp_tot_yds |   opp_pass_yds |   opp_rush_yds |
|:---------|--------:|-------------:|-----------------:|----------:|-----------:|-----------:|--------------:|---------------:|---------------:|
| W        |       9 |          235 |              147 |      3422 |       2362 |       1060 |          2748 |           1994 |            754 |
| L        |       7 |          132 |              201 |      2423 |       1913 |        510 |          3111 |           2314 |            797 |

```