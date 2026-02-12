import unittest

from bs4 import BeautifulSoup
from src.course_parser import parse_courses_with_columns, parse_table_columns, parse_value, time_to_minutes

class TestCourseParser(unittest.TestCase):

    def test_time_to_minutes_colon(self):
        self.assertEqual(time_to_minutes("9:30"), 570)
        self.assertEqual(time_to_minutes("0:15"), 15)

    def test_time_to_minutes_dot(self):
        self.assertEqual(time_to_minutes("9.45"), 585)
        self.assertEqual(time_to_minutes("0.05"), 5)

    def test_time_to_minutes_no_separator(self):
        self.assertEqual(time_to_minutes("10"), 600)
        self.assertEqual(time_to_minutes("0"), 0)

    def test_parse_value_numeric(self):
        self.assertEqual(parse_value("42"), 42)

    def test_parse_value_exam_schedule(self):
        value = "1404/10/11 از 11:00 تا 13:00"
        expected = ("1404/10/11", 660, 780)

        self.assertEqual(parse_value(value), expected)

    def test_parse_value_class_schedule(self):
        value = "شنبه 8:30 تا 10:00"
        expected = (0, 510, 600)

        self.assertEqual(parse_value(value), expected)

    def test_parse_value_unknown_format(self):
        self.assertEqual(parse_value("Some text"), "Some text")

    def test_parse_table_columns(self):
        html = """
        <table>
            <thead>
                <tr><th>Code</th><th>Name</th></tr>
            </thead>
        </table>
        """

        soup = BeautifulSoup(html, "html.parser")

        self.assertEqual(parse_table_columns(soup.table), ["Code", "Name"])

    def test_parse_table_single_row(self):
        html = """
        <table id="scrollable">
            <thead>
                <tr><th>Code</th><th>Name</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>123</td>
                    <td>Math</td>
                </tr>
            </tbody>
        </table>
        """

        columns, courses = parse_courses_with_columns(html)
        expected = [{"Code": 123, "Name": "Math"}]

        self.assertEqual(courses, expected)

    def test_parse_courses(self):
        html = """
        <table id="scrollable">
            <thead>
                <tr><th>Code</th><th>Class</th><th>Exam</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>101</td>
                    <td>شنبه 8:00 تا 9:30</td>
                    <td>1404/10/11 از 10:00 تا 12:00</td>
                </tr>
            </tbody>
        </table>
        """

        columns, courses = parse_courses_with_columns(html)

        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0]["Code"], 101)
        self.assertEqual(courses[0]["Class"], (0, 480, 570))
        self.assertEqual(courses[0]["Exam"], ("1404/10/11", 600, 720))

    def test_parse_courses_multiple_rows(self):
        html = """
        <table id="scrollable">
            <thead>
                <tr><th>Code</th><th>Class</th><th>Exam</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>101</td>
                    <td>شنبه 8:00 تا 9:30</td>
                    <td>1404/10/11 از 10:00 تا 12:00</td>
                </tr>
                <tr>
                    <td>102</td>
                    <td>یکشنبه 9:00 تا 10:30</td>
                    <td>1404/10/12 از 13:00 تا 15:00</td>
                </tr>
            </tbody>
        </table>
        """

        columns, courses = parse_courses_with_columns(html)

        self.assertEqual(len(courses), 2)
        self.assertEqual(courses[1]["Code"], 102)
        self.assertEqual(courses[1]["Class"], (1, 540, 630))
        self.assertEqual(courses[1]["Exam"], ("1404/10/12", 780, 900))


if __name__ == "__main__":
    unittest.main()
