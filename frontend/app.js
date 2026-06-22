/* ═══════════════════════════════════════════════════════════════
   TalentRank AI — Frontend Logic
   ═══════════════════════════════════════════════════════════════ */

// ─── Global State ───────────────────────────────────────────────
const state = {
    parsedJob: null,
    extractedProfile: null,
    currentAssessment: null,
    assessmentResult: null,
    assessedCandidates: [],  // [{name, email, profile, assessment_percentage}]
};

// Mock demo candidates for live demo
const DEMO_CANDIDATES = [
    {
        name: "Siddharth Rao",
        email: "siddharth.rao@example.com",
        profile: {
            name: "Siddharth Rao", email: "siddharth.rao@example.com",
            core_skills: ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "AWS"],
            years_experience: 6,
            projects: [
                { name: "HighThroughput Event Pipeline", description: "Async event-driven pipeline handling 50M events/day with asyncpg and Redis streams", tech_stack: ["Python", "asyncpg", "Redis", "Kafka"] },
                { name: "Database Sharding System", description: "Implemented horizontal sharding for PostgreSQL with 99.99% uptime", tech_stack: ["PostgreSQL", "Python", "pgbouncer"] }
            ],
            experience_history: [
                { company: "Zepto", role: "Senior Backend Engineer", duration_months: 30, highlights: ["Led DB optimization reducing p99 latency by 60%", "Built async task system on Celery+Redis"] },
                { company: "Razorpay", role: "Backend Engineer", duration_months: 24, highlights: ["Designed payment gateway microservices"] }
            ]
        },
        assessment_percentage: 96.2
    },
    {
        name: "Priya Sharma",
        email: "priya.sharma@example.com",
        profile: {
            name: "Priya Sharma", email: "priya.sharma@example.com",
            core_skills: ["Python", "Django", "MySQL", "Docker", "Kubernetes"],
            years_experience: 4,
            projects: [
                { name: "E-commerce Order System", description: "Built scalable order management for 1M+ daily orders", tech_stack: ["Django", "MySQL", "Celery"] }
            ],
            experience_history: [
                { company: "Meesho", role: "Backend Engineer", duration_months: 36, highlights: ["Optimized DB queries reducing load by 45%"] }
            ]
        },
        assessment_percentage: 78.5
    },
    {
        name: "Arjun Mehta",
        email: "arjun.mehta@example.com",
        profile: {
            name: "Arjun Mehta", email: "arjun.mehta@example.com",
            core_skills: ["Node.js", "Express", "MongoDB", "TypeScript"],
            years_experience: 3,
            projects: [
                { name: "Real-time Chat API", description: "WebSocket-based chat system for 100K concurrent users", tech_stack: ["Node.js", "Socket.io", "MongoDB", "Redis"] }
            ],
            experience_history: [
                { company: "Freshworks", role: "Full Stack Developer", duration_months: 30, highlights: ["Built real-time features for CRM product"] }
            ]
        },
        assessment_percentage: 65.0
    },
    {
        name: "Ananya Krishnan",
        email: "ananya.k@example.com",
        profile: {
            name: "Ananya Krishnan", email: "ananya.k@example.com",
            core_skills: ["Go", "gRPC", "PostgreSQL", "Kubernetes", "AWS", "Terraform"],
            years_experience: 7,
            projects: [
                { name: "Microservices Platform", description: "Built Go-based microservices framework used by 12 internal teams", tech_stack: ["Go", "gRPC", "Kubernetes", "Helm"] },
                { name: "Infrastructure-as-Code Pipeline", description: "Automated multi-region AWS deployment with Terraform", tech_stack: ["Terraform", "AWS", "Python"] }
            ],
            experience_history: [
                { company: "Flipkart", role: "Staff Engineer", duration_months: 42, highlights: ["Designed platform reducing deployment time by 70%"] },
                { company: "Ola", role: "Senior Engineer", duration_months: 30, highlights: ["Led Go microservices migration from monolith"] }
            ]
        },
        assessment_percentage: 91.5
    }
];

// ─── Toast Notifications ────────────────────────────────────────
function toast(msg, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    el.innerHTML = `<span>${icons[type]||'ℹ️'}</span><span>${msg}</span>`;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(() => el.remove(), 4000);
}

// ─── Tab Switching ──────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
    });
});

// ─── Loading State Helper ───────────────────────────────────────
function setLoading(textEl, loaderEl, btnEl, loading, loadingText = 'Processing...', defaultText = '') {
    if (loading) {
        btnEl.disabled = true;
        textEl.textContent = loadingText;
        loaderEl.classList.remove('hidden');
    } else {
        btnEl.disabled = false;
        textEl.textContent = defaultText || textEl.dataset.default || textEl.textContent;
        loaderEl.classList.add('hidden');
    }
}

// ─── Update candidate count badge ───────────────────────────────
function updateCandCount() {
    document.getElementById('cand-count-badge').textContent = state.assessedCandidates.length;
}

/* ═══════════════════════════════════════════════════════════════
   TAB 1: JOB SETUP
   ═══════════════════════════════════════════════════════════════ */

const parseJdBtn = document.getElementById('parse-jd-btn');
const parseJdText = document.getElementById('parse-jd-text');
const parseJdLoader = document.getElementById('parse-jd-loader');

