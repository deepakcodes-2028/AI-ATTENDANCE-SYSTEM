
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer') || (() => {
    const c = document.createElement('div');
    c.id = 'toastContainer';
    c.className = 'toast-container';
    document.body.appendChild(c);
    return c;
  })();

  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}


function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add('active');
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove('active');
}

document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
  }
});


let videoStream = null;
let recognitionInterval = null;
let registrationStream = null;

async function startCamera(videoElId = 'videoFeed') {
  const video = document.getElementById(videoElId);
  if (!video) return;
  try {
    videoStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
    video.srcObject = videoStream;
    await video.play();
  } catch (e) {
    showToast('Camera access denied or unavailable.', 'error');
  }
}

function stopCamera() {
  if (videoStream) {
    videoStream.getTracks().forEach(t => t.stop());
    videoStream = null;
  }
  if (recognitionInterval) {
    clearInterval(recognitionInterval);
    recognitionInterval = null;
  }
}

function captureFrame(videoElId = 'videoFeed') {
  const video = document.getElementById(videoElId);
  if (!video || !videoStream) return null;
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  canvas.getContext('2d').drawImage(video, 0, 0);
  return canvas.toDataURL('image/jpeg', 0.8);
}


function startRecognition() {
  const courseId = document.getElementById('courseSelect')?.value || '';
  const courseName = document.getElementById('courseSelect')?.options[document.getElementById('courseSelect')?.selectedIndex]?.text || '';

  if (!courseId) {
     showToast('Please select a course first.', 'error');
     return;
  }
  
  const btn = document.getElementById('startRecognitionBtn');
  const stopBtn = document.getElementById('stopRecognitionBtn');

  if (btn) btn.style.display = 'none';
  if (stopBtn) stopBtn.style.display = 'inline-flex';

  const statusEl = document.getElementById('cameraStatus');
  if (statusEl) {
    statusEl.innerHTML = '<span class="status-dot"></span> Scanning for faces...';
  }

  recognitionInterval = setInterval(async () => {
    const frame = captureFrame();
    if (!frame) return;

    try {
      const res = await fetch('/attendance/recognize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: frame, course_id: courseId })
      });
      const data = await res.json();

      if (data.face_locations) {
        drawFaceBoxes(data.face_locations, data.recognized);
      }

      if (data.recognized && data.recognized.length > 0) {
        data.recognized.forEach(s => {
          if (!document.getElementById(`ri-${s.student_id}`)) {
            s.course_name = courseName; // Add course name for display
            addRecognizedEntry(s);
          }
        });
      }
    } catch (e) {
      console.error('Recognition error:', e);
    }
  }, 2000);
}

function drawFaceBoxes(locations, recognized) {
  const canvas = document.getElementById('overlayCanvas');
  const video = document.getElementById('videoFeed');
  if (!canvas || !video) return;

  const ctx = canvas.getContext('2d');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.strokeStyle = '#00ff66';
  ctx.lineWidth = 3;
  ctx.fillStyle = '#00ff66';
  ctx.font = '16px Inter, sans-serif';

  locations.forEach((loc, i) => {
    const [top, right, bottom, left] = loc;
    const width = right - left;
    const height = bottom - top;

    // Draw rectangle
    ctx.strokeRect(left, top, width, height);

    // Draw label background
    let label = "Unknown";
    // Try to match with recognized list
    // (Note: this is a simple match based on index or heuristic if multiple faces)
    if (recognized && recognized.length > 0) {
        // Find if this face location corresponds to any recognized student
        // For simplicity, we show "Detected" or the name if provided in a similar order
        label = recognized[i] ? recognized[i].name : "Scanning...";
    }

    const labelWidth = ctx.measureText(label).width;
    ctx.fillRect(left, top - 25, labelWidth + 10, 25);
    
    ctx.fillStyle = '#000';
    ctx.fillText(label, left + 5, top - 7);
    ctx.fillStyle = '#00ff66'; // Reset for next face
  });
  
  // Clear boxes after 1.5 seconds if no new data
  setTimeout(() => {
    if (!recognitionInterval) ctx.clearRect(0, 0, canvas.width, canvas.height);
  }, 1500);
}

function stopRecognition() {
  if (recognitionInterval) {
    clearInterval(recognitionInterval);
    recognitionInterval = null;
  }
  const btn = document.getElementById('startRecognitionBtn');
  const stopBtn = document.getElementById('stopRecognitionBtn');
  if (btn) btn.style.display = 'inline-flex';
  if (stopBtn) stopBtn.style.display = 'none';

  const statusEl = document.getElementById('cameraStatus');
  if (statusEl) statusEl.textContent = 'Camera ready';
}

