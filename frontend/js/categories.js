/**
 * Categories View Controller
 */
class CategoriesController {
  constructor() {
    this.state = window.stateManager;
    this.init();
  }

  init() {
    this.bindEvents();
    this.render();
    this.state.subscribe(() => this.render());
  }

  bindEvents() {
    const createBtn = document.getElementById('cat-create-btn');
    if (createBtn) {
      createBtn.addEventListener('click', () => this.openCreateModal());
    }
  }

  render() {
    const grid = document.getElementById('categories-grid');
    if (!grid) return;

    const categories = this.state.getCategories();

    grid.innerHTML = categories.map(cat => `
      <div class="category-card">
        <div>
          <div class="category-card-top">
            <div class="category-icon-wrapper" style="background: ${this.hexToRgba(cat.color, 0.12)}; color: ${cat.color};">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
              </svg>
            </div>
            <span class="badge badge-purple" style="font-size: 0.75rem;">
              ${cat.count} ${cat.count === 1 ? 'doc' : 'docs'}
            </span>
          </div>

          <h3 class="category-name">${this.escapeHtml(cat.name)}</h3>
          <p class="category-desc">${this.escapeHtml(cat.description || 'No description provided.')}</p>
        </div>

        <div class="category-footer">
          <button class="btn btn-secondary btn-sm" onclick="window.categoriesController.openEditModal('${cat.id}')">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
            Edit
          </button>
          ${cat.name.toLowerCase() !== 'other' ? `
            <button class="btn btn-danger btn-sm" onclick="window.categoriesController.confirmDeleteCategory('${cat.id}')">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
              Delete
            </button>
          ` : `
            <span style="font-size: 0.75rem; color: var(--text-muted);">Default</span>
          `}
        </div>
      </div>
    `).join('');
  }

  openCreateModal() {
    window.app.showModal({
      title: 'Create New Category',
      body: `
        <div class="form-group">
          <label class="form-label" for="new-cat-name">Category Name *</label>
          <input type="text" id="new-cat-name" class="form-control" placeholder="e.g. Legal, Finance, Marketing">
        </div>
        <div class="form-group">
          <label class="form-label" for="new-cat-desc">Description</label>
          <textarea id="new-cat-desc" class="form-control" rows="3" placeholder="Brief description of documents stored under this category..."></textarea>
        </div>
        <div class="form-group">
          <label class="form-label">Accent Color</label>
          <div style="display: flex; gap: 0.5rem; align-items: center;">
            <input type="color" id="new-cat-color" value="#7c3aed" style="width: 42px; height: 38px; border-radius: var(--radius-sm); border: 1px solid var(--border-color); cursor: pointer;">
            <span style="font-size: 0.85rem; color: var(--text-secondary);">Select card accent color</span>
          </div>
        </div>
      `,
      confirmText: 'Create Category',
      onConfirm: async () => {
        const nameInput = document.getElementById('new-cat-name');
        const descInput = document.getElementById('new-cat-desc');
        const colorInput = document.getElementById('new-cat-color');

        if (!nameInput || !nameInput.value.trim()) {
          window.app.showToast('Please provide a category name.', 'error');
          return false;
        }

        const name = nameInput.value.trim();
        const desc = descInput ? descInput.value.trim() : '';
        const color = colorInput ? colorInput.value : '#7c3aed';

        const result = await this.state.addCategory(name, desc, color);
        if (result.success) {
          window.app.showToast(`Category "${name}" created successfully!`, 'success');
        } else {
          window.app.showToast(`Error: ${result.error}`, 'error');
        }
        return true;
      }
    });
  }