parseJdBtn.addEventListener('click', async () => {
    const jd = document.getElementById('jd-input').value.trim();
    if (!jd) { toast('Please enter a job description first.', 'error'); return; }

    setLoading(parseJdText, parseJdLoader, parseJdBtn, true, 'Parsing with AI...');
    try {
        const res = await fetch('/api/v1/parse-job', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_description: jd })
        });
        if (!res.ok) throw new Error(await res.text());
        state.parsedJob = await res.json();
        renderParsedJob(state.parsedJob);
        toast('Job profile parsed successfully!', 'success');
    } catch (e) {
        toast(`Error: ${e.message}`, 'error');
    } finally {
        setLoading(parseJdText, parseJdLoader, parseJdBtn, false, 'Parse with AI');
    }
});

function renderParsedJob(job) {
    const out = document.getElementById('job-parsed-output');
    out.classList.remove('empty-placeholder');
    const seniorityColor = { junior: 'tag-success', mid: 'tag-warn', senior: 'tag-accent', lead: 'tag-primary' };
    const sc = seniorityColor[job.seniority_level] || 'tag-primary';

    const skills = [...(job.tech_stack || []), ...(job.core_competencies || [])];
    const skillTags = skills.slice(0, 12).map(s => `<span class="tag tag-primary">${s}</span>`).join('');
    const reqTags = (job.critical_requirements || []).map(r => `<span class="tag tag-accent">⚠ ${r}</span>`).join('');

    out.innerHTML = `
        <div class="parsed-job">
            <div class="parsed-role">${job.role_title || 'Unknown Role'}</div>
            <div class="meta-pair">
                <span>Domain</span><span class="meta-value">${job.domain || 'Tech'}</span>
                <span>Seniority</span><span class="tag ${sc}">${job.seniority_level || 'mid'}</span>
                <span>Exp</span><span class="meta-value">${job.years_experience?.min || 0}–${job.years_experience?.preferred || 5} yrs</span>
            </div>
            <div>
                <div class="parsed-section-label">Tech Stack & Competencies</div>
                <div class="tag-cloud">${skillTags}</div>
            </div>
            <div>
                <div class="parsed-section-label">Critical Requirements</div>
                <div class="tag-cloud">${reqTags}</div>
            </div>
        </div>`;
}

/* ═══════════════════════════════════════════════════════════════
   TAB 2: ASSESS CANDIDATES
   ═══════════════════════════════════════════════════════════════ */

// ─── Upload Zone ────────────────────────────────────────────────
const uploadZone = document.getElementById('upload-zone');
const resumeFile = document.getElementById('resume-file');
const uploadClick = document.getElementById('upload-click');

uploadClick.addEventListener('click', () => resumeFile.click());
uploadZone.addEventListener('click', () => resumeFile.click());

uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFileUpload(files[0]);
});

resumeFile.addEventListener('change', e => {
    if (e.target.files.length > 0) handleFileUpload(e.target.files[0]);
});

async function handleFileUpload(file) {
    const progress = document.getElementById('upload-progress');
    const bar = document.getElementById('upload-bar');
    const statusText = document.getElementById('upload-status');

    progress.classList.remove('hidden');
    bar.style.width = '0%';
    statusText.textContent = 'Reading file...';

    // Animate progress
    let pct = 0;
    const interval = setInterval(() => {
        pct = Math.min(pct + Math.random() * 15, 85);
        bar.style.width = pct + '%';
    }, 200);

    try {
        statusText.textContent = 'Extracting resume data with AI...';
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch('/api/v1/upload-resume', { method: 'POST', body: formData });
        if (!res.ok) throw new Error(await res.text());

        state.extractedProfile = await res.json();

        clearInterval(interval);
        bar.style.width = '100%';
        statusText.textContent = '✅ Profile extracted!';

        setTimeout(() => {
            progress.classList.add('hidden');
            renderProfilePreview(state.extractedProfile);
        }, 700);

        toast(`Resume extracted: ${state.extractedProfile.name}`, 'success');
    } catch (e) {
        clearInterval(interval);
        toast(`Extraction failed: ${e.message}`, 'error');
        progress.classList.add('hidden');
    }
}

function renderProfilePreview(profile) {
    const card = document.getElementById('profile-preview-card');
    const preview = document.getElementById('profile-preview');
    card.style.display = 'block';

    const skills = (profile.core_skills || []).slice(0, 8).map(s => `<span class="tag tag-primary">${s}</span>`).join('');
    const projects = (profile.projects || []).slice(0, 3).map(p => `
        <div class="project-card">
            <div class="project-name">🔧 ${p.name}</div>
            <div class="project-desc">${p.description || ''}</div>
            <div class="tag-cloud" style="margin-top:0.4rem">${(p.tech_stack||[]).map(t=>`<span class="tag tag-accent">${t}</span>`).join('')}</div>
        </div>`).join('');

    preview.innerHTML = `
        <div class="profile-grid">
            <div>
                <div class="profile-name">${profile.name || 'Unknown'}</div>
                <div class="profile-email">${profile.email || ''}</div>
            </div>
            <div class="profile-stat-row">
                <div class="profile-stat">
                    <div class="profile-stat-num">${profile.years_experience || 0}</div>
                    <div class="profile-stat-label">Years Exp</div>
                </div>
                <div class="profile-stat">
                    <div class="profile-stat-num">${(profile.core_skills||[]).length}</div>
                    <div class="profile-stat-label">Skills</div>
                </div>
                <div class="profile-stat">
                    <div class="profile-stat-num">${(profile.projects||[]).length}</div>
                    <div class="profile-stat-label">Projects</div>
                </div>
            </div>
            <div>
                <div class="parsed-section-label">Core Skills</div>
                <div class="tag-cloud">${skills}</div>
            </div>
            <div>
                <div class="parsed-section-label">Key Projects</div>
                ${projects}
            </div>
        </div>`;
}

