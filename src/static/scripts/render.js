async function renderContent() {
    const area = document.getElementById('contentArea');
    if (state.activeTab === 'combos') {
        renderCombos(area);
    } else if (state.activeTab === 'professors') {
        await fetchAndRenderProfessors(area);
    } else if (state.activeTab === 'courses') {
        await fetchAndRenderCourses(area);
    }
}

function renderCombos(area) {
    if (!state.combinations.length) {
        area.innerHTML = emptyStateHtml(state.schedulerRun ? 'هیچ ترکیبی پیدا نشد' : 'هنوز ترکیبی پیدا نشده');
        return;
    }

    area.innerHTML = `<div class="combo-grid">${state.combinations.map((combo, ci) => renderComboCard(combo, ci)).join('')}</div>`;
    bindProfChips(area);
}

function renderComboCard(combo, idx) {
    const days = new Set(combo.combo.map(c => c.class_time?.weekday).filter(d => d !== undefined));

    const daysStr = [...days].sort().map(d => WEEKDAYS[d]).join('، ');
    const daysCount = days.size;

    const cells = combo.combo.map(c => {
        const classTime = c.class_time ? `${WEEKDAYS[c.class_time.weekday]} ${formatTime(c.class_time.start)}–${formatTime(c.class_time.end)}` : '—';
        const exam = c.exam ? `${formatJalaliDate(c.exam.date)} ساعت ${formatTime(c.exam.start)} تا ${formatTime(c.exam.end)}` : '—';

        return `
                    <div>
                        <div class="course-name">${escapeHtml(c.course_name)}</div>
                        <div class="course-meta">${escapeHtml(c.class_id || c.id || '')}</div>
                    </div>
                    <div>
                        <div class="course-time">${escapeHtml(classTime)}</div>
                        <div class="course-exam">امتحان: ${escapeHtml(exam)}</div>
                    </div>
                    <div>
                        <span class="prof-chip" data-prof="${escapeHtml(c.professor || 'نامشخص')}">${escapeHtml(c.professor || 'نامشخص')}</span>
                    </div>`;
    }).join('');

    return `
            <div class="combo-card">
                <div class="combo-card-header">
                    <span class="combo-badge">ترکیب ${toPersian(idx + 1)}</span>
                    <span class="combo-days"><span class="day-count">${toPersian(daysCount)} روز</span> ${escapeHtml(daysStr || 'بدون روز')}</span>
                </div>
                <div class="combo-body">
                    <div class="combo-table">${cells}</div>
                </div>
            </div>`;
}

function formatGroupSubtitle(group, mode) {
    if (mode === 'professors') {
        return group.name || group.professor_name || 'استاد نامشخص';
    }
    return group.course_names && group.course_names.length ? group.course_names.join('، ') : group.course_name;
}

function renderGroupCard(group, mode) {
    const subtitle = formatGroupSubtitle(group, mode);

    const rows = sortCourseRowItems(group.items).map(item => {
        const classTime = item.class_time ? `${WEEKDAYS[item.class_time.weekday]} ${formatTime(item.class_time.start)}–${formatTime(item.class_time.end)}` : '—';
        const exam = item.exam ? `${formatJalaliDate(item.exam.date)} ساعت ${formatTime(item.exam.start)} تا ${formatTime(item.exam.end)}` : '—';

        if (mode === 'professors') {
            return `
                    <div class="course-row">
                        <div>
                            <div class="course-time">${escapeHtml(classTime)}</div>
                            <div class="course-exam">امتحان: ${escapeHtml(exam)}</div>
                        </div>
                        <div>
                            <span class="prof-chip" data-prof="${escapeHtml(item.professor || 'نامشخص')}">${escapeHtml(item.professor || 'نامشخص')}</span>
                        </div>
                        <div></div>
                    </div>`;
        }
        return `
                <div class="course-row">
                    <div>
                        <div class="course-time">${escapeHtml(classTime)}</div>
                        <div class="course-exam">امتحان: ${escapeHtml(exam)}</div>
                    </div>
                    <div>
                        <span class="prof-chip" data-prof="${escapeHtml(item.professor || 'نامشخص')}">${escapeHtml(item.professor || 'نامشخص')}</span>
                    </div>
                </div>`;
    }).join('');

    return `
            <div class="combo-card">
                <div class="combo-card-header">
                    <div class="course-name">
                        <span>${escapeHtml(subtitle)}</span>
                        <span class="course-count">${toPersian(group.item_count || 0)} مورد</span>
                    </div>
                </div>
                <div class="combo-body">${rows}</div>
            </div>`;
}

