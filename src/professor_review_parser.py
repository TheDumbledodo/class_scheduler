import re
from collections import defaultdict
from bs4 import BeautifulSoup

ARABIC_TO_PERSIAN_MAP = str.maketrans({
    'ي': 'ی',
    'آ': 'ا',
})

RE_DIACRITICS = re.compile(r'[\u064B-\u065F\u0670]')
RE_TATWEEL = re.compile(r'\u0640+')
RE_INVISIBLE_CHARS = re.compile(r'[\u200B-\u200F\u2028-\u202F\u2060-\u2064\uFEFF\u00AD]')
RE_SEPARATORS = re.compile(r'[_\-]+')
RE_MULTIPLE_SPACES = re.compile(r' {2,}')

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

# --- course noise ---
RE_COURSE_SECTION_NOISE = re.compile(
    r'\s*(?:🔹\s*دروس(?:\s*تدریسی)?\s*[:\]]|📚\s*دروس\s*[:\]])\s*.*$'
)


def normalize(text: str) -> str:
    if not text:
        return ''

    text = RE_DIACRITICS.sub('', text)
    text = RE_TATWEEL.sub('', text)
    text = RE_INVISIBLE_CHARS.sub(' ', text)
    text = text.translate(ARABIC_TO_PERSIAN_MAP)
    text = RE_SEPARATORS.sub(' ', text)
    text = RE_MULTIPLE_SPACES.sub(' ', text)

    return text.strip().lower()


def _prof_key(raw: str) -> str:
    key = normalize(raw)
    key = RE_COURSE_SECTION_NOISE.sub('', key)

    return RE_MULTIPLE_SPACES.sub(' ', key).strip()


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

    for msg in soup.find_all('div', class_='message'):
        if 'service' in (msg.get('class') or ()):
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

        reviews.append({
            'professor': _prof_key(prof_raw),
            'review': review_norm,
            'course': normalize(_extract_course(raw)),
            'reactions': []
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
            dup = (entry['review'], entry['course'])

            if dup not in seen[key]:
                seen[key].add(dup)
                all_reviews.setdefault(key, []).append(entry)

    return all_reviews


def extract_reviews_for_professor(all_reviews: dict[str, list], name: str) -> list:
    key = _prof_key(name)

    if key in all_reviews:
        return all_reviews[key]

    qt = set(key.split())
    best, best_n = [], 0

    for k, v in all_reviews.items():
        n = len(qt & set(k.split()))
        if n > best_n:
            best_n, best = n, v

    return best
