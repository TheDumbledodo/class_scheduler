const state = {
    filters: [],
    allowedDays: new Set([0, 1, 2, 3, 4, 5]),
    combinations: [],
    activeTab: 'courses',
    processing: false,
    schedulerRun: false,
    settings: {
        top_n: 5,
        chainWeight: 5,
        gapThreshold: 45,
        fewDaysWeight: true,
        spreadExams: false,
        ignoreExamConflicts: false,
        timeFrom: 7 * 60,
        timeTo: 20 * 60,
        model: 'deepseek/deepseek-chat'
    },
    profSummaries: {},
    snapshot: {},
    courseFiles: [],
    reviewFiles: [],
    cachedCourses: [],
    cachedProfessors: []
};

const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const reviewUploadZone = document.getElementById('reviewUploadZone');
const reviewFileInput = document.getElementById('reviewFileInput');
const courseFilterSelect = document.getElementById('courseFilter');

async function bootstrap() {
    bindStaticControls();
    renderCourseFilterRows();
    updateRunButtonState();
    await renderContent();
}

function applySnapshot(snapshot) {
    state.snapshot = snapshot || {};
    state.schedulerRun = false;

    populateFilterDropdowns(state.snapshot);
    renderFileLists();

    document.getElementById('coursesCount').textContent = toPersian(state.snapshot.course_count || 0);
}

function populateFilterDropdowns(snapshot) {
    const data = snapshot || state.snapshot || {};
    const courseSelect = document.getElementById('courseFilter');

    courseSelect.innerHTML = '<option value="">+ افزودن درس</option>' +
        (data.course_values || []).map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');

    renderCourseFilterRows();
}

function renderFileLists() {
    const courseList = document.getElementById('fileList');
    const reviewList = document.getElementById('reviewFileList');

    courseList.innerHTML = (state.courseFiles || []).map(f => `
            <div class="file-item">
              <span class="file-name">${escapeHtml(f.name)}</span>
              <span class="file-remove" data-file="${escapeHtml(f.name)}" data-type="course">×</span>
            </div>`
    ).join('');

    reviewList.innerHTML = (state.reviewFiles || []).map(f => `
            <div class="file-item">
              <span class="file-name">${escapeHtml(f.name)}</span>
              <span class="file-remove" data-file="${escapeHtml(f.name)}" data-type="prof">×</span>
            </div>`
    ).join('');

    document.querySelectorAll('.file-remove').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();

            const filename = btn.dataset.file;
            const type = btn.dataset.type;

            const fileKey = type === 'course' ? 'courseFiles' : 'reviewFiles';
            state[fileKey] = state[fileKey].filter(f => f.name !== filename);

            await processUploadedFiles();
        });
    });
}

