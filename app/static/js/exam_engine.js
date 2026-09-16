/**
 * Interactive Exam Engine
 * Handles question pagination, draft autosaving, countdown timer with auto-submit,
 * question navigator palette status updates, mark for review, proctoring fullscreen enforcement,
 * floating webcam feed, and anti-cheating violation tracking.
 */
document.addEventListener('DOMContentLoaded', () => {
    const examForm = document.getElementById('examForm');
    const submissionId = document.getElementById('submissionId').value;
    const durationMinutes = parseInt(document.getElementById('examDuration').value, 10);
    const timerDisplay = document.getElementById('timerDisplay');
    const questionPanes = document.querySelectorAll('.question-pane');
    const paletteButtons = document.querySelectorAll('.palette-btn');
    const btnNext = document.getElementById('btnNext');
    const btnPrev = document.getElementById('btnPrev');
    const btnClearChoice = document.getElementById('btnClearChoice');
    const btnMarkReview = document.getElementById('btnMarkReview');
    const markReviewText = document.getElementById('markReviewText');
    const chkFlag = document.getElementById('chkFlag');
    const qCurrentIndexSpan = document.getElementById('qCurrentIndex');

    // Fullscreen Controls
    const btnHeaderFullscreen = document.getElementById('btnHeaderFullscreen');
    const headerFullscreenText = document.getElementById('headerFullscreenText');
    const btnEnableFullscreenModal = document.getElementById('btnEnableFullscreenModal');
    const fullscreenWarningModalEl = document.getElementById('fullscreenWarningModal');
    let fullscreenModalInstance = null;

    if (fullscreenWarningModalEl) {
        fullscreenModalInstance = new bootstrap.Modal(fullscreenWarningModalEl, {
            backdrop: 'static',
            keyboard: false
        });
    }

    // Violation Tracker Elements & State (5 Warnings Allowed)
    let violationCount = 0;
    const maxViolations = 5;
    let consecutiveMissingFaceCount = 0;
    const violationCountDisplay = document.getElementById('violationCountDisplay');
    const modalViolationCount = document.getElementById('modalViolationCount');
    const violationModalEl = document.getElementById('violationModal');
    let violationModalInstance = null;

    if (violationModalEl) {
        violationModalInstance = new bootstrap.Modal(violationModalEl, {
            backdrop: 'static',
            keyboard: false
        });
    }

    let currentQuestionIndex = 0;
    const totalQuestions = questionPanes.length;

    // 1. Live Proctoring Webcam Stream Setup & Camera Start/Stop Controls
    let webcamStream = null;
    let isCameraPaused = false;
    const btnToggleCamera = document.getElementById('btnToggleCamera');
    const toggleCamIcon = document.getElementById('toggleCamIcon');
    const toggleCamText = document.getElementById('toggleCamText');
    const recDot = document.getElementById('recDot');
    const procVid = document.getElementById('proctoringVideo');
    const webcamStatusOverlay = document.querySelector('.webcam-overlay-status');

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false })
            .then(stream => {
                webcamStream = stream;
                if (procVid) procVid.srcObject = stream;
            })
            .catch(err => {
                console.warn('Proctoring webcam stream notice:', err);
            });
    }

    if (btnToggleCamera && procVid) {
        btnToggleCamera.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (isCameraPaused) {
                try {
                    const p = procVid.play();
                    if (p && typeof p.catch === 'function') p.catch(err => console.warn('Play notice:', err));
                } catch (err) {
                    console.warn('Camera play notice:', err);
                }
                isCameraPaused = false;
                if (toggleCamText) toggleCamText.innerText = 'Pause';
                if (toggleCamIcon) toggleCamIcon.className = 'fa-solid fa-video text-success';
                if (recDot) recDot.style.background = '#dc3545';
                if (webcamStatusOverlay) webcamStatusOverlay.innerHTML = `<i class="fa-solid fa-shield-halved text-success me-1"></i> Active Feed (100% Integrity)`;
            } else {
                try {
                    procVid.pause();
                } catch (err) {
                    console.warn('Camera pause notice:', err);
                }
                isCameraPaused = true;
                if (toggleCamText) toggleCamText.innerText = 'Start';
                if (toggleCamIcon) toggleCamIcon.className = 'fa-solid fa-video-slash text-danger';
                if (recDot) recDot.style.background = '#6c757d';
                if (webcamStatusOverlay) webcamStatusOverlay.innerHTML = `<i class="fa-solid fa-video-slash text-danger me-1"></i> Camera Paused (50% Integrity)`;
            }
        });
    }

    // Floating Webcam Minimize / Expand Toggle
    const btnMinimizeWebcam = document.getElementById('btnMinimizeWebcam');
    const webcamBody = document.getElementById('webcamBody');
    const minimizeWebcamIcon = document.getElementById('minimizeWebcamIcon');
    if (btnMinimizeWebcam && webcamBody) {
        btnMinimizeWebcam.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const isHidden = webcamBody.classList.contains('d-none');
            if (isHidden) {
                webcamBody.classList.remove('d-none');
                if (minimizeWebcamIcon) minimizeWebcamIcon.className = 'fa-solid fa-chevron-down extra-small';
            } else {
                webcamBody.classList.add('d-none');
                if (minimizeWebcamIcon) minimizeWebcamIcon.className = 'fa-solid fa-chevron-up extra-small';
            }
        });
    }

    let isTerminated = false;

    // Show Violation Alert Modal without duplicate backend logging
    function showViolationModal(title, desc, currentCount) {
        if (violationCountDisplay) violationCountDisplay.innerText = currentCount;
        if (modalViolationCount) modalViolationCount.innerText = currentCount;

        if (violationModalInstance) {
            const titleEl = document.getElementById('violationModalTitle');
            const descEl = document.getElementById('violationModalDesc');
            if (titleEl) titleEl.innerText = title;
            if (descEl) descEl.innerText = desc;
            violationModalInstance.show();
        }
    }

    // 2. Anti-Cheating Security Violation Handler & Activity Logger (For Tab Switches / Focus Loss)
    async function handleSecurityViolation(reason, type) {
        if (remainingSeconds <= 0 || isTerminated) return;

        let isAutoSubmitted = false;
        let redirectUrl = null;

        // Log Browser Activity violation to Flask Backend
        try {
            const response = await fetch('/exam/api/log-violation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    submission_id: submissionId,
                    violation_type: type || 'TAB_SWITCH',
                    details: reason
                })
            });
            const data = await response.json();
            if (data && data.violation_count !== undefined) {
                violationCount = data.violation_count;
            } else {
                violationCount++;
            }
            if (data && data.auto_submitted) {
                isAutoSubmitted = true;
                redirectUrl = data.redirect_url;
            }
        } catch (err) {
            console.warn('Violation log error:', err);
            violationCount++;
        }

        if (violationCountDisplay) violationCountDisplay.innerText = violationCount;
        if (modalViolationCount) modalViolationCount.innerText = violationCount;

        if (isAutoSubmitted || violationCount >= maxViolations) {
            isTerminated = true;
            localStorage.removeItem(storageKey);
            alert('⚠️ Security Violation Limit Exceeded (5/5 Warnings): Your assessment has been automatically terminated and submitted due to repeated proctoring violations.');
            if (redirectUrl) {
                window.location.href = redirectUrl;
            } else {
                examForm.submit();
            }
        } else {
            let title = reason || 'Browser Tab Switch / Window Hidden Detected';
            let desc = 'Navigating away from the active exam window is strictly prohibited. This incident has been logged as a proctoring violation.';
            
            if (type === 'MULTIPLE_FACES') {
                title = 'OpenCV Warning: Multiple Persons Detected in Camera View';
                desc = 'Multiple faces were detected in your camera feed. Only the authorized candidate is permitted during the exam session.';
            } else if (type === 'NO_FACE') {
                title = 'OpenCV Warning: Candidate Face Missing from Camera View';
                desc = 'Your face was not detected in the webcam stream. Please position your face clearly in front of the camera.';
            }
            showViolationModal(title, desc, violationCount);
        }
    }

    // 3. OpenCV Face Monitoring Frame Capture Loop
    const hiddenCanvas = document.createElement('canvas');
    hiddenCanvas.width = 320;
    hiddenCanvas.height = 240;
    const hiddenCtx = hiddenCanvas.getContext('2d');

    async function processOpenCVFrame() {
        if (!procVid || procVid.paused || procVid.ended || remainingSeconds <= 0 || isTerminated || isCameraPaused) return;

        try {
            hiddenCtx.drawImage(procVid, 0, 0, hiddenCanvas.width, hiddenCanvas.height);
            const imageData = hiddenCanvas.toDataURL('image/jpeg', 0.5);
            const shouldLogThisFrame = (consecutiveMissingFaceCount >= 2);

            const res = await fetch('/exam/api/proctor/frame', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    submission_id: submissionId,
                    image_data: imageData,
                    should_log: shouldLogThisFrame
                })
            });
            const data = await res.json();
            if (data.success) {
                const integrityScore = data.integrity_score !== undefined ? data.integrity_score : 100;
                
                if (data.total_violations !== undefined) {
                    violationCount = data.total_violations;
                    if (violationCountDisplay) violationCountDisplay.innerText = violationCount;
                    if (modalViolationCount) modalViolationCount.innerText = violationCount;
                }

                if (data.auto_submitted || violationCount >= maxViolations) {
                    isTerminated = true;
                    localStorage.removeItem(storageKey);
                    alert('⚠️ Security Violation Limit Exceeded (5/5 Warnings): Your exam is being automatically submitted.');
                    window.location.href = data.redirect_url || `/exam/submission/${submissionId}/result`;
                    return;
                }

                if (data.status === 'NO_FACE') {
                    consecutiveMissingFaceCount++;
                    if (webcamStatusOverlay) {
                        webcamStatusOverlay.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-warning me-1"></i> Position face (${integrityScore}% Integrity)`;
                    }
                    if (consecutiveMissingFaceCount >= 3 && shouldLogThisFrame) {
                        showViolationModal(
                            'OpenCV Warning: Candidate Face Missing from Camera View',
                            'Your face was not detected in the webcam stream. Please position your face clearly in front of the camera.',
                            violationCount
                        );
                        consecutiveMissingFaceCount = 0;
                    }
                } else if (data.status === 'MULTIPLE_FACES') {
                    consecutiveMissingFaceCount = 0;
                    if (webcamStatusOverlay) {
                        webcamStatusOverlay.innerHTML = `<i class="fa-solid fa-users text-danger me-1"></i> Multiple Faces Detected (${integrityScore}% Integrity)`;
                    }
                    showViolationModal(
                        'OpenCV Warning: Multiple Persons Detected in Camera View',
                        'Multiple faces were detected in your camera feed. Only the authorized candidate is permitted during the exam session.',
                        violationCount
                    );
                } else {
                    consecutiveMissingFaceCount = 0;
                    if (webcamStatusOverlay) {
                        webcamStatusOverlay.innerHTML = `<i class="fa-solid fa-shield-halved text-success me-1"></i> Active Feed (${integrityScore}% Integrity)`;
                    }
                }
            }
        } catch (err) {
            console.warn('OpenCV frame processing notice:', err);
        }
    }

    // Run OpenCV Face Monitoring frame check every 4 seconds
    setInterval(processOpenCVFrame, 4000);

    // Tab Switch / Visibility Change Listener
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            handleSecurityViolation('Browser Tab Switch / Window Hidden Detected', 'TAB_SWITCH');
        }
    });

    // Window Focus Lost Listener (Alt+Tab / App Switch)
    window.addEventListener('blur', () => {
        handleSecurityViolation('Window Focus Lost (Alt+Tab / App Switching)', 'FOCUS_LOST');
    });

    // Disable Right-Click Context Menu
    document.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        return false;
    });

    // Disable Copy, Cut, Paste, Text Selection Dragging
    ['copy', 'cut', 'paste', 'selectstart'].forEach(evt => {
        document.addEventListener(evt, (e) => {
            e.preventDefault();
            return false;
        });
    });

    // Disable Keyboard Shortcuts (Ctrl+C, Ctrl+V, Ctrl+U, F12, Ctrl+Shift+I)
    document.addEventListener('keydown', (e) => {
        const key = e.key.toLowerCase();
        if (e.key === 'F12' || (e.ctrlKey && ['c', 'v', 'x', 'u', 'a', 'p', 's'].includes(key)) || (e.ctrlKey && e.shiftKey && ['i', 'j', 'c'].includes(key))) {
            e.preventDefault();
            return false;
        }
    });

    // Cross-Browser Fullscreen Helpers
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

    function isFullscreenActive() {
        return !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
    }

    function checkAndEnforceFullscreen() {
        if (isFullscreenActive()) {
            if (headerFullscreenText) headerFullscreenText.innerText = 'Fullscreen Active';
            if (btnHeaderFullscreen) {
                btnHeaderFullscreen.className = 'btn btn-success btn-sm d-flex align-items-center gap-2';
                btnHeaderFullscreen.innerHTML = '<i class="fa-solid fa-circle-check text-white"></i> <span>Fullscreen Active</span>';
            }
            if (fullscreenModalInstance) {
                fullscreenModalInstance.hide();
            }
        } else {
            if (headerFullscreenText) headerFullscreenText.innerText = 'Enable Fullscreen';
            if (btnHeaderFullscreen) {
                btnHeaderFullscreen.className = 'btn btn-warning btn-sm d-flex align-items-center gap-2';
                btnHeaderFullscreen.innerHTML = '<i class="fa-solid fa-expand me-1"></i> <span>Enable Fullscreen</span>';
            }
            if (fullscreenModalInstance) {
                fullscreenModalInstance.show();
            }
        }
    }

    // Fullscreen Trigger Event Listeners
    if (btnHeaderFullscreen) {
        btnHeaderFullscreen.addEventListener('click', () => {
            if (!isFullscreenActive()) {
                requestUniversalFullscreen(document.documentElement).catch(err => {
                    console.error('Header fullscreen error:', err);
                });
            } else {
                exitUniversalFullscreen().catch(err => {
                    console.error('Exit fullscreen error:', err);
                });
            }
        });
    }

    if (btnEnableFullscreenModal) {
        btnEnableFullscreenModal.addEventListener('click', () => {
            requestUniversalFullscreen(document.documentElement).then(() => {
                checkAndEnforceFullscreen();
            }).catch(err => {
                console.error('Modal fullscreen error:', err);
                alert('Please allow fullscreen mode in your browser to proceed.');
            });
        });
    }

    ['fullscreenchange', 'webkitfullscreenchange', 'mozfullscreenchange', 'MSFullscreenChange'].forEach(evt => {
        document.addEventListener(evt, checkAndEnforceFullscreen);
    });

    // 3. Countdown Timer Initialization
    let storageKey = `exam_timer_${submissionId}`;
    let remainingSeconds = localStorage.getItem(storageKey);

    if (!remainingSeconds) {
        remainingSeconds = durationMinutes * 60;
        localStorage.setItem(storageKey, remainingSeconds);
    } else {
        remainingSeconds = parseInt(remainingSeconds, 10);
    }

    function updateTimerDisplay() {
        const mins = Math.floor(remainingSeconds / 60);
        const secs = remainingSeconds % 60;
        const formatted = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        if (timerDisplay) {
            timerDisplay.innerText = formatted;
            if (remainingSeconds <= 120) {
                timerDisplay.parentElement.classList.add('warning');
            }
        }
    }

    updateTimerDisplay();

    const timerInterval = setInterval(() => {
        remainingSeconds--;
        localStorage.setItem(storageKey, remainingSeconds);
        updateTimerDisplay();

        if (remainingSeconds <= 0) {
            clearInterval(timerInterval);
            localStorage.removeItem(storageKey);
            alert('Time is up! Your exam is being submitted automatically.');
            examForm.submit();
        }
    }, 1000);

    // 4. Question View Switching
    function showQuestion(index) {
        if (index < 0 || index >= totalQuestions) return;
        currentQuestionIndex = index;

        questionPanes.forEach((pane, i) => {
            if (i === index) {
                pane.classList.remove('d-none');
            } else {
                pane.classList.add('d-none');
            }
        });

        // Update navigator palette active highlight
        paletteButtons.forEach((btn, i) => {
            if (i === index) {
                btn.classList.add('active-current');
            } else {
                btn.classList.remove('active-current');
            }
        });

        // Update Prev / Next Buttons
        if (btnPrev) btnPrev.disabled = (index === 0);
        if (btnNext) {
            if (index === totalQuestions - 1) {
                btnNext.innerHTML = 'Review & Finish <i class="fa-solid fa-flag-checkered ms-1"></i>';
            } else {
                btnNext.innerHTML = 'Next Question <i class="fa-solid fa-arrow-right ms-1"></i>';
            }
        }

        if (qCurrentIndexSpan) qCurrentIndexSpan.innerText = index + 1;

        // Sync Mark for Review button state for active question
        const activePane = questionPanes[index];
        const flagVal = activePane.dataset.isFlagged === 'true';
        if (chkFlag) chkFlag.checked = flagVal;
        if (markReviewText) {
            markReviewText.innerText = flagVal ? 'Marked for Review' : 'Mark for Review';
        }
    }

    // 5. Update Palette Button Styling based on selection/flag state
    function updatePaletteStatus(qId) {
        const pane = document.querySelector(`.question-pane[data-question-id="${qId}"]`);
        if (!pane) return;

        const index = parseInt(pane.dataset.index, 10);
        const paletteBtn = document.querySelector(`.palette-btn[data-index="${index}"]`);
        if (!paletteBtn) return;

        const selectedRadio = pane.querySelector('input[type="radio"]:checked');
        const isFlagged = pane.dataset.isFlagged === 'true';

        paletteBtn.classList.remove('answered', 'flagged', 'answered-flagged');

        if (selectedRadio && isFlagged) {
            paletteBtn.classList.add('answered-flagged');
        } else if (isFlagged) {
            paletteBtn.classList.add('flagged');
        } else if (selectedRadio) {
            paletteBtn.classList.add('answered');
        }
    }

    // 6. Send Draft Answer AJAX to Server
    async function saveDraftAnswer(qId, selectedOption, isFlagged) {
        try {
            await fetch('/exam/api/save-draft', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    submission_id: submissionId,
                    question_id: qId,
                    selected_option: selectedOption,
                    is_flagged: isFlagged
                })
            });
        } catch (err) {
            console.warn('Draft save notice:', err);
        }
    }

    // Event Listeners for Option Selection
    document.querySelectorAll('.option-label-card').forEach(card => {
        card.addEventListener('click', (e) => {
            const radio = card.querySelector('input[type="radio"]');
            if (radio) {
                radio.checked = true;
                const pane = card.closest('.question-pane');
                const qId = pane.dataset.questionId;
                const selectedOpt = parseInt(radio.value, 10);
                const isFlagged = pane.dataset.isFlagged === 'true' ? 1 : 0;

                // Highlight active card
                pane.querySelectorAll('.option-label-card').forEach(c => c.classList.remove('selected-active'));
                card.classList.add('selected-active');

                updatePaletteStatus(qId);
                saveDraftAnswer(qId, selectedOpt, isFlagged);
            }
        });
    });

    // Clear Selection Button
    if (btnClearChoice) {
        btnClearChoice.addEventListener('click', () => {
            const activePane = questionPanes[currentQuestionIndex];
            const qId = activePane.dataset.questionId;
            const checkedRadio = activePane.querySelector('input[type="radio"]:checked');

            if (checkedRadio) {
                checkedRadio.checked = false;
                activePane.querySelectorAll('.option-label-card').forEach(c => c.classList.remove('selected-active'));
                const isFlagged = activePane.dataset.isFlagged === 'true' ? 1 : 0;

                updatePaletteStatus(qId);
                saveDraftAnswer(qId, -1, isFlagged);
            }
        });
    }

    // Mark for Review Button Handler
    if (btnMarkReview) {
        btnMarkReview.addEventListener('click', () => {
            const activePane = questionPanes[currentQuestionIndex];
            const qId = activePane.dataset.questionId;
            const currentFlag = activePane.dataset.isFlagged === 'true';
            const newFlag = !currentFlag;

            activePane.dataset.isFlagged = newFlag ? 'true' : 'false';
            if (chkFlag) chkFlag.checked = newFlag;

            if (markReviewText) {
                markReviewText.innerText = newFlag ? 'Marked for Review' : 'Mark for Review';
            }

            const selectedRadio = activePane.querySelector('input[type="radio"]:checked');
            const selectedOpt = selectedRadio ? parseInt(selectedRadio.value, 10) : -1;

            updatePaletteStatus(qId);
            saveDraftAnswer(qId, selectedOpt, newFlag ? 1 : 0);
        });
    }

    // Navigation Controls
    if (btnNext) {
        btnNext.addEventListener('click', () => {
            if (currentQuestionIndex < totalQuestions - 1) {
                showQuestion(currentQuestionIndex + 1);
            } else {
                // Trigger submit modal
                const submitModal = new bootstrap.Modal(document.getElementById('submitModal'));
                updateSubmitModalSummary();
                submitModal.show();
            }
        });
    }

    if (btnPrev) {
        btnPrev.addEventListener('click', () => {
            if (currentQuestionIndex > 0) {
                showQuestion(currentQuestionIndex - 1);
            }
        });
    }

    // Palette direct click navigation
    paletteButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const index = parseInt(btn.dataset.index, 10);
            showQuestion(index);
        });
    });

    function updateSubmitModalSummary() {
        let answeredCount = 0;
        let flaggedCount = 0;

        questionPanes.forEach(pane => {
            if (pane.querySelector('input[type="radio"]:checked')) answeredCount++;
            if (pane.dataset.isFlagged === 'true') flaggedCount++;
        });

        document.getElementById('summaryTotal').innerText = totalQuestions;
        document.getElementById('summaryAnswered').innerText = answeredCount;
        document.getElementById('summaryUnanswered').innerText = totalQuestions - answeredCount;
        document.getElementById('summaryFlagged').innerText = flaggedCount;
    }

    // Clear timer storage when form submits
    examForm.addEventListener('submit', () => {
        localStorage.removeItem(storageKey);
    });

    // Initialize Question 0 and Fullscreen Check
    showQuestion(0);
    questionPanes.forEach(pane => {
        updatePaletteStatus(pane.dataset.questionId);
    });
    checkAndEnforceFullscreen();
});
