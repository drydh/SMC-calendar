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
import re
from urllib.request import urlopen  # Python 3

from bs4 import BeautifulSoup

ALTERNATE_SPEAKER_TAGS = ["Lecturer", "Doctoral student", "Respondent", "Participating"]

locale.setlocale(locale.LC_TIME, locale=("en_US", "utf-8"))

strptime = datetime.datetime.strptime

# READ COMMAND-LINE OPTIONS


def parse_date(val):
    return strptime(val, "%Y%m%d").date()


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


no_entries_string = {
    "en": "No calendar events were found",
    "sv": "Kalenderhändelser saknas",
}[args.lang]
no_entries_re = re.compile(no_entries_string)


def scrape_and_format():

    seminars = scrape_seminars()

    start_date = format_date_header(args.start)
    stop_date = format_date_header(args.stop)

    body = "\n".join(
        [
            "SEMINARS",
            "========",
            "",
            "This is an automatically generated summary of the Stockholm Mathematics Centre",
            f"web calendar for seminars from {start_date}, to {stop_date}.",
            "",
            "Send subscription requests to kalendarium@math-stockholm.se.",
            "",
            "",
        ]
    )

    body += "".join(
        format_day(day, seminar_list) for day, seminar_list in seminars if seminar_list
    )
    return body


def scrape_seminars():
    """DOWNLOAD ALL SEMINARS BETWEEN START AND STOP DATES

    This information is stored in the data structure
        seminars = [[<date object>, [seminar, ...]], ...]
    where seminar is a dictionary with keys
     ["start_time", "stop_time", "series", "speaker", "title", "calender_url"]
    """

    seminars = []
    day = args.start
    one_day = datetime.timedelta(days=1)
    while day <= args.stop:
        seminar_list = scrape_day(day)
        if seminar_list:
            seminars.append((day, seminar_list))
        day += one_day
    return seminars


def scrape_day(day):
    if args.lang == "en":
        url = "https://www.math-stockholm.se/en/kalender"
    else:
        url = "https://www.math-stockholm.se/kalender"
    url += f"?date={day.isoformat()}"
    url += "&length=1"
    # url += "&l=en_UK"

    print(f"Fetching seminars for {day.isoformat()} ({args.lang})")

    page = urlopen(url)
    content = BeautifulSoup(page, features="lxml")

    if content.find("h2", string=no_entries_re) or content.find(
        "p", string=no_entries_re
    ):
        return []

    return [
        parse_seminar(seminar_el)
        for seminar_el in content.findAll("li", {"class": "calendar__event"})
    ]


def parse_seminar(html):

    series = html.find("p", class_="calendar__eventinfo--bold")
    series = series.string.strip() if series is not None else ""

    # Speaker and title
    title = html.find("div").find("a")["title"]
    try:
        speaker, title = title.split(":", 1)
    except ValueError:
        speaker = ""
    speaker = speaker.strip()
    title = title.strip()

    for alternate_speaker_tag in ALTERNATE_SPEAKER_TAGS:
        if speaker != "":
            break
        speaker = find_row(html, f"{alternate_speaker_tag}:")
    if speaker == "":
        print(
            f"Warning: Did not find {'/'.join(ALTERNATE_SPEAKER_TAGS)} for {speaker}: {title}"
        )

    speaker = unescape_html(speaker)
    title = unescape_html(title)

    start_time = parse_span(html, "startTime")
    stop_time = parse_span(html, "endTime").lstrip("-").strip()

    calendar_url = html.find("div").find("a")["href"]
    calendar_url = calendar_url.split("?")[0]
    calendar_url = f"https://www.math-stockholm.se{calendar_url}"

    location = find_row(html, "Location:", "calendar__eventinfo-location")
    video = find_row(html, "Video link:", "calendar__eventinfo-location")

    if video:
        location = f"{location} ({video})" if location else video
    if not location:
        print(
            f"Warning: Did not find either location or video link for {speaker}: {title}"
        )

    return {
        "start_time": start_time,
        "stop_time": stop_time,
        "series": series,
        "speaker": speaker,
        "title": title,
        "location": location,
        "url": calendar_url,
    }


def find_row(entry, header, class_=None):
    divs = (
        entry.findAll("p", class_=class_) if class_ is not None else entry.findAll("p")
    )
    for div in divs:
        terms = div()
        with contextlib.suppress(IndexError):
            if terms[0].string.strip() == header:
                return unescape_html(terms[1].string.strip())
    return ""


def parse_span(html, class_):
    result = html.find("span", class_=class_)
    result = "" if result is None else result.string
    return result.strip()


def unescape_html(string):
    return BeautifulSoup(string, features="lxml").string


def format_seminar(seminar):
    lines = []
    if seminar["start_time"] or seminar["stop_time"]:
        lines.append(f"{seminar['start_time']:>5} - {seminar['stop_time']:>5}")

    lines.extend(
        f"       {seminar[tag]}"
        for tag in ["speaker", "title", "location", "series", "url"]
        if seminar[tag]
    )

    return "\n".join(lines)


def format_day(day, seminar_list):
    pieces = [f"{f'{day:%A}'.upper()}, {day:%B} {day.day:d}, {day:%Y}"]
    pieces.extend(format_seminar(seminar) for seminar in seminar_list)
    text = "\n\n".join(pieces)
    return f"\n{text}\n\n"


def format_date_header(day):
    return f"{day:%B} {day.day:d}, {day:%Y}"


# OPEN OUTPUT FILE AND OUTPUT SEMINARS

with open(args.output, mode="w", encoding="utf-8") as output:
    for line in scrape_and_format():
        output.write(line)
