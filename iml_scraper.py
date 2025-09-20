#!/usr/bin/env python3

import contextlib
import datetime
import re

import requests
from bs4 import BeautifulSoup

import smc_scraper

import sys

DEBUG = False

SPEAKER_RE = re.compile("Speaker.*")
DATE_RE = re.compile("Date:")
TIME_RE = re.compile("Time:")

try:
    import requests_cache
    session = requests_cache.CachedSession(cache_name='iml_cache', backend='sqlite')
    print(f"Using cache ({session.cache.db_path}).", file=sys.stderr)
    def is_cached(response):
        return response.from_cache
except ImportError:
    session = requests.Session()
    def is_cached(response):
        return False

def fetch_entries(
    start=datetime.date.today(),
    stop=datetime.date.today() + datetime.timedelta(days=14),
):
    filtered = [
        entry for entry in fetch_all_programs() if overlaps(start, stop, entry["dates"])
    ]
    expanded = [
        sub_entry
        for entry in filtered
        for sub_entry in (
            expand_program(entry) if entry["category"] == "Programs" else [entry]
        )
        if overlaps(start, stop, sub_entry["dates"])
    ]
    return sorted(expanded, key=lambda entry: entry["dates"])


def overlaps(start, stop, dates):
    return dates[1] >= start and (stop is None or stop >= dates[0])


######################################################################
# Fetch JSON from IML WordPress
######################################################################

def fetch_all_programs():
    print("Fetching IML site.", file=sys.stderr)
    response = session.get(api_program_url(1))
    pages_count = int(response.headers["X-WP-TotalPages"])
    print(f"  Fetching {pages_count} pages.", file=sys.stderr)
    return [
        trim_entry(entry)
        for page in range(1, pages_count + 1)
        for entry in session.get(api_program_url(page)).json()
    ]


def api_program_url(page):
    return f"https://www.mittag-leffler.se/wp-json/wp/v2/ventla_program?per_page=100&page={page}&lang=en&_fields=title.rendered,link,category.name,custom_date"


#################################################################

def trim_entry(entry):
    return {
        "title": entry["title"]["rendered"],
        "link": entry["link"],
        "category": entry["category"]["name"],
        "dates": parse_dates(entry["custom_date"]),
    }


def parse_dates(string):
    if " - " in string:
        start, stop = string.split(" - ")
        stop_date = parse_full_date(stop)
        # cannot avoid the string roundtrip here,
        # see https://github.com/python/cpython/issues/70647, re parsing "Feb 29"
        start_date = datetime.datetime.strptime(
            f"{start} {stop_date.year}", "%b %d %Y"
        ).date()
    else:
        stop_date = parse_full_date(string)
        start_date = stop_date
    if start_date > stop_date and DEBUG:
        print(string)
    return start_date, stop_date


def parse_full_date(date):
    for format in ["%b %d %Y", "%B %d, %Y"]:
        with contextlib.suppress(ValueError):
            return datetime.datetime.strptime(date, format).date()
    raise ValueError(f'"{date}" does not match any known format')


######################################################################
# Parse IML program HTML page.
######################################################################

def expand_program(program):
    print(f"Fetching program '{program['title']}' ({program['dates'][0]} - {program['dates'][1]}).", file=sys.stderr)
    link_content = session.get(program["link"]).text
    print(f"  Fetching seminars.", file=sys.stderr)
    seminars = parse_seminars(BeautifulSoup(link_content, features="lxml"))
    return [program] + seminars


def parse_seminars(html):
    seminar_section = html.find("section", {"data-section": "seminars"})
    if seminar_section is None:
        return []
    seminars = []
    for seminar_html in seminar_section.find_all("li"):
        link = seminar_html.find("a", class_="seminars__link")["href"]
        if link is None:
            print(html)
            continue
        print(f"    * {link}", file=sys.stderr, end='')
        response = session.get(link,headers={"Accept-Encoding": "gzip, deflate, br"})
        print(" [CACHED]" if is_cached(response) else "", file=sys.stderr)
        seminar = parse_seminar(BeautifulSoup(response.text, features="lxml"))
        seminar.update( {
            "link": link,
            "category": "IML Seminar",
        } )
        seminars.append(seminar)
    return seminars