// ─── Generate Assessment ────────────────────────────────────────
const genBtn = document.getElementById('gen-assessment-btn');
const genText = document.getElementById('gen-assessment-text');
const genLoader = document.getElementById('gen-assess-loader');

genBtn.addEventListener('click', async () => {
    if (!state.extractedProfile) { toast('Upload a resume first.', 'error'); return; }
    if (!state.parsedJob) { toast('Parse a job description in Tab 1 first.', 'error'); return; }

    setLoading(genText, genLoader, genBtn, true, 'Generating Assessment...');
    try {
        const body = {
            application_id: `app_${Date.now()}`,
            candidate_name: state.extractedProfile.name,
            candidate_email: state.extractedProfile.email || '',
            core_skills: state.extractedProfile.core_skills || [],
            projects: state.extractedProfile.projects || [],
            job_id: `job_${Date.now()}`,
            role: state.parsedJob.role_title || 'Unknown Role',
            critical_requirements: state.parsedJob.critical_requirements || []
        };
        const res = await fetch('/api/v1/generate-assessment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(await res.text());
        state.currentAssessment = await res.json();
        renderAssessment(state.currentAssessment);
        toast('Personalized assessment generated!', 'success');
    } catch (e) {
        toast(`Error: ${e.message}`, 'error');
    } finally {
        setLoading(genText, genLoader, genBtn, false, 'Re-Generate Assessment');
    }
});

function typeLabels(type) {
    const map = {
        scenario_coding: { label: 'Scenario Coding', cls: 'q-type-scenario' },
        architectural_tradeoff: { label: 'Architecture Tradeoff', cls: 'q-type-tradeoff' },
        debug_challenge: { label: 'Debug Challenge', cls: 'q-type-debug' },
        system_design: { label: 'System Design', cls: 'q-type-design' },
        concept_depth: { label: 'Concept Depth', cls: 'q-type-concept' },
    };
    return map[type] || { label: type, cls: 'q-type-concept' };
}

function renderAssessment(assessment) {
    const output = document.getElementById('assessment-output');
    const answerForm = document.getElementById('answer-form');
    const scoreResult = document.getElementById('score-result');
    const sub = document.getElementById('assess-sub');

    scoreResult.classList.add('hidden');
    output.classList.remove('empty-placeholder');
    answerForm.classList.remove('hidden');

    sub.textContent = `Personalized for ${assessment.candidate_name} — ${assessment.role}`;

    const meta = `
        <div class="assess-meta">
            <span class="tag tag-primary">ID: ${assessment.assessment_id}</span>
            <span class="tag tag-accent">${assessment.role}</span>
            <span class="tag tag-success">${assessment.questions.length} Questions</span>
        </div>`;
    output.innerHTML = meta;

    const container = document.getElementById('questions-container');
    container.innerHTML = '';
    assessment.questions.forEach((q, i) => {
        const t = typeLabels(q.type);
        const diffColor = { easy: '#34d399', medium: '#fbbf24', hard: '#f87171' }[q.difficulty] || '#94a3b8';
        const card = document.createElement('div');
        card.className = 'question-card';
        card.innerHTML = `
            <div class="q-header">
                <div class="q-num">${i + 1}</div>
                <span class="q-type-badge ${t.cls}">${t.label}</span>
                <span class="q-difficulty" style="color:${diffColor}">● ${q.difficulty || 'medium'}</span>
            </div>
            <div class="q-prompt">${q.prompt}</div>
            <textarea class="q-answer" id="answer-${q.question_id}" placeholder="Type your answer here..."></textarea>`;
        container.appendChild(card);
    });
}

// ─── Submit Assessment ──────────────────────────────────────────
const submitBtn = document.getElementById('submit-assess-btn');
const submitText = document.getElementById('submit-assess-text');
const submitLoader = document.getElementById('submit-assess-loader');

submitBtn.addEventListener('click', async () => {
    if (!state.currentAssessment) return;
    const answers = state.currentAssessment.questions.map(q => ({
        question_id: q.question_id,
        answer: document.getElementById(`answer-${q.question_id}`)?.value || ''
    }));
    const empty = answers.filter(a => !a.answer.trim()).length;
    if (empty > 0 && !confirm(`${empty} question(s) unanswered. Submit anyway?`)) return;

    setLoading(submitText, submitLoader, submitBtn, true, 'AI Scoring...');
    try {
        const body = {
            assessment_id: state.currentAssessment.assessment_id,
            application_id: state.currentAssessment.application_id,
            answers
        };
        const res = await fetch('/api/v1/submit-assessment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(await res.text());
        const result = await res.json();
        state.assessmentResult = result;

        // Add to assessed candidates pool
        const profile = state.extractedProfile;
        state.assessedCandidates.push({
            name: profile.name,
            email: profile.email || '',
            profile: profile,
            assessment_percentage: result.percentage
        });
        updateCandCount();

        renderScoreResult(result);
        toast(`Score: ${result.percentage}% — Added to ranking pool!`, 'success');
    } catch (e) {
        toast(`Scoring error: ${e.message}`, 'error');
    } finally {
        setLoading(submitText, submitLoader, submitBtn, false, 'Submit for AI Scoring');
    }
});

function renderScoreResult(result) {
    const el = document.getElementById('score-result');
    el.classList.remove('hidden');
    document.getElementById('answer-form').classList.add('hidden');

    const pct = result.percentage;
    const cls = pct >= 80 ? 'score-high-bg' : pct >= 60 ? 'score-med-bg' : 'score-low-bg';
    const csCls = pct >= 80 ? 'cs-high' : pct >= 60 ? 'cs-mid' : 'cs-low';

    const answersHTML = (result.scored_answers || []).map(sa => {
        const pctSA = ((sa.score / sa.max_score) * 100).toFixed(0);
        const scoreColor = pctSA >= 80 ? '#34d399' : pctSA >= 60 ? '#fbbf24' : '#f87171';
        const skills = (sa.demonstrated_skills || []).map(s => `<span class="sa-skill">${s}</span>`).join('');
        return `<div class="scored-answer">
            <div class="sa-header">
                <span class="sa-id">${sa.question_id}</span>
                <span class="sa-score" style="color:${scoreColor}">${sa.score}/${sa.max_score}</span>
            </div>
            <div class="sa-feedback">${sa.feedback}</div>
            <div class="sa-skills">${skills}</div>
        </div>`;
    }).join('');

    el.innerHTML = `
        <div class="score-header">
            <div class="score-circle-big ${cls}">${pct}%</div>
            <div>
                <div class="score-name">${result.candidate_name}</div>
                <div class="score-summary">${result.summary}</div>
                <div style="margin-top:0.5rem">
                    <span class="tag tag-success">Score: ${result.total_score}/${result.max_total}</span>
                </div>
            </div>
        </div>
        <div style="margin-top:1rem">${answersHTML}</div>
        <button class="btn btn-ghost btn-full" style="margin-top:1rem" onclick="
            document.getElementById('score-result').classList.add('hidden');
            document.getElementById('answer-form').classList.remove('hidden');
        ">← Retake Assessment</button>`;
}

/* ═══════════════════════════════════════════════════════════════
   TAB 3: RECRUITER DASHBOARD
   ═══════════════════════════════════════════════════════════════ */

document.getElementById('add-mock-dash-btn').addEventListener('click', () => {
    DEMO_CANDIDATES.forEach(c => {
        const exists = state.assessedCandidates.find(x => x.email === c.email);
        if (!exists) state.assessedCandidates.push(c);
    });
    updateCandCount();
    toast(`Added ${DEMO_CANDIDATES.length} demo candidates!`, 'success');
});

const rankAllBtn = document.getElementById('rank-all-btn');
const rankAllText = document.getElementById('rank-all-text');
const rankAllLoader = document.getElementById('rank-all-loader');

rankAllBtn.addEventListener('click', async () => {
    if (state.assessedCandidates.length === 0) {
        toast('No candidates to rank. Add demo candidates or assess resumes first.', 'error');
        return;
    }
    if (!state.parsedJob) {
        toast('Parse a job description in Tab 1 first.', 'error');
        return;
    }

    setLoading(rankAllText, rankAllLoader, rankAllBtn, true, `Ranking ${state.assessedCandidates.length} Candidates...`);
    try {
        const body = {
            job_id: `job_${Date.now()}`,
            role_title: state.parsedJob.role_title || 'Unknown Role',
            job_profile: state.parsedJob,
            candidates: state.assessedCandidates
        };
        const res = await fetch('/api/v1/recruiter-dashboard', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(await res.text());
        const dashboard = await res.json();
        renderDashboard(dashboard);
        toast(`Ranked ${dashboard.evaluated_candidates_count} candidates in ${dashboard.processing_time_ms}ms!`, 'success');
    } catch (e) {
        toast(`Ranking error: ${e.message}`, 'error');
    } finally {
        setLoading(rankAllText, rankAllLoader, rankAllBtn, false, 'Re-Rank All Candidates');
    }
});

function renderDashboard(dash) {
    document.getElementById('dash-role-title').textContent = `🏆 ${dash.role_title} — Shortlist`;
    document.getElementById('dash-sub').textContent = `${dash.evaluated_candidates_count} candidates evaluated in ${dash.processing_time_ms}ms`;

    const output = document.getElementById('dashboard-output');
    output.classList.remove('empty-placeholder', 'large-placeholder');

    const shortlist = dash.ranked_shortlist || [];
    const topScore = shortlist[0]?.composite_score || 0;
    const strongHires = shortlist.filter(c => c.recommendation === 'STRONG HIRE').length;

    const statsBar = `
        <div class="dash-stats-bar">
            <div class="dash-stat-card">
                <div class="ds-num">${dash.evaluated_candidates_count}</div>
                <div class="ds-label">Total Evaluated</div>
            </div>
            <div class="dash-stat-card">
                <div class="ds-num" style="color:#34d399">${strongHires}</div>
                <div class="ds-label">Strong Hires</div>
            </div>
            <div class="dash-stat-card">
                <div class="ds-num" style="color:#6366f1">${topScore.toFixed(1)}</div>
                <div class="ds-label">Top Score</div>
            </div>
            <div class="dash-stat-card">
                <div class="ds-num">${dash.processing_time_ms}ms</div>
                <div class="ds-label">Processing Time</div>
            </div>
        </div>`;

    const cards = shortlist.map((c, i) => renderRankCard(c, i)).join('');
    output.innerHTML = statsBar + cards;

    // Trigger bar animations
    setTimeout(() => {
        shortlist.forEach((c, i) => {
            const card = output.querySelectorAll('.rank-card')[i];
            if (!card) return;
            card.style.opacity = '1';
            card.querySelector('.bar-sem').style.width = `${c.resume_semantic_match}%`;
            card.querySelector('.bar-test').style.width = `${c.ai_test_score}%`;
            card.querySelector('.bar-vel').style.width = `${c.career_velocity}%`;
        });
    }, 150);
}

        return `<div class="rank-card ${rankClass}" style="animation-delay:${i * 0.08}s">
            <div class="rank-top">
                <div class="rank-num">#${c.rank}</div>
                <div class="rank-info">
                    <div class="rank-name">${c.name}</div>
                    <div class="rank-email">${c.email}</div>
                </div>
                <span class="rec-badge ${recClass}">${c.recommendation}</span>
                <div class="composite-score-big ${scoreClass}">${c.composite_score.toFixed(1)}</div>
            </div>

            <div class="score-matrix">
                <div class="matrix-item">
                    <div class="matrix-val">${(c.resume_semantic_match||0).toFixed(1)}</div>
                    <div class="matrix-label">Resume Fit</div>
                    <div class="matrix-bar-wrap"><div class="matrix-bar bar-sem" style="width:0%"></div></div>
                </div>
                <div class="matrix-item">
                    <div class="matrix-val">${(c.ai_test_score||0).toFixed(1)}</div>
                    <div class="matrix-label">Test Score</div>
                    <div class="matrix-bar-wrap"><div class="matrix-bar bar-test" style="width:0%"></div></div>
                </div>
                <div class="matrix-item">
                    <div class="matrix-val">${(c.career_velocity||0).toFixed(1)}</div>
                    <div class="matrix-label">Career Velocity</div>
                    <div class="matrix-bar-wrap"><div class="matrix-bar bar-vel" style="width:0%"></div></div>
                </div>
            </div>

            <div class="cap-map">${capItems}</div>

            <div class="ai-rec-box">
                <div class="ai-rec-label">AI Recommendation</div>
                <div class="ai-rec-text">${c.system_recommendation || 'No recommendation available.'}</div>
            </div>
        </div>`;
}


/* ═══════════════════════════════════════════════════════════════
   TAB 4: AI INTERVIEW ENGINE
   ═══════════════════════════════════════════════════════════════ */

// ─── Interview State ────────────────────────────────────────────
const iv = {
    session: null,           // Full session from /interview/start
    questions: [],           // List of questions
    currentIdx: 0,           // Current question index
    evaluations: [],         // Completed evaluations
    answers: {},             // { questionId: answerText }
};

// ─── Helper: show/hide interview panels ────────────────────────
function ivShow(panelId) {
    ['iv-setup-panel','iv-analysis-panel','iv-interview-panel','iv-report-panel'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('hidden', id !== panelId);
    });
}

// ─── Use Extracted Profile from Tab 2 ──────────────────────────
document.getElementById('iv-use-extracted-btn').addEventListener('click', () => {
    if (!state.extractedProfile) {
        toast('No profile extracted yet. Upload a resume in Tab 2 first.', 'error');
        return;
    }
    document.getElementById('iv-resume-input').value = state.extractedProfile.raw_text || JSON.stringify(state.extractedProfile, null, 2);
    const name = state.extractedProfile.name || '';
    const email = state.extractedProfile.email || '';
    if (name) document.getElementById('iv-candidate-name').value = name;
    if (email) document.getElementById('iv-candidate-email').value = email;
    toast('Profile loaded from Tab 2!', 'success');
});

// ─── Use Parsed JD from Tab 1 ──────────────────────────────────
document.getElementById('iv-use-jd-btn').addEventListener('click', () => {
    const jdText = document.getElementById('jd-input').value.trim();
    if (!jdText) {
        toast('No job description found. Parse one in Tab 1 first.', 'error');
        return;
    }
    document.getElementById('iv-jd-input').value = jdText;
    toast('Job description loaded from Tab 1!', 'success');
});

// ─── Start Interview ────────────────────────────────────────────
const ivStartBtn = document.getElementById('iv-start-btn');
const ivStartText = document.getElementById('iv-start-text');
const ivStartLoader = document.getElementById('iv-start-loader');

ivStartBtn.addEventListener('click', async () => {
    const resumeText = document.getElementById('iv-resume-input').value.trim();
    const jdText = document.getElementById('iv-jd-input').value.trim();
    if (!resumeText) { toast('Please provide resume text.', 'error'); return; }
    if (!jdText) { toast('Please provide a job description.', 'error'); return; }

    setLoading(ivStartText, ivStartLoader, ivStartBtn, true, 'Analyzing Resume & JD...');
    try {
        const body = {
            resume_text: resumeText,
            job_description: jdText,
            candidate_name: document.getElementById('iv-candidate-name').value.trim(),
            candidate_email: document.getElementById('iv-candidate-email').value.trim(),
        };
        const res = await fetch('/api/v1/interview/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(await res.text());
        iv.session = await res.json();
        iv.questions = iv.session.questions || [];
        iv.evaluations = [];
        iv.currentIdx = 0;
        iv.answers = {};

        renderAnalysisPanel(iv.session);
        ivShow('iv-analysis-panel');
        toast(`Analysis complete! ${iv.questions.length} questions generated.`, 'success');
    } catch (e) {
        toast(`Error: ${e.message}`, 'error');
    } finally {
        setLoading(ivStartText, ivStartLoader, ivStartBtn, false, 'Analyze & Start Interview');
    }
});

// ─── Render Analysis (Phase 1 + 2) ─────────────────────────────
function renderAnalysisPanel(session) {
    const ca = session.candidate_analysis || {};
    const ja = session.job_analysis || {};
    const match = parseFloat(ja.match_percentage || 0);

    // Title
    document.getElementById('iv-candidate-title').textContent = ca.candidate_name || session.candidate_name;

    // Match badge
    const matchEl = document.getElementById('iv-match-badge');
    const matchCls = match >= 70 ? 'match-high' : match >= 50 ? 'match-mid' : 'match-low';
    matchEl.innerHTML = `<span class="${matchCls}">${match.toFixed(1)}% Match</span>`;

    // Candidate profile
    const skillTags = (ca.skills || []).slice(0,10).map(s => `<span class="tag tag-primary">${s}</span>`).join('');
    const strengthItems = (ca.technical_strengths || []).map(s => `<div class="iv-item strength">✓ ${s}</div>`).join('');
    const weakItems = (ca.weak_areas || []).map(w => `<div class="iv-item weak">△ ${w}</div>`).join('');
    const projItems = (ca.projects || []).slice(0,3).map(p => `<div class="iv-item">${p}</div>`).join('');
    const expItems = (ca.experience || []).slice(0,3).map(e => `<div class="iv-item">${e}</div>`).join('');

    document.getElementById('iv-candidate-profile-display').innerHTML = `
        <div class="iv-profile-grid">
            <div class="iv-candidate-name">${ca.candidate_name || 'Candidate'}</div>
            <div>
                <div class="iv-group-label">Skills</div>
                <div class="tag-cloud" style="margin-bottom:0">${skillTags}</div>
            </div>
            <div>
                <div class="iv-group-label">Experience</div>
                <div class="iv-item-list">${expItems || '<div class="iv-item">No experience listed</div>'}</div>
            </div>
            <div>
                <div class="iv-group-label">Key Projects</div>
                <div class="iv-item-list">${projItems || '<div class="iv-item">No projects listed</div>'}</div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem">
                <div>
                    <div class="iv-group-label">Strengths</div>
                    <div class="iv-item-list">${strengthItems || '<div class="iv-item">-</div>'}</div>
                </div>
                <div>
                    <div class="iv-group-label">Weak Areas</div>
                    <div class="iv-item-list">${weakItems || '<div class="iv-item">-</div>'}</div>
                </div>
            </div>
            <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:0.85rem;font-size:0.83rem;color:var(--text-muted);line-height:1.6">
                ${ca.profile_summary || 'Profile analyzed.'}
            </div>
        </div>`;

    // JD Analysis
    const reqTags = (ja.required_skills || []).map(s => `<span class="tag tag-accent">${s}</span>`).join('');
    const prefTags = (ja.preferred_skills || []).map(s => `<span class="tag tag-warn">${s}</span>`).join('');
    const gapItems = (ja.skill_gap || []).map(g => `<div class="iv-gap-item">⚠ ${g}</div>`).join('');
    const respItems = (ja.responsibilities || []).slice(0,4).map(r => `<div class="iv-item">${r}</div>`).join('');

    document.getElementById('iv-job-analysis-display').innerHTML = `
        <div class="iv-profile-grid">
            <div>
                <div class="iv-group-label">Required Skills</div>
                <div class="tag-cloud">${reqTags}</div>
            </div>
            ${prefTags ? `<div><div class="iv-group-label">Preferred Skills</div><div class="tag-cloud">${prefTags}</div></div>` : ''}
            <div>
                <div class="iv-group-label">Key Responsibilities</div>
                <div class="iv-item-list">${respItems}</div>
            </div>
            <div>
                <div class="iv-group-label">Skill Gap</div>
                ${gapItems || '<div class="iv-strength-item">✓ No significant gaps detected</div>'}
            </div>
            <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:0.85rem;font-size:0.83rem;color:var(--text-muted);line-height:1.6">
                ${ja.strength_analysis || ''}
            </div>
        </div>`;
}

// ─── Proceed to Interview Questions ────────────────────────────
document.getElementById('iv-goto-interview-btn').addEventListener('click', () => {
    ivShow('iv-interview-panel');
    loadQuestion(0);
});

// ─── Load Question ──────────────────────────────────────────────
function loadQuestion(idx) {
    if (idx >= iv.questions.length) {
        // All done — show finish button
        document.getElementById('iv-finish-btn').classList.remove('hidden');
        document.getElementById('iv-next-btn').classList.add('hidden');
        return;
    }

    iv.currentIdx = idx;
    const q = iv.questions[idx];
    const total = iv.questions.length;

    // Update counter & progress
    document.getElementById('iv-q-counter').textContent = `Q ${idx + 1} / ${total}`;
    document.getElementById('iv-progress-bar').style.width = `${((idx + 1) / total) * 100}%`;
    document.getElementById('iv-interview-title').textContent = `Section ${q.section}: ${q.section_name}`;

    // Meta tags
    const sectionCls = `section-${q.section}`;
    const diffCls = `diff-${q.difficulty || 'medium'}`;
    document.getElementById('iv-q-meta').innerHTML = `
        <span class="iv-section-tag ${sectionCls}">Section ${q.section}</span>
        <span class="iv-category-tag">${q.category || ''}</span>
        <span class="iv-diff-dot ${diffCls}">● ${q.difficulty || 'medium'}</span>
    `;

    document.getElementById('iv-q-text').textContent = q.question;

    // Restore prior answer if any
    document.getElementById('iv-answer-input').value = iv.answers[q.question_id] || '';

    // Reset evaluation area
    document.getElementById('iv-live-eval').classList.add('hidden');
    document.getElementById('iv-live-eval').innerHTML = '';
    document.getElementById('iv-nav-actions').style.display = 'none';
    document.getElementById('iv-submit-q-btn').disabled = false;
}

// ─── Submit & Evaluate Answer ───────────────────────────────────
const ivSubmitBtn = document.getElementById('iv-submit-q-btn');
const ivSubmitText = document.getElementById('iv-submit-q-text');
const ivSubmitLoader = document.getElementById('iv-submit-q-loader');

ivSubmitBtn.addEventListener('click', async () => {
    const q = iv.questions[iv.currentIdx];
    const answer = document.getElementById('iv-answer-input').value.trim();
    iv.answers[q.question_id] = answer;

    setLoading(ivSubmitText, ivSubmitLoader, ivSubmitBtn, true, 'AI Evaluating...');
    try {
        const body = {
            session_id: iv.session.session_id,
            question_id: q.question_id,
            question: q.question,
            section_name: q.section_name,
            category: q.category,
            difficulty: q.difficulty,
            answer,
            section: q.section,
        };
        const res = await fetch('/api/v1/interview/evaluate-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(await res.text());
        const evaluation = await res.json();
        iv.evaluations.push(evaluation);

        renderLiveEvaluation(evaluation);
        toast(`Evaluated! Score: ${(evaluation.overall_question_score * 10).toFixed(1)}/100`, 'success');

        // Show nav buttons
        const navEl = document.getElementById('iv-nav-actions');
        navEl.style.display = 'flex';
        const isLast = iv.currentIdx >= iv.questions.length - 1;
        document.getElementById('iv-next-btn').classList.toggle('hidden', isLast);
        document.getElementById('iv-finish-btn').classList.toggle('hidden', !isLast);
        ivSubmitBtn.disabled = true;

    } catch (e) {
        toast(`Evaluation error: ${e.message}`, 'error');
    } finally {
        setLoading(ivSubmitText, ivSubmitLoader, ivSubmitBtn, false, 'Submit & Evaluate');
    }
});

// ─── Skip Question ──────────────────────────────────────────────
document.getElementById('iv-skip-btn').addEventListener('click', () => {
    const q = iv.questions[iv.currentIdx];
    iv.answers[q.question_id] = '';
    iv.evaluations.push({
        question_id: q.question_id,
        question: q.question,
        answer: '',
        technical_accuracy: 0, communication: 0, problem_solving: 0, confidence: 0,
        strengths: [], weaknesses: ['Skipped'],
        suggested_improvement: 'Attempt all questions — even partial answers demonstrate reasoning.',
        overall_question_score: 0
    });
    loadQuestion(iv.currentIdx + 1);
    document.getElementById('iv-live-eval').classList.add('hidden');
    document.getElementById('iv-nav-actions').style.display = 'none';
    toast('Question skipped.', 'info');
});

// ─── Next Question ──────────────────────────────────────────────
document.getElementById('iv-next-btn').addEventListener('click', () => {
    loadQuestion(iv.currentIdx + 1);
});

// ─── Finish & Generate Report ────────────────────────────────────
const ivFinishBtn = document.getElementById('iv-finish-btn');
ivFinishBtn.addEventListener('click', async () => {
    ivFinishBtn.disabled = true;
    ivFinishBtn.innerHTML = '<div class="btn-loader"></div> Generating HR Report...';
    try {
        const res = await fetch('/api/v1/interview/final-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: iv.session.session_id,
                evaluations: iv.evaluations
            })
        });
        if (!res.ok) throw new Error(await res.text());
        const report = await res.json();
        renderFinalReport(report);
        ivShow('iv-report-panel');
        toast('Final HR Report generated!', 'success');
    } catch (e) {
        toast(`Report error: ${e.message}`, 'error');
        ivFinishBtn.disabled = false;
        ivFinishBtn.innerHTML = '<span class="btn-icon">📋</span> Generate Final Report';
    }
});

