/**
 * Activity History View Controller
 * Renders real audit trail with keyword search, activity type filters, and date range filters.
 */
class ActivityController {
  constructor() {
    this.state = window.stateManager;
    this.searchQuery = '';
    this.typeFilter = 'all';
    this.dateFilter = 'all';

    this.init();
  }

  init() {
    this.bindEvents();
    this.render();
    this.state.subscribe(() => this.render());
  }

  bindEvents() {
    const searchInput = document.getElementById('act-search-input');
    const typeSelect = document.getElementById('act-type-filter');
    const dateSelect = document.getElementById('act-date-filter');

    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.toLowerCase().trim();
        this.render();
      });
    }

    if (typeSelect) {
      typeSelect.addEventListener('change', (e) => {
        this.typeFilter = e.target.value;
        this.render();
      });
    }

    if (dateSelect) {
      dateSelect.addEventListener('change', (e) => {
        this.dateFilter = e.target.value;
        this.render();
      });
    }
  }

  getFilteredActivities() {
    let activities = this.state.getActivities();

    // 1. Keyword search (title, description, document name, category, ID)
    if (this.searchQuery) {
      const q = this.searchQuery;
      activities = activities.filter(a => {
        const titleMatch = (a.title || '').toLowerCase().includes(q);
        const descMatch = (a.description || '').toLowerCase().includes(q);
        const docMatch = (a.documentName || '').toLowerCase().includes(q);
        const catMatch = (a.category || '').toLowerCase().includes(q);
        const idMatch = (a.id || '').toLowerCase().includes(q);
        const typeMatch = (a.type || '').toLowerCase().includes(q);
        return titleMatch || descMatch || docMatch || catMatch || idMatch || typeMatch;
      });
    }

    // 2. Filter by activity type
    if (this.typeFilter !== 'all') {
      const tf = this.typeFilter.toLowerCase();
      activities = activities.filter(a => {
        const at = (a.type || '').toLowerCase();
        if (tf === 'category') {
          return at.startsWith('category');
        }
        return at === tf || at.startsWith(tf);
      });
    }

    // 3. Filter by date range
    if (this.dateFilter !== 'all') {
      const now = new Date();
      activities = activities.filter(a => {
        const d = new Date(a.timestamp);
        const diffDays = (now - d) / (1000 * 60 * 60 * 24);
        if (this.dateFilter === 'today') return diffDays <= 1;
        if (this.dateFilter === '7days') return diffDays <= 7;
        if (this.dateFilter === '30days') return diffDays <= 30;
        return true;
      });
    }

    return activities;
  }

  render() {
    const feed = document.getElementById('activity-feed');
    const emptyState = document.getElementById('activity-empty-state');
    const totalCount = document.getElementById('activity-total-count');

    if (!feed) return;

    const filtered = this.getFilteredActivities();

    if (totalCount) totalCount.textContent = `${filtered.length} events`;

    if (filtered.length === 0) {
      feed.style.display = 'none';
      if (emptyState) emptyState.style.display = 'flex';
      return;
    }

    feed.style.display = 'flex';
    if (emptyState) emptyState.style.display = 'none';

    feed.innerHTML = filtered.map(item => {
      const dateObj = new Date(item.timestamp);
      const formattedDate = dateObj.toLocaleDateString();
      const formattedTime = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      const typeLabel = this.formatTypeLabel(item.type);

      return `
        <div class="activity-feed-item">
          <div class="activity-feed-icon ${this.getIconClass(item.type)}">
            ${this.getIconSvg(item.type)}
          </div>
          <div class="activity-feed-content" style="flex: 1;">
            <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; flex-wrap: wrap;">
              <div>
                <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                  <span class="badge ${this.getBadgeClass(item.type)}" style="font-size: 0.65rem; text-transform: uppercase; font-weight: 700;">
                    ${typeLabel}
                  </span>
                  <span class="activity-feed-title" style="font-weight: 600; font-size: 0.92rem; color: var(--text-primary);">
                    ${this.escapeHtml(item.title)}
                  </span>
                </div>
                ${item.description && item.description !== item.title ? `
                  <p style="color: var(--text-secondary); font-size: 0.825rem; margin-top: 0.25rem; line-height: 1.4;">
                    ${this.escapeHtml(item.description)}
                  </p>
                ` : ''}
              </div>
              <div style="text-align: right; font-size: 0.75rem; color: var(--text-muted);">
                <div>${formattedDate}</div>
                <div>${formattedTime}</div>
              </div>
            </div>

            <!-- Activity Details Meta Line -->
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px dashed var(--border-color); font-size: 0.75rem; color: var(--text-muted); flex-wrap: wrap;">
              <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
                ${item.documentName && item.documentName !== '-' ? `
                  <span>
                    <strong style="color: var(--text-primary);">Doc:</strong> ${this.escapeHtml(item.documentName)}
                  </span>
                ` : ''}
                ${item.documentId ? `
                  <span>
                    <strong>Doc ID:</strong> <code style="font-size: 0.7rem;">${item.documentId.substring(0, 8)}...</code>
                  </span>
                ` : ''}
                ${item.category && item.category !== '-' ? `
                  <span class="badge badge-purple" style="font-size: 0.65rem;">${item.category}</span>
                ` : ''}
                <span class="badge badge-success" style="font-size: 0.65rem;">${item.status || 'Success'}</span>
              </div>
              <span style="font-size: 0.7rem; color: var(--text-muted); opacity: 0.8;">
                Activity ID: <code>${item.id.substring(0, 8)}...</code>
              </span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  formatTypeLabel(type) {
    if (!type) return 'EVENT';
    const t = type.toLowerCase();
    if (t === 'upload') return 'DOCUMENT UPLOAD';
    if (t === 'download') return 'DOCUMENT DOWNLOAD';
    if (t === 'delete') return 'DOCUMENT DELETE';
    if (t === 'category_change' || t === 'category') return 'CATEGORY CHANGE';
    if (t === 'category_create') return 'CATEGORY CREATE';
    if (t === 'category_delete') return 'CATEGORY DELETE';
    return type.toUpperCase();
  }

  getIconClass(type) {
    if (!type) return 'stat-icon-purple';
    const t = type.toLowerCase();
    if (t === 'upload') return 'stat-icon-green';
    if (t === 'download') return 'stat-icon-blue';
    if (t === 'delete') return 'stat-icon-orange';
    if (t.startsWith('category')) return 'stat-icon-purple';
    return 'stat-icon-purple';
  }

  getBadgeClass(type) {
    if (!type) return 'badge-subtle';
    const t = type.toLowerCase();
    if (t === 'upload') return 'badge-success';
    if (t === 'download') return 'badge-info';
    if (t === 'delete') return 'badge-warning';
    if (t.startsWith('category')) return 'badge-purple';
    return 'badge-subtle';
  }

  getIconSvg(type) {
    const t = (type || '').toLowerCase();
    if (t === 'upload') {
      return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>';
    }
    if (t === 'download') {
      return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>';
    }
    if (t === 'delete') {
      return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>';
    }
    if (t.startsWith('category')) {
      return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>';
    }
    return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>';
  }

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.activityController = new ActivityController();
});