function bindStaticControls() {
    uploadZone.addEventListener('click', () => fileInput.click());
    reviewUploadZone.addEventListener('click', () => reviewFileInput.click());

    uploadZone.addEventListener('dragover', e => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
    uploadZone.addEventListener('drop', async e => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        await handleFiles(e.dataTransfer.files, 'course');
    });

    reviewUploadZone.addEventListener('dragover', e => {
        e.preventDefault();
        reviewUploadZone.classList.add('drag-over');
    });

    reviewUploadZone.addEventListener('dragleave', () => reviewUploadZone.classList.remove('drag-over'));
    reviewUploadZone.addEventListener('drop', async e => {
        e.preventDefault();
        reviewUploadZone.classList.remove('drag-over');
        await handleFiles(e.dataTransfer.files, 'prof');
    });

    fileInput.addEventListener('change', async e => handleFiles(e.target.files, 'course'));
    reviewFileInput.addEventListener('change', async e => handleFiles(e.target.files, 'prof'));

    courseFilterSelect.addEventListener('change', e => {
        const courseName = e.target.value;
        if (courseName) {
            addCourseFilter(courseName);
            e.target.value = '';
        }
    });

    document.querySelectorAll('#dayChips .chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const day = parseInt(chip.dataset.day);
            chip.classList.toggle('active');

            if (state.allowedDays.has(day))
                state.allowedDays.delete(day);
            else
                state.allowedDays.add(day);
        });
    });

    document.getElementById('timeFrom').addEventListener('change', e => {
        state.settings.timeFrom = parseInt(e.target.value);
    });
    document.getElementById('timeTo').addEventListener('change', e => {
        state.settings.timeTo = parseInt(e.target.value);
    });

    ['chainWeight', 'gapThreshold'].forEach(id => {
        const element = document.getElementById(id);
        const valSpan = document.getElementById(id + 'Val');

        element.addEventListener('input', () => {
            valSpan.textContent = toPersian(element.value);
            state.settings[id] = parseInt(element.value);
        });
    });

    document.getElementById('fewDaysWeight').addEventListener('change', e => state.settings.fewDaysWeight = e.target.checked);

    document.getElementById('topN').addEventListener('input', e => {
        state.settings.top_n = parseInt(e.target.value) || 5;

        document.getElementById('topNVal').textContent = toPersian(e.target.value);
    });
    document.getElementById('spreadExams').addEventListener('change', e => state.settings.spreadExams = e.target.checked);
    document.getElementById('ignoreExamConflicts').addEventListener('change', e => state.settings.ignoreExamConflicts = e.target.checked);

    const aiModel = document.getElementById('aiModel');
    if (aiModel) {
        aiModel.addEventListener('change', e => state.settings.model = e.target.value);
    }

    document.querySelectorAll('.results-tab').forEach(tab => {
        tab.addEventListener('click', async () => {
            document.querySelectorAll('.results-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            state.activeTab = tab.dataset.tab;
            await renderContent();
        });
    });

    document.getElementById('runBtn').addEventListener('click', runScheduler);

    document.getElementById('closeModal').addEventListener('click', () => {
        document.getElementById('profModal').classList.remove('open');
    });
    document.getElementById('profModal').addEventListener('click', e => {
        if (e.target === document.getElementById('profModal')) {
            document.getElementById('profModal').classList.remove('open');
        }
    });

    document.getElementById('advancedToggle').addEventListener('click', function () {
        this.classList.toggle('open');
        document.getElementById('advancedCollapsible').classList.toggle('open');
    });

    document.getElementById('clearAll').addEventListener('click', async () => {
        state.filters = [];
        state.combinations = [];
        state.schedulerRun = false;

        renderCourseFilterRows();
        updateRunButtonState();
        await renderContent();
        updateCounts();
    });

}

async function handleFiles(fileList, type) {
    const files = [];

    for (const file of fileList) {
        if (!file.name.toLowerCase().endsWith('.html')) {
            alert(`فایل ${file.name} فرمت معتبری ندارد. فقط فایل‌های HTML پشتیبانی می‌شوند.`);
            return;
        }
        const content = await file.text();
        files.push({name: file.name, content});
    }

    if (files.length === 0) {
        alert('هیچ فایلی انتخاب نشده است.');
        return;
    }

    const fileKey = type === 'course' ? 'courseFiles' : 'reviewFiles';
    const existing = state[fileKey];
    const existingNames = new Set(existing.map(f => f.name));

    for (const f of files) {
        if (existingNames.has(f.name)) {
            const idx = existing.findIndex(e => e.name === f.name);
            existing[idx] = f;
            continue
        }
        existing.push(f);
    }
    await processUploadedFiles();
}

async function processUploadedFiles() {
    if (!state.courseFiles.length && !state.reviewFiles.length) {
        state.cachedCourses = [];
        state.cachedProfessors = [];
        state.combinations = [];
        state.filters = [];
        state.schedulerRun = false;
        state.profSummaries = {};
        state.snapshot = {};

        renderFileLists();
        renderCourseFilterRows();
        updateRunButtonState();
        await renderContent();

        updateCounts();
        return;
    }

    try {
        const resp = await fetch('/api/process', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                course_files: state.courseFiles,
                prof_files: state.reviewFiles
            })
        });
        const data = await resp.json();

        if (data.success) {
            state.cachedCourses = data.courses || [];
            state.cachedProfessors = data.professors || [];
            state.profSummaries = {};

            for (const prof of state.cachedProfessors) {
                state.profSummaries[prof.name] = {
                    reviews: prof.reviews || [],
                    summary: null,
                    _fetched: false,
                };
            }

            applySnapshot(data.state || {});
            updateCounts();

            fileInput.value = '';
            reviewFileInput.value = '';

            await renderContent();
            return
        }
        alert('خطا در بارگذاری: ' + (data.error || 'نامشخص'));

    } catch (err) {
        alert('خطا در ارتباط با سرور');
    }
}

async function addCourseFilter(courseName) {
    if (state.filters.find(f => f.course_name === courseName)) return;
    state.filters.push({course_name: courseName, professor: ''});

    renderCourseFilterRows();
    updateRunButtonState();
    updateCounts();

    await renderContent();
}

