import unittest

from src.course_scheduler import CourseScheduler

class TestCourseScheduler(unittest.TestCase):

    def setUp(self):
        self.courses = {
            1: {"نام كلاس درس": (0, 540, 600), "زمان امتحان": ("1404/10/10", 540, 600)},
            2: {"نام كلاس درس": (0, 610, 670), "زمان امتحان": ("1404/10/11", 540, 600)},
            3: {"نام كلاس درس": (1, 540, 600), "زمان امتحان": ("1404/10/10", 600, 660)},
            4: {"نام كلاس درس": (1, 600, 660), "زمان امتحان": ("1404/10/12", 540, 600)},
        }
        self.scheduler = CourseScheduler(self.courses)

    def test_init_collects_valid_courses(self):
        self.assertEqual(set(self.scheduler.courses.keys()), {1, 2, 3, 4})
        self.assertEqual(len(self.scheduler.class_schedules), 4)
        self.assertEqual(len(self.scheduler.exams), 4)

    def test_extract_class_schedule(self):
        schedule = CourseScheduler.extract_class_schedule(1, self.courses[1])
        self.assertEqual(schedule["weekday"], 0)
        self.assertEqual(schedule["start"], 540)
        self.assertEqual(schedule["end"], 600)

    def test_extract_exam(self):
        exam = CourseScheduler.extract_exam(1, self.courses[1])
        self.assertEqual(exam["date"], "1404/10/10")
        self.assertEqual(exam["start"], 540)
        self.assertEqual(exam["end"], 600)

    def test_schedule_overlaps(self):
        a = {"weekday": 0, "start": 540, "end": 600}
        b = {"weekday": 0, "start": 590, "end": 650}
        c = {"weekday": 1, "start": 540, "end": 600}

        self.assertTrue(CourseScheduler.schedule_overlaps(a, b))
        self.assertFalse(CourseScheduler.schedule_overlaps(a, c))

    def test_exam_overlaps(self):
        a = {"date": "1404/10/10", "start": 540, "end": 600}
        b = {"date": "1404/10/10", "start": 590, "end": 650}
        c = {"date": "1404/10/11", "start": 540, "end": 600}

        self.assertTrue(CourseScheduler.exam_overlaps(a, b))
        self.assertFalse(CourseScheduler.exam_overlaps(a, c))

    def test_has_conflict(self):
        combo1 = (1, 2)
        self.assertFalse(self.scheduler.has_conflict(combo1))

        combo2 = (1, 3)
        self.assertFalse(self.scheduler.has_conflict(combo2))

        self.scheduler.class_schedules[2]["start"] = 550
        self.scheduler.class_schedules[2]["end"] = 570
        self.assertTrue(self.scheduler.has_conflict((1, 2)))

    def test_get_chain_score(self):
        combo = (1, 2)
        score = self.scheduler.get_chain_score(combo)
        self.assertEqual(score, 1)

        combo2 = (1, 3)
        score2 = self.scheduler.get_chain_score(combo2)
        self.assertEqual(score2, 0)

    def test_sort_combo(self):
        combo = (3, 1, 2, 4)
        sorted_combo = self.scheduler.sort_combo(combo)
        self.assertEqual(sorted_combo, (1, 2, 3, 4))

    def test_get_valid_combinations(self):
        valid_combos = self.scheduler.get_top_combinations()

        for combo in valid_combos:
            self.assertFalse(self.scheduler.has_conflict(combo))

if __name__ == "__main__":
    unittest.main()
