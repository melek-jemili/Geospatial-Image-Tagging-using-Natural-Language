/**
 * GeoVision Application - Main Logic
 */

class GeoVisionApp {
    constructor() {
        this.selectedFiles = [];
        this.maxFiles = 20;
        this.uploadedPaths = [];
        
        this.init();
    }

    // ============================================================
    // INITIALIZATION
    // ============================================================

    init() {
        this.setupEventListeners();
        this.checkHealth();
    }

    setupEventListeners() {
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');
        const processBtn = document.getElementById('processBtn');
        const clearBtn = document.getElementById('clearBtn');
        const viewMapBtn = document.getElementById('viewMapBtn');

        // Upload Zone Events
        uploadZone.addEventListener('click', () => fileInput.click());
        
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('drag-over');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('drag-over');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-over');
            this.handleFiles(Array.from(e.dataTransfer.files));
        });

        // File Input
        fileInput.addEventListener('change', (e) => {
            this.handleFiles(Array.from(e.target.files));
        });

        // Button Events
        processBtn.addEventListener('click', () => this.processImages());
        clearBtn.addEventListener('click', () => this.clearFiles());
        viewMapBtn.addEventListener('click', () => this.openMap());
    }

    checkHealth() {
        axios.get('/api/health')
            .then(response => {
                console.log('✅ Server is running');
            })
            .catch(error => {
                console.error('❌ Server error:', error);
                this.showStatus('Server not responding', 'error');
            });
    }

    // ============================================================
    // FILE HANDLING
    // ============================================================

    handleFiles(files) {
        const validFiles = files.filter(file => {
            const ext = file.name.split('.').pop().toLowerCase();
            const allowed = ['jpg', 'jpeg', 'png', 'tiff', 'heic', 'gif', 'bmp'];
            return allowed.includes(ext);
        });

        if (validFiles.length === 0) {
            this.showStatus('No valid images selected', 'error');
            return;
        }

        if (this.selectedFiles.length + validFiles.length > this.maxFiles) {
            this.showStatus(`Maximum ${this.maxFiles} images allowed`, 'error');
            return;
        }

        this.selectedFiles.push(...validFiles);
        this.updatePreview();
        this.showStatus(`Added ${validFiles.length} image(s)`, 'success');
    }

    updatePreview() {
        const previewSection = document.getElementById('previewSection');
        const previewGrid = document.getElementById('previewGrid');
        const uploadCount = document.getElementById('uploadCount');
        const processBtn = document.getElementById('processBtn');

        uploadCount.textContent = this.selectedFiles.length;

        if (this.selectedFiles.length === 0) {
            previewSection.classList.add('hidden');
            processBtn.disabled = true;
        } else {
            previewSection.classList.remove('hidden');
            processBtn.disabled = false;
        }

        previewGrid.innerHTML = this.selectedFiles.map((file, idx) => `
            <div class="preview-item" data-index="${idx}">
                <img src="${URL.createObjectURL(file)}" alt="${file.name}">
                <button class="preview-remove" onclick="app.removeFile(${idx})" type="button">
                    <i class="fas fa-times"></i>
                </button>
                <div style="position: absolute; bottom: 5px; left: 5px; font-size: 0.7rem; color: var(--primary); background: rgba(0,0,0,0.5); padding: 2px 4px; border-radius: 4px;">
                    ${(file.size / 1024 / 1024).toFixed(1)}MB
                </div>
            </div>
        `).join('');
    }

    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updatePreview();
    }

    clearFiles() {
        if (confirm('Clear all selected images?')) {
            this.selectedFiles = [];
            document.getElementById('fileInput').value = '';
            this.updatePreview();
        }
    }

    // ============================================================
    // UPLOAD & PROCESSING
    // ============================================================

    async processImages() {
        if (this.selectedFiles.length === 0) {
            this.showStatus('Select images first', 'error');
            return;
        }

        this.showLoading();

        try {
            // Step 1: Upload
            this.updateLoadingStep(1);
            this.updateLoadingText('Uploading images...');

            const formData = new FormData();
            this.selectedFiles.forEach(file => {
                formData.append('images', file);
            });

            const uploadResponse = await axios.post('/api/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            if (!uploadResponse.data.success) {
                throw new Error('Upload failed');
            }

            this.uploadedPaths = uploadResponse.data.images.map(img => img.path);
            console.log(`✅ Uploaded ${this.uploadedPaths.length} images`);

            // Step 2-5: Process
            this.updateLoadingStep(2);
            this.updateLoadingText('Processing images through pipeline...');
            
            const processResponse = await axios.post('/api/process', {
                image_paths: this.uploadedPaths
            });

            if (!processResponse.data.success) {
                throw new Error('Processing failed');
            }

            const results = processResponse.data;
            
            // Update steps as processing happens
            this.updateLoadingStep(3);
            await this.sleep(500);
            
            this.updateLoadingStep(4);
            this.updateLoadingText('Running quantum optimization...');
            await this.sleep(1000);
            
            this.updateLoadingStep(5);
            this.updateLoadingText('Generating interactive map...');
            await this.sleep(500);

            // Show success
            this.hideLoading();
            this.showSuccess(results);

            console.log('✅ Processing complete:', results);

        } catch (error) {
            this.hideLoading();
            console.error('❌ Error:', error);
            this.showStatus(error.response?.data?.error || error.message, 'error');
        }
    }

    // ============================================================
    // UI METHODS
    // ============================================================

    showLoading() {
        document.getElementById('loadingSpinner').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loadingSpinner').classList.add('hidden');
    }

    updateLoadingText(text) {
        document.getElementById('loadingText').textContent = text;
    }

    updateLoadingStep(stepNum) {
        // Remove active from all
        document.querySelectorAll('.loading-step').forEach(step => {
            step.classList.remove('active');
        });

        // Add active to current and previous
        for (let i = 1; i <= stepNum; i++) {
            const step = document.getElementById(`step-${i}`);
            if (step) step.classList.add('active');
        }
    }

    showSuccess(results) {
        document.getElementById('statsImages').textContent = results.summary.images_processed;
        document.getElementById('statsClusters').textContent = results.summary.clusters_found;
        document.getElementById('successOverlay').classList.remove('hidden');
    }

    openMap() {
        window.location.href = '/map_with_clustering.html';
    }

    showStatus(message, type = 'info') {
        const status = document.createElement('div');
        status.className = `status-message ${type}`;
        
        const icons = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'info': 'fa-info-circle'
        };

        status.innerHTML = `
            <div style="display: flex; align-items: center;">
                <i class="fas ${icons[type]} status-icon"></i>
                <div class="status-content">
                    <p>${message}</p>
                </div>
            </div>
        `;

        document.body.appendChild(status);

        setTimeout(() => {
            status.style.animation = 'slideOut 0.5s ease-out forwards';
            setTimeout(() => status.remove(), 500);
        }, 4000);
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// ============================================================
// INITIALIZE APP
// ============================================================

let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new GeoVisionApp();
    console.log('🚀 GeoVision App initialized');
});

// Add slide out animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from { opacity: 1; transform: translateX(0); }
        to { opacity: 0; transform: translateX(100px); }
    }
`;
document.head.appendChild(style);