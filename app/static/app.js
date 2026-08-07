document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const headerFps = document.getElementById('header-fps');
    const headerLatency = document.getElementById('header-latency');
    const statActiveWorkers = document.getElementById('stat-active-workers');
    const statCompliantWorkers = document.getElementById('stat-compliant-workers');
    const statNonCompliantWorkers = document.getElementById('stat-non-compliant-workers');
    const statZoneViolations = document.getElementById('stat-zone-violations');
    const compliancePercentage = document.getElementById('compliance-percentage');
    const complianceFill = document.getElementById('compliance-fill');
    const violationList = document.getElementById('violation-list');
    const emptyViolations = document.getElementById('empty-violations');
    const violationBadgeCount = document.getElementById('violation-badge-count');

    // ROI Modal Elements
    const btnRoiModal = document.getElementById('btn-roi-modal');
    const roiModal = document.getElementById('roi-modal');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const btnSaveRoi = document.getElementById('btn-save-roi');
    const btnResetRoi = document.getElementById('btn-reset-roi');
    const roiLabelInput = document.getElementById('roi-label');
    const roiEnabledInput = document.getElementById('roi-enabled');
    const roiCoordsInput = document.getElementById('roi-coords-input');

    // Fetch and sync live telemetry stats from FastAPI /api/v1/telemetry
    async function updateTelemetry() {
        try {
            const res = await fetch('/api/v1/telemetry');
            if (!res.ok) return;

            const data = await res.json();

            // Update top metric indicators
            headerFps.textContent = data.fps.toFixed(1);
            headerLatency.textContent = `${data.latency_ms.toFixed(1)} ms`;

            statActiveWorkers.textContent = data.active_workers;
            statCompliantWorkers.textContent = data.compliant_workers;
            statNonCompliantWorkers.textContent = data.non_compliant_workers;
            statZoneViolations.textContent = data.restricted_zone_violations || 0;

            // Compliance percentage
            const total = data.active_workers;
            const comp = data.compliant_workers;
            const score = total > 0 ? Math.round((comp / total) * 100) : 100;
            compliancePercentage.textContent = `${score}%`;
            complianceFill.style.width = `${score}%`;

            // Render Violation Cards
            renderViolations(data.violations || []);

        } catch (err) {
            console.error('Error polling telemetry:', err);
        }
    }

    function renderViolations(violations) {
        violationBadgeCount.textContent = `${violations.length} ACTIVE`;

        if (violations.length === 0) {
            violationList.innerHTML = '';
            violationList.appendChild(emptyViolations);
            return;
        }

        violationList.innerHTML = '';
        violations.forEach(v => {
            const card = document.createElement('div');
            card.className = `violation-card ${v.severity.toLowerCase()}`;

            const missingTags = v.missing_gear.map(g => `<span class="v-tag missing">NO ${g.toUpperCase()}</span>`).join(' ');
            const zoneTag = v.in_restricted_zone ? `<span class="v-tag zone">DANGER ZONE INTRUSION</span>` : '';

            card.innerHTML = `
                <div class="v-head">
                    <span class="v-id mono">WORKER TRACK ID #${v.track_id}</span>
                    <span class="v-severity ${v.severity}">${v.severity}</span>
                </div>
                <div class="v-body">
                    ${missingTags}
                    ${zoneTag}
                </div>
                <div class="v-time mono">${new Date().toLocaleTimeString()}</div>
            `;

            violationList.appendChild(card);
        });
    }

    // ROI Modal Handlers
    btnRoiModal.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/v1/roi');
            if (res.ok) {
                const config = await res.json();
                roiLabelInput.value = config.label || 'Restricted Zone Alpha';
                roiEnabledInput.checked = config.enabled;
                roiCoordsInput.value = JSON.stringify(config.polygon, null, 2);
            }
        } catch (err) {
            console.error('Error fetching ROI config:', err);
        }
        roiModal.classList.add('active');
    });

    btnCloseModal.addEventListener('click', () => {
        roiModal.classList.remove('active');
    });

    btnResetRoi.addEventListener('click', () => {
        roiLabelInput.value = 'Restricted Zone Alpha';
        roiEnabledInput.checked = true;
        roiCoordsInput.value = JSON.stringify([
            { x: 0.1, y: 0.4 },
            { x: 0.5, y: 0.4 },
            { x: 0.5, y: 0.95 },
            { x: 0.1, y: 0.95 }
        ], null, 2);
    });

    btnSaveRoi.addEventListener('click', async () => {
        try {
            const polygon = JSON.parse(roiCoordsInput.value);
            const payload = {
                enabled: roiEnabledInput.checked,
                label: roiLabelInput.value,
                polygon: polygon
            };

            const res = await fetch('/api/v1/roi', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                roiModal.classList.remove('active');
            } else {
                alert('Failed to update ROI config. Please check JSON syntax.');
            }
        } catch (err) {
            alert('Invalid JSON formatting for ROI polygon coordinates.');
        }
    });

    // Start live telemetry polling interval (every 300ms)
    setInterval(updateTelemetry, 300);
    updateTelemetry();
});
