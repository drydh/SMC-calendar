# SMC-calendar
Scripts for extracting **Polopoly calendar entries** from the SMC web page and
to compile a weekly digest email.

## Requirements
- Python (v2 or v3) with `bs4` (BeautifulSoup) and `lxml`.

## Contents
1. Python script `semads.py` to retrieve calendar entries.
1. Python script `seminarmailer.py` to send out the digest email.
1. Bash script `calendar.sh` to facilitate the previous two steps.
1. Python script `ML-ads.py` to retrieve calendar entries from the web page of Insitut Mittag-Leffler.
1. Bash script `mittag-leffler.sh` to facilitate the previous step.
1. Bash script `convert-tex-to-polopoly.sh` to convert simple TeX code to Polopoly html source.
