import re
from collections import defaultdict

from bs4 import BeautifulSoup

from src.persian_utils import normalize_persian

RE_PROFESSOR = re.compile(
    r'نام\s*(?:کامل\s*)?استاد\s*[:\]][^\S\n]*([^\n]+)'
    r'|استاد\s*[:\]][^\S\n]*#([^\n]+)'
    r'|استاد\s+[^\S\n]*#([^\n]+)'
)

RE_COURSE = re.compile(
    r'🔹دروس تدریسی[:\]]\s*(.+?)(?:\n|$)'
    r'|📚\s*دروس\s+(.+?)(?:\n|$)'
    r'|دروس\s*[:\]]\s*(.+?)(?:\n|$)'
)

RE_FOOTER_BLOCKS = re.compile(
    r'(?:^|\n)[^\n]*(?:╭──────────╮|⭕️\s*توجه|❤️لطفا دوستان|———————|👤سایت انجام پروژه)[^\n]*',
    re.MULTILINE,
)

RE_HTML_LINK = re.compile(r'<a\b[^>]*>.*?</a>', re.DOTALL)
RE_TELEGRAM_MENTION = re.compile(r'@\w+')
RE_URL = re.compile(r'https?://\S+|\bwww\.\S*', re.IGNORECASE)
RE_BOX_DRAWING = re.compile(r'[─╭╰╯╮⬅️〰]+')
RE_HASH_TAGS = re.compile(r'#.*$', re.MULTILINE)
RE_HAS_WORD = re.compile(r'\w')

RE_COURSE_SECTION_NOISE = re.compile(
    r'\s*(?:🔹\s*دروس(?:\s*تدریسی)?\s*[:\]]|📚\s*دروس\s*[:\]])\s*.*$'
)

RE_HONORIFICS = re.compile(r'(?:دکتر|استاد)\s*')

MONTH_NUM = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
}
RE_DATE = re.compile(
    r'(\d{1,2})\s*(' + '|'.join(MONTH_NUM) + r')\s*(\d{4})',
    re.IGNORECASE,
)


def normalize(text: str) -> str:
    text = normalize_persian(text)
    return text.lower()


def _parse_date(text: str) -> str:
    m = RE_DATE.search(text)
    if not m:
        return ''

    return f"{int(m.group(1)):02d}.{MONTH_NUM[m.group(2).lower()]:02d}.{m.group(3)}"


def strip_honorifics(name: str) -> str:
    return RE_HONORIFICS.sub('', name).strip()


def _prof_key(raw: str) -> str:
    key = normalize(raw)
    key = strip_honorifics(key)
    key = RE_COURSE_SECTION_NOISE.sub('', key)

    return ' '.join(key.split())


def _extract_professor(text: str) -> str:
    m = RE_PROFESSOR.search(text)

    return next((g for g in m.groups() if g), '').strip() if m else ''


def _extract_course(text: str) -> str:
    m = RE_COURSE.search(text)

    return next((g for g in m.groups() if g), '').strip() if m else ''


def _clean_review(text: str) -> str:
    text = RE_FOOTER_BLOCKS.sub('', text)
    text = RE_HTML_LINK.sub('', text)
    text = RE_TELEGRAM_MENTION.sub('', text)
    text = RE_URL.sub('', text)
    text = RE_BOX_DRAWING.sub('', text)
    text = RE_HASH_TAGS.sub('', text)

    lines = [
        ln.strip()
        for ln in text.splitlines()
        if ln and RE_HAS_WORD.search(ln)
    ]

    return "\n".join(lines)


def parse_telegram_reviews(html_content: str):
    soup = BeautifulSoup(html_content, "lxml")
    reviews = []
    current_date = ''

    for msg in soup.find_all('div', class_='message'):
        if 'service' in (msg.get('class') or ()):
            el = msg.find('div', class_='body details')
            if el:
                d = _parse_date(el.get_text(strip=True))
                if d:
                    current_date = d
            continue

        text_div = msg.find('div', class_='text')
        if not text_div:
            continue

        raw = text_div.get_text('\n', strip=True)

        prof_raw = _extract_professor(raw)
        if not prof_raw:
            continue

        review = _clean_review(raw)
        review_norm = normalize(review)

        if len(review_norm) < 10:
            continue

        reactions = []
        reactions_el = msg.find('span', class_='reactions')
        if reactions_el:
            for r in reactions_el.find_all('span', class_='reaction'):
                emoji_el = r.find('span', class_='emoji')
                count_el = r.find('span', class_='count')

                if emoji_el and count_el:
                    try:
                        reactions.append({
                            'emoji': emoji_el.get_text(strip=True),
                            'count': int(count_el.get_text(strip=True)),
                        })
                    except ValueError:
                        pass

        reviews.append({
            'professor': _prof_key(prof_raw),
            'review': review_norm,
            'course': normalize(_extract_course(raw)),
            'date': current_date,
            'reactions': reactions,
        })

    return reviews


def load_all_professor_reviews_from_strings(files: dict[str, str]) -> dict[str, list]:
    if not files:
        return {}

    all_reviews = {}
    seen = defaultdict(set)

    for fname, content in files.items():
        if not fname.lower().endswith('.html'):
            continue

        for entry in parse_telegram_reviews(content):
            key = entry['professor']
            dup = (entry['review'], entry['course'], entry['date'])

            if dup not in seen[key]:
                seen[key].add(dup)
                all_reviews.setdefault(key, []).append(entry)

    return all_reviews


from rapidfuzz import fuzz


def extract_reviews_for_professor(all_reviews: dict[str, list], name: str) -> list:
    key = _prof_key(name)
    seen = set()

    result = []
    if key in all_reviews:
        for r in all_reviews[key]:
            dup_id = (r.get("review"), r.get("course"), r.get("date"))
            if dup_id not in seen:
                seen.add(dup_id)
                result.append(r)

    qt = set(key.split())

    for k, v in all_reviews.items():
        if k == key:
            continue

        kt = set(k.split())

        token_score = len(qt & kt) / max(len(qt), len(kt))
        char_score = fuzz.token_sort_ratio(key, k) / 100

        score = 0.7 * char_score + 0.3 * token_score

        if score >= 0.70:
            for r in v:
                dup_id = (r.get("review"), r.get("course"), r.get("date"))

                if dup_id in seen:
                    continue

                seen.add(dup_id)
                result.append(r)

    return result
