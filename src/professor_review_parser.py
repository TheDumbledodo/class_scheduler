import os
import re
from difflib import SequenceMatcher
from bs4 import BeautifulSoup

_AR2FA = str.maketrans({
    'ك': 'ک', '\u0643': 'ک',
    'ي': 'ی', 'ى': 'ی', 'ئ': 'ی',
    'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا',
    'ة': 'ه',
    'ؤ': 'و',
})

_RE_DIACRITICS = re.compile(r'[\u064B-\u065F\u0670]')
_RE_TATWEEL = re.compile(r'\u0640+')
_RE_INVIS = re.compile(r'[\u200B-\u200F\u2028-\u202F\u2060-\u2064\uFEFF\u00AD]')
_RE_SEPARATORS = re.compile(r'[_\-]+')
_RE_SPACES = re.compile(r' {2,}')


def normalize(text: str) -> str:
    if not text:
        return ''
    text = _RE_DIACRITICS.sub('', text)
    text = _RE_TATWEEL.sub('', text)
    text = _RE_INVIS.sub(' ', text)
    text = text.translate(_AR2FA)
    text = re.sub(r'\bاله\b', 'الله', text)
    text = text.replace('مقالله', 'مقاله')
    text = _RE_SEPARATORS.sub(' ', text)
    text = _RE_SPACES.sub(' ', text)
    return text.strip().lower()


_RE_PROF = re.compile(
    r'نام\s*(?:کامل\s*)?استاد\s*[:\]][^\S\n]*([^\n]+)'
    r'|استاد\s*[:\]][^\S\n]*#([^\n]+)'
    r'|استاد\s+[^\S\n]*#([^\n]+)'
)

_RE_COURSE = re.compile(
    r'🔹دروس تدریسی[:\]]\s*(.+?)(?:\n|$)'
    r'|📚\s*دروس\s+(.+?)(?:\n|$)'
    r'|دروس\s*[:\]]\s*(.+?)(?:\n|$)'
)

_RE_HONORIFICS = re.compile(r'(?:دکتر|استاد|مهندس)\s*')
_RE_COURSE_NOISE = re.compile(
    r'\s*(?:🔹\s*دروس(?:\s*تدریسی)?\s*[:\]]|📚\s*دروس\s*[:\]])\s*.*$'
)

_MONTH_NUM = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
}
_RE_DATE = re.compile(
    r'(\d{1,2})\s*(' + '|'.join(_MONTH_NUM) + r')\s*(\d{4})',
    re.IGNORECASE,
)

_RE_FOOTER = re.compile(
    r'(?:^|\n)[^\n]*(?:'
    r'╭──────────╮|⭕️\s*توجه|❤️لطفا دوستان|———————|👤سایت انجام پروژه'
    r')[^\n]*',
    re.MULTILINE,
)

_RE_REVIEW_BODY = re.compile(
    r'(?:🔺توضیحات تکمیلی|📝توضیحات|توضیحات)\s*[:\]]\s*(.+)',
    re.DOTALL,
)
_RE_POS = re.compile(r'✅\s*نکات مثبت[:\]]*(.*?)(?:❌|$)', re.DOTALL)
_RE_NEG = re.compile(r'❌\s*نکات منفی[:\]]*(.*?)$', re.DOTALL)
_RE_FB = re.compile(r'🔻نام کامل استاد[^\n]*')

_RE_LINK = re.compile(r'<a\b[^>]*>.*?</a>', re.DOTALL)
_RE_MENTION = re.compile(r'@\w+')
_RE_URL = re.compile(r'https?://\S+|\bwww\.\S*|(?<!\w)www(?!\w)', re.IGNORECASE)
_RE_BOX = re.compile(r'[─╭╰╯╮⬅️〰]+')
_RE_HASH = re.compile(r'#.*$', re.MULTILINE)
_RE_WORD = re.compile(r'\w')

_BODY_ANCHORS = ('استاد', 'دروس', 'رشته')


def _parse_date(text: str) -> str:
    m = _RE_DATE.search(text)
    if not m:
        return ''
    return f"{int(m.group(1)):02d}.{_MONTH_NUM[m.group(2).lower()]:02d}.{m.group(3)}"


def _extract_professor(text: str) -> str:
    m = _RE_PROF.search(text)
    return next((g for g in m.groups() if g), '').strip() if m else ''


def _extract_course(text: str) -> str:
    m = _RE_COURSE.search(text)
    return next((g for g in m.groups() if g), '').strip() if m else ''


def _clean_lines(text: str) -> str:
    """Drop blank and emoji/symbol-only lines."""
    return '\n'.join(
        ln for ln in (ln.strip() for ln in text.split('\n'))
        if ln and _RE_WORD.search(ln)
    )


