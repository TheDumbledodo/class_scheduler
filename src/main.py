import os

from course_parser import parse_courses_with_columns, format_class_schedule, format_exam_schedule
from course_filter import filter_courses
from course_scheduler import CourseScheduler

FILES_DIR = "./files/"

def main():
    files = os.listdir(FILES_DIR)

    course_id = 1
    all_courses = {}

    for path in files:
        abs_path = os.path.join(FILES_DIR, path)

        with open(abs_path, encoding="utf-8") as file:
            columns, courses = parse_courses_with_columns(file.read())

            for course in courses:
                all_courses[course_id] = course
                course_id += 1

    filters = {'كد درس': [7000002171, 7000020525, 1803185334]}
    filtered_courses = filter_courses(all_courses, filters)

    print("Filtered courses:")

    for course_id, course in filtered_courses.items():
        print(f"{course} :{course_id}")

    print()
    print("Class/Exam schedules:")

    scheduler = CourseScheduler(filtered_courses)
    print(scheduler.class_schedules)
    print(scheduler.exams)

    valid_combinations = scheduler.get_top_combinations()

    print()
    print("Valid combinations:")

    for i, combo in enumerate(valid_combinations, start=1):
        print(f"\nCombination {i}:")

        for cid in combo:
            course = filtered_courses[cid]

            class_code = course.get("كد ارائه کلاس درس", "—")
            class_name = course.get("نام درس", "—")

            instructor = course.get("استاد", "—")

            schedule = course.get("زمانبندي تشکيل کلاس") or course.get("نام كلاس درس")
            exam = course.get("زمان امتحان")

            print(f"{class_name} | {instructor} | {format_class_schedule(schedule)} | {class_code}  • ")

if __name__ == '__main__':
    main()