function addRecognizedEntry(student) {
  const list = document.getElementById('recognizedList');
  if (!list) return;

  const emptyState = list.querySelector('.empty-state');
  if (emptyState) emptyState.remove();

  const initials = student.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  const isNew = !student.already_marked;
  const item = document.createElement('div');
  item.className = 'recognized-item';
  item.id = `ri-${student.student_id}`;
  item.innerHTML = `
    <div class="ri-avatar">${initials}</div>
    <div class="ri-info">
      <div class="ri-name">${student.name} - <span style="color:var(--accent);">${student.course_name}</span></div>
      <div class="ri-sub">ID: ${student.student_id} - Present</div>
    </div>
    <span class="badge ${isNew ? 'badge-green' : 'badge-gray'}">${isNew ? 'Marked ✓' : 'Already Marked'}</span>
  `;
  list.prepend(item);

  if (isNew) showToast(`Attendance marked for ${student.name}`, 'success');
}


async function startRegistrationCamera() {
  const video = document.getElementById('regVideo');
  if (!video) return;
  try {
    registrationStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
    video.srcObject = registrationStream;
    await video.play();
    document.getElementById('captureBtn').disabled = false;
  } catch (e) {
    showToast('Camera access denied.', 'error');
  }
}

function stopRegistrationCamera() {
  if (registrationStream) {
    registrationStream.getTracks().forEach(t => t.stop());
    registrationStream = null;
  }
}

async function captureAndRegister() {
  const studentId = document.getElementById('regStudentId')?.value;
  if (!studentId) {
    showToast('Please select a student first.', 'error');
    return;
  }

  const video = document.getElementById('regVideo');
  if (!video || !registrationStream) {
    showToast('Please start the camera first.', 'error');
    return;
  }

  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  canvas.getContext('2d').drawImage(video, 0, 0);
  const imageData = canvas.toDataURL('image/jpeg', 0.9);

  
  const preview = document.getElementById('capturePreview');
  if (preview) { preview.src = imageData; preview.style.display = 'block'; }

  const btn = document.getElementById('captureBtn');
  if (btn) { btn.disabled = true; btn.textContent = 'Registering...'; }

  try {
    const res = await fetch('/register-face', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: studentId, image: imageData })
    });
    const data = await res.json();

    if (data.success) {
      showToast(data.message, 'success');
      stopRegistrationCamera();
      closeModal('registerFaceModal');
      
      setTimeout(() => location.reload(), 1200);
    } else {
      showToast(data.message, 'error');
    }
  } catch (e) {
    showToast('Registration failed. Try again.', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '📸 Capture & Register'; }
  }
}


async function addStudent(e) {
  e.preventDefault();
  const form = document.getElementById('addStudentForm');
  const data = new FormData(form);

  try {
    const res = await fetch('/students/add', { method: 'POST', body: data });
    const result = await res.json();

    if (result.success) {
      showToast(result.message, 'success');
      closeModal('addStudentModal');
      setTimeout(() => location.reload(), 1000);
    } else {
      showToast(result.message, 'error');
    }
  } catch (e) {
    showToast('Failed to add student.', 'error');
  }
}

async function deleteStudent(sid, name) {
  if (!confirm(`Delete student "${name}"? This will remove all their attendance records.`)) return;

  try {
    const res = await fetch(`/students/delete/${sid}`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('Student deleted.', 'success');
      document.getElementById(`student-row-${sid}`)?.remove();
    }
  } catch (e) {
    showToast('Delete failed.', 'error');
  }
}


async function loadReports() {
  const filterDate = document.getElementById('filterDate')?.value || '';
  const courseId = document.getElementById('filterCourse')?.value || '';
  const studentName = document.getElementById('filterStudent')?.value || '';

  const params = new URLSearchParams({ date: filterDate, course_id: courseId, student_name: studentName });

  try {
    const res = await fetch(`/reports/data?${params}`);
    const rows = await res.json();
    renderReportTable(rows);
  } catch (e) {
    showToast('Failed to load report.', 'error');
  }
}

function renderReportTable(rows) {
  const tbody = document.getElementById('reportTableBody');
  const countEl = document.getElementById('reportCount');
  if (!tbody) return;

  if (countEl) countEl.textContent = `${rows.length} records`;

  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7">
      <div class="empty-state">
        <div class="es-icon">📋</div>
        <div class="es-text">No attendance records found</div>
        <div class="es-sub">Try adjusting your filters</div>
      </div>
    </td></tr>`;
    return;
  }

  tbody.innerHTML = rows.map(r => `
    <tr>
      <td><span class="badge badge-gray">#${r.student_id}</span></td>
      <td><strong>${r.student_name}</strong></td>
      <td>${r.course}</td>
      <td>${r.course_name || '—'}</td>
      <td><span style="font-family:var(--mono); font-size:13px;">${r.date}</span></td>
      <td><span class="badge badge-blue">${r.time}</span></td>
      <td><span class="badge ${r.status === 'Present' ? 'badge-green' : 'badge-red'}">${r.status}</span></td>
    </tr>
  `).join('');
}


document.addEventListener('DOMContentLoaded', () => {
  
  const path = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(link => {
    if (link.getAttribute('href') === path) link.classList.add('active');
  });

  
  if (path === '/reports') loadReports();
});