def _extract_review(text: str) -> str:
    cleaned = _RE_FOOTER.sub('', text)

    m = _RE_REVIEW_BODY.search(cleaned)
    if m:
        result = m.group(1).strip()
    else:
        mp = _RE_POS.search(cleaned)
        if mp:
            mn = _RE_NEG.search(cleaned)
            result = f"{mp.group(1).strip()}\n{mn.group(1).strip()}" if mn else mp.group(1).strip()
        else:
            mf = _RE_FB.search(cleaned)
            if mf:
                result = mf.group(0).strip()
            else:
                lines = _clean_lines(cleaned).split('\n')
                cut = 0
                for i, ln in enumerate(lines):
                    if any(kw in ln for kw in _BODY_ANCHORS):
                        cut = i + 1
                result = '\n'.join(lines[cut:]).strip()

    result = _RE_LINK.sub('', result)
    result = _RE_MENTION.sub('', result)
    result = _RE_URL.sub('', result)
    result = _RE_BOX.sub('', result)
    result = _clean_lines(result)
    return _RE_HASH.sub('', result).strip()


def strip_honorifics(name: str) -> str:
    """Remove common Persian honorifics (دکتر, استاد, مهندس) and #/@ from a name."""
    name = _RE_HONORIFICS.sub('', name)
    name = re.sub(r'[#@]', '', name)
    return name.strip()


def _prof_key(raw: str) -> str:
    """Normalize a raw professor name into a stable, searchable dict key."""
    key = normalize(raw)
    key = strip_honorifics(key)
    key = _RE_COURSE_NOISE.sub('', key)
    return _RE_SPACES.sub(' ', key).strip()


def parse_telegram_reviews(html_content: str) -> list[dict]:
    """
    Parse a Telegram HTML export.
    Returns list of dicts: {professor, review, course, date, reactions}.
    All text fields are fully normalized for keyword search.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    reviews: list[dict] = []
    current_date = ''

    for msg in soup.find_all('div', class_='message'):
        if 'service' in msg.get('class', []):
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

        raw_prof = _extract_professor(raw)
        if not raw_prof:
            continue

        review = _extract_review(raw)
        if len(review) < 10:
            continue

        reactions = []
        reactions_el = msg.find('span', class_='reactions')
        if reactions_el:
            for r in reactions_el.find_all('span', class_='reaction'):
                e_el = r.find('span', class_='emoji')
                c_el = r.find('span', class_='count')
                if e_el and c_el:
                    try:
                        reactions.append({
                            'emoji': e_el.get_text(strip=True),
                            'count': int(c_el.get_text(strip=True)),
                        })
                    except ValueError:
                        pass

        reviews.append({
            'professor': _prof_key(raw_prof),
            'review': normalize(review),
            'course': normalize(_extract_course(raw)),
            'date': current_date,
            'reactions': reactions,
        })

    return reviews


def load_all_professor_reviews(folder: str = 'uploads/professors') -> dict[str, list]:
    """
    Parse every .html in *folder*, group by professor key, dedup, and merge
    name variants with ≥50 % token overlap.
    Returns {professor_key: [entry_dict, ...]}
    """
    if not os.path.isdir(folder):
        return {}

    all_reviews: dict[str, list] = {}
    seen: dict[str, set] = {}

    for fname in os.listdir(folder):
        if not fname.lower().endswith('.html'):
            continue
        try:
            with open(os.path.join(folder, fname), encoding='utf-8') as fh:
                entries = parse_telegram_reviews(fh.read())
        except OSError:
            continue

        for entry in entries:
            key = entry['professor']
            dup = (entry['review'], entry['course'], entry['date'])
            if dup not in seen.setdefault(key, set()):
                seen[key].add(dup)
                all_reviews.setdefault(key, []).append(entry)

    keys = list(all_reviews)
    tokens = {k: set(k.split()) for k in keys}
    merged: set[str] = set()

    for i, ki in enumerate(keys):
        if ki in merged:
            continue
        ti = tokens[ki]
        for kj in keys[i + 1:]:
            if kj in merged:
                continue
            tj = tokens[kj]
            ovlp = len(ti & tj)
            token_ratio = ovlp / max(len(ti), len(tj)) if ovlp else 0
            char_ratio = SequenceMatcher(None, ki, kj).ratio()
            if (ovlp and token_ratio > 0.5) or char_ratio >= 0.85:
                src, dst = sorted((ki, kj), key=lambda k: len(all_reviews[k]))
                merged.add(src)
                seen_dst = seen.setdefault(dst, set())
                for e in all_reviews[src]:
                    dk = (e['review'], e['course'], e['date'])
                    if dk not in seen_dst:
                        seen_dst.add(dk)
                        all_reviews[dst].append(e)

    for k in merged:
        del all_reviews[k]

    return all_reviews


def extract_reviews_for_professor(all_reviews: dict[str, list], name: str) -> list:
    """
    Return reviews for *name*. Exact normalized key first,
    then best token-overlap fallback.
    """
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
