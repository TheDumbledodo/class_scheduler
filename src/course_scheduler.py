from collections import defaultdict
from itertools import combinations, product


def _normalize_class_schedule(course_id, course):
    """Return the class schedule dict if valid."""
    sched = course.get("زمانبندی تشکیل کلاس") or course.get("نام کلاس درس")

    if isinstance(sched, dict):
        if "weekday" not in sched or "start" not in sched or "end" not in sched:
            return None

        return {
            "id": course_id,
            "weekday": sched["weekday"],
            "start": sched["start"],
            "end": sched["end"]
        }

    if isinstance(sched, (tuple, list)) and len(sched) == 3:
        weekday, start, end = sched
        return {
            "id": course_id,
            "weekday": weekday,
            "start": start,
            "end": end
        }

    return None


def _normalize_exam_schedule(course_id, course):
    """Return the exam schedule dict if valid."""
    exam = course.get("زمان امتحان")

    if isinstance(exam, dict):
        if "date" not in exam or "start" not in exam or "end" not in exam:
            return None

        return {
            "id": course_id,
            "date": exam["date"],
            "start": exam["start"],
            "end": exam["end"]
        }

    if isinstance(exam, (tuple, list)) and len(exam) == 3:
        date, start, end = exam
        return {
            "id": course_id,
            "date": date,
            "start": start,
            "end": end
        }

    return None


class CourseScheduler:

    def __init__(self, courses, settings=None):
        self.courses = {}
        self.settings = settings or {}

        for course_id, course in courses.items():
            sched = course.get("زمانبندی تشکیل کلاس") or course.get("نام کلاس درس")

            if not sched:
                continue

            self.courses[course_id] = course

        self.class_schedules = self.collect_by_id(self.extract_class_schedule)
        self.exams = self.collect_by_id(self.extract_exam)

        self.groups = defaultdict(list)

        for course_id, course in self.courses.items():
            field_id = course.get("کد درس") or course.get("كد درس") or course.get("courseCode")

            if field_id is None:
                field_id = course_id

            self.groups[field_id].append(course_id)

    def collect_by_id(self, extractor):
        result = {}

        for course_id, course in self.courses.items():
            item = extractor(course_id, course)

            if item is None:
                continue

            result[course_id] = item

        return result

    @staticmethod
    def extract_class_schedule(course_id, course):
        return _normalize_class_schedule(course_id, course)

    @staticmethod
    def extract_exam(course_id, course):
        return _normalize_exam_schedule(course_id, course)

    def get_top_combinations(self, top_n=3):
        groups = list(self.groups.values())

        allowed_days = self.settings.get("allowed_days")
        time_from = self.settings.get("time_from")
        time_to = self.settings.get("time_to")
        gap_threshold = self.settings.get("gap_threshold", 45)
        chain_weight = self.settings.get("chain_weight", 5)
        few_days_weight = self.settings.get("few_days_weight", 3)
        spread_exams = self.settings.get("spread_exams", False)

        valid_groups = []
        for group in groups:
            filtered = []

            for cid in group:
                sched = self.class_schedules.get(cid)

                if not sched:
                    continue

                if allowed_days and sched["weekday"] not in allowed_days:
                    continue

                if time_from is not None and sched["start"] < time_from:
                    continue

                if time_to is not None and sched["end"] > time_to:
                    continue

                filtered.append(cid)

            if filtered:
                valid_groups.append(filtered)

        if not valid_groups:
            return []

        all_valid_combos = []
        for combo in product(*valid_groups):

            if self.has_conflict(combo):
                continue

            score = self.calculate_score(
                combo, chain_weight, gap_threshold, few_days_weight, spread_exams
            )
            all_valid_combos.append((score, combo))

        all_valid_combos.sort(key=lambda x: x[0], reverse=True)

        return [
            self.sort_combo(combo)
            for score, combo in all_valid_combos[:top_n]
        ]

    def calculate_score(self, combo, chain_weight, gap_threshold, few_days_weight, spread_exams):
        score = 0
        days_used = set()

        for i, cid_i in enumerate(combo):
            s_i = self.class_schedules[cid_i]
            days_used.add(s_i["weekday"])

            for j in range(i + 1, len(combo)):
                cid_j = combo[j]
                s_j = self.class_schedules[cid_j]

                if s_i["weekday"] != s_j["weekday"]:
                    continue

                gap = abs(s_j["start"] - s_i["end"])

                if gap <= gap_threshold:
                    score += chain_weight

        score += (6 - len(days_used)) * few_days_weight

        if spread_exams:
            dates = set()

            for cid in combo:
                exam = self.exams.get(cid)
                if exam:
                    dates.add(exam["date"])

            score += len(dates)

        return score

    def get_chain_score(self, combo, gap_threshold=45):
        score = 0

        for i, cid_i in enumerate(combo):
            s_i = self.class_schedules[cid_i]

            for j in range(i + 1, len(combo)):
                cid_j = combo[j]
                s_j = self.class_schedules[cid_j]

                if s_i["weekday"] != s_j["weekday"]:
                    continue

                gap = abs(s_j["start"] - s_i["end"])

                if gap <= gap_threshold:
                    score += 1

        return score

    def has_conflict(self, combo):
        ignore_conflicts = self.settings.get("ignore_exam_conflicts", False)

        for a, b in combinations(combo, 2):
            if self.schedule_overlaps(self.class_schedules[a], self.class_schedules[b]):
                return True

            exam_a = self.exams.get(a)
            exam_b = self.exams.get(b)

            if not ignore_conflicts and exam_a and exam_b and self.exam_overlaps(exam_a, exam_b):
                return True

        return False

    def sort_combo(self, combo):
        return tuple(sorted(combo, key=self.schedule_sort_key))

    def schedule_sort_key(self, course_id):
        schedule = self.class_schedules[course_id]

        return schedule["weekday"], schedule["start"]

    @staticmethod
    def schedule_overlaps(a, b):
        if a["weekday"] != b["weekday"]:
            return False

        return max(a["start"], b["start"]) < min(a["end"], b["end"])

    @staticmethod
    def exam_overlaps(a, b):
        if a["date"] != b["date"]:
            return False

        return max(a["start"], b["start"]) < min(a["end"], b["end"])
