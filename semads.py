#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# SEMADS.PY
#
# This script downloads the calendar of the SMC and
# formats the information as a text file.
#
# Usage
#
# python semads.py --start 20100301 --stop 20100308 --output message.txt
#
# The above run will download all items in the calendar from 20100301
# (March 1, 2010) to 20100308 (March 8, 2010), output the generated
# text file in message.txt.
#
# Compatibility
#
# Install required packages using:
# python -m pip install -r requirements.txt

import argparse
import contextlib
import datetime
import locale
from collections import defaultdict

import smc_scraper

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
    return datetime.date.fromisoformat(val)


parser = argparse.ArgumentParser()
parser.add_argument(
    "--start", type=parse_date, help="start date", metavar="YYYYMMDD", required=True
)
parser.add_argument(
    "--stop", type=parse_date, help="stop date", metavar="YYYYMMDD", required=True
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

args = parser.parse_args()

# Argument validation

if args.start > args.stop:
    raise ValueError("Start date must be before stop date")


def scrape_and_format():
    # + iml_scraper.scrape(args)
    seminars = smc_scraper.scrape(start=args.start, stop=args.stop, lang=args.lang)
    (seminars_by_day, multi_day) = expand_and_group_by_day(seminars)

    formatted_start = format_date_email(args.start)
    formatted_stop = format_date_email(args.stop)

    body = "\n".join(
        [
            "SEMINARS",
            "========",
            "",
            "This is an automatically generated summary of the Stockholm Mathematics Centre",
            f"web calendar for seminars from {formatted_start}, to {formatted_stop}.",
            "",
            "Send subscription requests to kalendarium@math-stockholm.se.",
            "",
            "",
        ]
    )

    body += "".join(
        format_day(day, seminar_list)
        for day, seminar_list in seminars_by_day
        if seminar_list
    )
    return (body, multi_day)


def expand_and_group_by_day(seminars):
    multi_day = []
    seminars_by_day = defaultdict(list)
    for seminar in seminars:
        days = days_list(seminar)
        if len(days) > 1:
            multi_day.append(
                f"{seminar["fields"][0]} on {seminar["day"]} {seminar["start_time"]}"
            )
        for day in days:
            seminars_by_day[day].append(seminar)
    return (sorted(seminars_by_day.items()), multi_day)


def days_list(seminar):
    end_day = seminar.get("end_day")
    day = seminar["day"]
    if end_day is None:
        return [day] if args.start <= day <= args.stop else []
    one_day = datetime.timedelta(days=1)
    days = []
    while day <= args.stop and day <= end_day:
        if day >= args.start:
            days.append(day)
        day += one_day
    return days


def format_day(day, seminar_list):
    pieces = [f"{f'{day:%A}'.upper()}, {day:%B} {day.day:d}, {day:%Y}"]
    pieces.extend(format_seminar(seminar) for seminar in seminar_list)
    text = "\n\n".join(pieces)
    return f"\n{text}\n\n"


def format_seminar(seminar):
    """
    Expected input is a dictionary with type
    {"day": date, "start_time": str, "stop_time": str, "end_day": None | date, fields: [str]]
    """
    # could be a custom dataclass

    lines = []
    if seminar["start_time"] or seminar["stop_time"]:
        lines.append(f"{seminar['start_time']:>5} - {seminar['stop_time']:>5}")
    lines.extend(f"       {field}" for field in seminar["fields"])
    return "\n".join(lines)


def format_date_email(day):
    return f"{day:%B} {day.day:d}, {day:%Y}"


# OPEN OUTPUT FILE AND OUTPUT SEMINARS
(mail_body, multi_day) = scrape_and_format()
with open(args.output, mode="w", encoding="utf-8") as output:
    output.write(mail_body)
for seminar in multi_day:
    print(f"WARNING: {seminar} spans multiple days, start and end times may be wrong")
if len(multi_day) > 0:
    print()
