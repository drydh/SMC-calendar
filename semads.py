#!/usr/bin/python
# -*- coding: utf-8 -*-
#
"""This script downloads the calendar of the SMC and
formats the information as a text file.

# Usage
 python semads.py --start 20100301 --stop 20100308 --output message.txt

 The above run will download all items in the calendar from 20100301
 (March 1, 2010) to 20100308 (March 8, 2010), output the generated
 text file in message.txt.

# Compatibility

 Install required packages using:
 python -m pip install -r requirements.txt
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import locale
from collections import defaultdict

import smc_scraper
from smc_scraper import Seminar


for locale_ in [("en_GB", "utf-8"), ("en_US", "utf-8"), "C"]:
    with contextlib.suppress(locale.Error):
        locale.setlocale(locale.LC_TIME, locale=locale_)
        break
else:
    print(
        "Warning: month and day names may be localized incorrectly, consider:\n"
        "\t`$ sudo locale-gen en_GB.utf8`"
    )

# READ COMMAND-LINE OPTIONS


def parse_date(val):
    """
    Like datetime.date.fromisoformat(), but also supports YYYYMMDD
    in Python < 3.11.
    """
    # If it looks like YYYYMMDD (8 digits, no separators)
    if len(val) == 8 and val.isdigit():
        try:
            return datetime.datetime.strptime(val, "%Y%m%d").date()
        except ValueError:
            # Fall through to raise same type of error as fromisoformat
            raise ValueError(f"Invalid isoformat string: {val}")
    else:
        return datetime.date.fromisoformat(val)


parser = argparse.ArgumentParser()
parser.add_argument(
    "--start", type=parse_date, help="start date", metavar="YYYYMMDD", required=True
)
parser.add_argument(
    "--stop-events",
    type=parse_date,
    help="stop date for events",
    metavar="YYYYMMDD",
)
parser.add_argument(
    "--stop-seminars",
    type=parse_date,
    help="stop date for seminars",
    metavar="YYYYMMDD",
)
parser.add_argument(
    "--output",
    action="store",
    help="name of destination file of email message",
    metavar="FILE",
    required=True,
)
parser.add_argument(
    "--lang",
    action="store",
    choices=["en", "sv"],
    help="language (sv/en)",
    metavar="en|sv",
    default="en",
)
parser.add_argument(
    "--max-events",
    action="store",
    type=int,
    help="maximum number of events, not counting ties (events before the seminar stop date are always included)",
    default=5,
)

args = parser.parse_args()

if args.stop_events is None:
    args.stop_events = args.start + datetime.timedelta(days=62)  # 9 weeks, ~2 months

if args.stop_seminars is None:
    args.stop_seminars = args.start + datetime.timedelta(days=6)

# Argument validation

if args.start > args.stop_events or args.start > args.stop_seminars:
    raise ValueError("Start date must be before stop date")


def scrape_and_format():
    # + iml_scraper.scrape(args)
    (events, seminars) = smc_scraper.scrape(
        start=args.start,
        stop_events=args.stop_events,
        stop_seminars=args.stop_seminars,
        lang=args.lang,
        max_events=args.max_events,
    )
    seminars_by_day = expand_and_group_by_day(seminars)

    formatted_start = format_date_email(args.start)
    formatted_stop = format_date_email(args.stop_seminars)

    body = "\n".join(
        [
            "This is an automatically generated summary of the Stockholm Mathematics Centre web calendar.",
            "",
            "Send subscription requests to kalendarium@math-stockholm.se.",
            "",
            "",
        ]
    )
    if events:
        body += "\n".join(["EVENTS", "======", "", ""])
        for event in events:
            body += event.format() + "\n\n"
        body += "\n\n"

    body += "\n".join(
        [
            "SEMINARS",
            "========",
            "",
            f"Seminars from {formatted_start}, to {formatted_stop}.",
            "",
            "",
        ]
    )

    body += "".join(
        format_day(day, seminar_list)
        for day, seminar_list in seminars_by_day
        if seminar_list
    )
    return body


def expand_and_group_by_day(seminars):
    seminars_by_day = defaultdict(list)
    for seminar in seminars:
        seminars_by_day[seminar.day].append(seminar)
    return sorted(seminars_by_day.items())


def format_day(day, seminar_list: list[Seminar]):
    pieces = [f"{f'{day:%A}'.upper()}, {day:%B} {day.day:d}, {day:%Y}"]
    pieces.extend(seminar.format() for seminar in seminar_list)
    text = "\n\n".join(pieces)
    return f"\n{text}\n\n"


def format_date_email(day):
    return f"{day:%B} {day.day:d}, {day:%Y}"


# OPEN OUTPUT FILE AND OUTPUT SEMINARS
mail_body = scrape_and_format()
with open(args.output, mode="w", encoding="utf-8") as output:
    output.write(mail_body)
