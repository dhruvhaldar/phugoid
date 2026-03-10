// Preset Buttons
const presetBtns = document.querySelectorAll('.preset-btn');
const velocityInput = document.getElementById('velocity');
const altitudeInput = document.getElementById('altitude');
const statusRegion = document.getElementById('status-region');
const velocityDisplay = document.getElementById('velocity-unit-display');
const altitudeDisplay = document.getElementById('altitude-unit-display');
const unitToggle = document.getElementById('unit-toggle');

const updateUnits = () => {
    const isImperial = unitToggle && unitToggle.checked;
    const v = parseFloat(velocityInput.value);
    if (!isNaN(v) && v > 0) {
        if (isImperial) {
            velocityDisplay.textContent = `(≈ ${(v / 1.94384).toFixed(1)} m/s)`;
        } else {
            velocityDisplay.textContent = `(≈ ${Math.round(v * 1.94384)} kts)`;
        }
    } else {
        velocityDisplay.textContent = '';
    }

    const h = parseFloat(altitudeInput.value);
    if (!isNaN(h)) {
        if (isImperial) {
            altitudeDisplay.textContent = `(≈ ${(h / 3.28084).toFixed(0)} m)`;
        } else {
            altitudeDisplay.textContent = `(≈ ${Math.round(h * 3.28084)} ft)`;
        }
    } else {
        altitudeDisplay.textContent = '';
    }
};

presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        velocityInput.value = btn.dataset.v;
        altitudeInput.value = btn.dataset.h;

        // Micro-UX: Briefly flash inputs to draw attention to changed values
        velocityInput.classList.remove('flash-update');
        altitudeInput.classList.remove('flash-update');

        // Trigger reflow to restart animation
        void velocityInput.offsetWidth;

        velocityInput.classList.add('flash-update');
        altitudeInput.classList.add('flash-update');

        setTimeout(() => {
            velocityInput.classList.remove('flash-update');
            altitudeInput.classList.remove('flash-update');
        }, 1000);

        // Visual feedback
        presetBtns.forEach(b => {
            b.classList.remove('selected');
            b.setAttribute('aria-pressed', 'false');
        });
        btn.classList.add('selected');
        btn.setAttribute('aria-pressed', 'true');

        updateUnits();

        // Mark results as stale if visible
        const resultsSection = document.getElementById('results');
        const vizSection = document.getElementById('visualization');
        if (resultsSection && !resultsSection.classList.contains('hidden')) {
            resultsSection.classList.add('stale');
            if (vizSection) vizSection.classList.add('stale');
        }

        // Announce to screen readers
        if (statusRegion) {
            statusRegion.textContent = `Preset ${btn.textContent} selected. Results outdated.`;
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

velocityInput.addEventListener('input', updateUnits);
altitudeInput.addEventListener('input', updateUnits);

const markResultsStale = () => {
    const resultsSection = document.getElementById('results');
    const vizSection = document.getElementById('visualization');

    // Only mark stale if results are currently visible
    if (resultsSection && !resultsSection.classList.contains('hidden')) {
        resultsSection.classList.add('stale');
        if (vizSection) vizSection.classList.add('stale');

        // Announce to screen readers
        if (statusRegion) {
            statusRegion.textContent = 'Inputs changed. Results are outdated.';
        }
    }
};

velocityInput.addEventListener('input', markResultsStale);
altitudeInput.addEventListener('input', markResultsStale);

if (unitToggle) {
    unitToggle.addEventListener('change', () => {
        const isImperial = unitToggle.checked;
        const velocityLabel = document.querySelector('label[for="velocity"]');
        const altitudeLabel = document.querySelector('label[for="altitude"]');

        const v = parseFloat(velocityInput.value);
        const h = parseFloat(altitudeInput.value);

        if (isImperial) {
            velocityLabel.childNodes[0].textContent = 'Velocity (kts) ';
            altitudeLabel.childNodes[0].textContent = 'Altitude (ft) ';
            
            if (!isNaN(v)) velocityInput.value = (v * 1.94384).toFixed(1);
            if (!isNaN(h)) altitudeInput.value = (h * 3.28084).toFixed(0);
        } else {
            velocityLabel.childNodes[0].textContent = 'Velocity (m/s) ';
            altitudeLabel.childNodes[0].textContent = 'Altitude (m) ';

            if (!isNaN(v)) velocityInput.value = (v / 1.94384).toFixed(1);
            if (!isNaN(h)) altitudeInput.value = (h / 3.28084).toFixed(0);
        }
        
        updateUnits();
        markResultsStale();
    });
}

// Initialize
updateUnits();

// Keyboard Shortcut: Detect OS and Add Listener
const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
const shortcutKey = isMac ? '⌘' : 'Ctrl';
const shortcutDisplay = document.getElementById('submit-shortcut');
const calculateBtn = document.getElementById('calculate-btn');

if (shortcutDisplay) {
    shortcutDisplay.textContent = `${shortcutKey} + Enter`;
}

if (calculateBtn) {
    calculateBtn.setAttribute('aria-keyshortcuts', `${isMac ? 'Meta' : 'Control'}+Enter`);
}

document.addEventListener('keydown', (e) => {
    // Check for Cmd+Enter (Mac) or Ctrl+Enter (Windows/Linux)
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        const btn = document.getElementById('calculate-btn');
        // Only trigger if button exists and is not disabled (e.g. not loading)
        if (btn && !btn.disabled) {
            btn.click();
        }
    }
});

