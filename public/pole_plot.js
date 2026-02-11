window.plotPoles = function(lonData, latData) {
    const traceLon = {
        x: lonData.map(d => d.real),
        y: lonData.map(d => d.imag),
        mode: 'markers',
        type: 'scatter',
        name: 'Longitudinal',
        marker: { size: 10, color: 'blue', symbol: 'x' }
    };

    const traceLat = {
        x: latData.map(d => d.real),
        y: latData.map(d => d.imag),
        mode: 'markers',
        type: 'scatter',
        name: 'Lateral',
        marker: { size: 10, color: 'red', symbol: 'circle' }
    };

    const layout = {
        title: 'Pole-Zero Map (S-Plane)',
        xaxis: {
            title: 'Real Axis (σ)',
            zeroline: true,
            showline: true,
            mirror: 'ticks',
            gridcolor: '#bdbdbd',
            gridwidth: 1,
            zerolinecolor: '#969696',
            zerolinewidth: 2,
        },
        yaxis: {
            title: 'Imaginary Axis (jω)',
            zeroline: true,
            showline: true,
            mirror: 'ticks',
            gridcolor: '#bdbdbd',
            gridwidth: 1,
            zerolinecolor: '#969696',
            zerolinewidth: 2,
        },
        shapes: [
            // Vertical line at x=0 (Stability boundary) is handled by zeroline
        ]
    };

    Plotly.newPlot('pole-plot', [traceLon, traceLat], layout);
};
