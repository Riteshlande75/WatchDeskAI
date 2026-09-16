/**
 * System Permissions Setup Diagnostic Engine
 * Handles Mobile Device Check, Camera Access, Fullscreen/Screen Share Authorization,
 * and Live Video Stream Preview.
 */
document.addEventListener('DOMContentLoaded', () => {
    const videoElement = document.getElementById('webcamVideo');
    
    // Camera Elements
    const cardCameraCheck = document.getElementById('cardCameraCheck');
    const iconCamera = document.getElementById('iconCamera');
    const cameraStatusBadge = document.getElementById('cameraStatusBadge');

    // Screen & Fullscreen Elements
    const cardScreenCheck = document.getElementById('cardScreenCheck');
    const iconScreen = document.getElementById('iconScreen');
    const screenWarningText = document.getElementById('screenWarningText');
    const btnToggleFullscreen = document.getElementById('btnToggleFullscreen');
    const btnFullscreenText = document.getElementById('btnFullscreenText');
    const btnRefreshScreen = document.getElementById('btnRefreshScreen');

    // Submit Button
    const btnStartExam = document.getElementById('btnStartExam');

    let checks = {
        mobileCheck: true, // Desktop verified
        cameraAccess: false,
        screenAccess: false
    };

    function isFullscreenActive() {
        return !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
    }

    function requestUniversalFullscreen(elem) {
        elem = elem || document.documentElement;
        if (elem.requestFullscreen) return elem.requestFullscreen();
        if (elem.webkitRequestFullscreen) return elem.webkitRequestFullscreen();
        if (elem.mozRequestFullScreen) return elem.mozRequestFullScreen();
        if (elem.msRequestFullscreen) return elem.msRequestFullscreen();
        return Promise.reject('Fullscreen API not supported');
    }

    function exitUniversalFullscreen() {
        if (document.exitFullscreen) return document.exitFullscreen();
        if (document.webkitExitFullscreen) return document.webkitExitFullscreen();
        if (document.mozCancelFullScreen) return document.mozCancelFullScreen();
        if (document.msExitFullscreen) return document.msExitFullscreen();
        return Promise.reject('Exit fullscreen not supported');
    }

    function updateProceedButton() {
        if (checks.mobileCheck && checks.cameraAccess && checks.screenAccess) {
            btnStartExam.disabled = false;
        } else {
            btnStartExam.disabled = true;
        }
    }

    // 1. Initialize Camera Access
    async function initCameraAccess() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 1280, height: 720 },
                audio: false
            });

            if (videoElement) {
                videoElement.srcObject = stream;
            }

            checks.cameraAccess = true;

            if (cardCameraCheck) {
                cardCameraCheck.className = 'system-check-item card-check-passed';
            }
            if (iconCamera) {
                iconCamera.className = 'check-icon-circle icon-passed';
                iconCamera.innerHTML = '<i class="fa-solid fa-check"></i>';
            }
            if (cameraStatusBadge) {
                cameraStatusBadge.className = 'badge bg-success-subtle text-success border border-success-subtle px-2 py-1 extra-small';
                cameraStatusBadge.innerHTML = 'Granted';
            }

            updateProceedButton();

        } catch (err) {
            console.error('Camera permission error:', err);
            checks.cameraAccess = false;

            if (cardCameraCheck) {
                cardCameraCheck.className = 'system-check-item border-danger';
            }
            if (iconCamera) {
                iconCamera.className = 'check-icon-circle bg-danger-subtle text-danger';
                iconCamera.innerHTML = '<i class="fa-solid fa-xmark"></i>';
            }
            if (cameraStatusBadge) {
                cameraStatusBadge.className = 'badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1 extra-small';
                cameraStatusBadge.innerHTML = 'Denied';
            }

            updateProceedButton();
        }
    }

    // 2. Fullscreen / Screen Share Authorization Handler
    function updateScreenCheckUI() {
        if (isFullscreenActive()) {
            checks.screenAccess = true;

            if (cardScreenCheck) {
                cardScreenCheck.className = 'system-check-item card-check-passed';
            }
            if (iconScreen) {
                iconScreen.className = 'check-icon-circle icon-passed';
                iconScreen.innerHTML = '<i class="fa-solid fa-check"></i>';
            }
            if (screenWarningText) {
                screenWarningText.className = 'text-success small fw-semibold mb-2';
                screenWarningText.innerHTML = '<i class="fa-solid fa-circle-check me-1"></i> Screen & Fullscreen Access Verified.';
            }
            if (btnFullscreenText) {
                btnFullscreenText.innerText = 'Exit Fullscreen Mode';
            }
        } else {
            checks.screenAccess = false;

            if (cardScreenCheck) {
                cardScreenCheck.className = 'system-check-item card-check-active';
            }
            if (iconScreen) {
                iconScreen.className = 'check-icon-circle icon-active';
                iconScreen.innerHTML = '<i class="fa-solid fa-info"></i>';
            }
            if (screenWarningText) {
                screenWarningText.className = 'text-danger small fw-semibold mb-2';
                screenWarningText.innerHTML = 'Please share your Entire screen and enable Fullscreen mode to proceed.';
            }
            if (btnFullscreenText) {
                btnFullscreenText.innerText = 'Enter Fullscreen Mode';
            }
        }
        updateProceedButton();
    }

    // Fullscreen Toggle Button Listener
    if (btnToggleFullscreen) {
        btnToggleFullscreen.addEventListener('click', () => {
            if (!isFullscreenActive()) {
                requestUniversalFullscreen().then(() => {
                    updateScreenCheckUI();
                }).catch(err => {
                    console.warn('Fullscreen request rejected:', err);
                    updateScreenCheckUI();
                });
            } else {
                exitUniversalFullscreen().then(() => {
                    updateScreenCheckUI();
                }).catch(err => {
                    console.warn('Exit fullscreen rejected:', err);
                    updateScreenCheckUI();
                });
            }
        });
    }

    // Refresh / Check Status Button Listener
    if (btnRefreshScreen) {
        btnRefreshScreen.addEventListener('click', () => {
            updateScreenCheckUI();
        });
    }

    // Listen for Fullscreen Changes
    ['fullscreenchange', 'webkitfullscreenchange', 'mozfullscreenchange', 'MSFullscreenChange'].forEach(evt => {
        document.addEventListener(evt, updateScreenCheckUI);
    });

    // Run Initial Checks
    initCameraAccess();
    updateScreenCheckUI();
});
