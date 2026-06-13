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
    if (state.lastError) {
        area.innerHTML = errorStateHtml(state.lastError);
        return;
    }
    if (!state.combinations.length) {
        area.innerHTML = emptyStateHtml(state.schedulerRun ? 'هیچ ترکیبی پیدا نشد' : 'هنوز ترکیبی پیدا نشده');
        return;
    }

    area.innerHTML = `<div class="combo-grid">${state.combinations.map((combo, ci) => renderComboCard(combo, ci)).join('')}</div>`;
    area.querySelectorAll('.prof-chip').forEach(chip => {
        chip.addEventListener('click', () => openProfModal(chip.dataset.prof));
    });
}

function renderComboCard(combo, idx) {
    const days = new Set(combo.combo.map(c => c.class_time?.weekday).filter(d => d !== undefined));

    const daysStr = [...days].sort().map(d => WEEKDAYS[d]).join('، ');
    const daysCount = days.size;

    const cells = combo.combo.map(c => {
        const classTime = c.class_time ? `${WEEKDAYS[c.class_time.weekday]} ${formatTime(c.class_time.start)}–${formatTime(c.class_time.end)}` : '—';
        const exam = c.exam ? `${c.exam.date} ${formatTime(c.exam.start)}–${formatTime(c.exam.end)}` : '—';

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

function getProfessorScopes() {
    const scopes = new Set(Object.keys(state.profSummaries || {}));
    state.filters
        .filter(f => f.professor)
        .forEach(f => scopes.add(f.professor));

    return [...scopes].filter(Boolean);
}

function resolveProfessorSummaryFromState(name) {
    const summaries = state.profSummaries || {};
    if (summaries[name]) {
        return {name, value: summaries[name]};
    }

    for (const [key, value] of Object.entries(summaries)) {
        if (professorNameMatches(name, key)) {
            return {name: key, value};
        }
    }
    return null;
}

function filterProfessorsByScope(professors) {
    const scopes = getProfessorScopes();
    if (!scopes.length) return professors;

    return professors.filter(prof => scopes.some(scope => professorNameMatches(scope, prof.name)));
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
        const exam = item.exam ? `${item.exam.date} ${formatTime(item.exam.start)}–${formatTime(item.exam.end)}` : '—';

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
                        <span class="course-count">(${toPersian(group.item_count || 0)} مورد)</span>
                    </div>
                </div>
                <div class="combo-body">${rows}</div>
            </div>`;
}

async function fetchAndRenderProfessors(area) {
    const professors = filterProfessorsByScope(state.cachedProfessors || []);
    document.getElementById('profsCount').textContent = toPersian(professors.length);

    if (!professors.length) {
        area.innerHTML = emptyStateHtml('هیچ استادی یافت نشد');
        return;
    }
    area.innerHTML = `<div class="combo-grid">${professors.map(prof => renderProfessorReviewCard(prof)).join('')}</div>`;
    bindProfChips(area);
}

async function fetchAndRenderCourses(area) {
    if (!state.cachedCourses.length) {
        area.innerHTML = emptyStateHtml('هنوز فایلی بارگذاری نشده');
        return;
    }

    const filters = state.filters.map(f => ({
        course_name: f.course_name,
        professor: f.professor || ''
    }));

    const hasFilters = filters.some(f => f.course_name);
    const filtered = hasFilters
        ? state.cachedCourses.filter(c => filters.some(r => courseMatchesFilter(c, r)))
        : state.cachedCourses;

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
        chip.addEventListener('click', () => openProfModal(chip.dataset.prof));
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
    body.innerHTML = '<div class="loading-row"><span class="spinner"></span><span>در حال بارگذاری...</span></div>';

    document.getElementById('profModal').classList.add('open');

    const apiKey = document.getElementById('apiKey').value.trim();
    const local = resolveProfessorSummaryFromState(name);
    if (local) {
        renderProfModalBody(body, {
            reviews: local.value.reviews || [],
            summary: null
        });
    }

    if (apiKey || !local) {
        try {
            const resp = await fetch(`/api/professor/${encodeURIComponent(name)}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    prof_files: state.reviewFiles,
                    api_key: apiKey || ''
                })
            });
            const data = await resp.json();
            renderProfModalBody(body, data);
        } catch (err) {
            if (!local) {
                body.innerHTML = '<div style="color:var(--bad)">خطا در دریافت اطلاعات</div>';
            }
        }
    }
}

function renderProfModalBody(body, data) {
    const reviews = (data.reviews || []).map(normalizeReview);
    const summary = data.summary;

    body.innerHTML = `
            <div style="color:var(--text3);margin-bottom:12px;">${toPersian(reviews.length)} نظر برای این استاد ثبت شده است.</div>

            ${summary ? `<div class="ai-summary"><div class="ai-label">خلاصه هوش مصنوعی</div><div class="ai-text">${escapeHtml(summary)}</div></div>` : ''}

            ${reviews.length ? `<div class="section-label" style="margin-bottom:8px;">نظرات دانشجویان</div>
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
