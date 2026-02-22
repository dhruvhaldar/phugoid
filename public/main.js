// Preset Buttons
const presetBtns = document.querySelectorAll('.preset-btn');
const velocityInput = document.getElementById('velocity');
const altitudeInput = document.getElementById('altitude');
const statusRegion = document.getElementById('status-region');

presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        velocityInput.value = btn.dataset.v;
        altitudeInput.value = btn.dataset.h;

        // Visual feedback
        presetBtns.forEach(b => {
            b.classList.remove('selected');
            b.setAttribute('aria-pressed', 'false');
        });
        btn.classList.add('selected');
        btn.setAttribute('aria-pressed', 'true');

        // Announce to screen readers
        if (statusRegion) {
            statusRegion.textContent = `Preset ${btn.textContent} selected`;
        }
    });
});

// Clear selection on manual input
const clearPresetSelection = () => {
    presetBtns.forEach(b => {
        b.classList.remove('selected');
        b.setAttribute('aria-pressed', 'false');
    });
};

velocityInput.addEventListener('input', clearPresetSelection);
altitudeInput.addEventListener('input', clearPresetSelection);

document.getElementById('flight-controls').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('calculate-btn');
    const errorDiv = document.getElementById('error-message');
    const originalText = 'Calculate Trim & Stability';

    // Reset state
    errorDiv.textContent = '';
    document.getElementById('status-region').textContent = '';
    btn.classList.add('loading');
    btn.disabled = true;
    btn.textContent = 'Calculating...';

    try {
        const velocity = parseFloat(document.getElementById('velocity').value);
        const altitude = parseFloat(document.getElementById('altitude').value);

        // Trim
        const trimRes = await fetch('/api/trim', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({velocity, altitude})
        });
        const trimData = await trimRes.json();

        if (trimData.detail) {
            throw new Error(trimData.detail);
        }

        document.getElementById('trim-alpha').textContent = trimData.alpha_deg.toFixed(2);
        document.getElementById('trim-elevator').textContent = trimData.elevator_deg.toFixed(2);
        document.getElementById('trim-throttle').textContent = (trimData.throttle * 100).toFixed(1);
        document.getElementById('trim-theta').textContent = trimData.theta_deg.toFixed(2);

        // Update 3D viewer (if implemented)
        if (window.updateAircraftAttitude) {
            window.updateAircraftAttitude(trimData.theta_deg * Math.PI / 180, 0, 0);
        }

        // Analyze
        const analyzeRes = await fetch('/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({velocity, altitude})
        });
        const analyzeData = await analyzeRes.json();

        if (analyzeData.detail) {
            throw new Error(analyzeData.detail);
        }

        // Plot Poles
        if (window.plotPoles) {
            window.plotPoles(analyzeData.longitudinal, analyzeData.lateral);
        }

        // List Modes
        const lonList = document.getElementById('lon-modes');
        lonList.innerHTML = '';
        analyzeData.longitudinal.forEach(m => {
            const li = document.createElement('li');
            li.textContent = `Eval: ${m.real.toFixed(3)} ± ${Math.abs(m.imag).toFixed(3)}j | Wn: ${m.wn.toFixed(3)} | Zeta: ${m.zeta.toFixed(3)}`;
            lonList.appendChild(li);
        });

        const latList = document.getElementById('lat-modes');
        latList.innerHTML = '';
        analyzeData.lateral.forEach(m => {
            const li = document.createElement('li');
            li.textContent = `Eval: ${m.real.toFixed(3)} ± ${Math.abs(m.imag).toFixed(3)}j | Wn: ${m.wn.toFixed(3)} | Zeta: ${m.zeta.toFixed(3)}`;
            latList.appendChild(li);
        });

        // UX: Show Results, Hide Empty State
        document.getElementById('results').classList.remove('hidden');
        document.getElementById('visualization').classList.remove('hidden');
        document.getElementById('empty-state').classList.add('hidden');

        // UX: Trigger resize to ensure charts render correctly in now-visible containers
        window.dispatchEvent(new Event('resize'));

        // Announce success to screen readers
        document.getElementById('status-region').textContent = 'Calculation complete. Results updated.';
    } catch (err) {
        errorDiv.textContent = err.message || 'An unexpected error occurred';
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
        btn.textContent = originalText;
    }
});

// Copy Trim Results
const copyBtn = document.getElementById('copy-trim-btn');
if (copyBtn) {
    const originalHtml = copyBtn.innerHTML;

    copyBtn.addEventListener('click', async () => {
        const alpha = document.getElementById('trim-alpha').textContent;
        const elevator = document.getElementById('trim-elevator').textContent;
        const throttle = document.getElementById('trim-throttle').textContent;
        const theta = document.getElementById('trim-theta').textContent;

        const text = `Trim State:
Alpha: ${alpha} deg
Elevator: ${elevator} deg
Throttle: ${throttle} %
Theta: ${theta} deg`;

        try {
            await navigator.clipboard.writeText(text);

            // Visual Feedback
            copyBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span class="btn-text">Copied!</span>
            `;
            copyBtn.classList.add('success');
            copyBtn.setAttribute('aria-label', 'Copied to clipboard');

            // Revert after 2 seconds
            setTimeout(() => {
                copyBtn.innerHTML = originalHtml;
                copyBtn.classList.remove('success');
                copyBtn.setAttribute('aria-label', 'Copy trim results to clipboard');
            }, 2000);

            // Screen reader announcement
            const statusRegion = document.getElementById('status-region');
            if (statusRegion) {
                statusRegion.textContent = 'Trim results copied to clipboard';
            }

        } catch (err) {
            console.error('Failed to copy:', err);
        }
    });
}
