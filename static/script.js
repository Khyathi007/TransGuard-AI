let mediaStream = null;
let mediaRecorder = null;
let recordedChunks = [];
let sirenAudioInterval = null;
let captureCount = 0;
let currentActiveIncidentId = null;
let animFrameId = null;
const MAX_CAPTURES = 60;

// Theme Toggle Functionality
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('transguard_theme', newTheme);
}

document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('transguard_theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateClock();
    
    // Automatic dashboard polling every 2 seconds
    setInterval(pollDashboardState, 2000);
});

function updateClock() {
    const timeEl = document.getElementById('live-clock-time');
    const dateEl = document.getElementById('live-clock-date');
    if (timeEl && dateEl) {
        const now = new Date();
        timeEl.innerText = now.toLocaleTimeString();
        dateEl.innerText = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
    }
}
setInterval(updateClock, 1000);

// Immediate Camera Stream & Continuous Timestamped Canvas Recording (.MP4)
function startCameraAndRecording(incidentId) {
    currentActiveIncidentId = incidentId;
    const videoEl = document.getElementById('webcam-feed');
    const canvasEl = document.getElementById('capture-canvas');
    const overlayEl = document.getElementById('camera-overlay-box');
    if (!videoEl || !canvasEl) return;

    navigator.mediaDevices.getUserMedia({ 
        video: { width: { ideal: 1280 }, height: { ideal: 720 } }, 
        audio: false 
    })
    .then(stream => {
        mediaStream = stream;
        videoEl.srcObject = stream;
        
        videoEl.onloadedmetadata = () => {
            videoEl.play();

            if (overlayEl) overlayEl.style.display = 'none';

            const tag = document.getElementById('cam-status-tag');
            if (tag) {
                tag.innerText = 'LIVE STREAMING & RECORDING';
                tag.style.background = '#dcfce7';
                tag.style.color = '#15803d';
            }

            // 1. Continuous high-fps canvas render loop (Pushes live frames + timestamps continuously)
            function renderLoop() {
                if (mediaStream && !videoEl.paused && !videoEl.ended) {
                    drawTimestampToCanvas(videoEl, canvasEl);
                    animFrameId = requestAnimationFrame(renderLoop);
                }
            }
            if (animFrameId) cancelAnimationFrame(animFrameId);
            renderLoop();

            // 2. Capture live stream from canvas (30 FPS)
            const canvasStream = canvasEl.captureStream(30);
            recordedChunks = [];

            // Strict MP4 options selection for QuickTime and universal player playback
            let options = { mimeType: 'video/mp4;codecs=avc1' };
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options = { mimeType: 'video/mp4' };
            }

            try {
                mediaRecorder = new MediaRecorder(canvasStream, options);
            } catch (e) {
                mediaRecorder = new MediaRecorder(canvasStream);
            }

            mediaRecorder.ondataavailable = event => {
                if (event.data && event.data.size > 0) {
                    recordedChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = uploadRecordedVideo;
            
            // Collect chunks continuously without time cutoff
            mediaRecorder.start(250);

            // 3. Still image capture loop
            captureCount = 0;
            const captureInterval = setInterval(() => {
                if (captureCount >= MAX_CAPTURES || !mediaStream) {
                    clearInterval(captureInterval);
                    return;
                }
                captureFrame(videoEl, canvasEl, incidentId);
            }, 2000);
        };
    })
    .catch(err => console.warn("Camera access denied or unavailable:", err));
}

function drawTimestampToCanvas(video, canvas) {
    if (!video || video.paused || video.ended) return;

    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;
    if (width === 0 || height === 0) return;

    if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
    }

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, width, height);

    // High-contrast, sharp, crisp timestamp watermark overlay
    const now = new Date();
    const timestampStr = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) + " " + now.toLocaleTimeString();

    const boxWidth = 300;
    const boxHeight = 38;
    const paddingX = 14;
    const paddingY = height - 52;

    ctx.fillStyle = "rgba(15, 23, 42, 0.95)";
    ctx.fillRect(paddingX, paddingY, boxWidth, boxHeight);

    ctx.fillStyle = "#22c55e"; // Accent green border bar
    ctx.fillRect(paddingX, paddingY, 5, boxHeight);

    ctx.font = "bold 15px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
    ctx.fillStyle = "#ffffff";
    ctx.fillText("📷 " + timestampStr, paddingX + 14, paddingY + 25);
}

function captureFrame(video, canvas, incidentId) {
    if (!mediaStream || video.paused || video.ended) return;

    drawTimestampToCanvas(video, canvas);
    const base64Img = canvas.toDataURL('image/jpeg', 0.95);

    fetch('/api/upload_frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ incident_id: incidentId, image: base64Img })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            captureCount = data.total_count || (captureCount + 1);
            const subtextEl = document.getElementById('alert-card-subtext');
            if (subtextEl) subtextEl.innerText = `${captureCount} images captured`;
            appendGalleryImage(data.path, data.captured_at);
        }
    });
}

