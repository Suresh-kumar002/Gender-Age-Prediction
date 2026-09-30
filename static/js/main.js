const fileInput = document.getElementById('imageInput');
const fileName = document.getElementById('fileName');
const webcamBtn = document.getElementById('webcamBtn');
const webcamWrapper = document.getElementById('webcamWrapper');
const webcamVideo = document.getElementById('webcamVideo');
const captureBtn = document.getElementById('captureBtn');
const uploadForm = document.getElementById('uploadForm');

let webcamStream = null;

if (fileInput && fileName) {
  fileInput.addEventListener('change', function () {
    const selected = this.files && this.files[0] ? this.files[0].name : 'No file chosen';
    fileName.textContent = selected;
  });
}

const revealEls = document.querySelectorAll('.reveal');
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.15 });

revealEls.forEach((el) => revealObserver.observe(el));

document.querySelectorAll('.tilt-card').forEach((card) => {
  card.addEventListener('mousemove', (event) => {
    const rect = card.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const rotateY = ((x / rect.width) - 0.5) * 10;
    const rotateX = (0.5 - (y / rect.height)) * 10;
    card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
  });

  card.addEventListener('mouseleave', () => {
    card.style.transform = '';
  });
});

if (webcamBtn && webcamVideo && webcamWrapper && captureBtn && uploadForm) {
  webcamBtn.addEventListener('click', async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert('This browser does not support webcam access.');
      return;
    }

    try {
      webcamStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user' },
        audio: false
      });

      webcamVideo.srcObject = webcamStream;
      webcamWrapper.hidden = false;
      webcamBtn.textContent = 'Camera Open';
    } catch (error) {
      alert('Camera access was denied. Please allow permission and try again.');
    }
  });

  captureBtn.addEventListener('click', () => {
    if (!webcamVideo.srcObject) {
      alert('Open the webcam first.');
      return;
    }

    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = webcamVideo.videoWidth || 640;
    canvas.height = webcamVideo.videoHeight || 480;
    context.drawImage(webcamVideo, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(async (blob) => {
      const formData = new FormData(uploadForm);
      formData.delete('image');
      formData.append('image', blob, 'webcam-shot.png');

      try {
        const response = await fetch(uploadForm.action, {
          method: 'POST',
          body: formData
        });

        const html = await response.text();
        document.open();
        document.write(html);
        document.close();
      } catch (error) {
        alert('Unable to process webcam image. Please try again.');
      }
    }, 'image/png');
  });
}
