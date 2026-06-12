import os
import re
import traceback
from collections import defaultdict

import unicodedata
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.ai_summarizer import summarize_professor
from src.course_parser import parse_courses_with_columns
from src.course_scheduler import CourseScheduler
from src.persian_utils import normalize_persian
from src.professor_review_parser import load_all_professor_reviews_from_strings, extract_reviews_for_professor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_EXTENSIONS = {'html'}

app = FastAPI(title="Class Scheduler")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "src", "templates"))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def secure_filename(filename: str | bytes):
    filename = os.fsdecode(os.path.basename(filename)).strip()
    filename = unicodedata.normalize("NFKD", filename)
    filename = re.sub(r"[^A-Za-z0-9._\-\u0600-\u06FF]+", "_", filename)
    filename = filename.strip("._")
    return filename or "upload.html"


def json_response(content, status_code=200):
    return JSONResponse(content=content, status_code=status_code)


async def get_request_data(request: Request):
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def parse_courses_from_files(course_files):
    parsed_courses = {}
    parsing_errors = []

    for f in (course_files or []):
        raw_name = f.get("name", "unknown.html")
        content = f.get("content", "")

        if not content or not allowed_file(raw_name):
            continue

        name = secure_filename(raw_name)

        try:
            _, courses = parse_courses_with_columns(content)
        except Exception as e:
            parsing_errors.append(f"Error parsing {name}: {str(e)}")
            continue

        if not courses:
            parsing_errors.append(f"No courses found in {name}.")
            continue

        for idx, course in enumerate(courses):
            unique_id = f"{name}_{idx}"
            course["__source_file"] = name
            course["__source_row"] = idx + 1
            course["__source_id"] = unique_id
            course["__professor"] = get_course_professor(course)
            course["__course_name"] = get_course_name(course)
            parsed_courses[unique_id] = course

    return parsed_courses, parsing_errors


def get_course_name(course):
    value = course.get("نام درس") or course.get("نام کلاس درس") or "Unknown"
    return value.strip() if isinstance(value, str) else str(value)


def get_course_class_id(course, fallback=None):
    for key in ("كد درس", "کد درس", "courseCode", "course_id"):
        value = course.get(key)

        if value not in (None, ""):
            return str(value).strip()

    if fallback is not None:
        return str(fallback)

    return "نامشخص"


def get_course_professor(course):
    for key in course:
        if "استاد" in key:
            value = course.get(key)

            if value not in (None, ""):
                return str(value).strip()

    return None


def get_course_schedule(course):
    return course.get("زمانبندی تشکیل کلاس") or course.get("نام کلاس درس")


def is_valid_course_row(course):
    sched = get_course_schedule(course)

    if not isinstance(sched, dict):
        return False

    if sched.get("weekday") is None or sched.get("start") is None or sched.get("end") is None:
        return False

    return bool(get_course_professor(course))


def build_dashboard_snapshot(parsed_courses):
    visible_courses = [course for course in parsed_courses.values() if is_valid_course_row(course)]

    prof_values = sorted(set(
        get_course_professor(c) for c in visible_courses
        if get_course_professor(c)
    ))

    course_values = sorted(set(
        get_course_name(c) for c in visible_courses
        if get_course_name(c)
    ))

    course_professors = build_course_professor_map(visible_courses)

    return {
        "columns": get_available_filter_columns(parsed_courses),
        "prof_values": prof_values,
        "course_values": course_values,
        "course_professors": course_professors,
        "course_count": len(visible_courses)
    }


def build_course_professor_map(courses):
    course_professors = defaultdict(set)

    for course in courses:
        course_name = get_course_name(course)
        professor = get_course_professor(course)

        if course_name and professor:
            course_professors[course_name].add(professor)

    return {
        course_name: sorted(professors)
        for course_name, professors in sorted(course_professors.items(), key=lambda item: item[0])
    }


def get_available_filter_columns(courses):
    columns = set()

    for course in courses.values():
        for k, v in course.items():
            if str(k).startswith("__"):
                continue

            if isinstance(v, tuple):
                continue

            columns.add(k)

    return sorted(columns)


def serialize_schedule(sched):
    if not sched or not isinstance(sched, dict):
        return None

    return {
        "weekday": sched.get("weekday"),
        "start": sched.get("start"),
        "end": sched.get("end"),
        "date": sched.get("date", "")
    }


def serialize_course(course, cid=None):
    sched = get_course_schedule(course)
    exam = course.get("زمان امتحان")

    prof_name = get_course_professor(course)
    class_id = get_course_class_id(course, cid)
    source_file = course.get("__source_file")
    source_row = course.get("__source_row")

    return {
        "id": class_id,
        "class_id": class_id,
        "unique_id": cid,
        "course_name": get_course_name(course),
        "professor": prof_name,
        "class_time": serialize_schedule(sched) if sched else None,
        "exam": serialize_schedule(exam) if exam else None,
        "source_file": source_file,
        "source_row": source_row,
        "source_label": f"{source_file}:{source_row}" if source_file and source_row else source_file,
        "raw": {k: v for k, v in course.items() if not isinstance(v, dict) and not str(k).startswith("__")}
    }


