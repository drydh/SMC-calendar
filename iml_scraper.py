#!/usr/bin/env python3

import datetime
import re

import requests
from bs4 import BeautifulSoup

DEBUG = False

SPEAKER_RE = re.compile("Speaker")
DATE_RE = re.compile("Date:")
TIME_RE = re.compile("Time:")


def fetch_entries(
    start=datetime.date.today(),
    stop=datetime.date.today() + datetime.timedelta(days=14),
):
    filtered = [
        entry for entry in fetch_all_entries() if overlaps(start, stop, entry["dates"])
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


def fetch_all_entries():
    response = requests.get(api_url(1))
    pages_count = int(response.headers["X-WP-TotalPages"])
    return [
        trim_entry(entry)
        for page in range(1, pages_count + 1)
        for entry in requests.get(api_url(page)).json()
    ]


def api_url(page):
    return f"https://www.mittag-leffler.se/wp-json/wp/v2/ventla_program?per_page=100&page={page}&lang=en"


def trim_entry(entry):
    return {
        "title": entry["title"]["rendered"],
        "link": entry["link"],
        "category": entry["category"]["name"],
        "dates": parse_dates(entry["custom_date"]),
    }


def parse_dates(string):
    start, stop = string.split(" - ")
    stop_date = datetime.datetime.strptime(stop, "%b %d %Y").date()
    start_date = datetime.datetime.strptime(start, "%b %d").date()
    start_date = datetime.date(stop_date.year, start_date.month, start_date.day)
    if start_date > stop_date and DEBUG:
        print(string)
    return (start_date, stop_date)


def expand_program(program):
    link_content = requests.get(program["link"]).text
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
        seminar = parse_seminar(
            BeautifulSoup(requests.get(link).text, features="lxml")
        ) | {
            "link": link,
            "category": "IML Seminar",
        }
        seminars.append(seminar)
    return seminars


def parse_seminar(html):
    # print(html, end="\n" * 3)
    title = html.find("h1", class_="article__title").string
    try:
        speaker = html.find("p", string=SPEAKER_RE).find_next("p").string.strip()
    except AttributeError:
        speaker = ""
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
    entry |= entry.pop("other_fields", {})
    for header, value in entry.items():
        print_field(header, value)


def print_field(header, value):
    if value is not None:
        print(f"{header.title()}: {value}")


if __name__ == "__main__":
    for entry in fetch_entries():
        print_formatted(entry)
        print(end="\n" * 3)
