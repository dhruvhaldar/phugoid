
window.initAircraftViewer = function() {
    const container = document.getElementById('3d-viewer');

    // Wait for container to have dimensions
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 400;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x87CEEB); // Sky blue

    const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    camera.position.set(-5, 2, 5);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    container.appendChild(renderer.domElement);

    // Add Aircraft (simplified as a group of boxes)
    const aircraft = new THREE.Group();

    // Fuselage
    const fuselage = new THREE.Mesh(
        new THREE.BoxGeometry(4, 0.5, 0.5),
        new THREE.MeshLambertMaterial({ color: 0xffffff })
    );
    aircraft.add(fuselage);

    // Wing
    const wing = new THREE.Mesh(
        new THREE.BoxGeometry(1, 0.1, 6),
        new THREE.MeshLambertMaterial({ color: 0xff0000 })
    );
    wing.position.set(0.5, 0.2, 0);
    aircraft.add(wing);

    // Tail
    const tail = new THREE.Mesh(
        new THREE.BoxGeometry(0.8, 0.1, 2),
        new THREE.MeshLambertMaterial({ color: 0xff0000 })
    );
    tail.position.set(-1.8, 0.2, 0);
    aircraft.add(tail);

    // Vertical Stabilizer
    const vstab = new THREE.Mesh(
        new THREE.BoxGeometry(0.5, 1, 0.1),
        new THREE.MeshLambertMaterial({ color: 0xff0000 })
    );
    vstab.position.set(-1.8, 0.5, 0);
    aircraft.add(vstab);

    scene.add(aircraft);

    // Axes Helper
    const axesHelper = new THREE.AxesHelper( 2 );
    scene.add( axesHelper );

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 10, 10);
    scene.add(directionalLight);

    // Grid (Ground)
    const gridHelper = new THREE.GridHelper(50, 50);
    gridHelper.position.y = -5;
    scene.add(gridHelper);

    function animate() {
        requestAnimationFrame(animate);
        renderer.render(scene, camera);
    }

    animate();

    // Initial trim update
    window.updateAircraftAttitude = function(theta, phi, psi) {
        // Theta (Pitch) -> Rotation around Z (if X is forward?)
        // In standard Flight Dynamics: X is forward, Y is right, Z is down.
        // In Three.js: X is right, Y is up, Z is backward (out of screen).

        // Let's align aircraft model with Three.js world.
        // Fuselage along X axis currently (BoxGeometry(4, ...)).
        // So X is longitudinal axis.

        // Pitch (Theta): Rotation around Z axis (Transverse axis).
        // Roll (Phi): Rotation around X axis (Longitudinal).
        // Yaw (Psi): Rotation around Y axis (Vertical).

        aircraft.rotation.z = theta;
        aircraft.rotation.x = -phi; // Check sign
        aircraft.rotation.y = -psi;
    };

    // Handle resize
    window.addEventListener('resize', () => {
        const w = container.clientWidth;
        const h = container.clientHeight;
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    });
};

window.addEventListener('load', window.initAircraftViewer);
