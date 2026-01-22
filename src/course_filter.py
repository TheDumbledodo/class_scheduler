from enum import Enum, auto

class FilterMode(Enum):
    ANY_MATCH = auto()
    ALL_MATCH = auto()

def filter_courses(courses, filters, mode=FilterMode.ALL_MATCH):
    filtered_courses = {}

    for course_id, course in courses.items():

        match mode:
            case FilterMode.ALL_MATCH:
                if all(matches_filter(course.get(k), v) for k, v in filters.items()):
                    filtered_courses[course_id] = course

            case FilterMode.ANY_MATCH:
                if any(matches_filter(course.get(k), v) for k, v in filters.items()):
                    filtered_courses[course_id] = course

    return filtered_courses

def matches_filter(value, filter_value):
    if isinstance(filter_value, (list, set, tuple)):
        return value in filter_value

    return value == filter_value
