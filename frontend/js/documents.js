/**
 * All Documents View Controller
 * Handles document search, filtering, sorting, category overriding, and metadata preview.
 */
class DocumentsController {
  constructor() {
    this.state = window.stateManager;
    this.searchQuery = '';
    this.selectedCategory = 'all';
    this.selectedType = 'all';
    this.selectedSizeRange = 'all';
    this.selectedDateRange = 'all';
    this.selectedSort = 'newest';
    this.currentPage = 1;
    this.itemsPerPage = 8;

    this.init();
  }

  init() {
    this.bindEvents();
    this.populateCategoryFilter();
    this.render();

    this.state.subscribe(() => {
      this.populateCategoryFilter();
      this.render();
    });
  }

  bindEvents() {
    const searchInput = document.getElementById('doc-search-input');
    const categoryFilter = document.getElementById('doc-category-filter');
    const typeFilter = document.getElementById('doc-type-filter');
    const sizeFilter = document.getElementById('doc-size-filter');
    const dateFilter = document.getElementById('doc-date-filter');
    const sortFilter = document.getElementById('doc-sort-filter');

    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.toLowerCase().trim();
        this.currentPage = 1;
        this.render();
      });
    }

    if (categoryFilter) {
      categoryFilter.addEventListener('change', (e) => {
        this.selectedCategory = e.target.value;
        this.currentPage = 1;
        this.render();
      });
    }

    if (typeFilter) {
      typeFilter.addEventListener('change', (e) => {
        this.selectedType = e.target.value;
        this.currentPage = 1;
        this.render();
      });
    }

    if (sizeFilter) {
      sizeFilter.addEventListener('change', (e) => {
        this.selectedSizeRange = e.target.value;
        this.currentPage = 1;
        this.render();
      });
    }

    if (dateFilter) {
      dateFilter.addEventListener('change', (e) => {
        this.selectedDateRange = e.target.value;
        this.currentPage = 1;
        this.render();
      });
    }

    if (sortFilter) {
      sortFilter.addEventListener('change', (e) => {
        this.selectedSort = e.target.value;
        this.render();
      });
    }
  }

  populateCategoryFilter() {
    const categoryFilter = document.getElementById('doc-category-filter');
    if (!categoryFilter) return;

    const currentVal = categoryFilter.value;
    const categories = this.state.getCategories();

    categoryFilter.innerHTML = '<option value="all">All Categories</option>' +
      categories.map(c => `<option value="${c.name}">${c.name}</option>`).join('');

    if (currentVal && Array.from(categoryFilter.options).some(o => o.value === currentVal)) {
      categoryFilter.value = currentVal;
    }
  }

  getFilteredDocuments() {
    let docs = this.state.getDocuments();

    // 1. Keyword / Name / Extension / Category Search
    if (this.searchQuery) {
      const q = this.searchQuery.replace(/^\./, '');
      docs = docs.filter(d => {
        const nameMatch = d.name.toLowerCase().includes(q);
        const origMatch = d.originalName && d.originalName.toLowerCase().includes(q);
        const catMatch = d.category.toLowerCase().includes(q);
        const typeMatch = d.type.toLowerCase().includes(q);
        const extMatch = (d.extension || '').toLowerCase().includes(q);
        return nameMatch || origMatch || catMatch || typeMatch || extMatch;
      });
    }

    // 2. Category Filter
    if (this.selectedCategory !== 'all') {
      docs = docs.filter(d => d.category.toLowerCase() === this.selectedCategory.toLowerCase());
    }

    // 3. File Type Filter
    if (this.selectedType !== 'all') {
      docs = docs.filter(d => d.type.toUpperCase() === this.selectedType.toUpperCase());
    }

    // 4. File Size Filter (< 1MB, 1-5MB, 5-10MB, > 10MB)
    if (this.selectedSizeRange !== 'all') {
      const oneMb = 1024 * 1024;
      docs = docs.filter(d => {
        const size = d.size || 0;
        if (this.selectedSizeRange === 'under1mb') return size < oneMb;
        if (this.selectedSizeRange === '1to5mb') return size >= oneMb && size < 5 * oneMb;
        if (this.selectedSizeRange === '5to10mb') return size >= 5 * oneMb && size < 10 * oneMb;
        if (this.selectedSizeRange === 'over10mb') return size >= 10 * oneMb;
        return true;
      });
    }

    // 5. Date Filter
    if (this.selectedDateRange !== 'all') {
      const now = new Date();
      docs = docs.filter(d => {
        const docDate = new Date(d.uploadDate);
        const diffDays = (now - docDate) / (1000 * 60 * 60 * 24);
        if (this.selectedDateRange === 'today') return diffDays <= 1;
        if (this.selectedDateRange === '7days') return diffDays <= 7;
        if (this.selectedDateRange === '30days') return diffDays <= 30;
        return true;
      });
    }

    // 6. Sorting (Name, Upload Date, File Size, Category)
    docs.sort((a, b) => {
      if (this.selectedSort === 'newest') return new Date(b.uploadDate) - new Date(a.uploadDate);
      if (this.selectedSort === 'oldest') return new Date(a.uploadDate) - new Date(b.uploadDate);
      if (this.selectedSort === 'name-asc') return a.name.localeCompare(b.name);
      if (this.selectedSort === 'name-desc') return b.name.localeCompare(a.name);
      if (this.selectedSort === 'category-asc') return a.category.localeCompare(b.category);
      if (this.selectedSort === 'category-desc') return b.category.localeCompare(a.category);
      if (this.selectedSort === 'size-desc') return (b.size || 0) - (a.size || 0);
      if (this.selectedSort === 'size-asc') return (a.size || 0) - (b.size || 0);
      return 0;
    });

    return docs;
  }

  render() {
    const tableBody = document.getElementById('doc-table-body');
    const emptyState = document.getElementById('doc-empty-state');
    const tableContainer = document.getElementById('doc-table-container');
    const paginationWrapper = document.getElementById('doc-pagination-wrapper');
    const paginationInfo = document.getElementById('doc-pagination-info');
    const paginationControls = document.getElementById('doc-pagination-controls');

    if (!tableBody) return;

    const filtered = this.getFilteredDocuments();
    const totalItems = filtered.length;
    const totalPages = Math.ceil(totalItems / this.itemsPerPage) || 1;

    if (this.currentPage > totalPages) this.currentPage = totalPages;

    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    const endIndex = Math.min(startIndex + this.itemsPerPage, totalItems);
    const pageItems = filtered.slice(startIndex, endIndex);

    if (totalItems === 0) {
      if (tableContainer) tableContainer.style.display = 'none';
      if (emptyState) emptyState.style.display = 'flex';
      if (paginationWrapper) paginationWrapper.style.display = 'none';
      return;
    }

    if (tableContainer) tableContainer.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    if (paginationWrapper) paginationWrapper.style.display = 'flex';

    // Render Table Rows
    tableBody.innerHTML = pageItems.map(doc => `
      <tr>
        <td>
          <div class="file-title-cell">
            <div class="file-icon-box ${this.getFileIconClass(doc.type)}">${doc.type}</div>
            <div>
              <div class="file-info-main">${this.escapeHtml(doc.name)}</div>
              <div class="file-info-sub">${doc.type} &bull; .${doc.extension || 'file'} &bull; <span style="color: var(--primary-purple-dark); font-weight: 500;">By: ${this.escapeHtml(doc.uploadedBy || 'Anonymous')}</span></div>
            </div>
          </div>
        </td>
        <td>
          <div style="display: inline-flex; align-items: center; gap: 0.35rem;">
            <span class="badge badge-purple" style="cursor: pointer;" title="Click to change category" onclick="window.documentsController.openChangeCategoryModal('${doc.id}')">
              ${doc.category}
            </span>
            ${doc.isManual ? `
              <span class="badge" style="font-size: 0.65rem; background: #e0e7ff; color: #4338ca; border: 1px solid #c7d2fe;" title="Manually categorized by user">
                Manual
              </span>
            ` : `
              <span class="badge" style="font-size: 0.65rem; background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0;" title="Rule-based automatic suggestion">
                Auto
              </span>
            `}
          </div>
        </td>
        <td>${this.state.formatBytes(doc.size)}</td>
        <td style="color: var(--text-muted); font-size: 0.8rem;">
          ${new Date(doc.uploadDate).toLocaleDateString()} ${new Date(doc.uploadDate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </td>
        <td>
          <div class="gap-2" style="display: flex;">
            <button class="btn btn-secondary btn-sm" title="Preview Document & Metadata" onclick="window.documentsController.previewDocument('${doc.id}')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
              Preview
            </button>
            <button class="btn btn-secondary btn-sm" title="Change Category" onclick="window.documentsController.openChangeCategoryModal('${doc.id}')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
              </svg>
            </button>
            <button class="btn btn-secondary btn-sm" title="Download Document" onclick="window.documentsController.downloadDocument('${doc.id}')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
            <button class="btn btn-danger btn-sm" title="Delete Document" onclick="window.documentsController.confirmDeleteDocument('${doc.id}')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </td>
      </tr>
    `).join('');

    // Pagination Info & Buttons
    if (paginationInfo) {
      paginationInfo.textContent = `Showing ${startIndex + 1} to ${endIndex} of ${totalItems} documents`;
    }

    if (paginationControls) {
      let buttonsHtml = `
        <button class="page-btn" ${this.currentPage === 1 ? 'disabled' : ''} onclick="window.documentsController.goToPage(${this.currentPage - 1})">
          Prev
        </button>
      `;

      for (let i = 1; i <= totalPages; i++) {
        buttonsHtml += `
          <button class="page-btn ${this.currentPage === i ? 'active' : ''}" onclick="window.documentsController.goToPage(${i})">
            ${i}
          </button>
        `;
      }

      buttonsHtml += `
        <button class="page-btn" ${this.currentPage === totalPages ? 'disabled' : ''} onclick="window.documentsController.goToPage(${this.currentPage + 1})">
          Next
        </button>
      `;
      paginationControls.innerHTML = buttonsHtml;
    }
  }

  goToPage(page) {
    this.currentPage = page;
    this.render();
  }

  async previewDocument(id) {
    const doc = this.state.getDocuments().find(d => d.id === id);
    if (!doc) return;

    // Fetch live metadata from backend endpoint
    let meta = {
      filename: doc.name,
      original_filename: doc.originalName || doc.name,
      file_extension: doc.extension || doc.name.split('.').pop(),
      mime_type: doc.mimeType || 'application/octet-stream',
      file_size_formatted: this.state.formatBytes(doc.size),
      file_size_bytes: doc.size,
      file_type: doc.type,
      sha256_hash: doc.hash,
      category: doc.category,
      is_manually_categorized: doc.isManual,
      upload_timestamp: doc.uploadDate,
      is_previewable: ['pdf', 'png', 'jpg', 'jpeg', 'txt'].includes((doc.extension || '').toLowerCase())
    };

    try {
      const res = await window.apiService.getDocumentMetadata(id);
      if (res.success && res.data) {
        meta = res.data;
      }
    } catch (e) {
      console.warn('Could not fetch server metadata, using local record:', e);
    }

    const previewUrl = window.apiService.getPreviewUrl(id);
    const ext = (meta.file_extension || '').toLowerCase();
    const isPdf = ext === 'pdf';
    const isImage = ['png', 'jpg', 'jpeg'].includes(ext);
    const isText = ext === 'txt';

    let viewerHtml = '';
    if (isPdf) {
      viewerHtml = `
        <div style="border: 1px solid var(--border-color); border-radius: var(--radius-md); overflow: hidden; background: #525659;">
          <iframe src="${previewUrl}" style="width: 100%; height: 480px; border: none;" title="PDF Preview"></iframe>
        </div>
      `;
    } else if (isImage) {
      viewerHtml = `
        <div style="text-align: center; background: var(--bg-surface-subtle); padding: 1.5rem; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
          <img src="${previewUrl}" alt="${this.escapeHtml(meta.filename)}" style="max-width: 100%; max-height: 420px; border-radius: var(--radius-sm); object-fit: contain; box-shadow: var(--shadow-sm);">
        </div>
      `;
    } else if (isText) {
      viewerHtml = `
        <div style="border: 1px solid var(--border-color); border-radius: var(--radius-md); overflow: hidden;">
          <iframe src="${previewUrl}" style="width: 100%; height: 360px; border: none; background: #ffffff; padding: 0.5rem;" title="Text Preview"></iframe>
        </div>
      `;
    } else {
      viewerHtml = `
        <div style="border: 1.5px dashed var(--border-color); border-radius: var(--radius-md); padding: 2.25rem 1.5rem; text-align: center; background: var(--bg-surface-subtle);">
          <div class="file-icon-box ${this.getFileIconClass(meta.file_type)}" style="width: 54px; height: 54px; font-size: 1rem; margin: 0 auto 1rem;">
            ${meta.file_type}
          </div>
          <h4 style="font-size: 1.05rem; color: var(--text-primary);">Browser Preview Not Supported for .${ext}</h4>
          <p style="color: var(--text-secondary); font-size: 0.85rem; max-width: 420px; margin: 0.5rem auto 1.25rem;">
            Native inline preview is available for PDF, TXT, and Images. For <strong>${meta.file_type}</strong> files, download the original document to view it in Microsoft Office or LibreOffice.
          </p>
          <button class="btn btn-primary" onclick="window.documentsController.downloadDocument('${doc.id}')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Download Original File
          </button>
        </div>
      `;
    }

    const categories = this.state.getCategories();
    const categoryOptions = categories.map(c =>
      `<option value="${c.name}" ${c.name === meta.category ? 'selected' : ''}>${c.name}</option>`
    ).join('');

    window.app.showModal({
      title: `Document Details & Preview: ${meta.filename}`,
      body: `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <!-- Extracted Structural Metadata Card -->
          <div style="background: var(--bg-surface-subtle); padding: 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-color); font-size: 0.82rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">
              <strong style="color: var(--text-primary); font-size: 0.88rem;">Extracted Document Metadata</strong>
              <span class="badge ${meta.is_manually_categorized ? 'badge-primary' : 'badge-subtle'}">
                ${meta.is_manually_categorized ? 'Manually Overridden' : 'Auto Rule-Based'}
              </span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.6rem;">
              <div><strong>Filename:</strong> <span style="word-break: break-all;">${this.escapeHtml(meta.filename)}</span></div>
              <div><strong>Original Name:</strong> <span style="word-break: break-all;">${this.escapeHtml(meta.original_filename)}</span></div>
              <div><strong>Extension:</strong> <code>.${meta.file_extension}</code> (${meta.file_type})</div>
              <div><strong>MIME Type:</strong> <code>${meta.mime_type}</code></div>
              <div><strong>File Size:</strong> ${meta.file_size_formatted} (${meta.file_size_bytes.toLocaleString()} bytes)</div>
              <div><strong>Uploaded At:</strong> ${new Date(meta.upload_timestamp).toLocaleString()}</div>
              <div><strong>Uploaded By:</strong> <span class="badge" style="background: #ede9fe; color: #6d28d9; font-weight: 600;">${this.escapeHtml(meta.uploaded_by || doc.uploadedBy || 'Anonymous')}</span></div>
              <div style="grid-column: span 2; word-break: break-all;">
                <strong>SHA-256 Hash:</strong> <code style="font-size: 0.75rem; background: #fff; padding: 2px 4px; border: 1px solid #e2e8f0; border-radius: 4px;">${meta.sha256_hash}</code>
              </div>
            </div>

            <!-- Manual Category Override Control -->
            <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px dashed var(--border-color); display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap;">
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <label for="preview-category-select" style="font-weight: 600;">Category:</label>
                <select id="preview-category-select" class="form-control" style="width: auto; padding: 0.25rem 0.5rem; font-size: 0.82rem;">
                  ${categoryOptions}
                </select>
                <button type="button" class="btn btn-primary btn-sm" onclick="window.documentsController.saveCategoryChangeFromPreview('${doc.id}')">
                  Update Category
                </button>
              </div>
              <span style="font-size: 0.75rem; color: var(--text-muted); font-style: italic;">
                * Structural & cryptographic metadata only. Text/OCR extraction not enabled.
              </span>
            </div>
          </div>

          <!-- Document Content Viewer -->
          ${viewerHtml}
        </div>
      `,
      confirmText: 'Download Original File',
      onConfirm: () => this.downloadDocument(doc.id)
    });
  }

  async saveCategoryChangeFromPreview(id) {
    const select = document.getElementById('preview-category-select');
    if (!select) return;
    const newCategory = select.value;
    const success = await this.state.updateDocumentCategory(id, newCategory);
    if (success) {
      window.app.showToast(`Category updated to "${newCategory}" (manual override saved).`, 'success');
      window.app.closeModal();
    } else {
      window.app.showToast('Failed to update document category.', 'error');
    }
  }

  openChangeCategoryModal(id) {
    const doc = this.state.getDocuments().find(d => d.id === id);
    if (!doc) return;

    const categories = this.state.getCategories();
    const optionsHtml = categories.map(c =>
      `<option value="${c.name}" ${c.name === doc.category ? 'selected' : ''}>${c.name}</option>`
    ).join('');

    window.app.showModal({
      title: 'Change Document Category',
      body: `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <p>
            Manually override the category classification for document <strong>"${this.escapeHtml(doc.name)}"</strong>.
          </p>
          <div class="form-group">
            <label class="form-label" for="change-cat-select">Select Category</label>
            <select id="change-cat-select" class="form-control">
              ${optionsHtml}
              <option value="__custom__">+ Enter Custom Category...</option>
            </select>
          </div>
          <div class="form-group" id="custom-cat-input-group" style="display: none;">
            <label class="form-label" for="change-cat-custom">Custom Category Name</label>
            <input type="text" id="change-cat-custom" class="form-control" placeholder="e.g. Legal, Finance">
          </div>
          <p style="font-size: 0.8rem; color: var(--text-secondary); background: #f8fafc; padding: 0.5rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            Manual category overrides take precedence over automatic suggestions and are preserved permanently.
          </p>
        </div>
      `,
      confirmText: 'Apply Category',
      onConfirm: async () => {
        const select = document.getElementById('change-cat-select');
        const customInput = document.getElementById('change-cat-custom');
        let targetCategory = select ? select.value : '';

        if (targetCategory === '__custom__') {
          targetCategory = customInput ? customInput.value.trim() : '';
          if (!targetCategory) {
            window.app.showToast('Please enter a custom category name.', 'error');
            return false;
          }
        }

        const success = await this.state.updateDocumentCategory(id, targetCategory);
        if (success) {
          window.app.showToast(`Category changed to "${targetCategory}"!`, 'success');
        } else {
          window.app.showToast('Failed to update category.', 'error');
        }
        return true;
      }
    });

    const select = document.getElementById('change-cat-select');
    const customGroup = document.getElementById('custom-cat-input-group');
    if (select && customGroup) {
      select.addEventListener('change', (e) => {
        customGroup.style.display = e.target.value === '__custom__' ? 'block' : 'none';
      });
    }
  }

  downloadDocument(id) {
    const doc = this.state.getDocuments().find(d => d.id === id);
    if (!doc) return;

    window.app.showToast(`Downloading "${doc.name}"...`, 'info');
    const downloadUrl = `${window.apiService.baseUrl}/api/documents/${id}/download`;
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.setAttribute('download', doc.name);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  confirmDeleteDocument(id) {
    const doc = this.state.getDocuments().find(d => d.id === id);
    if (!doc) return;

    window.app.showModal({
      title: 'Confirm Delete Document',
      body: `
        <p>Are you sure you want to permanently delete <strong>"${this.escapeHtml(doc.name)}"</strong>?</p>
        <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 0.5rem;">
          This action will remove the document metadata from SQLite and delete the file from local storage.
        </p>
      `,
      confirmText: 'Delete Document',
      confirmClass: 'btn-danger',
      onConfirm: async () => {
        const success = await this.state.deleteDocument(id);
        if (success) {
          window.app.showToast(`Deleted document "${doc.name}"`, 'success');
        } else {
          window.app.showToast(`Failed to delete document "${doc.name}"`, 'error');
        }
      }
    });
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
  window.documentsController = new DocumentsController();
});
