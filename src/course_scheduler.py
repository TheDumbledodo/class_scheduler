from itertools import combinations

class CourseScheduler:

    def __init__(self, courses):
        self.courses = {}

        for course_id, course in courses.items():
            has_schedule = course.get("زمانبندي تشکيل کلاس") or course.get("نام كلاس درس")
            has_exam = course.get("زمان امتحان")

            if not has_schedule or not has_exam:
                continue

            self.courses[course_id] = course

        self.class_schedules = self.collect_by_id(self.extract_class_schedule)
        self.exams = self.collect_by_id(self.extract_exam)

    def collect_by_id(self, extractor):
        result = {}

        for course_id, course in self.courses.items():
            item = extractor(course_id, course)

            if item is None:
                continue

            result[course_id] = item

        return result

    def get_valid_combinations(self):
        course_ids = list(self.courses.keys())

        r = len(course_ids)

        best_score = -1
        best_combinations = []

        for combo in combinations(course_ids, r):

            if self.has_conflict(combo):
                continue

            score = self.get_chain_score(combo)

            if score > best_score:
                best_score = score
                best_combinations = [combo]

            elif score == best_score:
                best_combinations.append(combo)

        return [self.sort_combo(combo) for combo in best_combinations]

    def get_chain_score(self, combo):
        score = 0

        for a, b in combinations(combo, 2):
            if self.schedule_chainable(
                    self.class_schedules[a],
                    self.class_schedules[b]
            ):
                score += 1

        return score

    def has_conflict(self, combo):
        for a, b in combinations(combo, 2):
            if self.schedule_overlaps(
                    self.class_schedules[a],
                    self.class_schedules[b]
            ):
                return True

            if self.exam_overlaps(
                    self.exams[a],
                    self.exams[b]
            ):
                return True

        return False

    def sort_combo(self, combo):
        return tuple(sorted(combo, key=self.schedule_sort_key))

    def schedule_sort_key(self, course_id):
        schedule = self.class_schedules[course_id]

        return schedule["weekday"], schedule["start"]

    @staticmethod
    def extract_exam(course_id, course):
        exam = course.get("زمان امتحان")

        if not exam or len(exam) < 3:
            return None

        date, start, end = exam

        return {
            "id": course_id,
            "date": date,
            "start": start,
            "end": end
        }

    @staticmethod
    def exam_overlaps(a, b):
        if a["date"] != b["date"]:
            return False

        return max(a["start"], b["start"]) < min(a["end"], b["end"])

    @staticmethod
    def schedule_overlaps(a, b):
        if a["weekday"] != b["weekday"]:
            return False

        return max(a["start"], b["start"]) < min(a["end"], b["end"])

    @staticmethod
    def extract_class_schedule(course_id, course):
        schedule = course.get("زمانبندي تشکيل کلاس") or course.get("نام كلاس درس")

        if not schedule or len(schedule) < 3:
            return None

        weekday, start, end = schedule

        return {
            "id": course_id,
            "weekday": weekday,
            "start": start,
            "end": end
        }

    @staticmethod
    def schedule_chainable(a, b):
        if a["weekday"] != b["weekday"]:
            return False

        gap = abs(b["start"] - a["end"])
        return gap <= 30
