/**
 * Dashboard View Controller
 * Integrates real database statistics from /api/dashboard/statistics
 * Renders interactive Chart.js visualizations for category and file-type distribution.
 */
class DashboardController {
  constructor() {
    this.state = window.stateManager;
    this.categoryChart = null;
    this.fileTypeChart = null;
    this.init();
  }

  init() {
    this.render();
    this.state.subscribe(() => this.render());
  }

  async render() {
    const isLoggedIn = !!((window.authManager && window.authManager.currentUser) || (window.apiService && window.apiService.getUser()));

    if (!isLoggedIn) {
      // Strictly 0 for unauthenticated guests
      const elTotalDocs = document.getElementById('dash-total-docs');
      const elStorageUsed = document.getElementById('dash-storage-used');
      const elTotalCategories = document.getElementById('dash-total-categories');
      const elTotalActivities = document.getElementById('dash-total-activities');

      if (elTotalDocs) elTotalDocs.textContent = '0';
      if (elStorageUsed) elStorageUsed.textContent = '0.00 KB';
      if (elTotalCategories) elTotalCategories.textContent = this.state.getCategories().length || 6;
      if (elTotalActivities) elTotalActivities.textContent = '0';

      const storageFill = document.getElementById('dash-storage-fill');
      const storagePercentText = document.getElementById('dash-storage-percent');
      const storageDetailText = document.getElementById('dash-storage-detail');

      if (storageFill) storageFill.style.width = '0%';
      if (storagePercentText) storagePercentText.textContent = '0%';
      if (storageDetailText) storageDetailText.textContent = '0.00 KB of 500 MB used (0%)';

      this.renderCategoryChart(null, this.state.getCategories(), []);
      this.renderFileTypeChart(null, []);
      this.renderRecentUploads([]);
      return;
    }

    // 1. Fetch live statistics from backend endpoint for logged-in user
    let stats = null;
    if (isLoggedIn) {
      stats = this.state.getDashboardStats();
      try {
        const res = await window.apiService.getDashboardStatistics();
        if (res.success && res.data) {
          stats = res.data;
        }
      } catch (e) {
        console.warn('Dashboard stats API fetch error:', e);
      }
    }

    const docs = isLoggedIn ? this.state.getDocuments() : [];
    const categories = this.state.getCategories();
    const activities = isLoggedIn ? this.state.getActivities() : [];
    const settings = this.state.getSettings();

    // Fallback numbers: strictly 0 for unauthenticated guests
    const totalDocs = isLoggedIn && stats ? stats.total_documents : docs.length;
    const totalStorageBytes = isLoggedIn && stats && stats.storage ? stats.storage.used_bytes : (isLoggedIn ? this.state.getTotalStorageBytes() : 0);
    const storageFormatted = isLoggedIn && stats && stats.storage ? stats.storage.used_formatted : this.state.formatBytes(totalStorageBytes);
    const totalCategories = categories.length;
    const recentActivityCount = isLoggedIn && stats ? (stats.recent_activity_count ?? stats.total_activities) : (isLoggedIn ? activities.length : 0);

    const quotaMb = settings.storageQuotaMb || 500;
    const quotaBytes = quotaMb * 1024 * 1024;
    const usagePercent = isLoggedIn && stats && stats.storage ? Math.round(stats.storage.percentage) : 0;

    // 2. Render 4 Stat Cards
    const elTotalDocs = document.getElementById('dash-total-docs');
    const elStorageUsed = document.getElementById('dash-storage-used');
    const elTotalCategories = document.getElementById('dash-total-categories');
    const elTotalActivities = document.getElementById('dash-total-activities');

    if (elTotalDocs) elTotalDocs.textContent = totalDocs;
    if (elStorageUsed) elStorageUsed.textContent = storageFormatted;
    if (elTotalCategories) elTotalCategories.textContent = totalCategories;
    if (elTotalActivities) elTotalActivities.textContent = recentActivityCount;

    // 3. Render Storage Usage & Capacity
    const storageFill = document.getElementById('dash-storage-fill');
    const storagePercentText = document.getElementById('dash-storage-percent');
    const storageDetailText = document.getElementById('dash-storage-detail');

    if (storageFill) storageFill.style.width = `${Math.max(2, usagePercent)}%`;
    if (storagePercentText) storagePercentText.textContent = `${usagePercent}%`;
    if (storageDetailText) storageDetailText.textContent = `${storageFormatted} of ${quotaMb} MB used (${usagePercent}%)`;

    // 4. Render Chart 1: Documents by Category
    this.renderCategoryChart(isLoggedIn && stats ? stats.category_distribution : null, categories, docs);

    // 5. Render Chart 2: Documents by File Type
    this.renderFileTypeChart(isLoggedIn && stats ? stats.file_type_distribution : null, docs);

    // 6. Render Recent Uploads Section
    this.renderRecentUploads(isLoggedIn && stats && stats.recent_documents ? stats.recent_documents : docs.slice(0, 5));
  }

