// Medical AI Platform - Frontend JavaScript
// Professional, minimal implementation

const API_BASE = window.location.origin;
let currentFile = null;

// Check authentication on page load
function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        // Not logged in, redirect to login
        window.location.href = '/login.html';
        return false;
    }
    return true;
}

// Run auth check immediately
if (!checkAuth()) {
    // Stop executing the rest of the script
    throw new Error('Authentication required');
}

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function () {
    // DOM Elements - with null checks
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const diseaseType = document.getElementById('diseaseType');
    const patientId = document.getElementById('patientId');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultsSection = document.getElementById('resultsSection');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const newAnalysisBtn = document.getElementById('newAnalysisBtn');
    const detailsToggle = document.getElementById('detailsToggle');
    const detailsContent = document.getElementById('detailsContent');

    // Load System Stats (Hospital Count)
    loadSystemStats();

    function loadSystemStats() {
        const token = localStorage.getItem('access_token');
        if (!token) return;

        fetch(`${API_BASE}/api/v1/federated/hospitals`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
            .then(response => response.json())
            .then(data => {
                const countElement = document.getElementById('active-hospitals-count');
                if (countElement && data.total_hospitals !== undefined) {
                    countElement.textContent = `${data.total_hospitals} Hospitals`;
                }
            })
            .catch(err => console.error('Failed to load system stats:', err));
    }

    // Exit if this isn't the analysis page
    if (!uploadArea || !fileInput || !analyzeBtn) {
        console.log('Not on analysis page, skipping analysis-specific initialization');
        return;
    }

    // Upload Area Handlers
    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    // File Selection Handler
    function handleFileSelect(file) {
        // Validate file
        const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
        const maxSize = 10 * 1024 * 1024; // 10MB

        if (!validTypes.includes(file.type)) {
            showNotification('Please upload a valid image file (JPG, PNG)', 'error');
            return;
        }

        if (file.size > maxSize) {
            showNotification('File size must be less than 10MB', 'error');
            return;
        }

        currentFile = file;

        // Update UI
        const fileName = file.name;
        uploadArea.innerHTML = `
        <div class="upload-icon-wrapper">
            <svg class="upload-icon" viewBox="0 0 64 64" fill="none">
                <circle cx="32" cy="32" r="28" stroke="url(#upload-gradient)" stroke-width="3"/>
                <path d="M24 32L29 37L40 26" stroke="url(#upload-gradient)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </div>
        <h3 class="upload-title">✓ ${fileName}</h3>
        <p class="upload-subtitle">Click to change file</p>
    `;

        checkFormValidity();
    }

    // Form Validation
    diseaseType.addEventListener('change', checkFormValidity);
    patientId.addEventListener('input', checkFormValidity);

    function checkFormValidity() {
        const isValid = currentFile && diseaseType.value;
        analyzeBtn.disabled = !isValid;
    }

    // Analyze Button Handler
    analyzeBtn.addEventListener('click', async () => {
        if (!currentFile || !diseaseType.value) return;

        showLoading(true);

        try {
            // Create FormData
            const formData = new FormData();
            formData.append('file', currentFile);
            formData.append('disease_type', diseaseType.value);
            if (patientId.value) {
                formData.append('patient_id', patientId.value);
            }

            // Send request with JWT token
            const token = localStorage.getItem('access_token');

            if (!token) {
                showNotification('Please login first', 'error');
                setTimeout(() => {
                    window.location.href = '/login.html';
                }, 2000);
                return;
            }

            // Create AbortController for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 second timeout

            const response = await fetch(`${API_BASE}/api/v1/inference`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (response.status === 401) {
                // Token expired, redirect to login
                showNotification('Session expired. Please login again.', 'error');
                setTimeout(() => {
                    window.location.href = '/login.html';
                }, 2000);
                return;
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                console.error('Server error:', errorData);
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            // Debug: log the result structure
            console.log('API Response:', result);

            // Check for error in response
            if (result.error) {
                throw new Error(result.error);
            }

            // Display results
            displayResults(result);

            // Increment inference count for federated dashboard
            let inferenceCount = parseInt(localStorage.getItem('inference_count') || '0');
            inferenceCount++;
            localStorage.setItem('inference_count', inferenceCount.toString());

            showNotification('Analysis completed successfully', 'success');

        } catch (error) {
            console.error('Analysis error:', error);
            showNotification('Analysis failed. Please try again.', 'error');
        } finally {
            showLoading(false);
        }
    });

    // Display Results
    function displayResults(result) {
        // Scroll to results
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth' });

        // Handle different response formats
        let diagnosis, modelUsed, processingTime;

        if (result.predictions && result.predictions.length > 0) {
            // Array format from API
            diagnosis = result.predictions[0];
            modelUsed = result.model_used || 'Medical AI Model';
            processingTime = result.processing_time || 1.5;
        } else if (result.predicted_class) {
            // Direct model result format
            diagnosis = {
                class: result.predicted_class,
                confidence: result.confidence
            };
            modelUsed = result.model || 'Medical AI Model';
            processingTime = result.inference_time || result.processing_time || 1.5;
        } else {
            console.error('Unknown result format:', result);
            showNotification('Invalid result format received', 'error');
            return;
        }

        // Primary diagnosis
        document.getElementById('diagnosisName').textContent = diagnosis.class || diagnosis.predicted_class || 'Unknown';
        document.getElementById('confidenceText').textContent =
            `${(diagnosis.confidence * 100).toFixed(1)}% Confidence`;

        // Animate confidence bar
        setTimeout(() => {
            document.getElementById('confidenceFill').style.width =
                `${diagnosis.confidence * 100}%`;
        }, 100);

        // No confidence badge in new design - confidence shown in bar

        // Analysis details
        document.getElementById('modelName').textContent = modelUsed;
        document.getElementById('processingTime').textContent =
            `${processingTime.toFixed(2)}s`;
        document.getElementById('requestId').textContent =
            result.request_id || generateRequestId();

        // Image preview
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('previewImage').src = e.target.result;
        };
        reader.readAsDataURL(currentFile);
    }

    // New Analysis Handler
    newAnalysisBtn.addEventListener('click', () => {
        // Reset form
        currentFile = null;
        diseaseType.value = '';
        patientId.value = '';
        fileInput.value = '';

        // Reset upload area
        uploadArea.innerHTML = `
        <div class="upload-icon-wrapper">
            <svg class="upload-icon" viewBox="0 0 64 64" fill="none">
                <rect width="64" height="64" rx="16" fill="url(#upload-gradient)" opacity="0.1"/>
                <path d="M32 42V22M32 22L24 30M32 22L40 30" stroke="url(#upload-gradient)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M20 36V44C20 46.2091 21.7909 48 24 48H40C42.2091 48 44 46.2091 44 44V36" stroke="url(#upload-gradient)" stroke-width="3" stroke-linecap="round"/>
            </svg>
        </div>
        <h3 class="upload-title">Drop medical image here</h3>
        <p class="upload-subtitle">or click to browse files</p>
        <div class="upload-meta">
            <span class="upload-format">DICOM • PNG • JPG</span>
            <span class="upload-size">Maximum 10MB</span>
        </div>
    `;

        // Hide results
        resultsSection.style.display = 'none';

        // Scroll to diagnostics
        document.getElementById('diagnostics').scrollIntoView({ behavior: 'smooth' });

        checkFormValidity();
    });

    // Details Toggle Handler
    if (detailsToggle && detailsContent) {
        detailsToggle.addEventListener('click', () => {
            detailsContent.classList.toggle('hidden');
            const toggleText = detailsToggle.querySelector('span');
            const isHidden = detailsContent.classList.contains('hidden');
            toggleText.textContent = isHidden ? 'Show Details' : 'Hide Details';
        });
    }

    // Loading Overlay
    function showLoading(show) {
        loadingOverlay.style.display = show ? 'flex' : 'none';
    }

    // Notification System
    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'};
        color: white;
        border-radius: 0.5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
        z-index: 10000;
        font-weight: 500;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    `;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Remove after 4 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }

    // Utility Functions
    function generateRequestId() {
        return 'REQ-' + Date.now().toString(36).toUpperCase() + '-' +
            Math.random().toString(36).substr(2, 5).toUpperCase();
    }

    // Smooth Scrolling for Nav Links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Portal Login Button - Redirect to login page
    const portalBtn = document.querySelector('.btn-nav-primary');
    if (portalBtn) {
        portalBtn.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = '/login.html';
        });
    }

    // Hero CTA Buttons
    const startAnalysisBtn = document.querySelector('.btn-hero-primary');
    if (startAnalysisBtn) {
        startAnalysisBtn.addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('diagnostics').scrollIntoView({ behavior: 'smooth' });
        });
    }

    const watchDemoBtn = document.querySelector('.btn-hero-secondary');
    if (watchDemoBtn) {
        watchDemoBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showDemoModal();
        });
    }

    // Demo Modal
    function showDemoModal() {
        const modal = document.createElement('div');
        modal.style.cssText = `
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.95);
        backdrop-filter: blur(10px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        padding: 2rem;
    `;

        modal.innerHTML = `
        <div style="
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 2rem;
            max-width: 600px;
            width: 100%;
            position: relative;
        ">
            <button id="closeModal" style="
                position: absolute;
                top: 1rem;
                right: 1rem;
                background: transparent;
                border: none;
                color: white;
                font-size: 1.5rem;
                cursor: pointer;
                padding: 0.5rem;
                line-height: 1;
            ">×</button>
            
            <h3 style="
                font-size: 1.5rem;
                font-weight: 700;
                margin-bottom: 1rem;
                color: white;
            ">System Demo</h3>
            
            <div style="
                background: rgba(255, 255, 255, 0.02);
                border-radius: 8px;
                padding: 1.5rem;
                margin-bottom: 1.5rem;
            ">
                <p style="color: var(--color-text-secondary); line-height: 1.8; margin-bottom: 1rem;">
                    <strong style="color: white;">🔬 How to Use:</strong><br>
                    1. Navigate to "Diagnostics" section<br>
                    2. Upload a medical image (DICOM, PNG, JPG)<br>
                    3. Select disease category<br>
                    4. Click "Analyze Image"<br>
                    5. View real-time AI diagnostic results
                </p>
                
                <p style="color: var(--color-text-secondary); line-height: 1.8;">
                    <strong style="color: white;">🔒 Privacy Features:</strong><br>
                    • Split Learning: 233x data reduction<br>
                    • Shuffle DP: ε=0.1 privacy guarantee<br>
                    • Async FedAvg: No synchronization needed<br>
                    • AES-256 + TLS 1.2+ encryption
                </p>
            </div>
            
            <button id="startDemo" style="
                width: 100%;
                padding: 1rem 2rem;
                background: linear-gradient(135deg, #4A9EFF 0%, #1E40AF 100%);
                color: white;
                font-weight: 600;
                border-radius: 9999px;
                border: none;
                cursor: pointer;
                font-size: 1.0625rem;
            ">Start Using Platform</button>
        </div>
    `;

        document.body.appendChild(modal);

        document.getElementById('closeModal').addEventListener('click', () => modal.remove());
        document.getElementById('startDemo').addEventListener('click', () => {
            modal.remove();
            document.getElementById('diagnostics').scrollIntoView({ behavior: 'smooth' });
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
    document.head.appendChild(style);

    // Logout function
    function logout() {
        // Clear all tokens and user data
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('hospital_id');
        localStorage.removeItem('inference_count');

        // Show notification
        showNotification('Logged out successfully', 'success');

        // Redirect to login after short delay
        setTimeout(() => {
            window.location.href = '/login.html';
        }, 1000);
    }

}); // End DOMContentLoaded

// Initialize
console.log('Medical AI Platform initialized');
console.log('API Base:', API_BASE);
