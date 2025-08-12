// Zmienne globalne
let scene, camera, renderer, controls;
let earth, clouds, atmosphere, nightLights, moon;
let satellites = [];
let rotationSpeed = 0.0005;
let autoRotate = true;
let sunLight, sunPosition;
let time = 0;
let raycaster, mouse;
let infoPanel;

// Inicjalizacja sceny
function init() {
    // Tworzenie sceny
    scene = new THREE.Scene();
    
    // Kamera
    camera = new THREE.PerspectiveCamera(
        75, 
        window.innerWidth / window.innerHeight, 
        0.1, 
        1000
    );
    camera.position.z = 2.5;
    
    // Renderer z maksymalną jakością
    renderer = new THREE.WebGLRenderer({ 
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
        precision: "highp",
        logarithmicDepthBuffer: true
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio); // Pełna rozdzielczość ekranu
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    document.body.appendChild(renderer.domElement);
    
    // Kontrolki orbity
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 1.5;
    controls.maxDistance = 10;
    
    // Oświetlenie
    setupLighting();
    
    // Tworzenie Ziemi
    createEarth();
    
    // Tworzenie chmur
    createClouds();
    
    // Tworzenie atmosfery
    createAtmosphere();
    
    // Tworzenie świateł nocnych
    createNightLights();
    
    // Tworzenie Księżyca
    createMoon();
    
    // Tworzenie satelitów i ISS
    createSatellites();
    
    // Tworzenie markerów miast
    createCityMarkers();
    
    // Gwiazdy w tle
    createStars();
    
    // Inicjalizacja raycaster dla interakcji
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();
    
    // Ukryj komunikat o ładowaniu
    document.getElementById('loading').style.display = 'none';
    
    // Nasłuchiwanie na zdarzenia
    setupEventListeners();
    
    // Start animacji
    animate();
}

// Konfiguracja oświetlenia
function setupLighting() {
    // Światło słoneczne - zbalansowane
    sunLight = new THREE.DirectionalLight(0xffffff, 1.2);
    sunLight.position.set(5, 3, 5);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 0.5;
    sunLight.shadow.camera.far = 50;
    scene.add(sunLight);
    
    // Pozycja słońca
    sunPosition = new THREE.Vector3(5, 3, 5);
    
    // Światło ambientowe - delikatne
    const ambientLight = new THREE.AmbientLight(0x333344, 0.4);
    scene.add(ambientLight);
}

// Tworzenie modelu Ziemi
function createEarth() {
    const geometry = new THREE.SphereGeometry(1, 256, 256);
    
    // Tekstury Ziemi
    const textureLoader = new THREE.TextureLoader();
    
    // Najpierw utwórz podstawowy materiał
    const material = new THREE.MeshPhongMaterial({
        color: 0xffffff,
        specular: new THREE.Color(0x111111),
        shininess: 5
    });
    
    earth = new THREE.Mesh(geometry, material);
    earth.castShadow = true;
    earth.receiveShadow = true;
    scene.add(earth);
    
    // Ładowanie tekstur z obsługą błędów i CORS
    textureLoader.crossOrigin = 'anonymous';
    
    // Lista alternatywnych źródeł tekstur - ULTRA HIGH RES
    const textureUrls = [
        // NASA Blue Marble - 8K resolution
        'https://eoimages.gsfc.nasa.gov/images/imagerecords/74000/74218/world.200412.3x21600x21600.A1.png',
        // NASA Visible Earth - bardzo wysoka rozdzielczość
        'https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57752/land_ocean_ice_cloud_8192.jpg',
        // Alternatywne 4K
        'https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_atmos_4096.jpg',
        // NASA Blue Marble Next Generation
        'https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73909/world.topo.bathy.200412.3x5400x2700.jpg',
        // Zapasowe 2K
        'https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_atmos_2048.jpg'
    ];
    
    let textureIndex = 0;
    
    function loadEarthTexture() {
        if (textureIndex >= textureUrls.length) {
            console.log('All texture URLs failed, using procedural texture');
            // Tworzenie proceduralnej tekstury jako ostateczność
            const canvas = document.createElement('canvas');
            canvas.width = 4096;
            canvas.height = 2048;
            const ctx = canvas.getContext('2d');
            
            // Gradient dla oceanów
            const oceanGradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            oceanGradient.addColorStop(0, '#001a33');
            oceanGradient.addColorStop(0.5, '#003366');
            oceanGradient.addColorStop(1, '#001a33');
            ctx.fillStyle = oceanGradient;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Losowe kontynenty
            ctx.fillStyle = '#228b22';
            for (let i = 0; i < 5; i++) {
                const x = Math.random() * canvas.width;
                const y = Math.random() * canvas.height;
                const w = 50 + Math.random() * 100;
                const h = 40 + Math.random() * 80;
                ctx.fillRect(x, y, w, h);
            }
            
            const texture = new THREE.CanvasTexture(canvas);
            material.map = texture;
            material.needsUpdate = true;
            return;
        }
        
        textureLoader.load(
            textureUrls[textureIndex],
            function(texture) {
                // Włącz anizotropię dla ostrzejszych tekstur
                texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
                texture.minFilter = THREE.LinearMipMapLinearFilter;
                texture.magFilter = THREE.LinearFilter;
                material.map = texture;
                material.needsUpdate = true;
                renderer.render(scene, camera);
                console.log('Earth texture loaded successfully at high resolution');
            },
            function(xhr) {
                // Progress update
                if (xhr.lengthComputable) {
                    const percentComplete = xhr.loaded / xhr.total * 100;
                    const progress = document.getElementById('loadingProgress');
                    if (progress) {
                        progress.textContent = Math.round(percentComplete) + '%';
                    }
                }
            },
            function(error) {
                console.log(`Failed to load texture ${textureIndex + 1}, trying next...`);
                textureIndex++;
                loadEarthTexture();
            }
        );
    }
    
    loadEarthTexture();
    
    // Próba załadowania wysokiej rozdzielczości normal map
    const normalMapUrls = [
        'https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_normal_2048.jpg',
        'https://raw.githubusercontent.com/turban/webgl-earth/master/images/elev_bump_4k.jpg'
    ];
    
    let normalIndex = 0;
    function loadNormalMap() {
        if (normalIndex >= normalMapUrls.length) return;
        
        textureLoader.load(
            normalMapUrls[normalIndex],
            function(texture) {
                texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
                material.normalMap = texture;
                material.normalScale = new THREE.Vector2(0.85, 0.85);
                material.needsUpdate = true;
            },
            undefined,
            function() {
                normalIndex++;
                loadNormalMap();
            }
        );
    }
    loadNormalMap();
    
    // Specular map dla oceanów
    const specularMapUrls = [
        'https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_specular_2048.jpg',
        'https://raw.githubusercontent.com/turban/webgl-earth/master/images/water_4k.png'
    ];
    
    let specularIndex = 0;
    function loadSpecularMap() {
        if (specularIndex >= specularMapUrls.length) return;
        
        textureLoader.load(
            specularMapUrls[specularIndex],
            function(texture) {
                texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
                material.specularMap = texture;
                material.needsUpdate = true;
            },
            undefined,
            function() {
                specularIndex++;
                loadSpecularMap();
            }
        );
    }
    loadSpecularMap();
}

// Tworzenie chmur
function createClouds() {
    const geometry = new THREE.SphereGeometry(1.01, 128, 128);
    
    const textureLoader = new THREE.TextureLoader();
    textureLoader.crossOrigin = 'anonymous';
    const cloudsTexture = textureLoader.load(
        'https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_clouds_2048.png',
        function() { renderer.render(scene, camera); },
        undefined,
        function(error) {
            console.log('Failed to load clouds texture, creating procedural clouds');
            // Proceduralne chmury jako zapasowe
            const canvas = document.createElement('canvas');
            canvas.width = 4096;
            canvas.height = 2048;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
            for (let i = 0; i < 50; i++) {
                const x = Math.random() * canvas.width;
                const y = Math.random() * canvas.height;
                const r = 10 + Math.random() * 30;
                ctx.beginPath();
                ctx.arc(x, y, r, 0, Math.PI * 2);
                ctx.fill();
            }
            const texture = new THREE.CanvasTexture(canvas);
            material.map = texture;
            material.needsUpdate = true;
        }
    );
    
    const material = new THREE.MeshPhongMaterial({
        map: cloudsTexture,
        transparent: true,
        opacity: 0.4,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide
    });
    
    clouds = new THREE.Mesh(geometry, material);
    scene.add(clouds);
}

// Tworzenie atmosfery
function createAtmosphere() {
    const geometry = new THREE.SphereGeometry(1.1, 128, 128);
    
    const material = new THREE.ShaderMaterial({
        vertexShader: `
            varying vec3 vNormal;
            void main() {
                vNormal = normalize(normalMatrix * normal);
                gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
        `,
        fragmentShader: `
            varying vec3 vNormal;
            void main() {
                float intensity = pow(0.7 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.0);
                gl_FragColor = vec4(0.3, 0.6, 1.0, 1.0) * intensity;
            }
        `,
        blending: THREE.AdditiveBlending,
        side: THREE.BackSide,
        transparent: true
    });
    
    atmosphere = new THREE.Mesh(geometry, material);
    scene.add(atmosphere);
}

// Tworzenie świateł nocnych miast
function createNightLights() {
    const geometry = new THREE.SphereGeometry(0.995, 128, 128);
    
    const textureLoader = new THREE.TextureLoader();
    textureLoader.crossOrigin = 'anonymous';
    
    // Wysokiej rozdzielczości tekstura świateł nocnych
    const nightTextureUrls = [
        'https://eoimages.gsfc.nasa.gov/images/imagerecords/55000/55167/earth_lights_lrg.jpg',
        'https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_lights_2048.png'
    ];
    
    let nightTexture = null;
    let nightIndex = 0;
    
    function loadNightTexture() {
        if (nightIndex >= nightTextureUrls.length) return;
        
        textureLoader.load(
            nightTextureUrls[nightIndex],
            function(texture) {
                texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
                nightTexture = texture;
                if (nightLights && nightLights.material.uniforms) {
                    nightLights.material.uniforms.nightTexture.value = texture;
                }
                renderer.render(scene, camera);
            },
            undefined,
            function(error) {
                console.log(`Failed to load night texture ${nightIndex + 1}, trying next...`);
                nightIndex++;
                loadNightTexture();
            }
        );
    }
    
    loadNightTexture();
    
    const material = new THREE.ShaderMaterial({
        uniforms: {
            nightTexture: { value: nightTexture },
            sunDirection: { value: new THREE.Vector3(1, 0, 0) }
        },
        vertexShader: `
            varying vec2 vUv;
            varying vec3 vNormal;
            varying vec3 vPosition;
            void main() {
                vUv = uv;
                vNormal = normalize(normalMatrix * normal);
                vPosition = (modelMatrix * vec4(position, 1.0)).xyz;
                gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
        `,
        fragmentShader: `
            uniform sampler2D nightTexture;
            uniform vec3 sunDirection;
            varying vec2 vUv;
            varying vec3 vNormal;
            varying vec3 vPosition;
            
            void main() {
                vec3 viewDirection = normalize(cameraPosition - vPosition);
                float dotNL = dot(vNormal, sunDirection);
                
                // Intensywność świateł nocnych bazująca na pozycji słońca
                float nightIntensity = smoothstep(-0.1, 0.4, -dotNL);
                
                vec4 nightColor = texture2D(nightTexture, vUv);
                nightColor.rgb *= nightIntensity * 2.0;
                
                gl_FragColor = vec4(nightColor.rgb, nightColor.a * nightIntensity);
            }
        `,
        blending: THREE.AdditiveBlending,
        transparent: true,
        depthWrite: false
    });
    
    nightLights = new THREE.Mesh(geometry, material);
    scene.add(nightLights);
}

// Tworzenie Księżyca
function createMoon() {
    const moonGroup = new THREE.Group();
    
    const geometry = new THREE.SphereGeometry(0.27, 32, 32);
    
    const textureLoader = new THREE.TextureLoader();
    textureLoader.crossOrigin = 'anonymous';
    const moonTexture = textureLoader.load(
        'https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/moon_1024.jpg',
        function() { renderer.render(scene, camera); },
        undefined,
        function(error) {
            console.log('Failed to load moon texture, using grey color');
        }
    );
    
    const material = new THREE.MeshPhongMaterial({
        map: moonTexture,
        bumpScale: 0.002
    });
    
    moon = new THREE.Mesh(geometry, material);
    moon.position.set(3.5, 0, 0);
    moon.castShadow = true;
    moon.receiveShadow = true;
    
    moonGroup.add(moon);
    scene.add(moonGroup);
    
    // Zapisz grupę dla animacji
    moon.group = moonGroup;
}

// Tworzenie satelitów i ISS
function createSatellites() {
    // ISS
    const issGeometry = new THREE.BoxGeometry(0.05, 0.02, 0.08);
    const issMaterial = new THREE.MeshPhongMaterial({ 
        color: 0xcccccc,
        emissive: 0x444444
    });
    const iss = new THREE.Mesh(issGeometry, issMaterial);
    
    // Panele słoneczne ISS
    const panelGeometry = new THREE.BoxGeometry(0.15, 0.001, 0.05);
    const panelMaterial = new THREE.MeshPhongMaterial({ 
        color: 0x1a1a2e,
        emissive: 0x0f3460
    });
    
    const leftPanel = new THREE.Mesh(panelGeometry, panelMaterial);
    leftPanel.position.x = -0.1;
    iss.add(leftPanel);
    
    const rightPanel = new THREE.Mesh(panelGeometry, panelMaterial);
    rightPanel.position.x = 0.1;
    iss.add(rightPanel);
    
    const issGroup = new THREE.Group();
    issGroup.add(iss);
    issGroup.userData = { 
        radius: 1.1, 
        speed: 0.002,
        inclination: 0.9,
        name: 'ISS'
    };
    satellites.push(issGroup);
    scene.add(issGroup);
    
    // Satelity komunikacyjne
    for (let i = 0; i < 5; i++) {
        const satGeometry = new THREE.OctahedronGeometry(0.02);
        const satMaterial = new THREE.MeshPhongMaterial({ 
            color: 0xffffff,
            emissive: 0xff0000,
            emissiveIntensity: 0.5
        });
        const satellite = new THREE.Mesh(satGeometry, satMaterial);
        
        const satGroup = new THREE.Group();
        satGroup.add(satellite);
        satGroup.userData = { 
            radius: 1.2 + Math.random() * 0.3, 
            speed: 0.001 + Math.random() * 0.002,
            inclination: Math.random() * Math.PI,
            offset: Math.random() * Math.PI * 2,
            name: `Satelita ${i + 1}`
        };
        satellites.push(satGroup);
        scene.add(satGroup);
    }
}

// Tworzenie markerów miast
function createCityMarkers() {
    const cities = [
        { name: 'Warszawa', lat: 52.2297, lon: 21.0122, color: 0xff0000 },
        { name: 'Nowy Jork', lat: 40.7128, lon: -74.0060, color: 0x00ff00 },
        { name: 'Londyn', lat: 51.5074, lon: -0.1278, color: 0x0080ff },
        { name: 'Tokio', lat: 35.6762, lon: 139.6503, color: 0xffff00 },
        { name: 'Sydney', lat: -33.8688, lon: 151.2093, color: 0xff00ff },
        { name: 'Paryż', lat: 48.8566, lon: 2.3522, color: 0x00ffff },
        { name: 'Moskwa', lat: 55.7558, lon: 37.6173, color: 0xffa500 },
        { name: 'Pekin', lat: 39.9042, lon: 116.4074, color: 0xff69b4 },
        { name: 'Rio de Janeiro', lat: -22.9068, lon: -43.1729, color: 0x32cd32 },
        { name: 'Kapsztad', lat: -33.9249, lon: 18.4241, color: 0x9370db }
    ];
    
    cities.forEach(city => {
        // Konwersja współrzędnych geograficznych na pozycję 3D
        const phi = (90 - city.lat) * Math.PI / 180;
        const theta = (city.lon + 180) * Math.PI / 180;
        
        const x = Math.sin(phi) * Math.cos(theta);
        const y = Math.cos(phi);
        const z = Math.sin(phi) * Math.sin(theta);
        
        // Marker
        const markerGeometry = new THREE.ConeGeometry(0.01, 0.03, 6);
        const markerMaterial = new THREE.MeshPhongMaterial({
            color: city.color,
            emissive: 0x000000,
            emissiveIntensity: 0
        });
        
        const marker = new THREE.Mesh(markerGeometry, markerMaterial);
        marker.position.set(x * 1.01, y * 1.01, z * 1.01);
        marker.lookAt(x * 2, y * 2, z * 2);
        marker.userData = { name: city.name, lat: city.lat, lon: city.lon };
        
        // Grupa dla rotacji z Ziemią
        const markerGroup = new THREE.Group();
        markerGroup.add(marker);
        earth.add(markerGroup);
        
        // Usunięto pulsującą sferę - powodowała artefakty
    });
}

// Tworzenie gwiazd w tle
function createStars() {
    const starsGeometry = new THREE.BufferGeometry();
    const starsMaterial = new THREE.PointsMaterial({
        color: 0xffffff,
        size: 0.7,
        map: new THREE.TextureLoader().load(
            'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAMElEQVQImWNgoBn4////fwYGBgYGRkZGhlWrVjEwMjL+Z2BgYPj////////////////////////////8A3JqEQClrqnTAAAAAElFTkSuQmCC'
        ),
        transparent: true
    });
    
    const starsVertices = [];
    for (let i = 0; i < 10000; i++) {
        const x = (Math.random() - 0.5) * 2000;
        const y = (Math.random() - 0.5) * 2000;
        const z = (Math.random() - 0.5) * 2000;
        starsVertices.push(x, y, z);
    }
    
    starsGeometry.setAttribute('position', new THREE.Float32BufferAttribute(starsVertices, 3));
    const stars = new THREE.Points(starsGeometry, starsMaterial);
    scene.add(stars);
}

// Konfiguracja nasłuchiwaczy zdarzeń
function setupEventListeners() {
    // Zmiana rozmiaru okna
    window.addEventListener('resize', onWindowResize, false);
    
    // Kontrolki
    document.getElementById('rotation').addEventListener('change', (e) => {
        autoRotate = e.target.checked;
    });
    
    document.getElementById('clouds').addEventListener('change', (e) => {
        clouds.visible = e.target.checked;
    });
    
    document.getElementById('atmosphere').addEventListener('change', (e) => {
        atmosphere.visible = e.target.checked;
    });
    
    document.getElementById('speed').addEventListener('input', (e) => {
        rotationSpeed = e.target.value * 0.0001;
    });
    
    document.getElementById('nightLights').addEventListener('change', (e) => {
        if (nightLights) nightLights.visible = e.target.checked;
    });
    
    document.getElementById('moon').addEventListener('change', (e) => {
        if (moon && moon.group) moon.group.visible = e.target.checked;
    });
    
    document.getElementById('timeSpeed').addEventListener('input', (e) => {
        // Prędkość upływu czasu będzie użyta w animacji
    });
    
    document.getElementById('cityMarkers').addEventListener('change', (e) => {
        earth.traverse((child) => {
            if (child.type === 'Group' && child.children.some(c => c.userData.name)) {
                child.visible = e.target.checked;
            }
        });
    });
    
    document.getElementById('satellites').addEventListener('change', (e) => {
        satellites.forEach(sat => {
            sat.visible = e.target.checked;
        });
    });
    
    // Obsługa kliknięć
    window.addEventListener('click', onMouseClick, false);
    window.addEventListener('mousemove', onMouseMove, false);
}

// Obsługa zmiany rozmiaru okna
function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

// Animacja
function animate() {
    requestAnimationFrame(animate);
    
    // Aktualizacja czasu
    const timeSpeed = document.getElementById('timeSpeed') ? document.getElementById('timeSpeed').value / 1000 : 0.01;
    time += timeSpeed;
    
    // Rotacja automatyczna
    if (autoRotate) {
        earth.rotation.y += rotationSpeed;
        clouds.rotation.y += rotationSpeed * 1.2;
        if (nightLights) nightLights.rotation.y = earth.rotation.y;
    }
    
    // Animacja pozycji słońca (cykl dzienny)
    const sunAngle = time * 0.1;
    sunPosition.x = Math.cos(sunAngle) * 5;
    sunPosition.z = Math.sin(sunAngle) * 5;
    sunLight.position.copy(sunPosition);
    
    // Aktualizacja kierunku słońca dla świateł nocnych
    if (nightLights && nightLights.material.uniforms) {
        nightLights.material.uniforms.sunDirection.value = sunPosition.clone().normalize();
    }
    
    // Orbita Księżyca
    if (moon && moon.group) {
        moon.group.rotation.y = time * 0.05;
        moon.rotation.y += 0.001;
    }
    
    // Animacja satelitów
    satellites.forEach((satGroup) => {
        const data = satGroup.userData;
        const angle = time * data.speed + (data.offset || 0);
        const x = Math.cos(angle) * data.radius;
        const y = Math.sin(angle * data.inclination) * 0.2;
        const z = Math.sin(angle) * data.radius;
        satGroup.position.set(x, y, z);
        satGroup.lookAt(0, 0, 0);
    });
    
    // Aktualizacja kontrolek
    controls.update();
    
    // Renderowanie
    renderer.render(scene, camera);
}

// Obsługa ruchu myszy
function onMouseMove(event) {
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
}

// Obsługa kliknięć
function onMouseClick(event) {
    raycaster.setFromCamera(mouse, camera);
    
    // Sprawdź kliknięcie na Ziemię
    const intersects = raycaster.intersectObject(earth);
    
    if (intersects.length > 0) {
        const point = intersects[0].point;
        const spherical = new THREE.Spherical();
        spherical.setFromVector3(point);
        
        // Konwersja na współrzędne geograficzne
        const lat = 90 - (spherical.phi * 180) / Math.PI;
        const lon = ((spherical.theta * 180) / Math.PI + earth.rotation.y * 180 / Math.PI) % 360;
        
        showInfoPanel(`Szerokość: ${lat.toFixed(2)}°, Długość: ${lon.toFixed(2)}°`);
    }
    
    // Sprawdź kliknięcie na markery miast
    const cityIntersects = raycaster.intersectObjects(earth.children, true);
    if (cityIntersects.length > 0) {
        const clickedObject = cityIntersects[0].object;
        if (clickedObject.userData && clickedObject.userData.name) {
            showInfoPanel(`Miasto: ${clickedObject.userData.name}`);
        }
    }
}

// Wyświetlanie panelu informacyjnego
function showInfoPanel(text) {
    if (!infoPanel) {
        infoPanel = document.createElement('div');
        infoPanel.style.position = 'absolute';
        infoPanel.style.top = '60px';
        infoPanel.style.left = '50%';
        infoPanel.style.transform = 'translateX(-50%)';
        infoPanel.style.background = 'rgba(0,0,0,0.8)';
        infoPanel.style.color = 'white';
        infoPanel.style.padding = '10px 20px';
        infoPanel.style.borderRadius = '5px';
        infoPanel.style.fontFamily = 'Arial';
        document.body.appendChild(infoPanel);
    }
    
    infoPanel.textContent = text;
    infoPanel.style.display = 'block';
    
    setTimeout(() => {
        if (infoPanel) infoPanel.style.display = 'none';
    }, 3000);
}

// Inicjalizacja po załadowaniu strony
window.addEventListener('DOMContentLoaded', init);