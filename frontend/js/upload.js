/**
 * Upload Document View Controller
 * Handles drag & drop, file selection, target category assignment, and batch/individual uploads.
 */
class UploadController {
  constructor() {
    this.state = window.stateManager;
    this.queue = [];
    this.isUploading = false;
    this.maxSizeBytes = 20 * 1024 * 1024; // 20 MB (Part 4 requirement)
    this.allowedExtensions = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'png', 'jpg', 'jpeg'];

    this.init();
  }

  init() {
    this.bindEvents();
    this.populateCategoryOptions();
    if (this.state) {
      this.state.subscribe(() => this.populateCategoryOptions());
    }
  }

  populateCategoryOptions() {
    const targetCatSelect = document.getElementById('upload-target-category');
    if (!targetCatSelect) return;

    const currentVal = targetCatSelect.value || 'auto';
    const categories = this.state ? this.state.getCategories() : [];

    targetCatSelect.innerHTML = `
      <option value="auto" ${currentVal === 'auto' ? 'selected' : ''}>Auto-Detect Category</option>
      ${categories.map(c => `
        <option value="${this.escapeHtml(c.name)}" ${currentVal === c.name ? 'selected' : ''}>
          ${this.escapeHtml(c.name)}
        </option>
      `).join('')}
    `;
  }

  bindEvents() {
    const dropzone = document.getElementById('upload-dropzone');
    const fileInput = document.getElementById('upload-file-input');
    const browseBtn = document.getElementById('upload-browse-btn');
    const uploadAllBtn = document.getElementById('upload-all-btn');
    const clearQueueBtn = document.getElementById('upload-clear-btn');

    if (browseBtn && fileInput) {
      browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
      });
    }

    if (dropzone && fileInput) {
      dropzone.addEventListener('click', () => {
        fileInput.click();
      });

      // Drag and Drop listeners
      ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
          e.preventDefault();
          e.stopPropagation();
          dropzone.classList.add('dragover');
        });
      });

      ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
          e.preventDefault();
          e.stopPropagation();
          dropzone.classList.remove('dragover');
        });
      });

      dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length) {
          this.handleFiles(files);
        }
      });

      fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length) {
          this.handleFiles(e.target.files);
          fileInput.value = ''; // Reset input so same file can be re-selected if removed
        }
      });
    }

    if (uploadAllBtn) {
      uploadAllBtn.addEventListener('click', () => this.startUploadAll());
    }

    if (clearQueueBtn) {
      clearQueueBtn.addEventListener('click', () => this.clearQueue());
    }
  }

  handleFiles(fileList) {
    const targetCatSelect = document.getElementById('upload-target-category');
    const selectedDefault = targetCatSelect ? targetCatSelect.value : 'auto';

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const ext = file.name.split('.').pop().toLowerCase();

      // Check format
      if (!this.allowedExtensions.includes(ext)) {
        window.app.showToast(`Unsupported format for "${file.name}". Supported: PDF, DOC/DOCX, PPT/PPTX, XLS/XLSX, TXT, PNG/JPG.`, 'error');
        continue;
      }

      // Check size
      if (file.size > this.maxSizeBytes) {
        window.app.showToast(`File "${file.name}" exceeds 20 MB limit (${this.state.formatBytes(file.size)}).`, 'error');
        continue;
      }

      // Check duplicates in existing queue
      if (this.queue.some(item => item.file.name === file.name && item.file.size === file.size)) {
        window.app.showToast(`File "${file.name}" is already in the upload queue.`, 'warning');
        continue;
      }

      // Determine initial category from dropdown or auto-detector
      let category = 'Other';
      if (selectedDefault && selectedDefault !== 'auto') {
        category = selectedDefault;
      } else {
        category = this.state.suggestCategory(file.name);
      }

      this.queue.push({
        id: 'q-' + Date.now() + '-' + Math.random().toString(36).substring(2, 6),
        file,
        name: file.name,
        size: file.size,
        type: this.state.detectFileType(file.name),
        category,
        progress: 0,
        status: 'queued', // 'queued', 'uploading', 'success', 'error'
        errorMessage: null
      });
    }

    this.renderQueue();
  }

  updateItemCategory(id, newCategory) {
    const item = this.queue.find(i => i.id === id);
    if (item) {
      item.category = newCategory;
    }
  }

  renderQueue() {
    const queueSection = document.getElementById('upload-queue-section');
    const queueList = document.getElementById('upload-queue-list');
    const queueCountBadge = document.getElementById('upload-queue-count');
    const uploadAllBtn = document.getElementById('upload-all-btn');

    if (!queueSection || !queueList) return;

    if (this.queue.length === 0) {
      queueSection.style.display = 'none';
      return;
    }

    queueSection.style.display = 'block';
    if (queueCountBadge) queueCountBadge.textContent = `${this.queue.length} files`;

    const pendingCount = this.queue.filter(i => i.status === 'queued' || i.status === 'uploading').length;
    if (uploadAllBtn) {
      uploadAllBtn.disabled = pendingCount === 0 || this.isUploading;
      uploadAllBtn.innerHTML = this.isUploading
        ? '<span class="status-dot connecting"></span> Uploading...'
        : 'Upload All Files';
    }

    const categories = this.state ? this.state.getCategories() : [];

    queueList.innerHTML = this.queue.map(item => `
      <div class="queue-item" id="queue-${item.id}">
        <div class="queue-item-info">
          <div class="file-icon-box ${this.getFileIconClass(item.type)}">${item.type}</div>
          <div style="flex: 1;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;">
              <span class="file-info-main">${this.escapeHtml(item.name)}</span>
              <span style="font-size: 0.78rem; color: var(--text-muted);">${this.state.formatBytes(item.size)}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 0.65rem; margin-top: 0.4rem; flex-wrap: wrap;">
              <div style="display: inline-flex; align-items: center; gap: 0.35rem;">
                <label style="font-size: 0.78rem; font-weight: 600; color: var(--text-secondary); margin: 0;">Category:</label>
                <select class="form-control form-control-sm" style="max-width: 170px; padding: 0.2rem 0.5rem; font-size: 0.82rem; height: auto; border-radius: 6px; cursor: pointer;" onchange="window.uploadController.updateItemCategory('${item.id}', this.value)" ${item.status !== 'queued' ? 'disabled' : ''}>
                  ${categories.map(c => `
                    <option value="${this.escapeHtml(c.name)}" ${c.name === item.category ? 'selected' : ''}>
                      ${this.escapeHtml(c.name)}
                    </option>
                  `).join('')}
                </select>
              </div>
              ${this.getStatusBadge(item.status)}
            </div>
            <div class="progress-track" style="margin-top: 0.5rem;">
              <div class="progress-fill" style="width: ${item.progress}%; background: ${item.status === 'error' ? 'var(--color-danger)' : 'var(--button-gradient)'};"></div>
            </div>
          </div>
        </div>

        <div>
          ${item.status === 'queued' ? `
            <div style="display: flex; align-items: center; gap: 0.4rem;">
              <button type="button" class="btn btn-primary btn-sm" onclick="window.uploadController.uploadSingleItem('${item.id}')" title="Upload this file now" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">
                Upload
              </button>
              <button type="button" class="btn btn-icon btn-sm" title="Remove from queue" onclick="window.uploadController.removeFromQueue('${item.id}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          ` : ''}
          ${item.status === 'success' ? `
            <span style="color: var(--color-success); display: flex;" title="Upload completed">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
            </span>
          ` : ''}
        </div>
      </div>
    `).join('');
  }

  removeFromQueue(id) {
    this.queue = this.queue.filter(i => i.id !== id);
    this.renderQueue();
  }

  clearQueue() {
    this.queue = [];
    this.renderQueue();
  }

  async uploadSingleItem(id) {
    const item = this.queue.find(i => i.id === id);
    if (!item || item.status !== 'queued') return;

    item.status = 'uploading';
    item.progress = 25;
    this.renderQueue();

    const result = await this.state.uploadFileToBackend(item.file, item.category);

    if (result.success) {
      item.status = 'success';
      item.progress = 100;
      window.app.showToast(`"${item.name}" uploaded to "${item.category}"!`, 'success');
    } else {
      item.status = 'error';
      item.errorMessage = result.error;
      window.app.showToast(`Upload failed for "${item.name}": ${result.error}`, 'error');
    }

    this.renderQueue();
  }

  async startUploadAll() {
    if (this.isUploading) return;
    this.isUploading = true;
    this.renderQueue();

    const queuedItems = this.queue.filter(i => i.status === 'queued');

    for (const item of queuedItems) {
      item.status = 'uploading';
      item.progress = 25;
      this.renderQueue();

      // Real upload to FastAPI backend with user-chosen category
      const result = await this.state.uploadFileToBackend(item.file, item.category);

      if (result.success) {
        item.status = 'success';
        item.progress = 100;
      } else {
        item.status = 'error';
        item.errorMessage = result.error;
        window.app.showToast(`Upload failed for "${item.name}": ${result.error}`, 'error');
      }

      this.renderQueue();
    }

    this.isUploading = false;
    this.renderQueue();
    
    const successCount = this.queue.filter(i => i.status === 'success').length;
    if (successCount > 0) {
      window.app.showToast(`Successfully processed and categorized ${successCount} files!`, 'success');
    }
  }

  getStatusBadge(status) {
    switch (status) {
      case 'queued':
        return '<span class="badge badge-warning" style="font-size: 0.65rem;">Queued</span>';
      case 'uploading':
        return '<span class="badge badge-info" style="font-size: 0.65rem;">Uploading...</span>';
      case 'success':
        return '<span class="badge badge-success" style="font-size: 0.65rem;">Completed</span>';
      case 'error':
        return '<span class="badge badge-danger" style="font-size: 0.65rem;">Failed</span>';
      default:
        return '';
    }
  }

  getFileIconClass(type) {
    switch (type) {
      case 'PDF': return 'file-icon-pdf';
      case 'WORD':
      case 'DOCX': return 'file-icon-doc';
      case 'POWERPOINT':
      case 'PPTX': return 'file-icon-ppt';
      case 'EXCEL':
      case 'XLSX': return 'file-icon-xls';
      case 'IMAGE': return 'file-icon-img';
      case 'TEXT': return 'file-icon-txt';
      default: return 'file-icon-generic';
    }
  }

  escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.uploadController = new UploadController();
});