function renderCourseFilterRows() {
    const container = document.getElementById('courseFilterRows');
    const courseProfMap = (state.snapshot && state.snapshot.course_professors) || {};

    container.innerHTML = state.filters.map((f, i) => {
        const profs = courseProfMap[f.course_name] || [];
        const profOptions = profs.map(p =>
            `<option value="${escapeHtml(p)}" ${f.professor === p ? 'selected' : ''}>${escapeHtml(p)}</option>`
        ).join('');

        const hasProf = f.professor && profs.length;
        const profSelect = profs.length ? `
                <select class="course-filter-prof-select ${hasProf ? 'has-value' : ''}" data-idx="${i}" aria-label="استاد">
                    <option value="">هر استادی</option>
                    ${profOptions}
                </select>` : '';
        return `

            <div class="course-filter-row" data-idx="${i}">
                <span class="course-filter-name" title="${escapeHtml(f.course_name)}">${escapeHtml(f.course_name)}</span>
                ${profSelect}
                <button class="btn-remove-filter" data-idx="${i}" title="حذف" aria-label="حذف درس">×</button>
            </div>`;
    }).join('');

    container.querySelectorAll('.btn-remove-filter').forEach(btn => {
        btn.addEventListener('click', async () => {
            state.filters.splice(parseInt(btn.dataset.idx), 1);

            renderCourseFilterRows();
            updateRunButtonState();
            updateCounts();

            await renderContent();
        });
    });

    container.querySelectorAll('.course-filter-prof-select').forEach(sel => {
        sel.addEventListener('change', async e => {
            const idx = parseInt(e.target.dataset.idx);
            state.filters[idx].professor = e.target.value;
            e.target.classList.toggle('has-value', !!e.target.value);

            updateCounts();
            await renderContent();
        });
    });
}

async function runScheduler() {
    if (state.processing || !state.filters.length) {
        return;
    }
    if (state.settings.timeFrom >= state.settings.timeTo) {
        state.combinations = [];
        state.schedulerRun = true;
        state.activeTab = 'combos';

        await renderContent();

        state.processing = false;
        updateRunButtonState();
        return;
    }
    state.processing = true;

    const btn = document.getElementById('runBtn');
    btn.disabled = true;

    const filters = state.filters.map(f => ({
        course_name: f.course_name,
        professor: f.professor || ''
    }));

    const settings = {
        top_n: state.settings.top_n,
        chain_weight: state.settings.chainWeight,
        gap_threshold: state.settings.gapThreshold,
        few_days_weight: state.settings.fewDaysWeight ? 3 : 0,
        spread_exams: state.settings.spreadExams,
        ignore_exam_conflicts: state.settings.ignoreExamConflicts,
        time_from: state.settings.timeFrom,
        time_to: state.settings.timeTo,
        allowed_days: [...state.allowedDays]
    };

    const api_key = document.getElementById('apiKey').value.trim();

    try {
        const resp = await fetch('/api/filter', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                course_files: state.courseFiles,
                prof_files: state.reviewFiles,
                filters, settings, api_key
            })
        });

        const results = await resp.json();
        if (results.error) {
            state.combinations = [];
            state.schedulerRun = true;
            state.activeTab = 'combos';

            await renderContent();
            return;
        }

        state.schedulerRun = true;
        state.combinations = results;
        state.profSummaries = {};

        results.forEach(combo => {
            Object.assign(state.profSummaries, combo.professors);
        });

        document.getElementById('combosCount').textContent = toPersian(results.length);
        updateCounts();

        document.querySelectorAll('.results-tab').forEach(t => t.classList.remove('active'));
        document.querySelector('[data-tab="combos"]').classList.add('active');

        state.activeTab = 'combos';
        await renderContent();

    } catch (err) {
        state.combinations = [];
        state.schedulerRun = true;
        state.activeTab = 'combos';

        await renderContent();
    } finally {
        btn.disabled = false;
        state.processing = false;
        updateRunButtonState();
    }
}

function updateCounts() {
    const courses = state.cachedCourses.filter(isFiltered);
    document.getElementById('coursesCount').textContent = toPersian(courses.length);

    const profs = (state.cachedProfessors || []).filter(p => p.classes?.some(c => isFiltered(c)));
    document.getElementById('profsCount').textContent = toPersian(profs.length);

    document.getElementById('combosCount').textContent = toPersian(state.combinations.length);
}

function updateRunButtonState() {
    const btn = document.getElementById('runBtn');
    const disabled = state.processing || !state.filters.length;
    btn.disabled = disabled;
    btn.title = disabled ? 'برای یافتن ترکیب‌ها باید حداقل یک فیلتر اضافه کنید' : 'یافتن ترکیب‌های برتر';
}
