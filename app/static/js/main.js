// ExamGuard Camera Capture Handler
document.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('cameraVideo');
    const canvas = document.getElementById('cameraCanvas');
    const btnCapture = document.getElementById('btnCapturePhoto');
    const btnRetake = document.getElementById('btnRetakePhoto');
    const photoBase64Input = document.getElementById('photoBase64');
    const cameraModalEl = document.getElementById('cameraModal');

    let stream = null;

    if (cameraModalEl) {
        cameraModalEl.addEventListener('shown.bs.modal', async () => {
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" }
                });
                video.srcObject = stream;
                video.classList.remove('d-none');
                canvas.classList.add('d-none');
            } catch (err) {
                console.error("Camera access error:", err);
                alert("Camera access denied or unavailable.");
            }
        });

        cameraModalEl.addEventListener('hidden.bs.modal', () => {
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                stream = null;
            }
        });
    }

    if (btnCapture) {
        btnCapture.addEventListener('click', () => {
            if (!video.srcObject) return;
            const ctx = canvas.getContext('2d');
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
            photoBase64Input.value = dataUrl;

            // Update UI preview
            const previewContainer = document.getElementById('photoPreviewContainer');
            const previewImg = document.getElementById('photoPreviewImg');
            if (previewImg && previewContainer) {
                previewImg.src = dataUrl;
                previewContainer.classList.remove('d-none');
            }

            // Close Modal
            const modalInstance = bootstrap.Modal.getInstance(cameraModalEl);
            if (modalInstance) modalInstance.hide();
        });
    }
});