async function fetchAndRenderProfessors(area) {
    const professors = state.cachedProfessors || [];
    const shown = professors.filter(p => p.classes?.some(c => isFiltered(c)));

    document.getElementById('profsCount').textContent = toPersian(shown.length);

    if (!shown.length) {
        area.innerHTML = emptyStateHtml('هیچ استادی یافت نشد');
        return;
    }
    area.innerHTML = `<div class="combo-grid">${shown.map(prof => renderProfessorReviewCard(prof)).join('')}</div>`;
    bindProfChips(area);
}

async function fetchAndRenderCourses(area) {
    if (!state.cachedCourses.length) {
        area.innerHTML = emptyStateHtml('هنوز فایلی بارگذاری نشده');
        return;
    }

    const filtered = state.cachedCourses.filter(isFiltered);
    const groups = groupCourseItems(filtered);
    document.getElementById('coursesCount').textContent = toPersian(filtered.length);

    if (!groups.length) {
        area.innerHTML = emptyStateHtml('درسی یافت نشد');
        return;
    }
    area.innerHTML = `<div class="combo-grid">${groups.map(group => renderGroupCard(group, 'courses')).join('')}</div>`;
    bindProfChips(area);
}

function groupCourseItems(items) {
    const map = {};

    for (const item of items) {
        const key = item.class_id || item.id || item.unique_id || 'نامشخص';
        if (!map[key]) map[key] = [];
        map[key].push(item);
    }
    const sorted = Object.entries(map).sort(([a], [b]) => a.localeCompare(b));

    return sorted.map(([classId, groupItems]) => {
        groupItems.sort((a, b) => {
            const aDay = a.class_time?.weekday ?? 99;
            const bDay = b.class_time?.weekday ?? 99;
            if (aDay !== bDay) return aDay - bDay;
            const aStart = a.class_time?.start ?? Number.MAX_SAFE_INTEGER;
            const bStart = b.class_time?.start ?? Number.MAX_SAFE_INTEGER;
            if (aStart !== bStart) return aStart - bStart;
            return (a.course_name || '').localeCompare(b.course_name || '');
        });

        const courseNames = [...new Set(groupItems.map(i => i.course_name).filter(Boolean))].sort();
        const professors = [...new Set(groupItems.map(i => i.professor).filter(Boolean))].sort();

        return {
            class_id: classId,
            course_name: courseNames[0] || 'Unknown',
            course_names: courseNames,
            professors: professors,
            items: groupItems,
            item_count: groupItems.length
        };
    });
}

function bindProfChips(area) {
    area.querySelectorAll('.prof-chip').forEach(chip => {
        const name = chip.dataset.prof;
        const cached = state.profSummaries[name];

        if (cached && cached.reviews && cached.reviews.length) {
            chip.addEventListener('click', () => openProfModal(name));
            return
        }
        chip.classList.add('disabled');
    });
}