function appendGalleryImage(path, timeStr) {
    const gallery = document.getElementById('live-gallery-grid');
    if (!gallery) return;

    const div = document.createElement('div');
    div.className = 'thumb-box';
    div.innerHTML = `<img src="/static/${path}" alt="frame"><div class="thumb-time">${timeStr}</div>`;
    gallery.insertBefore(div, gallery.firstChild);
    if (gallery.children.length > 8) gallery.removeChild(gallery.lastChild);
}

function stopCamera() {
    if (animFrameId) {
        cancelAnimationFrame(animFrameId);
        animFrameId = null;
    }

    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }

    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    const videoEl = document.getElementById('webcam-feed');
    if (videoEl) videoEl.srcObject = null;

    const overlayEl = document.getElementById('camera-overlay-box');
    if (overlayEl) overlayEl.style.display = 'block';

    const tag = document.getElementById('cam-status-tag');
    if (tag) {
        tag.innerText = 'STANDBY';
        tag.style.background = '#f1f5f9';
        tag.style.color = '#64748b';
    }
}

// Upload full-length MP4 video to server silently
function uploadRecordedVideo() {
    if (recordedChunks.length === 0 || !currentActiveIncidentId) return;

    // Force MP4 blob output
    const rawBlob = new Blob(recordedChunks, { type: 'video/mp4' });

    const formData = new FormData();
    formData.append('video', rawBlob, `incident_${currentActiveIncidentId}.mp4`);
    formData.append('incident_id', currentActiveIncidentId);

    fetch('/api/upload_video', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => console.log("Recorded MP4 video stored to server successfully:", data.video_path));
}

function openTestIncidentModal() {
    fetch('/api/simulate_alert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ response: 'PENDING' })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            startSirenSound();
            startCameraAndRecording(data.incident_id);
            pollDashboardState();

            const modal = document.getElementById('sim-modal');
            if (modal) modal.style.display = 'flex';
        }
    });
}

function selectOwnerResponse(chosenResponse) {
    const modal = document.getElementById('sim-modal');
    if (modal) modal.style.display = 'none';

    if (currentActiveIncidentId) {
        fetch('/api/update_threat_level', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ incident_id: currentActiveIncidentId, response: chosenResponse })
        })
        .then(res => res.json())
        .then(() => pollDashboardState());
    }
}

let activeAlertTriggered = false;

function pollDashboardState() {
    fetch('/api/poll')
        .then(res => res.json())
        .then(data => {
            if (!data.authenticated) return;

            const alertBadge = document.getElementById('alert-count-badge');
            const alertStatCount = document.getElementById('stat-alert-count');
            const statusCardVal = document.getElementById('status-card-val');
            const subtextEl = document.getElementById('alert-card-subtext');
            const shieldBox = document.getElementById('shield-status-box');

            if (alertBadge) alertBadge.innerText = data.alert_count;
            if (alertStatCount) alertStatCount.innerText = data.alert_count;

            if (data.has_active) {
                document.body.classList.add('alert-active');

                if (!activeAlertTriggered) {
                    activeAlertTriggered = true;
                    startSirenSound();
                    startCameraAndRecording(data.incident.id);
                }

                if (statusCardVal) {
                    statusCardVal.innerHTML = data.incident.threat_level === 'HIGH' ? '<span class="val-high">HIGH ALERT</span>' : '<span class="val-low">LOW ALERT</span>';
                }

                if (subtextEl) subtextEl.innerText = `${data.captured_count} images captured`;

                if (shieldBox) {
                    shieldBox.className = 'shield-card extended-bar';
                    shieldBox.innerHTML = `
                        <div class="shield-header-tag">SECURITY MONITOR</div>
                        <div class="shield-icon-container shield-alert">
                            <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                                <line x1="12" y1="8" x2="12" y2="12"></line>
                                <line x1="12" y1="16" x2="12.01" y2="16"></line>
                            </svg>
                        </div>
                        <div class="shield-title" style="color: var(--accent-red);">UNAUTHORIZED ACCESS</div>
                        <div class="shield-desc">Transformer breach detected. Recording live video feed.</div>
                    `;
                }
            } else {
                document.body.classList.remove('alert-active');
                if (activeAlertTriggered) {
                    stopCamera();
                    stopSirenSound();
                    activeAlertTriggered = false;
                }
                if (statusCardVal) statusCardVal.innerHTML = '<span class="val-safe">SAFE</span>';
                if (subtextEl) subtextEl.innerText = '0 images captured';
            }
        });
}

function startSirenSound() {
    if (sirenAudioInterval) return;
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        let highTone = true;
        sirenAudioInterval = setInterval(() => {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(highTone ? 950 : 650, audioCtx.currentTime);
            gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.35);
            highTone = !highTone;
        }, 400);
    } catch(e) {}
}

function stopSirenSound() {
    if (sirenAudioInterval) {
        clearInterval(sirenAudioInterval);
        sirenAudioInterval = null;
    }
}

function stopAlertManually() {
    stopSirenSound();
    stopCamera();
    document.body.classList.remove('alert-active');
    fetch('/api/stop_alert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ incident_id: currentActiveIncidentId })
    }).then(() => pollDashboardState());
}

function triggerSimulatedAlertModal(chosenResponse) {
    fetch('/api/simulate_alert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ response: chosenResponse })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            pollDashboardState();
        }
    });
}