def parse_seminar(html):
    # print(html, end="\n" * 3)
    title = html.find("h1", class_="article__title").string
    try:
        speaker = html.find("p", string=SPEAKER_RE).find_next("p").string.strip()
    except AttributeError:
        if ":" in title:
            speaker, title = title.split(":", 1)
            title = title.strip()
            speaker = speaker.strip()
        else:
            speaker = None

    other_fields = parse_other_fields(html.find("div", class_="event-info--seminar"))
    date = datetime.date.fromisoformat(other_fields.pop("Date"))
    time = other_fields.pop("Time")
    return {
        "title": title,
        "speaker": speaker,
        "dates": (date, date),
        "time": time,
        "other_fields": other_fields,
    }


def parse_other_fields(html):
    ret = {}
    for p in html.find_all("p"):
        stripped_strings = [s.strip(":").strip() for s in p.stripped_strings]
        stripped_strings = [s for s in stripped_strings if s]
        key, *rest = stripped_strings
        value = "".join(rest).lstrip(":").strip()
        ret[key.rstrip(":")] = value
    return ret

######################################################################
# Format output
######################################################################

def print_formatted(entry):
    print(entry.pop("title"))
    print_field("speaker", entry.pop("speaker", None))
    print_field("link", entry.pop("link"))
    dates = entry.pop("dates")
    if dates[0] == dates[1]:
        dates_string = f"{dates[0]}"
    else:
        dates_string = f"{dates[0]} -- {dates[1]}"
    print_field("dates", dates_string)
    print_field("time", entry.pop("time", None))
    entry.update( entry.pop("other_fields", {}) )
    for header, value in entry.items():
        print_field(header, value)


def print_field(header, value):
    if value is not None:
        print(f"{header.title()}: {value}")

def match_str(str1,str2):
    return (str1 or "").strip() == (str2 or "").strip()

def matches(in_calendar, entry):
    matches_title = match_str(entry["title"], in_calendar.title)
    if isinstance(in_calendar, smc_scraper.Event):
        matches_speaker = True
        matches_dates = entry["dates"] == (in_calendar.start_day,
                                           in_calendar.end_day)
        matches_time = True
    elif isinstance(in_calendar, smc_scraper.Seminar):
        matches_speaker = match_str(entry["speaker"], in_calendar.speaker)
        matches_dates = entry["dates"][0] == entry["dates"][1] == in_calendar.day
        matches_time = entry["time"] == f"{in_calendar.start_time.strftime('%H:%M') if in_calendar.start_time else ''} - {in_calendar.end_time.strftime('%H:%M') if in_calendar.end_time else ''}"
    else:
        raise ValueError(f'"{in_calendar}" of unknown class')

    if( matches_title and matches_speaker and not (matches_dates and matches_time) ):
        print( "Potential match but not identical date and time:" )
        print( f"{entry['dates']}, {entry['time']}" )
    if( not matches_title and matches_speaker and matches_dates and matches_time ):
        print( "Matches speaker and time but not identical title." )
        print( f"SMC calendar title '{in_calendar.title}'." )

    return matches_title and matches_speaker and matches_dates and matches_time


if __name__ == "__main__":
    print("Fetching SMC site (for comparison).", file=sys.stderr)
    calendar = smc_scraper.scrape(
        start=datetime.date.today(),
        stop_seminars=datetime.date.today() + datetime.timedelta(days=14),
        stop_events=datetime.date.today() + datetime.timedelta(days=14),
        lang="en",
        max_events=None,
    )
    for entry in fetch_entries():
        print(end="\n" * 3)
        if "speaker" in entry and any(
            matches(in_calendar, entry)
            for calendar_section in calendar
            for in_calendar in calendar_section
        ):
            print(f"'{entry['title']}' matches a calendar entry")
            continue
        print_formatted(entry)
