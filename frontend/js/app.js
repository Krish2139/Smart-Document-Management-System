/**
 * Main Application Orchestrator
 */
class App {
  constructor() {
    this.api = window.apiService;
    this.modalCallback = null;
    this.init();
  }

  init() {
    this.bindGlobalEvents();
    this.runHealthCheck();
  }

  bindGlobalEvents() {
    // Refresh button
    const refreshBtn = document.getElementById('btn-refresh-health');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.runHealthCheck());
    }

    // Mobile sidebar toggle
    const mobileBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.querySelector('.app-sidebar');
    if (mobileBtn && sidebar) {
      mobileBtn.addEventListener('click', () => {
        sidebar.classList.toggle('mobile-open');
      });

      // Close sidebar when clicking any nav link on mobile
      document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
          sidebar.classList.remove('mobile-open');
        });
      });
    }

    // Modal close bindings
    const modalBackdrop = document.getElementById('app-modal-backdrop');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');
    const modalConfirmBtn = document.getElementById('modal-confirm-btn');

    if (modalCloseBtn) modalCloseBtn.addEventListener('click', () => this.closeModal());
    if (modalCancelBtn) modalCancelBtn.addEventListener('click', () => this.closeModal());
    if (modalBackdrop) {
      modalBackdrop.addEventListener('click', (e) => {
        if (e.target === modalBackdrop) this.closeModal();
      });
    }

    if (modalConfirmBtn) {
      modalConfirmBtn.addEventListener('click', () => {
        if (typeof this.modalCallback === 'function') {
          const shouldClose = this.modalCallback();
          if (shouldClose !== false) {
            this.closeModal();
          }
        } else {
          this.closeModal();
        }
      });
    }
  }

  /**
   * Universal Modal Dialog
   */
  showModal({ title, body, confirmText = 'Confirm', confirmClass = 'btn-primary', onConfirm = null }) {
    const backdrop = document.getElementById('app-modal-backdrop');
    const titleEl = document.getElementById('modal-title');
    const bodyEl = document.getElementById('modal-body');
    const confirmBtn = document.getElementById('modal-confirm-btn');

    if (!backdrop || !titleEl || !bodyEl || !confirmBtn) return;

    titleEl.textContent = title;
    bodyEl.innerHTML = body;
    confirmBtn.textContent = confirmText;
    confirmBtn.className = `btn ${confirmClass}`;
    this.modalCallback = onConfirm;

    backdrop.classList.add('open');
  }

  closeModal() {
    const backdrop = document.getElementById('app-modal-backdrop');
    if (backdrop) backdrop.classList.remove('open');
    this.modalCallback = null;
  }

  /**
   * Floating Toast Notification
   */
  showToast(message, type = 'info', duration = 3500) {
    let container = document.getElementById('app-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'app-toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    let icon = '';
    if (type === 'error') {
      icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" style="flex-shrink: 0;"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
    } else if (type === 'success') {
      icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" style="flex-shrink: 0;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
    } else {
      icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2" style="flex-shrink: 0;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `
      ${icon}
      <div style="flex: 1; font-weight: 500;">${this.escapeHtml(message)}</div>
      <button style="background: none; border: none; color: #94a3b8; cursor: pointer; padding: 0; font-size: 1.1rem; line-height: 1;" onclick="this.parentElement.remove()">
        &times;
      </button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  /**
   * Health Check with visual update
   */
  async runHealthCheck() {
    const topbarStatusPill = document.getElementById('topbar-status-pill');
    const jsonOutput = document.getElementById('json-health-output');
    const lastCheckedTime = document.getElementById('status-last-checked');
    const latencyBadge = document.getElementById('status-latency');

    if (topbarStatusPill) {
      topbarStatusPill.innerHTML = '<span class="status-dot connecting"></span> Checking...';
      topbarStatusPill.className = 'badge badge-warning';
    }

    const result = await this.api.checkHealth();

    if (lastCheckedTime) {
      lastCheckedTime.textContent = new Date().toLocaleTimeString();
    }

    if (latencyBadge) {
      latencyBadge.textContent = `${result.latencyMs} ms`;
    }

    if (result.success && result.data) {
      const data = result.data;
      const isHealthy = data.status === 'healthy';

      if (topbarStatusPill) {
        topbarStatusPill.innerHTML = `<span class="status-dot ${isHealthy ? 'healthy' : 'degraded'}"></span> API ${isHealthy ? 'Online' : 'Degraded'}`;
        topbarStatusPill.className = `badge ${isHealthy ? 'badge-success' : 'badge-danger'}`;
      }

      if (jsonOutput) {
        jsonOutput.textContent = JSON.stringify(data, null, 2);
      }
    } else {
      if (topbarStatusPill) {
        topbarStatusPill.innerHTML = '<span class="status-dot degraded"></span> API Offline';
        topbarStatusPill.className = 'badge badge-danger';
      }

      if (jsonOutput) {
        jsonOutput.textContent = JSON.stringify({
          error: result.error || 'Backend not responding',
          hint: 'Ensure FastAPI backend is running on http://127.0.0.1:8000'
        }, null, 2);
      }
    }
  }

  escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});