  renderCategoryChart(distribution, categories, docs) {
    const container = document.getElementById('dash-category-chart');
    const canvas = document.getElementById('dash-category-canvas');
    const countBadge = document.getElementById('dash-cat-count-badge');

    if (!container) return;

    // Calculate data points
    let labels = [];
    let counts = [];
    let colors = [];

    if (distribution && distribution.length > 0) {
      labels = distribution.map(d => d.category_name);
      counts = distribution.map(d => d.count);
      colors = distribution.map(d => d.color || '#7c3aed');
    } else {
      labels = categories.map(c => c.name);
      counts = categories.map(c => c.count || 0);
      colors = categories.map(c => c.color || '#7c3aed');
    }

    const totalDocs = counts.reduce((a, b) => a + b, 0);
    if (countBadge) countBadge.textContent = `${labels.length} Categories`;

    // Handle Empty State
    if (totalDocs === 0) {
      if (this.categoryChart) {
        this.categoryChart.destroy();
        this.categoryChart = null;
      }
      if (canvas) canvas.style.display = 'none';
      container.innerHTML = `
        <div style="text-align: center; padding: 2.5rem 1rem; color: var(--text-secondary); font-size: 0.85rem;">
          <div style="margin-bottom: 0.5rem; opacity: 0.4;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            </svg>
          </div>
          No documents uploaded yet.<br>Category distribution will appear here.
        </div>
      `;
      return;
    }

    // Restore canvas if container was replaced by empty state
    if (!document.getElementById('dash-category-canvas')) {
      container.innerHTML = '<canvas id="dash-category-canvas" style="max-height: 240px;"></canvas>';
    }
    const currentCanvas = document.getElementById('dash-category-canvas');
    currentCanvas.style.display = 'block';

    // Check if Chart.js is loaded
    if (typeof Chart !== 'undefined') {
      if (this.categoryChart) {
        this.categoryChart.destroy();
      }

      const ctx = currentCanvas.getContext('2d');
      this.categoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: counts,
            backgroundColor: colors,
            borderWidth: 2,
            borderColor: '#ffffff',
            hoverOffset: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                boxWidth: 12,
                padding: 12,
                font: { size: 11, family: 'Inter, system-ui, sans-serif' }
              }
            },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const val = context.raw || 0;
                  const pct = totalDocs > 0 ? Math.round((val / totalDocs) * 100) : 0;
                  return ` ${context.label}: ${val} docs (${pct}%)`;
                }
              }
            }
          },
          cutout: '62%'
        }
      });
    } else {
      // Clean HTML visual bar fallback if Chart.js CDN is unavailable
      container.innerHTML = labels.map((name, i) => {
        const count = counts[i];
        const pct = totalDocs > 0 ? Math.round((count / totalDocs) * 100) : 0;
        return `
          <div class="category-bar-row" style="margin-bottom: 0.5rem;">
            <span class="category-bar-label" style="width: 100px;">${name}</span>
            <div class="category-bar-track" style="flex: 1; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden;">
              <div class="category-bar-fill" style="width: ${pct}%; height: 100%; background: ${colors[i] || '#7c3aed'};"></div>
            </div>
            <span class="category-bar-count" style="width: 75px; text-align: right; font-size: 0.8rem;">${count} (${pct}%)</span>
          </div>
        `;
      }).join('');
    }
  }

  renderFileTypeChart(distribution, docs) {
    const container = document.getElementById('dash-filetype-chart');
    const countBadge = document.getElementById('dash-type-count-badge');

    if (!container) return;

    let labels = [];
    let counts = [];
    const typeColors = {
      'PDF': '#ef4444',
      'WORD': '#3b82f6',
      'POWERPOINT': '#f97316',
      'EXCEL': '#10b981',
      'IMAGE': '#8b5cf6',
      'TEXT': '#64748b',
      'OTHER': '#94a3b8'
    };

    if (distribution && distribution.length > 0) {
      labels = distribution.map(d => d.file_type);
      counts = distribution.map(d => d.count);
    } else {
      // Aggregate from client documents
      const typeMap = {};
      docs.forEach(d => {
        const t = d.type || 'OTHER';
        typeMap[t] = (typeMap[t] || 0) + 1;
      });
      labels = Object.keys(typeMap);
      counts = Object.values(typeMap);
    }

    const totalDocs = counts.reduce((a, b) => a + b, 0);
    if (countBadge) countBadge.textContent = `${labels.length} Formats`;

    if (totalDocs === 0) {
      if (this.fileTypeChart) {
        this.fileTypeChart.destroy();
        this.fileTypeChart = null;
      }
      container.innerHTML = `
        <div style="text-align: center; padding: 2.5rem 1rem; color: var(--text-secondary); font-size: 0.85rem;">
          <div style="margin-bottom: 0.5rem; opacity: 0.4;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
          </div>
          No files uploaded yet.<br>File format distribution will appear here.
        </div>
      `;
      return;
    }

    if (!document.getElementById('dash-filetype-canvas')) {
      container.innerHTML = '<canvas id="dash-filetype-canvas" style="max-height: 240px;"></canvas>';
    }
    const currentCanvas = document.getElementById('dash-filetype-canvas');
    currentCanvas.style.display = 'block';

    const barColors = labels.map(t => typeColors[t.toUpperCase()] || '#7c3aed');

    if (typeof Chart !== 'undefined') {
      if (this.fileTypeChart) {
        this.fileTypeChart.destroy();
      }

      const ctx = currentCanvas.getContext('2d');
      this.fileTypeChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Documents',
            data: counts,
            backgroundColor: barColors,
            borderRadius: 6,
            borderSkipped: false
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (context) => ` ${context.raw} document(s)`
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { precision: 0, font: { size: 10 } },
              grid: { color: '#f1f5f9' }
            },
            x: {
              ticks: { font: { size: 10, weight: '500' } },
              grid: { display: false }
            }
          }
        }
      });
    } else {
      container.innerHTML = labels.map((type, i) => {
        const count = counts[i];
        const pct = totalDocs > 0 ? Math.round((count / totalDocs) * 100) : 0;
        return `
          <div class="category-bar-row" style="margin-bottom: 0.5rem;">
            <span class="category-bar-label" style="width: 80px;">${type}</span>
            <div class="category-bar-track" style="flex: 1; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden;">
              <div class="category-bar-fill" style="width: ${pct}%; height: 100%; background: ${barColors[i]};"></div>
            </div>
            <span class="category-bar-count" style="width: 75px; text-align: right; font-size: 0.8rem;">${count} docs</span>
          </div>
        `;
      }).join('');
    }
  }

  renderRecentUploads(recentDocs) {
    const recentDocsList = document.getElementById('dash-recent-docs');
    if (!recentDocsList) return;

    if (!recentDocs || recentDocs.length === 0) {
      recentDocsList.innerHTML = `
        <div class="placeholder-box" style="padding: 2.5rem 1rem;">
          <div class="placeholder-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
          </div>
          <h4 style="font-size: 1rem; color: var(--text-primary); margin-top: 0.5rem;">No documents uploaded yet</h4>
          <p style="color: var(--text-secondary); font-size: 0.825rem; max-width: 320px;">
            Upload documents in the Upload section to begin automated processing and classification.
          </p>
          <a href="#upload" class="btn btn-primary btn-sm mt-3" onclick="window.navigationManager.navigateTo('upload')">
            Upload Document
          </a>
        </div>
      `;
      return;
    }

    recentDocsList.innerHTML = `
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Document Name</th>
              <th>Category</th>
              <th>Size</th>
              <th>Uploaded</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            ${recentDocs.map(doc => {
              const name = doc.filename || doc.name;
              const type = doc.file_type || doc.type;
              const cat = doc.category_name || doc.category;
              const size = doc.file_size || doc.size;
              const date = doc.created_at || doc.uploadDate;
              return `
                <tr>
                  <td>
                    <div class="file-title-cell">
                      <div class="file-icon-box ${this.getFileIconClass(type)}">${type}</div>
                      <div>
                        <div class="file-info-main">${this.escapeHtml(name)}</div>
                        <div class="file-info-sub">${type} &bull; ${doc.id.substring(0, 8)}...</div>
                      </div>
                    </div>
                  </td>
                  <td><span class="badge badge-purple">${cat}</span></td>
                  <td>${this.state.formatBytes(size)}</td>
                  <td style="color: var(--text-muted); font-size: 0.8rem;">
                    ${new Date(date).toLocaleDateString()} ${new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                  <td>
                    <button class="btn btn-secondary btn-sm" onclick="window.documentsController.previewDocument('${doc.id}')">
                      Preview
                    </button>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
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
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.dashboardController = new DashboardController();
});
