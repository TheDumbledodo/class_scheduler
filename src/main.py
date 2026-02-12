import os

from course_parser import parse_courses_with_columns, format_class_schedule
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

    class_name_filters = {'نام درس': [
        "معماری کامپیوتری پیشرفته",
        "مدارهای الکتریکی و الکترونیکی",
        "طراحی الگوریتم ها",
        "نظریه زبان ها و ماشین ها",
        "هوش مصنوعی",
        "داده کاوی",
        "آزمایشگاه مدارهای الکتریکی و الکترونیکی",
        "آزمایشگاه فیزیک 2",
        "زبان انگلیسی عمومی-ترکیبی(3)",
    ]}
    class_id_filters = {
        'کد درس': [
            7000038449,
            7000031539,
            7000031559,
            7000031543,
            7000031545,
            7000031565,
            7000031555,
            7000031533,
            99092
        ]
    }
    filtered_courses = filter_courses(all_courses, class_name_filters)

    print(f"Found {len(filtered_courses)} out of {len(all_courses)} courses.")

    scheduler = CourseScheduler(filtered_courses)
    valid_combinations = scheduler.get_top_combinations()

    print()
    print("Valid combinations:")

    for i, combo in enumerate(valid_combinations, start=1):
        print(f"\nCombination {i}:")

        total_credits = 0

        for cid in combo:
            course = filtered_courses[cid]

            class_credit = course.get("تعداد واحد نظری", 0) + course.get("تعداد واحد عملی", 0)
            total_credits += class_credit

            class_code = course.get("کد ارائه کلاس درس", "—")
            class_name = course.get("نام درس", "—")

            instructor = course.get("استاد", "—")

            schedule = course.get("زمانبندی تشکیل کلاس") or course.get("نام کلاس درس")

            print(f"{class_name} | {instructor} | {format_class_schedule(schedule)} | {class_code}  • ")

        print()
        print("Total credit:", total_credits)


if __name__ == '__main__':
    main()
