import re

ARABIC_TO_PERSIAN = str.maketrans({
    'ك': 'ک',
    'ي': 'ی',
})

RE_DIACRITICS = re.compile(r'[\u064B-\u065F\u0670]')
RE_TATWEEL = re.compile(r'\u0640+')
RE_INVISIBLE = re.compile(r'[\u200B-\u200F\u2028-\u202F\u2060-\u2064\uFEFF\u00AD]')
RE_SEPARATORS = re.compile(r'[_\-]+')
RE_SPACES = re.compile(r' {2,}')


def normalize_persian(text: str) -> str:
    if not text:
        return ''

    text = RE_DIACRITICS.sub('', text)
    text = RE_TATWEEL.sub('', text)
    text = RE_INVISIBLE.sub(' ', text)
    text = text.translate(ARABIC_TO_PERSIAN)
    text = RE_SEPARATORS.sub(' ', text)
    text = RE_SPACES.sub(' ', text)

    return text.strip()