def normalize_lookup_text(value):
    return normalize_persian(str(value or "")).casefold()


def normalize_course_filter_rows(filters_list):
    rows = []

    for item in filters_list or []:
        if not isinstance(item, dict):
            continue

        course_name = ""
        professor = ""

        if "course_name" in item or "professor" in item:
            course_name = str(item.get("course_name", "")).strip()
            professor = str(item.get("professor", "")).strip()

        elif "column" in item and "value" in item:
            column = str(item.get("column", "")).strip()
            value = str(item.get("value", "")).strip()

            if column in ("نام درس", "درس", "course_name", "__course_name"):
                course_name = value
            elif column in ("نام استاد", "استاد", "professor", "__professor"):
                professor = value

        if course_name or professor:
            row = {}
            if course_name:
                row["course_name"] = course_name
            if professor:
                row["professor"] = professor
            rows.append(row)

    return rows


def course_matches_filter_row(course, row):
    course_name = row.get("course_name", "")
    professor = row.get("professor", "")

    if course_name and normalize_lookup_text(get_course_name(course)) != normalize_lookup_text(course_name):
        return False

    if professor and normalize_lookup_text(get_course_professor(course)) != normalize_lookup_text(professor):
        return False

    return bool(course_name or professor)


def filter_courses_by_rows(courses, rows):
    normalized_rows = normalize_course_filter_rows(rows)

    if not normalized_rows:
        return dict(courses)

    filtered_courses = {}

    for course_id, course in courses.items():
        if any(course_matches_filter_row(course, row) for row in normalized_rows):
            filtered_courses[course_id] = course

    return filtered_courses


def group_courses_by_class_id(course_items):
    groups = defaultdict(list)
    for item in course_items:
        if not item:
            continue

        group_key = str(item.get("class_id") or item.get("id") or item.get("unique_id") or "نامشخص")
        groups[group_key].append(item)

    grouped = []

    for class_id, items in sorted(groups.items(), key=lambda kv: kv[0]):
        items.sort(key=lambda row: (
            (row.get("class_time") or {}).get("weekday") is None,
            (row.get("class_time") or {}).get("weekday", 99),
            (row.get("class_time") or {}).get("start") is None,
            (row.get("class_time") or {}).get("start", 10 ** 9),
            row.get("course_name") or "",
            row.get("source_file") or "",
            row.get("source_row") or 0,
            row.get("unique_id") or ""
        ))

        course_names = sorted({row.get("course_name") for row in items if row.get("course_name")})
        professors = sorted({row.get("professor") for row in items if row.get("professor")})
        source_files = sorted({row.get("source_file") for row in items if row.get("source_file")})

        grouped.append({
            "class_id": class_id,
            "course_name": course_names[0] if course_names else "Unknown",
            "course_names": course_names,
            "professors": professors,
            "source_files": source_files,
            "items": items,
            "item_count": len(items),
        })

    return grouped


def visible_course_items(parsed_courses):
    return {
        cid: course
        for cid, course in parsed_courses.items()
        if is_valid_course_row(course)
    }


def build_professor_summary(courses_list, all_reviews):
    profs = {}

    for course in courses_list:
        name = course.get("professor") or "نامشخص"
        entry = profs.setdefault(name, {
            "name": name,
            "courses": 0,
            "reviews": extract_reviews_for_professor(all_reviews, name),
            "class_ids": [],
            "classes": []
        })

        entry["courses"] += 1
        entry["class_ids"].append(course.get("class_id") or course.get("id") or course.get("unique_id"))
        entry["classes"].append(course)

    for name, revs in all_reviews.items():
        profs.setdefault(name, {
            "name": name,
            "courses": 0,
            "reviews": revs,
            "class_ids": [],
            "classes": []
        })

    for p in profs.values():
        p["class_ids"] = sorted({cid for cid in p["class_ids"] if cid})
        p["review_count"] = len(p["reviews"])
        p["classes"].sort(key=lambda row: (
            row.get("class_id") or "",
            row.get("course_name") or "",
            row.get("source_file") or "",
            row.get("source_row") or 0
        ))

    return sorted(
        [p for p in profs.values() if p["review_count"] > 0],
        key=lambda p: p["name"]
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request}
    )


