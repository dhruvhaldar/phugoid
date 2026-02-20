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
        presetBtns.forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');

        // Announce to screen readers
        if (statusRegion) {
            statusRegion.textContent = `Preset ${btn.textContent} selected`;
        }
    });
});

// Clear selection on manual input
const clearPresetSelection = () => {
    presetBtns.forEach(b => b.classList.remove('selected'));
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
