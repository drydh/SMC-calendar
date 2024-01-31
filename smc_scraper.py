import contextlib
import datetime
import re
from urllib.request import urlopen

from bs4 import BeautifulSoup

from utility import unescape_html

ALTERNATE_SPEAKER_TAGS = ["Lecturer", "Doctoral student", "Respondent", "Participating"]


def scrape(args):
    html = fetch_calendar(args)

    no_entries_string = {
        "en": r"No (upcoming |)calendar events were found",
        "sv": r"[Kk]alenderhändelser saknas",
    }[args.lang]
    no_entries_re = re.compile(no_entries_string)
    if html.find("h2", string=no_entries_re) or html.find("p", string=no_entries_re):
        return []

    return [
        parse_seminar(entry) for entry in html.find_all("li", class_="calendar__event")
    ]


def parse_seminar(html):

    day, end_day = parse_days(html)

    series = html.find("p", class_="calendar__eventinfo--bold")
    series = series.string.strip() if series is not None else ""

    # Speaker and title
    speaker, title = parse_speaker_and_title(html)

    start_time = parse_span(html, "startTime")
    stop_time = parse_span(html, "endTime").lstrip("-").strip()

    calendar_url = html.find("div").find("a")["href"]
    calendar_url = calendar_url.split("?")[0]
    calendar_url = f"https://www.math-stockholm.se{calendar_url}"

    location = parse_location(html)
    if not location:
        print(
            f"Warning: Did not find either location or video link for {speaker}: {title}"
        )
    fields = [
        field for field in [speaker, title, location, series, calendar_url] if field
    ]
    return {
        "day": day,
        "start_time": start_time,
        "stop_time": stop_time,
        "end_day": end_day,
        "fields": fields,
    }


def parse_location(html):
    location = find_row(html, "Location:", "calendar__eventinfo-location")

    video = find_row(html, "Video link:", "calendar__eventinfo-location")
    if video:
        location = f"{location} ({video})" if location else video

    return location


def parse_days(html):
    dates = html.find("p", class_="calendar calendar__eventinfo-startday")
    day = dates.find("span", class_="startDate").string.split()[1].rstrip(",")
    day = datetime.date.fromisoformat(day)
    end_day = dates.find("span", class_="endDate")
    if end_day is not None:
        end_day = end_day.string.split()[1].rstrip(",")
        end_day = datetime.date.fromisoformat(end_day)
    return day, end_day


def parse_speaker_and_title(html):
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
    return speaker, title


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


def fetch_calendar(args):
    url = construct_url(args.start, args.stop, args.lang)

    print(
        f"Fetching seminars for {args.start.isoformat()} - {args.stop.isoformat()} ({args.lang})"
    )

    raw_content = urlopen(url)
    return BeautifulSoup(raw_content, features="lxml")


def construct_url(start, stop, lang):
    length = (stop - start).days + 1
    url = f"https://www.math-stockholm.se/{'en/' if lang == 'en' else ''}kalender"
    url += f"?date={start.isoformat()}&length={length}"
    # url += "&l=en_UK"
    return url
