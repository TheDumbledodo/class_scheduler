const WEEKDAYS = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه'];

function toPersian(n) {
    return String(n).replace(/[0-9]/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
}

function toPersianDate(dateStr) {
    if (!dateStr) return '';
    const m = dateStr.match(/(\d{2})\.(\d{2})\.(\d{4})/);

    if (!m) return dateStr;
    let d = parseInt(m[1]), mon = parseInt(m[2]), y = parseInt(m[3]);

    const gdm = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
    const gy2 = mon > 2 ? y + 1 : y;

    let days = 355666 + 365 * y + Math.floor((gy2 + 3) / 4) - Math.floor((gy2 + 99) / 100) + Math.floor((gy2 + 399) / 400) + d + gdm[mon - 1];
    let jy = -1595 + 33 * Math.floor(days / 12053);

    days %= 12053;
    jy += 4 * Math.floor(days / 1461);
    days %= 1461;

    if (days > 365) {
        jy += Math.floor((days - 1) / 365);
        days = (days - 1) % 365;
    }
    let jm = days < 186 ? 1 + Math.floor(days / 31) : 7 + Math.floor((days - 186) / 30);
    let jd = 1 + (days < 186 ? days % 31 : (days - 186) % 30);

    const months = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'];
    return `${toPersian(jd)} ${months[jm - 1]} ${toPersian(jy)}`;
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
    return toPersian(t);
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

function errorStateHtml(message) {
    return `<div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--bad)">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <div class="empty-state-title" style="color:var(--bad)">خطا</div>
            <div class="empty-state-sub" style="color:var(--bad);white-space:pre-wrap;text-align:right;direction:rtl;">${escapeHtml(message)}</div>
        </div>`;
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