  openEditModal(id) {
    const cat = this.state.getCategories().find(c => c.id === id);
    if (!cat) return;

    window.app.showModal({
      title: `Edit Category: ${cat.name}`,
      body: `
        <div class="form-group">
          <label class="form-label" for="edit-cat-name">Category Name *</label>
          <input type="text" id="edit-cat-name" class="form-control" value="${this.escapeHtml(cat.name)}">
        </div>
        <div class="form-group">
          <label class="form-label" for="edit-cat-desc">Description</label>
          <textarea id="edit-cat-desc" class="form-control" rows="3">${this.escapeHtml(cat.description || '')}</textarea>
        </div>
        <div class="form-group">
          <label class="form-label">Accent Color</label>
          <div style="display: flex; gap: 0.5rem; align-items: center;">
            <input type="color" id="edit-cat-color" value="${cat.color || '#7c3aed'}" style="width: 42px; height: 38px; border-radius: var(--radius-sm); border: 1px solid var(--border-color); cursor: pointer;">
            <span style="font-size: 0.85rem; color: var(--text-secondary);">Select card accent color</span>
          </div>
        </div>
      `,
      confirmText: 'Save Changes',
      onConfirm: async () => {
        const nameInput = document.getElementById('edit-cat-name');
        const descInput = document.getElementById('edit-cat-desc');
        const colorInput = document.getElementById('edit-cat-color');

        if (!nameInput || !nameInput.value.trim()) {
          window.app.showToast('Category name cannot be empty.', 'error');
          return false;
        }

        const name = nameInput.value.trim();
        const desc = descInput ? descInput.value.trim() : '';
        const color = colorInput ? colorInput.value : cat.color;

        const result = await this.state.updateCategory(id, name, desc, color);
        if (result.success) {
          window.app.showToast(`Category "${name}" updated successfully!`, 'success');
        } else {
          window.app.showToast(`Error: ${result.error}`, 'error');
        }
        return true;
      }
    });
  }

  confirmDeleteCategory(id) {
    const cat = this.state.getCategories().find(c => c.id === id);
    if (!cat) return;

    const otherCategories = this.state.getCategories().filter(c => c.id !== id);
    const optionsHtml = otherCategories.map(c =>
      `<option value="${c.name}" ${c.name.toLowerCase() === 'other' ? 'selected' : ''}>${c.name}</option>`
    ).join('');

    const hasDocs = cat.count > 0;

    window.app.showModal({
      title: `Delete Category: ${cat.name}`,
      body: `
        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
          <p>Are you sure you want to delete category <strong>"${this.escapeHtml(cat.name)}"</strong>?</p>
          ${hasDocs ? `
            <div style="background: #fffbeb; border: 1px solid #fef3c7; border-left: 4px solid #f59e0b; padding: 0.85rem; border-radius: var(--radius-sm); font-size: 0.85rem; color: #92400e;">
              <strong>Active Documents Warning:</strong> This category contains <strong>${cat.count}</strong> document(s). To prevent data loss, select a destination category to safely reassign all associated documents before deletion:
            </div>
            <div class="form-group" style="margin-top: 0.25rem;">
              <label class="form-label" for="delete-reassign-select">Reassign Documents To:</label>
              <select id="delete-reassign-select" class="form-control">
                ${optionsHtml}
              </select>
            </div>
          ` : `
            <p style="color: var(--text-secondary); font-size: 0.85rem;">
              This category currently contains 0 documents and will be safely deleted.
            </p>
          `}
        </div>
      `,
      confirmText: hasDocs ? 'Confirm Reassignment & Delete' : 'Delete Category',
      confirmClass: 'btn-danger',
      onConfirm: async () => {
        const select = document.getElementById('delete-reassign-select');
        const reassignTo = select ? select.value : 'Other';
        const success = await this.state.deleteCategory(id, reassignTo);
        if (success) {
          window.app.showToast(`Category "${cat.name}" deleted (docs reassigned to ${reassignTo}).`, 'success');
        } else {
          window.app.showToast(`Failed to delete category "${cat.name}".`, 'error');
        }
      }
    });
  }

  hexToRgba(hex, alpha = 1) {
    if (!hex) return `rgba(124, 58, 237, ${alpha})`;
    let c = hex.replace('#', '');
    if (c.length === 3) c = c.split('').map(x => x + x).join('');
    const num = parseInt(c, 16);
    return `rgba(${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}, ${alpha})`;
  }

  escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.categoriesController = new CategoriesController();
});