function renderProfessorReviewCard(prof) {
    const reviews = prof.reviews || [];
    return `
            <div class="combo-card" style="width:fit-content">
                <div class="combo-card-header">
                    <span class="combo-badge">${escapeHtml(prof.name)}</span>
                    <span class="combo-score"><span class="day-count">${toPersian(prof.review_count || 0)} نظر</span></span>
                </div>
                <div class="combo-body">
                    ${reviews.length ? `<div class="reviews-list">${reviews.map(review => {

        const normalized = normalizeReview(review);
        return `
                            <div class="review-item">
                                <div class="review-header">
                                    <span class="review-course">${escapeHtml(normalized.course || 'نظریه')}</span>
                                    ${normalized.date ? `<span class="review-date">${toPersianDate(normalized.date)}</span>` : ''}
                                </div>
                                ${normalized.text ? `<div class="review-text">${escapeHtml(normalized.text).replace(/\n/g, '<br>')}</div>` : ''}
                                ${normalized.reactions && normalized.reactions.length ? `<div class="review-reactions">${normalized.reactions.map(r => `<span class="reaction-badge">${r.emoji}\uFE0F ${toPersian(r.count)}</span>`).join('')}</div>` : ''}
                            </div>`;
    }).join('')}</div>` : '<div class="review-item"><div class="review-text">نظری ثبت نشده است.</div></div>'}
                </div>
            </div>`;
}

async function openProfModal(name) {
    document.getElementById('profModalTitle').textContent = name;

    const body = document.getElementById('profModalBody');
    const apiKey = document.getElementById('apiKey').value.trim();
    const cached = state.profSummaries[name];
    const needsFetch = apiKey && cached && cached.reviews && cached.reviews.length && !cached._fetched;

    if (needsFetch) {
        renderProfModalBody(body, {reviews: cached.reviews, summary: null});
        body.insertAdjacentHTML('afterbegin', '<div class="loading-row"><svg class="ai-icon pulse" viewBox="0 0 24 24" width="18" height="18"><circle cx="12" cy="12" r="4.5" fill="#888"/></svg><span>خلاصه هوش مصنوعی...</span></div>');
        document.getElementById('profModal').classList.add('open');

        try {
            const resp = await fetch(`/api/professor/${encodeURIComponent(name)}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    prof_files: state.reviewFiles,
                    api_key: apiKey || '',
                    model: state.settings.model
                })
            });
            const data = await resp.json();
            const revs = (data.reviews && data.reviews.length) ? data.reviews : (cached?.reviews || []);

            state.profSummaries[name] = {
                reviews: revs,
                summary: data.summary || null,
                _fetched: true
            };
            renderProfModalBody(body, {reviews: revs, summary: data.summary || null});

        } catch (err) {
            state.profSummaries[name] = {
                reviews: cached?.reviews || [],
                summary: null,
                _fetched: true
            };
            renderProfModalBody(body, cached || {reviews: [], summary: null});
        }
        return
    }
    document.getElementById('profModal').classList.add('open');
    renderProfModalBody(body, cached || {reviews: [], summary: null});
}

function renderProfModalBody(body, data) {
    const reviews = (data.reviews || []).map(normalizeReview);
    const summary = data.summary;

    body.innerHTML = `
            ${summary ? `<div class="ai-summary"><div class="ai-label"><svg viewBox="0 0 24 24" width="14" height="14" style="vertical-align:middle;margin-inline-end:4px"><circle cx="12" cy="12" r="4.5" fill="#888"/></svg>خلاصه هوش مصنوعی</div><div class="ai-text">${escapeHtml(summary)}</div></div>` : ''}

            ${reviews.length ? `<div class="section-label" style="margin-bottom:8px;color:#000">نظرات دانشجویان</div>
            <div class="reviews-list">${reviews.map(r => `
                <div class="review-item">
                    <div class="review-header">
                        <span class="review-course">${escapeHtml(r.course || 'درس نامشخص')}</span>
                        ${r.date ? `<span class="review-date">${toPersianDate(r.date)}</span>` : ''}
                    </div>
                    ${r.text ? `<div class="review-text">${escapeHtml(r.text).replace(/\n/g, '<br>')}</div>` : ''}
                    ${r.reactions && r.reactions.length ? `<div class="review-reactions">${r.reactions.map(rt => `<span class="reaction-badge">${rt.emoji}\uFE0F ${toPersian(rt.count)}</span>`).join('')}</div>` : ''}
                </div>`).join('')}</div>` : ''}
        `;
}

bootstrap().catch(console.error);
