import os
import traceback
from collections import defaultdict

from flask import Flask, request, render_template, jsonify, redirect, url_for
from werkzeug.utils import secure_filename

from src.ai_summarizer import summarize_professor
from src.course_filter import filter_courses, FilterMode
from src.course_parser import parse_courses_with_columns
from src.course_scheduler import CourseScheduler
from src.professor_review_parser import load_all_professor_reviews, extract_reviews_for_professor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
COURSES_FOLDER = os.path.join(UPLOAD_FOLDER, "courses")
PROFS_FOLDER = os.path.join(UPLOAD_FOLDER, "professors")
ALLOWED_EXTENSIONS = {'html'}

os.makedirs(COURSES_FOLDER, exist_ok=True)
os.makedirs(PROFS_FOLDER, exist_ok=True)

app = Flask(__name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_list(folder):
    try:
        return sorted([
            f for f in os.listdir(folder)
            if f.lower().endswith('.html')
        ])
    except FileNotFoundError:
        return []


parsed_courses = {}
parsing_errors = []

_course_parse_cache = None
_prof_reviews_cache = {}


def _file_mtime_snapshot(folder):
    snap = {}

    for fname in get_file_list(folder):
        fpath = os.path.join(folder, fname)
        try:
            snap[fname] = os.path.getmtime(fpath)
        except OSError:
            snap[fname] = 0

    return snap


def _load_cached_reviews():
    global _prof_reviews_cache

    prof_files_state = _file_mtime_snapshot(PROFS_FOLDER)
    cache_key = str(sorted(prof_files_state.items()))

    if _prof_reviews_cache.get("key") != cache_key:
        _prof_reviews_cache = {
            "key": cache_key,
            "data": load_all_professor_reviews(PROFS_FOLDER),
        }

    return _prof_reviews_cache["data"]


def parse_all_courses():
    global parsed_courses, parsing_errors, _course_parse_cache

    current_files = _file_mtime_snapshot(COURSES_FOLDER)
    if _course_parse_cache == current_files:
        return

    parsed_courses = {}
    parsing_errors = []

    for fname in get_file_list(COURSES_FOLDER):
        fpath = os.path.join(COURSES_FOLDER, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            parsing_errors.append(f"Could not read {fname}: {str(e)}")
            continue

        try:
            _, courses = parse_courses_with_columns(content)
        except Exception as e:
            parsing_errors.append(f"Error parsing {fname}: {str(e)}")
            continue

        if not courses:
            parsing_errors.append(f"No courses found in {fname}. Check if table id='scrollable' exists.")
            continue

        for idx, course in enumerate(courses):
            unique_id = f"{fname}_{idx}"
            course["__source_file"] = fname
            course["__source_row"] = idx + 1
            course["__source_id"] = unique_id
            course["__professor"] = get_course_professor(course)
            course["__course_name"] = get_course_name(course)
            parsed_courses[unique_id] = course

    _course_parse_cache = current_files


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


def build_dashboard_snapshot():
    parse_all_courses()
    visible_courses = [course for course in parsed_courses.values() if is_valid_course_row(course)]

    prof_values = sorted(set(
        get_course_professor(c) for c in visible_courses
        if get_course_professor(c)
    ))

    course_values = sorted(set(
        get_course_name(c) for c in visible_courses
        if get_course_name(c)
    ))

    return {
        "columns": get_available_filter_columns(parsed_courses),
        "course_files": get_file_list(COURSES_FOLDER),
        "prof_files": get_file_list(PROFS_FOLDER),
        "parsing_errors": parsing_errors,
        "prof_values": prof_values,
        "course_values": course_values,
        "course_count": len(visible_courses)
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


def visible_course_items():
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


@app.route("/")
def index():
    snapshot = build_dashboard_snapshot()
    return render_template("index.html", **snapshot)


@app.route("/upload", methods=["POST"])
def upload():
    if request.is_json:
        pass

    if 'course_files' in request.files:
        files = request.files.getlist('course_files')

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(COURSES_FOLDER, filename))

    if 'prof_files' in request.files:
        files = request.files.getlist('prof_files')

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(PROFS_FOLDER, filename))
    return redirect(url_for("index"))


@app.route("/api/upload", methods=["POST"])
def api_upload():
    try:
        if 'course_files' in request.files:
            for file in request.files.getlist('course_files'):
                if file and allowed_file(file.filename):
                    file.save(os.path.join(COURSES_FOLDER, secure_filename(file.filename)))

        if 'prof_files' in request.files:
            for file in request.files.getlist('prof_files'):
                if file and allowed_file(file.filename):
                    file.save(os.path.join(PROFS_FOLDER, secure_filename(file.filename)))

        snapshot = build_dashboard_snapshot()

        return jsonify({
            "success": True,
            "state": snapshot,
            "parsed_count": snapshot["course_count"]
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/files")
def api_files():
    snapshot = build_dashboard_snapshot()
    return jsonify(snapshot)


@app.route("/api/files/courses/<filename>", methods=["DELETE"])
def delete_course_file(filename):
    filepath = os.path.join(COURSES_FOLDER, filename)

    if os.path.exists(filepath) and allowed_file(filename):
        os.remove(filepath)
        return jsonify({"success": True, "state": build_dashboard_snapshot()})

    return jsonify({"success": False, "error": "File not found"}), 404


@app.route("/api/files/profs/<filename>", methods=["DELETE"])
def delete_prof_file(filename):
    filepath = os.path.join(PROFS_FOLDER, filename)

    if os.path.exists(filepath) and allowed_file(filename):
        os.remove(filepath)
        return jsonify({"success": True, "state": build_dashboard_snapshot()})

    return jsonify({"success": False, "error": "File not found"}), 404


@app.route("/api/files/all", methods=["DELETE"])
def delete_all_files():
    for fname in os.listdir(COURSES_FOLDER):
        fpath = os.path.join(COURSES_FOLDER, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)

    for fname in os.listdir(PROFS_FOLDER):
        fpath = os.path.join(PROFS_FOLDER, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)

    return jsonify({"success": True, "state": build_dashboard_snapshot()})


@app.route("/api/columns")
def api_columns():
    parse_all_courses()
    return jsonify(get_available_filter_columns(parsed_courses))


@app.route("/api/column_values")
def api_column_values():
    column = request.args.get("column", "").strip()

    if not column:
        return jsonify([])
    values = set()

    for c in parsed_courses.values():
        val = c.get(column)
        if val is not None and not isinstance(val, (tuple, list, dict)):
            values.add(str(val))

    return jsonify(sorted(values))


@app.route("/api/courses", methods=["POST"])
def api_courses():
    parse_all_courses()
    data = request.get_json() or {}
    filters_list = data.get("filters", [])
    filters = build_filters(filters_list)
    visible_courses = visible_course_items()
    filtered = filter_courses(visible_courses, filters, FilterMode.ALL_MATCH) if filters else visible_courses
    courses_list = [serialize_course(course, cid) for cid, course in filtered.items()]

    return jsonify(
        courses=courses_list,
        groups=group_courses_by_class_id(courses_list),
    )


@app.route("/api/professors")
def api_professors():
    parse_all_courses()
    all_reviews = _load_cached_reviews()
    courses_list = [serialize_course(course, cid) for cid, course in visible_course_items().items()]
    profs = build_professor_summary(courses_list, all_reviews)

    return jsonify(
        professors=profs,
        class_groups=group_courses_by_class_id(courses_list),
    )


@app.route("/api/professor/<name>", methods=["POST"])
def api_professor_detail(name):
    data = request.get_json() or {}
    api_key = data.get("api_key", "")
    all_reviews = _load_cached_reviews()
    revs = extract_reviews_for_professor(all_reviews, name)
    summary = None

    if api_key and revs:
        summary = summarize_professor(revs, name, api_key=api_key)

    return jsonify({
        "name": name,
        "reviews": revs,
        "summary": summary
    })


@app.route("/api/filter", methods=["POST"])
def api_filter():
    try:
        parse_all_courses()
        data = request.get_json() or {}
        filters_list = data.get("filters", [])
        settings = data.get("settings", {})
        api_key = data.get("api_key", "")

        filters = build_filters(filters_list)
        filter_mode = FilterMode.ALL_MATCH

        visible_courses = visible_course_items()

        if not filters:
            return jsonify(error="At least one filter is required."), 400

        filtered = filter_courses(visible_courses, filters, filter_mode)

        scheduler = CourseScheduler(filtered, settings=settings)
        combinations = scheduler.get_top_combinations(
            top_n=settings.get("top_n", 5)
        )

        all_reviews = load_all_professor_reviews(PROFS_FOLDER)

        results = []

        for combo in combinations:
            combo_info = []
            profs_seen = {}

            for cid in combo:
                course = scheduler.courses.get(cid, {})
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
                    summary = None
                    if api_key and revs:
                        summary = summarize_professor(revs, prof_name, api_key=api_key)
                    profs_seen[prof_name] = {
                        "reviews": revs,
                        "summary": summary
                    }
            results.append({
                "combo": combo_info,
                "professors": profs_seen
            })

        return jsonify(results)

    except Exception as e:
        traceback.print_exc()
        return jsonify(error=str(e)), 500


def build_filters(filters_list):
    filters = {}

    for f in filters_list:
        col = f.get("column", "").strip()
        val = f.get("value", "").strip()

        if not col or not val:
            continue

        if col in ("نام استاد", "استاد", "professor"):
            col = "__professor"
        elif col in ("نام درس", "درس", "course_name"):
            col = "__course_name"

        if ',' in val:
            try:
                parsed_val = [int(v.strip()) for v in val.split(',') if v.strip()]
                current = filters.get(col)

                if current is None:
                    filters[col] = parsed_val
                elif isinstance(current, list):
                    for item in parsed_val:
                        if item not in current:
                            current.append(item)
                else:
                    merged = [current]
                    for item in parsed_val:
                        if item not in merged:
                            merged.append(item)
                    filters[col] = merged
            except ValueError:
                current = filters.get(col)

                if current is None:
                    filters[col] = val
                elif isinstance(current, list):
                    if val not in current:
                        current.append(val)
                else:
                    filters[col] = [current, val] if current != val else current
        else:
            try:
                parsed_val = int(val)
            except ValueError:
                parsed_val = val

            current = filters.get(col)

            if current is None:
                filters[col] = parsed_val
            elif isinstance(current, list):
                if parsed_val not in current:
                    current.append(parsed_val)
            else:
                if current != parsed_val:
                    filters[col] = [current, parsed_val]
    return filters


if __name__ == "__main__":
    parse_all_courses()
    app.run(debug=True)
