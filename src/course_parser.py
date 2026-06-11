import re

from bs4 import BeautifulSoup

WEEKDAYS = [
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه شنبه",
    "چهارشنبه",
    "پنج شنبه",
    "جمعه",
]


def parse_courses_with_columns(content):
    soup = BeautifulSoup(content, "html.parser")
    table = soup.find("table", id="scrollable")

    if not table:
        return [], []

    columns = parse_table_columns(table)
    courses = parse_courses(table)

    return columns, courses


def parse_table_columns(table):
    columns = []

    for th in table.thead.tr.find_all("th"):
        text = normalize_text(th.get_text(strip=True))

        columns.append(text)

    return columns


def parse_courses(table):
    courses = []
    columns = parse_table_columns(table)

    for tr in table.tbody.find_all("tr"):
        course = {}
        columns_iter = iter(columns)

        for td in tr.find_all("td"):
            column = normalize_text(next(columns_iter)).strip()

            if not column or td.find("img"):
                continue

            value = td.get_text(strip=True)
            course[column] = parse_value(value)

        courses.append(course)

    return courses


def parse_value(value):
    value = normalize_text(value)

    if value.isdigit():
        return int(value)

    exam_schedule = re.match(
        r"(\d{4}/\d{2}/\d{2}) از (\d{2}:\d{2}) تا (\d{2}:\d{2})",
        value
    )
    if exam_schedule:
        date, start, end = exam_schedule.groups()
        return {
            "date": date,
            "start": time_to_minutes(start),
            "end": time_to_minutes(end)
        }

    class_schedule = re.match(
        r"(شنبه|یکشنبه|دوشنبه|سه\s*شنبه|چهارشنبه|پنج\s*شنبه|جمعه)\s+"
        r"(?:از\s*)?"
        r"(\d{1,2}[:.]?\d{0,2})\s*(?:تا|الی)\s*(\d{1,2}[:.]?\d{2})",
        value
    )
    if class_schedule:
        weekday, start, end = class_schedule.groups()
        return {
            "weekday": WEEKDAYS.index(weekday),
            "start": time_to_minutes(start),
            "end": time_to_minutes(end)
        }

    return value


def normalize_text(text: str) -> str:
    return (
        text.strip()
        .replace('\u200c', ' ')
        .replace('ي', 'ی')
        .replace('ك', 'ک')
    )


def time_to_minutes(time):
    if ":" in time:
        hour, minute = time.split(":")
    elif "." in time:
        hour, minute = time.split(".")
    else:
        hour, minute = time, "0"

    return int(hour) * 60 + int(minute)


def minutes_to_time(minutes):
    hour = minutes // 60
    minute = minutes % 60

    return f"{hour:02d}:{minute:02d}"


def format_exam_schedule(value):
    date, start, end = value

    return f"{date} از {minutes_to_time(start)} تا {minutes_to_time(end)}"


def format_class_schedule(value):
    weekday, start, end = value
    day_name = WEEKDAYS[weekday] or "نامشخص"

    return f"{day_name} {minutes_to_time(start)} تا {minutes_to_time(end)}"