@app.post("/api/process")
async def api_process(request: Request):
    try:
        data = await get_request_data(request)
        course_files = data.get("course_files", [])
        prof_files = data.get("prof_files", [])

        parsed_courses, errors = parse_courses_from_files(course_files)
        snapshot = build_dashboard_snapshot(parsed_courses)
        snapshot["parsing_errors"] = errors

        all_courses = [serialize_course(c, cid) for cid, c in parsed_courses.items() if is_valid_course_row(c)]
        groups = group_courses_by_class_id(all_courses)

        all_reviews = load_all_professor_reviews_from_strings({
            f["name"]: f["content"] for f in (prof_files or [])
        })
        professors = build_professor_summary(all_courses, all_reviews)

        return json_response({
            "success": True,
            "state": snapshot,
            "parsed_count": snapshot["course_count"],
            "courses": all_courses,
            "groups": groups,
            "professors": professors
        })
    except Exception as e:
        traceback.print_exc()
        return json_response({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/courses")
async def api_courses(request: Request):
    try:
        data = await get_request_data(request)
        course_files = data.get("course_files", [])
        filters_list = data.get("filters", [])

        parsed_courses, _ = parse_courses_from_files(course_files)
        rows = normalize_course_filter_rows(filters_list)
        visible = visible_course_items(parsed_courses)
        filtered = filter_courses_by_rows(visible, rows) if rows else visible
        courses_list = [serialize_course(course, cid) for cid, course in filtered.items()]

        return json_response({
            "courses": courses_list,
            "groups": group_courses_by_class_id(courses_list),
        })
    except Exception as e:
        traceback.print_exc()
        return json_response({"error": str(e)}, status_code=500)


@app.post("/api/professors")
async def api_professors(request: Request):
    try:
        data = await get_request_data(request)
        course_files = data.get("course_files", [])
        prof_files = data.get("prof_files", [])

        parsed_courses, _ = parse_courses_from_files(course_files)
        all_reviews = load_all_professor_reviews_from_strings({
            f["name"]: f["content"] for f in (prof_files or [])
        })
        courses_list = [serialize_course(course, cid) for cid, course in visible_course_items(parsed_courses).items()]
        profs = build_professor_summary(courses_list, all_reviews)

        return json_response({
            "professors": profs,
            "class_groups": group_courses_by_class_id(courses_list),
        })
    except Exception as e:
        traceback.print_exc()
        return json_response({"error": str(e)}, status_code=500)


@app.post("/api/professor/{name}")
async def api_professor_detail(name: str, request: Request):
    try:
        data = await get_request_data(request)
        prof_files = data.get("prof_files", [])
        api_key = data.get("api_key", "")

        all_reviews = load_all_professor_reviews_from_strings({
            f["name"]: f["content"] for f in (prof_files or [])
        })
        revs = extract_reviews_for_professor(all_reviews, name)
        summary = None

        if api_key and revs:
            review_texts = [r['review'] if isinstance(r, dict) else r for r in revs]
            summary = summarize_professor(review_texts, name, api_key=api_key)

        return json_response({
            "name": name,
            "reviews": revs,
            "summary": summary
        })
    except Exception as e:
        return json_response({"error": str(e)}, status_code=500)


@app.post("/api/filter")
async def api_filter(request: Request):
    try:
        data = await get_request_data(request)
        course_files = data.get("course_files", [])
        prof_files = data.get("prof_files", [])
        filters_list = data.get("filters", [])
        settings = data.get("settings", {})
        api_key = data.get("api_key", "")

        time_from = settings.get("time_from")
        time_to = settings.get("time_to")
        if time_from is not None and time_to is not None and time_from >= time_to:
            return json_response({"error": "محدوده زمانی نامعتبر"}, status_code=400)

        parsed_courses, _ = parse_courses_from_files(course_files)
        rows = normalize_course_filter_rows(filters_list)

        visible = visible_course_items(parsed_courses)

        if not rows or not any(row.get("course_name") for row in rows):
            return json_response({"error": "At least one class is required."}, status_code=400)

        filtered = filter_courses_by_rows(visible, rows)

        scheduler = CourseScheduler(filtered, settings=settings)
        combinations = scheduler.get_top_combinations(
            top_n=settings.get("top_n", 5)
        )

        all_reviews = load_all_professor_reviews_from_strings({
            f["name"]: f["content"] for f in (prof_files or [])
        })

        results = []

        for combo in combinations:
            combo_info = []
            profs_seen = {}

            for cid in combo:
                course = filtered.get(cid, {})
                sched = scheduler.class_schedules.get(cid)
                exam = scheduler.exams.get(cid)
                prof_name = None

                for k in course:
                    if "استاد" in k:
                        prof_name = course[k]
                        break
                item = {
                    "id": cid,
                    "class_id": get_course_class_id(course, cid),
                    "course_name": get_course_name(course),
                    "professor": prof_name,
                    "class_time": serialize_schedule(sched) if sched else None,
                    "exam": serialize_schedule(exam) if exam else None,
                    "source_file": course.get("__source_file"),
                    "source_row": course.get("__source_row")
                }
                combo_info.append(item)

                if prof_name and prof_name not in profs_seen:
                    revs = extract_reviews_for_professor(all_reviews, prof_name)
                    review_texts = [r['review'] if isinstance(r, dict) else r for r in revs]
                    summary = None
                    if api_key and revs:
                        summary = summarize_professor(review_texts, prof_name, api_key=api_key)
                    profs_seen[prof_name] = {
                        "reviews": revs,
                        "summary": summary
                    }
            results.append({
                "combo": combo_info,
                "professors": profs_seen
            })

        return json_response(results)

    except Exception as e:
        traceback.print_exc()
        return json_response({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