document.getElementById('flight-controls').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('calculate-btn');
    const errorDiv = document.getElementById('error-message');
    const originalText = btn.innerHTML;

    // Reset state
    errorDiv.textContent = '';
    document.getElementById('status-region').textContent = '';
    btn.classList.add('loading');
    btn.disabled = true;
    btn.setAttribute('aria-busy', 'true');
    btn.innerHTML = 'Calculating...';

    // Disable inputs and preset buttons during calculation
    const inputs = document.querySelectorAll('#flight-controls input, .preset-btn');
    inputs.forEach(input => input.disabled = true);

    try {
        let velocity = parseFloat(document.getElementById('velocity').value);
        let altitude = parseFloat(document.getElementById('altitude').value);

        // Convert to Metric for API if currently in Imperial
        if (unitToggle && unitToggle.checked) {
            velocity = velocity / 1.94384;
            altitude = altitude / 3.28084;
        }

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
            body: JSON.stringify({velocity, altitude}) // velocity/altitude are already Metric here
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
            const isStable = m.real <= 0;
            const statusText = isStable ? 'Stable' : 'Unstable';
            const color = isStable ? 'var(--accent-green)' : 'var(--accent-red)';
            const textColor = isStable ? 'var(--text-color)' : '#fff';
            li.innerHTML = `Eval: ${m.real.toFixed(3)} ± ${Math.abs(m.imag).toFixed(3)}j | Wn: ${m.wn.toFixed(3)} | Zeta: ${m.zeta.toFixed(3)} <strong style="background-color: ${color}; color: ${textColor}; padding: 2px 5px; margin-left: 5px; border: 1px solid var(--border-color); font-size: 0.9em;">${statusText}</strong>`;
            lonList.appendChild(li);
        });

        const latList = document.getElementById('lat-modes');
        latList.innerHTML = '';
        analyzeData.lateral.forEach(m => {
            const li = document.createElement('li');
            const isStable = m.real <= 0;
            const statusText = isStable ? 'Stable' : 'Unstable';
            const color = isStable ? 'var(--accent-green)' : 'var(--accent-red)';
            const textColor = isStable ? 'var(--text-color)' : '#fff';
            li.innerHTML = `Eval: ${m.real.toFixed(3)} ± ${Math.abs(m.imag).toFixed(3)}j | Wn: ${m.wn.toFixed(3)} | Zeta: ${m.zeta.toFixed(3)} <strong style="background-color: ${color}; color: ${textColor}; padding: 2px 5px; margin-left: 5px; border: 1px solid var(--border-color); font-size: 0.9em;">${statusText}</strong>`;
            latList.appendChild(li);
        });

        // UX: Show Results, Hide Empty State
        const resultsSection = document.getElementById('results');
        resultsSection.classList.remove('hidden');
        resultsSection.classList.remove('stale');

        const vizSection = document.getElementById('visualization');
        vizSection.classList.remove('hidden');
        vizSection.classList.remove('stale');

        document.getElementById('empty-state').classList.add('hidden');

        // UX: Scroll to results and focus for accessibility
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        resultsSection.focus({ preventScroll: true });

        // UX: Trigger resize to ensure charts render correctly in now-visible containers
        window.dispatchEvent(new Event('resize'));

        // Announce success to screen readers
        document.getElementById('status-region').textContent = 'Calculation complete. Results updated.';
    } catch (err) {
        errorDiv.textContent = err.message || 'An unexpected error occurred';
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
        btn.removeAttribute('aria-busy');
        btn.innerHTML = originalText;

        // Re-enable inputs
        inputs.forEach(input => input.disabled = false);
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

// UX Improvement: Auto-select number inputs on focus (using delegation)
document.addEventListener('focusin', function(e) {
    if (e.target.matches('input[type="number"]')) {
        // Use a short timeout to prevent mouseup from deselecting the text in some browsers
        setTimeout(() => e.target.select(), 10);
    }
});

// Quick Start from Empty State
const quickStartBtn = document.getElementById('quick-start-btn');
if (quickStartBtn) {
    quickStartBtn.addEventListener('click', () => {
        // Trigger the first preset
        if (presetBtns.length > 0) {
            presetBtns[0].click();
        }
        // Trigger calculation
        const calculateBtn = document.getElementById('calculate-btn');
        if (calculateBtn && !calculateBtn.disabled) {
            calculateBtn.click();
        }
    });
}