// ─── Restart ────────────────────────────────────────────────────
document.getElementById('iv-restart-btn').addEventListener('click', () => {
    iv.session = null; iv.questions = []; iv.evaluations = []; iv.currentIdx = 0; iv.answers = {};
    document.getElementById('iv-resume-input').value = '';
    document.getElementById('iv-jd-input').value = '';
    document.getElementById('iv-candidate-name').value = '';
    document.getElementById('iv-candidate-email').value = '';
    ivShow('iv-setup-panel');
});

// ─── Render Live Evaluation (Phase 4) ──────────────────────────
function renderLiveEvaluation(ev) {
    const pct = ev.overall_question_score * 10;
    const bgCls = pct >= 70 ? 'score-high-bg' : pct >= 50 ? 'score-med-bg' : 'score-low-bg';

    const meterColor = (v) => {
        const p = v * 10;
        return p >= 70 ? '#34d399' : p >= 50 ? '#fbbf24' : '#f87171';
    };

    const meters = [
        { label: 'Technical', val: ev.technical_accuracy },
        { label: 'Communication', val: ev.communication },
        { label: 'Problem Solving', val: ev.problem_solving },
        { label: 'Confidence', val: ev.confidence },
    ].map(m => `
        <div class="iv-meter">
            <div class="iv-meter-val" style="color:${meterColor(m.val)}">${(m.val * 10).toFixed(0)}</div>
            <div class="iv-meter-label">${m.label}</div>
            <div class="iv-meter-bar"><div class="iv-meter-fill" style="background:${meterColor(m.val)};width:${m.val * 10}%"></div></div>
        </div>`).join('');

    const strengthsHtml = (ev.strengths || []).map(s => `<div class="iv-feedback-item"><span style="color:#34d399">+</span> ${s}</div>`).join('') || '<div class="iv-feedback-item">—</div>';
    const weakHtml = (ev.weaknesses || []).map(w => `<div class="iv-feedback-item"><span style="color:#f87171">−</span> ${w}</div>`).join('') || '<div class="iv-feedback-item">—</div>';

    const el = document.getElementById('iv-live-eval');
    el.classList.remove('hidden');
    el.innerHTML = `
        <div class="iv-eval-card">
            <div class="iv-eval-header">
                <div class="iv-eval-score-circle ${bgCls}">${pct.toFixed(0)}<div style="font-size:0.5rem;opacity:0.7">/100</div></div>
                <div>
                    <div style="font-family:var(--font-display);font-weight:700;color:#fff;font-size:1rem">AI Evaluation Complete</div>
                    <div style="font-size:0.8rem;color:var(--text-dim)">Question ${iv.currentIdx + 1} of ${iv.questions.length}</div>
                </div>
            </div>
            <div class="iv-score-meters">${meters}</div>
            <div class="iv-feedback-grid">
                <div class="iv-feedback-box">
                    <div class="iv-feedback-title">Strengths</div>
                    ${strengthsHtml}
                </div>
                <div class="iv-feedback-box">
                    <div class="iv-feedback-title">Areas to Improve</div>
                    ${weakHtml}
                </div>
            </div>
            <div class="iv-improvement-box">
                <strong style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;color:var(--accent);display:block;margin-bottom:0.3rem">AI Improvement Suggestion</strong>
                ${ev.suggested_improvement || 'Keep practicing!'}
            </div>
        </div>`;
}

