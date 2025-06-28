from __future__ import annotations

from typing import NamedTuple
import contextlib
import datetime
import re
from urllib.request import urlopen

from bs4 import BeautifulSoup
from datetime import date, time

from utility import unescape_html

ALTERNATE_SPEAKER_TAGS = ["Lecturer", "Doctoral student", "Respondent", "Participating"]
EVENT_SERIES = [
    "Conference",
    "SMC Colloquium",
    "Göran Gustafsson Lectures in mathematics",
]
INDENT = " " * 7
CONFERENCE_LIKE_WORDS = ["Conference", "Workshop"]


class Event(NamedTuple):
    start_day: date
    end_day: date | None
    title: str
    location: str | None
    series: str
    calendar_url: str

    def format(self):
        dates = Event.format_date_range(self.start_day, self.end_day)
        if self.series == "Conference":
            description = next(
                self.title
                for word in CONFERENCE_LIKE_WORDS
                if self.title.startswith(word)
            )
        else:
            description = None
        if description is None:
            description = f"{self.series}, {self.title}"
        lines = [f"* {dates}, {description}"]
        if self.location is not None:
            lines.append(f"{INDENT}{self.location}")
        lines.append(f"{INDENT}{self.calendar_url}")
        return "\n".join(lines)

    def day_range(self):
        return self.start_day, self.end_day

    @staticmethod
    def format_date_range(start_day: date, end_day: date | None) -> str:
        """
        Format a short range of dates (expected to span less than 11 months)
        """
        if end_day is None:
            return f"{start_day.strftime('%B %d')}"
        if start_day.month == end_day.month:
            return f"{start_day.strftime('%B')} {start_day.day} - {end_day.day}"
        return f"{start_day.strftime('%B')} {start_day.day} - {start_day.strftime('%B')} {end_day.day}"


class Seminar(NamedTuple):
    day: date
    start_time: time | None
    end_time: time | None
    speaker: str | None
    title: str
    location: str | None
    series: str
    calendar_url: str

    def format(self):
        lines = []
        if self.start_time or self.end_time:
            start_time = (
                self.start_time.strftime("%H:%M") if self.start_time is not None else ""
            )
            end_time = (
                self.end_time.strftime("%H:%M") if self.end_time is not None else ""
            )
            lines.append(f"{start_time:>5} - {end_time:>5}")
        lines.extend(
            f"{INDENT}{field}"
            for field in (
                self.speaker,
                self.title,
                self.location,
                self.series,
                self.calendar_url,
            )
            if field
        )
        return "\n".join(lines)


def scrape(
    start: date,
    stop_events: date,
    stop_seminars: date,
    lang: str,
    max_events: int | None,
) -> tuple[list[Event], list[Seminar]]:
    stop = max(stop_events, stop_seminars)
    html = fetch_calendar(start, stop, lang)

    no_entries_string = {
        "en": r"No (upcoming |)calendar events were found",
        "sv": r"[Kk]alenderhändelser saknas",
    }[lang]
    no_entries_re = re.compile(no_entries_string)
    if html.find("h2", string=no_entries_re) or html.find("p", string=no_entries_re):
        return [], []

    events, seminars = [], []
    for entry in html.find_all("li", class_="calendar__event"):
        entry = parse_calendar_entry(entry)
        if isinstance(entry, Event):
            if entry.start_day > stop_events:
                continue
            if entry.start_day > stop_seminars and (
                max_events is None
                or max_events == 0
                or (
                    len(events) >= max_events
                    and events[-1].day_range() < entry.day_range()
                )
            ):
                continue
            events.append(entry)
        elif entry.day <= stop_seminars:
            seminars.append(entry)
    events.sort(key=lambda event: (event.start_day, event.end_day, event.title))
    return events, seminars


def parse_calendar_entry(html) -> Event | Seminar:

    day, end_day = parse_days(html)

    series = html.find("p", class_="calendar__eventinfo--bold")
    series = series.string.strip() if series is not None else ""

    start_time = parse_span(html, "startTime")
    end_time = parse_span(html, "endTime").lstrip("-").strip()
    start_time = parse_time(start_time)
    end_time = parse_time(end_time)

    title = html.find("div").find("a")["title"]

    calendar_url = html.find("div").find("a")["href"]
    calendar_url = calendar_url.split("?")[0]
    calendar_url = f"https://www.math-stockholm.se{calendar_url}"

    location = parse_location(html)
    if not location:
        print(f"Warning: Did not find either location or video link for {title}")
    if is_event(series, day, end_day):
        if series.startswith("Seminar, "):
            series = series.lstrip("Seminar, ")
        return Event(day, end_day, title, location, series, calendar_url)

    # Speaker and title
    title, speaker = split_title_and_speaker(title, html)
    if not speaker:
        print(
            f"Warning: Did not find {'/'.join(ALTERNATE_SPEAKER_TAGS)} for {speaker}: {title}"
        )
    return Seminar(
        day, start_time, end_time, speaker, title, location, series, calendar_url
    )


def is_event(series: str, start_day: date | None, end_day: date | None) -> bool:
    return (
        series in EVENT_SERIES
        or start_day is None
        or (end_day is not None and start_day < end_day)
    )


def parse_location(html):
    location = find_row(html, "Location:", "calendar__eventinfo-location")

    video = find_row(html, "Video link:", "calendar__eventinfo-location")
    if video:
        location = f"{location} ({video})" if location else video

    return location


def parse_days(html) -> tuple[date, date | None]:
    dates = html.find("p", class_="calendar calendar__eventinfo-startday")
    day = dates.find("span", class_="startDate").string.split()[1].rstrip(",")
    day = datetime.date.fromisoformat(day)
    end_day = dates.find("span", class_="endDate")
    if end_day is not None:
        end_day = end_day.string.split()[1].rstrip(",")
        end_day = datetime.date.fromisoformat(end_day)
    return day, end_day


def parse_time(string) -> time | None:
    try:
        return datetime.time.fromisoformat(string)
    except ValueError:
        return None


def split_title_and_speaker(title, html) -> tuple[str, str | None]:

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
    title = unescape_html(title)
    speaker = unescape_html(speaker)
    if speaker == "":
        speaker = None
    return title, speaker


def find_row(entry, header, class_=None):
    divs = (
        entry.find_all("p", class_=class_) if class_ is not None else entry.findAll("p")
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


def fetch_calendar(start, stop, lang):
    url = construct_url(start, stop, lang)

    print(f"Fetching seminars for {start.isoformat()} - {stop.isoformat()} ({lang})")

    raw_content = urlopen(url)
    return BeautifulSoup(raw_content, features="lxml")


def construct_url(start, stop, lang):
    length = (stop - start).days + 1
    url = f"https://www.math-stockholm.se/{'en/' if lang == 'en' else ''}kalender"
    url += f"?date={start.isoformat()}&length={length}"
    # url += "&l=en_UK"
    return url
