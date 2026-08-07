document.addEventListener('DOMContentLoaded', () => {
    // DOM Cache
    const headerFps = document.getElementById('header-fps');
    const headerLatency = document.getElementById('header-latency');
    const statActiveWorkers = document.getElementById('stat-active-workers');
    const statCompliantWorkers = document.getElementById('stat-compliant-workers');
    const statNonCompliantWorkers = document.getElementById('stat-non-compliant-workers');
    const compliancePercentage = document.getElementById('compliance-percentage');
    const complianceFill = document.getElementById('compliance-fill');
    const violationList = document.getElementById('violation-list');
    const emptyViolations = document.getElementById('empty-violations');
    const violationBadgeCount = document.getElementById('violation-badge-count');
    const statusBadgeContainer = document.getElementById('status-badge-container');
    const pipelineStatusText = document.getElementById('pipeline-status-text');
    const toastContainer = document.getElementById('toast-container');

    // Controls & Modal
    const btnSimViolation = document.getElementById('btn-sim-violation');
    const btnAudioToggle = document.getElementById('btn-audio-toggle');
    const audioStateText = document.getElementById('audio-state-text');

    // Upload DOM Elements
    const dropzone = document.getElementById('upload-dropzone');
    const fileInput = document.getElementById('file-input');
    const dropzonePrompt = document.getElementById('dropzone-prompt');
    const uploadLoader = document.getElementById('upload-loader');
    const uploadResults = document.getElementById('upload-results');
    const resultPreview = document.getElementById('result-preview');
    const resWorkers = document.getElementById('res-workers');
    const resCompliant = document.getElementById('res-compliant');
    const resViolations = document.getElementById('res-violations');
    const btnClearUpload = document.getElementById('btn-clear-upload');

    let audioEnabled = true;
    let audioCtx = null;
    let lastViolationCount = 0;
    let isFetching = false;

    function getAudioContext() {
        if (!audioCtx) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (AudioContextClass) audioCtx = new AudioContextClass();
        }
        if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
        return audioCtx;
    }

    function playBeepSound() {
        if (!audioEnabled) return;
        try {
            const ctx = getAudioContext();
            if (!ctx) return;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(880, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.22);
            gain.gain.setValueAtTime(0.12, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.22);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.22);
        } catch (e) {}
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);
        setTimeout(() => toast.remove(), 3200);
    }

    async function updateTelemetry() {
        if (isFetching) return;
        isFetching = true;
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000);
            const res = await fetch('/api/v1/telemetry', { signal: controller.signal });
            clearTimeout(timeoutId);

            if (res.ok) {
                const data = await res.json();
                headerFps.textContent = data.fps.toFixed(1);
                headerLatency.textContent = `${data.latency_ms.toFixed(1)} ms`;
                statActiveWorkers.textContent = data.active_workers;
                statCompliantWorkers.textContent = data.compliant_workers;
                statNonCompliantWorkers.textContent = data.non_compliant_workers;

                const total = data.active_workers;
                const comp = data.compliant_workers;
                const score = total > 0 ? Math.round((comp / total) * 100) : 100;
                compliancePercentage.textContent = `${score}%`;
                complianceFill.style.width = `${score}%`;

                const violations = data.violations || [];
                if (violations.length > 0) {
                    statusBadgeContainer.className = 'status-badge alert';
                    pipelineStatusText.textContent = 'SAFETY BREACH';
                    if (violations.length > lastViolationCount) {
                        playBeepSound();
                        showToast(`Alert: ${violations.length} safety breach(es) flagged!`, 'warning');
                    }
                } else {
                    statusBadgeContainer.className = 'status-badge live';
                    pipelineStatusText.textContent = 'LIVE PIPELINE';
                }
                lastViolationCount = violations.length;
                renderViolations(violations);
            }
        } catch (err) {} finally { isFetching = false; }
    }

    function renderViolations(violations) {
        violationBadgeCount.textContent = `${violations.length} ACTIVE`;
        if (violations.length === 0) {
            violationList.innerHTML = '';
            violationList.appendChild(emptyViolations);
            return;
        }
        const fragment = document.createDocumentFragment();
        violations.forEach(v => {
            const card = document.createElement('div');
            card.className = `violation-card ${v.severity.toLowerCase()}`;
            const missingTags = (v.missing_gear || []).map(g => `<span class="v-tag missing">NO ${g.toUpperCase()}</span>`).join(' ');
            card.innerHTML = `<div class="v-head"><span class="v-id mono">WORKER TRACK ID #${v.track_id}</span><span class="v-severity ${v.severity}">${v.severity}</span></div><div class="v-body">${missingTags}</div><div class="v-time mono">${new Date().toLocaleTimeString()}</div>`;
            fragment.appendChild(card);
        });
        violationList.innerHTML = '';
        violationList.appendChild(fragment);
    }

    // Upload & Analysis Handling
    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.style.borderColor = 'var(--accent-primary)'; });
    dropzone.addEventListener('dragleave', () => { dropzone.style.borderColor = 'var(--border-default)'; });
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--border-default)';
        if (e.dataTransfer.files.length) handleFileUpload(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => { if (fileInput.files.length) handleFileUpload(fileInput.files[0]); });

    async function handleFileUpload(file) {
        if (!file.type.startsWith('image/')) {
            showToast('Please upload a valid image file (JPG, PNG)', 'error');
            return;
        }
        dropzonePrompt.style.display = 'none';
        uploadLoader.style.display = 'flex';
        uploadResults.style.display = 'none';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/api/v1/analyze/upload', { method: 'POST', body: formData });
            if (res.ok) {
                const data = await res.json();
                resultPreview.src = data.image_data;
                resWorkers.textContent = data.summary.active_workers;
                resCompliant.textContent = data.summary.compliant_workers;
                resViolations.textContent = data.summary.non_compliant_workers;
                uploadResults.style.display = 'block';
                showToast('Offline frame analysis complete!', 'success');
            } else { showToast('Failed to process image file', 'error'); }
        } catch (err) { showToast('Network error during file upload', 'error'); } finally {
            uploadLoader.style.display = 'none';
            dropzonePrompt.style.display = 'block';
        }
    }

    btnClearUpload.addEventListener('click', (e) => {
        e.stopPropagation();
        uploadResults.style.display = 'none';
        fileInput.value = '';
    });

    // Control Handlers
    btnSimViolation.addEventListener('click', async () => {
        getAudioContext();
        try {
            const res = await fetch('/api/v1/test/trigger-violation', { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                showToast(`Triggered mock PPE violation for Worker ID #${data.triggered_worker_id}`, 'warning');
                updateTelemetry();
            }
        } catch (err) { showToast('Failed to trigger mock violation', 'error'); }
    });

    btnAudioToggle.addEventListener('click', () => {
        getAudioContext();
        audioEnabled = !audioEnabled;
        audioStateText.textContent = audioEnabled ? 'Sound ON' : 'Muted';
        showToast(audioEnabled ? 'Audio alerts enabled' : 'Audio alerts muted', 'info');
    });



    setInterval(updateTelemetry, 350);
    updateTelemetry();
});
