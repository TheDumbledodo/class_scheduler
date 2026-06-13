const WEEKDAYS = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه'];

const JALALI_MONTHS = [
    'فروردین',
    'اردیبهشت',
    'خرداد',
    'تیر',
    'مرداد',
    'شهریور',
    'مهر',
    'آبان',
    'آذر',
    'دی',
    'بهمن',
    'اسفند'
];

function toPersian(n) {
    return String(n).replace(/[0-9]/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
}

function formatJalaliParts(jy, jm, jd) {
    return `${toPersian(jd)} ${JALALI_MONTHS[jm - 1]} ${toPersian(jy)}`;
}

function gregorianToJalali(gy, gm, gd) {
    const gdm = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
    const gy2 = gm > 2 ? gy + 1 : gy;

    let days =
        355666 +
        365 * gy +
        Math.floor((gy2 + 3) / 4) -
        Math.floor((gy2 + 99) / 100) +
        Math.floor((gy2 + 399) / 400) +
        gd +
        gdm[gm - 1];

    let jy = -1595 + 33 * Math.floor(days / 12053);

    days %= 12053;
    jy += 4 * Math.floor(days / 1461);
    days %= 1461;

    if (days > 365) {
        jy += Math.floor((days - 1) / 365);
        days = (days - 1) % 365;
    }

    const jm = days < 186
        ? 1 + Math.floor(days / 31)
        : 7 + Math.floor((days - 186) / 30);

    const jd = 1 + (days < 186 ? days % 31 : (days - 186) % 30);

    return {jy, jm, jd};
}

function toPersianDate(dateStr) {
    if (!dateStr) return '';

    const m = dateStr.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
    if (!m) return dateStr;

    const {jy, jm, jd} = gregorianToJalali(
        Number(m[3]),
        Number(m[2]),
        Number(m[1])
    );

    return formatJalaliParts(jy, jm, jd);
}

function formatJalaliDate(dateStr) {
    if (!dateStr) return '';

    const m = dateStr.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/);
    if (!m) return dateStr;

    return formatJalaliParts(
        Number(m[1]),
        Number(m[2]),
        Number(m[3])
    );
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatTime(min) {
    const h = Math.floor(min / 60);
    const m = min % 60;
    const t = `${h}:${String(m).padStart(2, '0')}`;
    return toPersian(t).replace(/:۰۰$/, '');
}

function normalizeReview(review) {
    if (typeof review === 'string') {
        const courseMatch = review.match(/درس\s*:\s*([^|]+)/);
        return {
            text: review,
            course: courseMatch ? courseMatch[1].trim() : '',
            date: '',
            reactions: []
        };
    }

    const raw = review?.review || review?.text || '';
    const courseMatch = raw.match(/درس\s*:\s*([^|]+)/);

    return {
        text: raw,
        course: courseMatch ? courseMatch[1].trim() : (review?.course || ''),
        date: review?.date || '',
        reactions: review?.reactions || []
    };
}

function getCourseRowSortKey(item) {
    const time = item.class_time || {};
    const hasDay = time.weekday !== undefined && time.weekday !== null;
    const hasStart = time.start !== undefined && time.start !== null;

    return [
        hasDay ? 0 : 1,
        hasDay ? Number(time.weekday) : 99,
        hasStart ? 0 : 1,
        hasStart ? Number(time.start) : Number.MAX_SAFE_INTEGER,
        String(item.course_name || ''),
        String(item.source_file || ''),
        Number(item.source_row || 0),
        String(item.unique_id || '')
    ];
}

function sortCourseRowItems(items) {
    return [...(items || [])].sort((a, b) => {
        const ak = getCourseRowSortKey(a);
        const bk = getCourseRowSortKey(b);

        for (let i = 0; i < ak.length; i += 1) {
            if (ak[i] < bk[i]) return -1;
            if (ak[i] > bk[i]) return 1;
        }
        return 0;
    });
}

function emptyStateHtml(title) {
    return `<div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="9" y1="21" x2="9" y2="9"/>
            </svg>
            <div class="empty-state-title">${escapeHtml(title)}</div>
        </div>`;
}

function courseMatchesFilter(course, row) {
    const cName = (row.course_name || '').trim();
    const prof = (row.professor || '').trim();

    if (cName && (course.course_name || '') !== cName) return false;
    if (prof && (course.professor || '') !== prof) return false;

    return !!(cName || prof);
}

function getActiveFilters() {
    return state.filters.filter(f => f.course_name).map(f => ({
        course_name: f.course_name,
        professor: f.professor || ''
    }));
}

function isFiltered(course) {
    const filters = getActiveFilters();

    return !filters.length || filters.some(r => courseMatchesFilter(course, r));
}
