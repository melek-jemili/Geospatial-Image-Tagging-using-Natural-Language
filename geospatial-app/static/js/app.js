/* ========================================
   MAIN APPLICATION LOGIC
   ======================================== */

class GeoSpatialApp {
    constructor() {
        this.selectedFiles = [];
        this.maxFiles = 20;
        this.processedData = null;
        this.map = null;
        this.globeViewer = null;
        
        this.init();
    }

    // ========================================
    // INITIALIZATION
    // ========================================

    init() {
        this.setupEventListeners();
        this.checkHealth();
    }

    setupEventListeners() {
        // Drag & Drop
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');

        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            this.handleFiles(Array.from(e.dataTransfer.files));
        });

        fileInput.addEventListener('change', (e) => {
            this.handleFiles(Array.from(e.target.files));
        });

        // Process Button
        document.getElementById('processBtn').addEventListener('click', () => {
            this.processImages();
        });

        // Clear Button
        document.getElementById('clearBtn').addEventListener('click', () => {
            this.clearSelectedFiles();
        });
    }

    checkHealth() {
        axios.get('/api/health')
            .then(response => {
                console.log('✅ API Health:', response.data);
            })
            .catch(error => {
                console.error('❌ API Error:', error);
                alert('Error connecting to API. Please make sure the Flask server is running.');
            });
    }

    // ========================================
    // FILE HANDLING
    // ========================================

    handleFiles(files) {
        const validFiles = files.filter(file => {
            const ext = file.name.split('.').pop().toLowerCase();
            const allowed = ['jpg', 'jpeg', 'png', 'tiff', 'heic', 'gif', 'bmp'];
            return allowed.includes(ext);
        });

        if (validFiles.length === 0) {
            alert('No valid image files selected.');
            return;
        }

        // Check total count
        if (this.selectedFiles.length + validFiles.length > this.maxFiles) {
            alert(`Maximum ${this.maxFiles} images allowed. You've selected ${this.selectedFiles.length + validFiles.length}.`);
            return;
        }

        // Add files
        this.selectedFiles.push(...validFiles);
        this.updatePreview();
    }

    updatePreview() {
        const grid = document.getElementById('imagePreviewGrid');
        const items = document.getElementById('previewItems');
        const count = document.getElementById('imageCount');
        const uploadCount = document.getElementById('upload-count');
        const processBtn = document.getElementById('processBtn');

        count.textContent = this.selectedFiles.length;
        uploadCount.textContent = this.selectedFiles.length;

        if (this.selectedFiles.length === 0) {
            grid.style.display = 'none';
        } else {
            grid.style.display = 'block';
        }

        items.innerHTML = this.selectedFiles.map((file, idx) => `
            <div class="preview-item" id="preview-${idx}">
                <img src="${URL.createObjectURL(file)}" alt="${file.name}">
                <button class="preview-remove" onclick="app.removeFile(${idx})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');

        processBtn.disabled = this.selectedFiles.length === 0;
    }

    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updatePreview();
    }

    clearSelectedFiles() {
        if (confirm('Clear all selected images?')) {
            this.selectedFiles = [];
            document.getElementById('fileInput').value = '';
            this.updatePreview();
        }
    }

    // ========================================
    // IMAGE PROCESSING
    // ========================================

    async processImages() {
        if (this.selectedFiles.length === 0) {
            alert('Please select images first.');
            return;
        }

        // Show loading
        this.showLoading('Uploading images...');

        try {
            // Step 1: Upload images
            const uploadFormData = new FormData();
            this.selectedFiles.forEach(file => {
                uploadFormData.append('images', file);
            });

            console.log(`📤 Uploading ${this.selectedFiles.length} images...`);
            const uploadResponse = await axios.post('/api/upload', uploadFormData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            const uploadedImages = uploadResponse.data.images;
            console.log(`✅ Upload complete: ${uploadedImages.length} images`);

            if (uploadedImages.length === 0) {
                this.hideLoading();
                alert('Upload failed.');
                return;
            }

            // Show pipeline section
            document.getElementById('upload-section').style.display = 'none';
            document.getElementById('pipeline-section').style.display = 'flex';

            // Step 2: Process through pipeline
            this.updateLoading('Processing through pipeline...');

            const processingResponse = await axios.post('/api/process', {
                image_paths: uploadedImages.map(img => img.path)
            });

            this.processedData = processingResponse.data;
            console.log('✅ Processing complete:', this.processedData);

            // Update pipeline visualization
            this.updatePipelineVisualization(this.processedData);

            // Wait a bit then show globe section
            setTimeout(() => {
                this.hideLoading();
                document.getElementById('pipeline-section').style.display = 'flex';
                document.getElementById('globe-section').style.display = 'flex';
                document.getElementById('map-section').style.display = 'flex';
                
                // Show ready announcement
                document.getElementById('readyAnnouncement').style.display = 'block';

                // Initialize map and globe
                this.initializeMap();
                this.initializeGlobe();

                // Populate results table
                this.populateResults();

                // Scroll to pipeline
                document.getElementById('pipeline-section').scrollIntoView({ behavior: 'smooth' });
            }, 1000);

        } catch (error) {
            console.error('Processing error:', error);
            this.hideLoading();
            alert(`Error: ${error.response?.data?.error || error.message}`);
        }
    }

    // ========================================
    // PIPELINE VISUALIZATION
    // ========================================

    updatePipelineVisualization(data) {
        // Update stats
        document.getElementById('gpsCount').textContent = data.summary.images_with_gps;
        document.getElementById('clusterCount').textContent = data.summary.total_clusters;
        document.getElementById('processingTime').textContent = `${data.summary.processing_time.toFixed(2)}s`;

        // Update step progress
        const steps = [
            { id: 'exif', percent: 100 },
            { id: 'nlp', percent: 100 },
            { id: 'embeddings', percent: 100 },
            { id: 'quantum', percent: 100 },
            { id: 'vectordb', percent: 100 }
        ];

        steps.forEach(step => {
            const stepEl = document.getElementById(`step-${step.id}`);
            const statusEl = document.getElementById(`status-${step.id}`);
            const progressEl = stepEl.querySelector('.progress-bar');

            if (progressEl) {
                progressEl.style.width = `${step.percent}%`;
            }
            
            stepEl.classList.add('completed');
            if (statusEl) {
                statusEl.textContent = '✅ Complete';
            }
        });
    }

    // ========================================
    // MAP INITIALIZATION
    // ========================================

    initializeMap() {
        if (!this.processedData || this.processedData.images.length === 0) {
            console.warn('No data for map');
            return;
        }

        const images = this.processedData.images;

        // Calculate bounds
        const lats = images.map(img => img.latitude);
        const lons = images.map(img => img.longitude);
        const centerLat = (Math.min(...lats) + Math.max(...lats)) / 2;
        const centerLon = (Math.min(...lons) + Math.max(...lons)) / 2;

        // Create map
        this.map = L.map('mapViewer').setView([centerLat, centerLon], 3);

        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
            minZoom: 2
        }).addTo(this.map);

        // Add markers by cluster
        const clusterColors = {
            'cluster_0': '#FF6B6B',
            'cluster_1': '#4ECDC4',
            'cluster_2': '#45B7D1',
            'cluster_3': '#96CEB4',
            'cluster_4': '#FECA57'
        };

        const featureGroupsByCluster = {};

        images.forEach(img => {
            const cluster = img.cluster || 'default';
            if (!featureGroupsByCluster[cluster]) {
                featureGroupsByCluster[cluster] = L.featureGroup().addTo(this.map);
            }

            const color = clusterColors[cluster] || '#A0A0A0';
            const topTags = img.top_tags.slice(0, 5).join(', ');
            const objects = Array.isArray(img.objects) ? [...new Set(img.objects)].slice(0, 10).join(', ') : 'None';

            const popupContent = `
                <div style="min-width: 250px; font-family: Arial, sans-serif; font-size: 12px;">
                    <div style="margin-bottom: 10px; border-bottom: 1px solid #ddd; padding-bottom: 10px;">
                        <strong style="font-size: 14px; color: #333;">${img.filename}</strong>
                    </div>
                    
                    <div style="margin-bottom: 8px;">
                        <strong>📍 Location:</strong><br>
                        Lat: ${img.latitude.toFixed(4)}<br>
                        Lon: ${img.longitude.toFixed(4)}
                    </div>

                    <div style="margin-bottom: 8px;">
                        <strong>📷 Camera:</strong> ${img.camera || 'Unknown'}<br>
                        <strong>📅 Date:</strong> ${img.datetime || 'Unknown'}
                    </div>

                    <div style="margin-bottom: 8px;">
                        <strong>🏷️ Top Tags:</strong><br>
                        <div style="flex-wrap: wrap; display: flex; gap: 4px;">
                            ${img.tags.slice(0, 8).map(tag => 
                                `<span style="background: rgba(0,212,255,0.2); color: #00d4ff; padding: 2px 8px; border-radius: 12px; font-size: 11px;">${tag}</span>`
                            ).join('')}
                        </div>
                    </div>

                    <div>
                        <strong>🔍 Objects:</strong><br>
                        <span style="font-size: 11px; color: #666;">${objects}</span>
                    </div>
                </div>
            `;

            const marker = L.circleMarker([img.latitude, img.longitude], {
                radius: 8,
                fillColor: color,
                color: color,
                weight: 2,
                opacity: 1,
                fillOpacity: 0.7
            }).bindPopup(popupContent);

            marker.addTo(featureGroupsByCluster[cluster]);
        });

        // Add layer control
        const overlays = {};
        Object.entries(featureGroupsByCluster).forEach(([cluster, fg]) => {
            const count = images.filter(img => img.cluster === cluster).length;
            overlays[`${cluster} (${count} images)`] = fg;
        });

        L.control.layers({}, overlays, { position: 'topright' }).addTo(this.map);

        console.log('✅ Map initialized');
    }

    // ========================================
    // GLOBE INITIALIZATION
    // ========================================

    initializeGlobe() {
        const container = document.getElementById('globeViewer');
        if (!container || !this.processedData) {
            console.warn('Globe container or data missing');
            return;
        }

        // Create globe using Three.js
        const width = container.clientWidth;
        const height = container.clientHeight;

        // Scene setup
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        camera.position.z = 2.5;

        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(width, height);
        renderer.setClearColor(0x000000, 0);
        container.appendChild(renderer.domElement);

        // Create globe geometry
        const geometry = new THREE.SphereGeometry(1, 64, 64);

        // Create globe material with gradient
        const canvas = document.createElement('canvas');
        canvas.width = 2048;
        canvas.height = 1024;
        const ctx = canvas.getContext('2d');

        // Draw gradient background
        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        gradient.addColorStop(0, '#0a3d62');
        gradient.addColorStop(0.5, '#1b5d84');
        gradient.addColorStop(1, '#0f3460');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Add some noise/texture
        for (let i = 0; i < 1000; i++) {
            const x = Math.random() * canvas.width;
            const y = Math.random() * canvas.height;
            const size = Math.random() * 2 + 1;
            ctx.fillStyle = `rgba(0, 212, 255, ${Math.random() * 0.3})`;
            ctx.fillRect(x, y, size, size);
        }

        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.MeshPhongMaterial({ map: texture });
        const globe = new THREE.Mesh(geometry, material);
        scene.add(globe);

        // Add lights
        const light = new THREE.DirectionalLight(0xffffff, 0.8);
        light.position.set(5, 3, 5);
        scene.add(light);

        scene.add(new THREE.AmbientLight(0xffffff, 0.4));

        // Add image markers as points
        const markerGeometry = new THREE.BufferGeometry();
        const markerPositions = [];
        const markerColors = [];

        const clusterColorMap = {
            'cluster_0': new THREE.Color('#FF6B6B'),
            'cluster_1': new THREE.Color('#4ECDC4'),
            'cluster_2': new THREE.Color('#45B7D1'),
            'cluster_3': new THREE.Color('#96CEB4'),
            'cluster_4': new THREE.Color('#FECA57')
        };

        this.processedData.images.forEach(img => {
            const lat = img.latitude * Math.PI / 180;
            const lon = img.longitude * Math.PI / 180;

            const x = Math.cos(lat) * Math.cos(lon);
            const y = Math.sin(lat);
            const z = Math.cos(lat) * Math.sin(lon);

            markerPositions.push(x, y, z);

            const cluster = img.cluster || 'default';
            const color = clusterColorMap[cluster] || new THREE.Color('#A0A0A0');
            markerColors.push(color.r, color.g, color.b);
        });

        markerGeometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(markerPositions), 3));
        markerGeometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(markerColors), 3));

        const markerMaterial = new THREE.PointsMaterial({
            size: 0.05,
            vertexColors: true,
            sizeAttenuation: true
        });

        const markers = new THREE.Points(markerGeometry, markerMaterial);
        scene.add(markers);

        // Animation loop
        let animationId;
        const animate = () => {
            animationId = requestAnimationFrame(animate);

            // Rotate globe
            globe.rotation.y += 0.0003;
            markers.rotation.y += 0.0003;

            renderer.render(scene, camera);
        };

        animate();

        // Handle window resize
        const onWindowResize = () => {
            const newWidth = container.clientWidth;
            const newHeight = container.clientHeight;
            camera.aspect = newWidth / newHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(newWidth, newHeight);
        };

        window.addEventListener('resize', onWindowResize);

        // Mouse controls
        let isDragging = false;
        let previousMousePosition = { x: 0, y: 0 };

        renderer.domElement.addEventListener('mousedown', (e) => {
            isDragging = true;
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        renderer.domElement.addEventListener('mousemove', (e) => {
            if (isDragging) {
                const deltaMove = {
                    x: e.clientX - previousMousePosition.x,
                    y: e.clientY - previousMousePosition.y
                };

                globe.rotation.y += deltaMove.x * 0.01;
                globe.rotation.x += deltaMove.y * 0.01;
                markers.rotation.y = globe.rotation.y;
                markers.rotation.x = globe.rotation.x;

                previousMousePosition = { x: e.clientX, y: e.clientY };
            }
        });

        renderer.domElement.addEventListener('mouseup', () => {
            isDragging = false;
        });

        // Zoom with mouse wheel
        renderer.domElement.addEventListener('wheel', (e) => {
            e.preventDefault();
            camera.position.z += e.deltaY * 0.001;
            camera.position.z = Math.max(1.5, Math.min(5, camera.position.z));
        });

        console.log('✅ Globe initialized');
    }

    // ========================================
    // RESULTS TABLE
    // ========================================

    populateResults() {
        const tbody = document.getElementById('resultsBody');
        tbody.innerHTML = '';

        this.processedData.images.forEach(img => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${img.filename}</strong></td>
                <td>${img.latitude.toFixed(4)}, ${img.longitude.toFixed(4)}</td>
                <td><span class="tag-badge">${img.cluster || 'N/A'}</span></td>
                <td>
                    ${img.top_tags.slice(0, 3).map(tag => 
                        `<span class="tag-badge">${tag}</span>`
                    ).join('')}
                </td>
                <td>${Array.isArray(img.objects) ? img.objects.slice(0, 5).join(', ') : 'None'}</td>
            `;
            tbody.appendChild(row);
        });
    }

    // ========================================
    // UI UTILITIES
    // ========================================

    showLoading(message = 'Processing...') {
        const spinner = document.getElementById('loadingSpinner');
        document.getElementById('loadingText').textContent = message;
        spinner.style.display = 'flex';
    }

    updateLoading(message) {
        document.getElementById('loadingText').textContent = message;
    }

    hideLoading() {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

// ========================================
// INITIALIZE APP
// ========================================

let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new GeoSpatialApp();
    console.log('🚀 GeoSpatial App initialized');
});
