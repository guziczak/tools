class Earth3D {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.earth = null;
        this.clouds = null;
        this.atmosphere = null;
        this.stars = null;
        
        this.init();
    }
    
    init() {
        this.createScene();
        this.createCamera();
        this.createRenderer();
        this.createLights();
        this.createEarth();
        this.createClouds();
        this.createAtmosphere();
        this.createStars();
        this.createControls();
        this.setupEventListeners();
        this.animate();
        this.hideLoading();
    }
    
    createScene() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x000011);
    }
    
    createCamera() {
        this.camera = new THREE.PerspectiveCamera(
            75,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        this.camera.position.z = 3;
    }
    
    createRenderer() {
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true,
            alpha: true 
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        document.getElementById('container').appendChild(this.renderer.domElement);
    }
    
    createLights() {
        const ambientLight = new THREE.AmbientLight(0x404040, 0.3);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1.2);
        directionalLight.position.set(5, 3, 5);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        this.scene.add(directionalLight);
        
        const pointLight = new THREE.PointLight(0x4444ff, 0.5, 100);
        pointLight.position.set(-5, -3, -5);
        this.scene.add(pointLight);
    }
    
    createEarth() {
        const geometry = new THREE.SphereGeometry(1, 64, 64);
        
        const textureLoader = new THREE.TextureLoader();
        
        const earthTexture = textureLoader.load('https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_atmos_2048.jpg', () => {
            console.log('Tekstura Ziemi załadowana');
        });
        
        const bumpTexture = textureLoader.load('https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_normal_2048.jpg', () => {
            console.log('Mapa wypukłości załadowana');
        });
        
        const specularTexture = textureLoader.load('https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_specular_2048.jpg', () => {
            console.log('Mapa odbicia załadowana');
        });
        
        const material = new THREE.MeshPhongMaterial({
            map: earthTexture,
            bumpMap: bumpTexture,
            bumpScale: 0.05,
            specularMap: specularTexture,
            specular: new THREE.Color(0x333333),
            shininess: 25
        });
        
        this.earth = new THREE.Mesh(geometry, material);
        this.earth.castShadow = true;
        this.earth.receiveShadow = true;
        this.scene.add(this.earth);
    }
    
    createClouds() {
        const geometry = new THREE.SphereGeometry(1.01, 64, 64);
        
        const textureLoader = new THREE.TextureLoader();
        const cloudsTexture = textureLoader.load('https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_clouds_1024.png', () => {
            console.log('Tekstura chmur załadowana');
        });
        
        const material = new THREE.MeshPhongMaterial({
            map: cloudsTexture,
            transparent: true,
            opacity: 0.4,
            depthWrite: false
        });
        
        this.clouds = new THREE.Mesh(geometry, material);
        this.scene.add(this.clouds);
    }
    
    createAtmosphere() {
        const geometry = new THREE.SphereGeometry(1.1, 64, 64);
        
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
        
        this.atmosphere = new THREE.Mesh(geometry, material);
        this.scene.add(this.atmosphere);
    }
    
    createStars() {
        const starsGeometry = new THREE.BufferGeometry();
        const starsMaterial = new THREE.PointsMaterial({
            color: 0xFFFFFF,
            size: 0.02,
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
        this.stars = new THREE.Points(starsGeometry, starsMaterial);
        this.scene.add(this.stars);
    }
    
    createControls() {
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.minDistance = 1.5;
        this.controls.maxDistance = 10;
        this.controls.enablePan = false;
        this.controls.rotateSpeed = 0.5;
    }
    
    setupEventListeners() {
        window.addEventListener('resize', () => this.onWindowResize(), false);
        
        window.addEventListener('mousemove', (event) => {
            this.mouseX = (event.clientX / window.innerWidth) * 2 - 1;
            this.mouseY = -(event.clientY / window.innerHeight) * 2 + 1;
        });
    }
    
    onWindowResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        
        if (this.earth) {
            this.earth.rotation.y += 0.001;
        }
        
        if (this.clouds) {
            this.clouds.rotation.y += 0.0012;
        }
        
        if (this.controls) {
            this.controls.update();
        }
        
        this.renderer.render(this.scene, this.camera);
    }
    
    hideLoading() {
        setTimeout(() => {
            const loading = document.getElementById('loading');
            if (loading) {
                loading.style.display = 'none';
            }
        }, 2000);
    }
}

window.addEventListener('load', () => {
    new Earth3D();
});