// ─── Render Final HR Report (Phase 5) ──────────────────────────
function renderFinalReport(report) {
    document.getElementById('iv-report-name').textContent = `${report.candidate_name} — Evaluation Report`;

    const rec = report.final_recommendation;
    const recCls = rec === 'HIRE' ? 'rec-hire' : rec === 'MAYBE HIRE' ? 'rec-maybe' : 'rec-reject';
    const overallCls = report.overall_score >= 80 ? '#34d399' : report.overall_score >= 60 ? '#fbbf24' : '#f87171';

    // Stats grid
    const statsGrid = `
        <div class="iv-report-grid">
            <div class="iv-report-stat">
                <div class="iv-report-stat-val" style="color:${overallCls}">${report.overall_score}</div>
                <div class="iv-report-stat-label">Overall Score</div>
            </div>
            <div class="iv-report-stat">
                <div class="iv-report-stat-val" style="color:#6366f1">${report.technical_score}</div>
                <div class="iv-report-stat-label">Technical</div>
            </div>
            <div class="iv-report-stat">
                <div class="iv-report-stat-val" style="color:#a855f7">${report.communication_score}</div>
                <div class="iv-report-stat-label">Communication</div>
            </div>
            <div class="iv-report-stat">
                <div class="iv-report-stat-val" style="color:#ec4899">${report.job_match_percentage.toFixed(1)}%</div>
                <div class="iv-report-stat-label">Job Match</div>
            </div>
        </div>`;

    // Recommendation banner
    const recBanner = `
        <div class="iv-recommendation-banner ${recCls}">
            <div class="iv-rec-label">Final HR Recommendation</div>
            <div class="iv-rec-status">${rec}</div>
            <div class="iv-rec-reasoning">${report.recommendation_reasoning}</div>
        </div>`;

    // Summary card
    const summaryCard = `
        <div class="iv-report-section" style="margin-bottom:1.25rem">
            <div class="iv-report-section-title">Candidate Summary</div>
            <p style="font-size:0.87rem;color:var(--text-muted);line-height:1.7">${report.candidate_summary}</p>
        </div>`;

    // Skill Assessment + Section Scores
    const skillRows = Object.entries(report.skill_assessment || {}).map(([skill, level]) => {
        const lvlCls = `level-${level.toLowerCase().replace(' ', '-')}`;
        return `<div class="iv-skill-row">
            <span class="iv-skill-name">${skill}</span>
            <span class="iv-skill-level ${lvlCls}">${level}</span>
        </div>`;
    }).join('');

    const sectionColors = { A: '#6366f1', B: '#a855f7', C: '#f59e0b', D: '#10b981' };
    const sectionNames = { A: 'Resume-Based', B: 'Technical', C: 'Scenario', D: 'Behavioral' };
    const sectionScoreRows = Object.entries(report.section_scores || {}).map(([s, score]) => `
        <div class="iv-section-score-row">
            <span class="iv-ss-label">${sectionNames[s] || s}</span>
            <span class="iv-ss-val" style="color:${sectionColors[s]}">${score}/100</span>
        </div>
        <div class="iv-ss-bar-outer">
            <div class="iv-ss-bar-fill" style="background:${sectionColors[s]};width:${score}%"></div>
        </div>
    `).join('');

    const twoCol = `
        <div class="iv-report-two-col">
            <div class="iv-report-section">
                <div class="iv-report-section-title">Skill Assessment</div>
                ${skillRows || '<p style="color:var(--text-dim);font-size:0.83rem">No skills assessed</p>'}
            </div>
            <div class="iv-report-section">
                <div class="iv-report-section-title">Section Scores</div>
                ${sectionScoreRows}
            </div>
        </div>`;

    // Strengths & Improvements
    const strengthsList = (report.key_strengths || []).map(s => `
        <div class="iv-strength-item"><span>✓</span> ${s}</div>`).join('');
    const improvList = (report.areas_of_improvement || []).map(w => `
        <div class="iv-gap-item"><span>△</span> ${w}</div>`).join('');

    const lastRow = `
        <div class="iv-report-two-col">
            <div class="iv-report-section">
                <div class="iv-report-section-title">Key Strengths</div>
                ${strengthsList || '<p style="color:var(--text-dim);font-size:0.83rem">—</p>'}
            </div>
            <div class="iv-report-section">
                <div class="iv-report-section-title">Areas of Improvement</div>
                ${improvList || '<p style="color:var(--text-dim);font-size:0.83rem">—</p>'}
            </div>
        </div>`;

    document.getElementById('iv-final-report-content').innerHTML =
        statsGrid + recBanner + summaryCard + twoCol + lastRow;
}

}
