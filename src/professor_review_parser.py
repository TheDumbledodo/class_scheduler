import os
import re

from bs4 import BeautifulSoup


def normalize_name(value):
    if value is None:
        return ""
    text = str(value).strip().replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def professor_name_matches(query, candidate):
    query_norm = normalize_name(query)
    candidate_norm = normalize_name(candidate)

    if not query_norm or not candidate_norm:
        return False

    if query_norm == candidate_norm:
        return True

    query_tokens = {token for token in query_norm.split(" ") if token}
    candidate_tokens = {token for token in candidate_norm.split(" ") if token}

    return bool(query_tokens & candidate_tokens)


def parse_telegram_reviews(html_content):
    """
    Parse a Telegram chat export HTML containing messages with #استاد_شناسی.
    Returns a list of dicts: {'professor': str, 'review': str}
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    messages = soup.find_all('div', class_='message')
    reviews = []

    for msg in messages:
        if 'استاد_شناسی' not in msg.get_text():
            continue

        text_div = msg.find('div', class_='text')
        if not text_div:
            continue

        full_text = text_div.get_text('\n', strip=True)

        prof_match = re.search(r'نام\s*استاد\s*:\s*(.+)', full_text)
        if not prof_match:
            continue

        prof_name = prof_match.group(1).strip()
        prof_name = re.sub(r'\s*[\s<]+.*', '', prof_name)

        course_match = re.search(r'دروس\s*:\s*(.+?)(?:\n|$)', full_text)
        course_name = course_match.group(1).strip() if course_match else ''

        desc_match = re.search(r'توضیحات\s*:\s*(.*?)(?:╭──────────╮|$)', full_text, re.DOTALL)
        review_text = desc_match.group(1).strip() if desc_match else ''

        review_text = re.sub(r'<a href.*?</a>', '', review_text)
        review_text = re.sub(r'╭.*?╯', '', review_text, flags=re.DOTALL)
        review_text = re.sub(r'@wtiau_asatid\s*🎓', '', review_text)
        review_text = review_text.strip()

        if not review_text:
            continue

        combined_review = (
                (f"درس: {course_name} | " if course_name else "") +
                review_text
        )

        reviews.append({
            'professor': prof_name,
            'review': combined_review
        })

    return reviews


def load_all_professor_reviews(professors_folder='uploads/professors'):
    """
    Read all .html files in the folder, parse them as Telegram exports,
    and group reviews by professor name.
    Returns: { professor_name: [review_str, ...] }
    """
    all_reviews = {}
    if not os.path.isdir(professors_folder):
        return all_reviews

    for fname in os.listdir(professors_folder):
        if not fname.lower().endswith('.html'):
            continue
        fpath = os.path.join(professors_folder, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
        except EOFError:
            continue

        parsed = parse_telegram_reviews(content)
        for entry in parsed:
            name = entry['professor']
            all_reviews.setdefault(name, []).append(entry['review'])

    return all_reviews


def extract_reviews_for_professor(all_reviews, professor_name):
    """
    Return the list of review texts for a given professor.
    Tries exact, then case‑insensitive, then substring match.
    """
    if professor_name in all_reviews:
        return all_reviews[professor_name]

    for key, val in all_reviews.items():
        if key.strip().lower() == professor_name.strip().lower():
            return val

    best_match = None
    best_score = 0
    query_tokens = {token for token in normalize_name(professor_name).split(" ") if token}

    for key, val in all_reviews.items():
        candidate_norm = normalize_name(key)
        candidate_tokens = {token for token in candidate_norm.split(" ") if token}

        overlap = len(query_tokens & candidate_tokens)

        if overlap > best_score:
            best_score = overlap
            best_match = val

    if best_match is not None and best_score > 0:
        return best_match

    return []
