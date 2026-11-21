/**
 * Client-Side State & Backend Sync Manager
 * Synchronizes frontend data with FastAPI REST API endpoints
 */

const DEFAULT_CATEGORIES = [
  { id: 'cat-academic', name: 'Academic', description: 'Course materials, syllabi, study guides and lecture notes.', color: '#3b82f6', icon: 'book', count: 0 },
  { id: 'cat-research', name: 'Research', description: 'Academic papers, scholarly journals, survey data and abstracts.', color: '#8b5cf6', icon: 'cpu', count: 0 },
  { id: 'cat-personal', name: 'Personal', description: 'Identity records, certificates, personal taxes and resumes.', color: '#10b981', icon: 'user', count: 0 },
  { id: 'cat-projects', name: 'Projects', description: 'Software blueprints, specifications, project plans and diagrams.', color: '#f59e0b', icon: 'briefcase', count: 0 },
  { id: 'cat-business', name: 'Business', description: 'Corporate contracts, financial invoices, purchase orders and agreements.', color: '#ec4899', icon: 'trending-up', count: 0 },
  { id: 'cat-other', name: 'Other', description: 'Miscellaneous uncategorized files and general archives.', color: '#64748b', icon: 'folder', count: 0 },
];

class StateManager {
  constructor() {
    this.api = window.apiService;
    this.documents = [];
    this.categories = DEFAULT_CATEGORIES;
    this.activities = [];
    this.dashboardStats = null;
    this.settings = {
      fullName: 'User Profile',
      email: 'user@smartdoc.local',
      role: 'User',
      autoCategorize: true,
      duplicateDetection: true,
      defaultCategory: 'Other',
      maxUploadSizeMb: 25,
      storageQuotaMb: 500
    };

    this.listeners = [];
    this.isSyncing = false;

    // Initial sync with backend
    this.syncWithBackend();
  }

  subscribe(listener) {
    this.listeners.push(listener);
  }

  notify() {
    this.listeners.forEach(fn => {
      try { fn(this); } catch (e) { console.error('Listener error:', e); }
    });
  }

  async syncWithBackend() {
    if (this.isSyncing) return;
    this.isSyncing = true;

    const isLoggedIn = !!((window.authManager && window.authManager.currentUser) || (this.api && this.api.getUser()));

    try {
      // 1. Fetch Categories
      const catRes = await this.api.getCategories();
      if (catRes.success && Array.isArray(catRes.data)) {
        this.categories = catRes.data.map(c => ({
          id: c.id,
          name: c.name,
          description: c.description || '',
          color: c.color || '#7c3aed',
          icon: c.icon || 'folder',
          count: isLoggedIn ? (c.document_count || 0) : 0
        }));
      }

      if (!isLoggedIn) {
        // Guest/unauthenticated: zero out all user data
        this.documents = [];
        this.activities = [];
        this.dashboardStats = {
          total_documents: 0,
          total_storage_used: 0,
          total_storage_used_formatted: "0.00 KB",
          storage_usage_percentage: 0,
          storage: {
            used_bytes: 0,
            used_formatted: "0.00 KB",
            quota_bytes: 524288000,
            quota_formatted: "500 MB",
            percentage: 0
          },
          total_categories: this.categories.length,
          recent_activity_count: 0,
          total_activities: 0,
          category_distribution: this.categories.map(c => ({
            category_id: c.id,
            category_name: c.name,
            count: 0,
            percentage: 0,
            color: c.color || '#7c3aed'
          })),
          file_type_distribution: [],
          recent_documents: []
        };
        this.settings = {
          fullName: '',
          email: '',
          role: 'User',
          autoCategorize: true,
          duplicateDetection: true,
          defaultCategory: 'Other',
          maxUploadSizeMb: 25,
          storageQuotaMb: 500
        };
        this.notify();
        this.isSyncing = false;
        return;
      }

      // 2. Fetch Documents (when logged in)
      const docRes = await this.api.getDocuments({ limit: 500 });
      if (docRes.success && docRes.data && Array.isArray(docRes.data.items)) {
        this.documents = docRes.data.items.map(d => ({
          id: d.id,
          name: d.filename,
          originalName: d.original_filename,
          size: d.file_size,
          type: d.file_type,
          extension: d.file_extension,
          mimeType: d.mime_type,
          category: d.category_name,
          isManual: d.is_manually_categorized,
          userId: d.user_id,
          uploadedBy: d.uploaded_by || 'Anonymous',
          uploadDate: d.created_at,
          hash: d.sha256_hash,
          url: `${this.api.baseUrl}/api/documents/${d.id}/download`
        }));
      }

      // 3. Fetch Activities
      const actRes = await this.api.getActivities({ limit: 200 });
      if (actRes.success && actRes.data && Array.isArray(actRes.data.items)) {
        this.activities = actRes.data.items.map(a => ({
          id: a.id,
          type: a.activity_type,
          title: a.title,
          description: a.description || a.title,
          documentId: a.document_id,
          documentName: a.document_name,
          category: a.category_name,
          timestamp: a.created_at || a.timestamp,
          status: a.status,
          details: a.details
        }));
      }

      // 4. Fetch Real Dashboard Overview Statistics
      const dashRes = await this.api.getDashboardStatistics();
      if (dashRes.success && dashRes.data) {
        this.dashboardStats = dashRes.data;
      }

      // 5. Fetch Settings
      const setRes = await this.api.getSettings();
      if (setRes.success && setRes.data) {
        const user = (window.authManager && window.authManager.currentUser) || this.api.getUser();
        this.settings = {
          fullName: (user && user.full_name) ? user.full_name : (user && user.username ? user.username : (setRes.data.full_name || '')),
          email: (user && user.email) ? user.email : (setRes.data.email || ''),
          role: (user && user.role) ? user.role : (setRes.data.role || 'User'),
          autoCategorize: setRes.data.auto_categorize,
          duplicateDetection: setRes.data.duplicate_detection,
          defaultCategory: setRes.data.default_category,
          maxUploadSizeMb: setRes.data.max_upload_size_mb,
          storageQuotaMb: setRes.data.storage_quota_mb
        };
      }
    } catch (e) {
      console.warn('Initial backend sync failed, using cached state:', e);
    } finally {
      this.isSyncing = false;
      this.notify();
    }
  }

  /* Documents */
  getDocuments() {
    return [...this.documents];
  }

  getDashboardStats() {
    return this.dashboardStats;
  }

  async uploadFileToBackend(file, category) {
    const res = await this.api.uploadDocument(file, category);
    if (res.success && res.data) {
      await this.syncWithBackend();
      return { success: true, doc: res.data };
    }
    const errMsg = res.data && res.data.error ? res.data.error.message : (res.error || 'Upload failed');
    return { success: false, error: errMsg };
  }

  async deleteDocument(id) {
    const res = await this.api.deleteDocument(id);
    if (res.success) {
      await this.syncWithBackend();
      return true;
    }
    return false;
  }

  async updateDocumentCategory(id, categoryName) {
    const res = await this.api.updateDocumentCategory(id, categoryName);
    if (res.success) {
      await this.syncWithBackend();
      return true;
    }
    return false;
  }

  /* Categories */
  getCategories() {
    return [...this.categories];
  }

  async addCategory(name, description = '', color = '#7c3aed') {
    const res = await this.api.createCategory({ name, description, color, icon: 'folder' });
    if (res.success) {
      await this.syncWithBackend();
      return { success: true, category: res.data };
    }
    const errMsg = res.data && res.data.error ? res.data.error.message : (res.error || 'Create category failed');
    return { success: false, error: errMsg };
  }

  async updateCategory(id, name, description, color) {
    const res = await this.api.updateCategory(id, { name, description, color });
    if (res.success) {
      await this.syncWithBackend();
      return { success: true, category: res.data };
    }
    const errMsg = res.data && res.data.error ? res.data.error.message : (res.error || 'Update category failed');
    return { success: false, error: errMsg };
  }

  async deleteCategory(id, reassignTo = 'Other') {
    const res = await this.api.deleteCategory(id, reassignTo);
    if (res.success) {
      await this.syncWithBackend();
      return true;
    }
    return false;
  }

  /* Activities */
  getActivities() {
    return [...this.activities];
  }

  async clearActivities() {
    this.activities = [];
    this.notify();
  }

  /* Settings */
  getSettings() {
    return { ...this.settings };
  }

  async updateSettings(newSettings) {
    const payload = {};
    if (newSettings.fullName !== undefined) payload.full_name = newSettings.fullName;
    if (newSettings.email !== undefined) payload.email = newSettings.email;
    if (newSettings.role !== undefined) payload.role = newSettings.role;
    if (newSettings.autoCategorize !== undefined) payload.auto_categorize = newSettings.autoCategorize;
    if (newSettings.duplicateDetection !== undefined) payload.duplicate_detection = newSettings.duplicateDetection;
    if (newSettings.defaultCategory !== undefined) payload.default_category = newSettings.defaultCategory;
    if (newSettings.maxUploadSizeMb !== undefined) payload.max_upload_size_mb = newSettings.maxUploadSizeMb;
    if (newSettings.storageQuotaMb !== undefined) payload.storage_quota_mb = newSettings.storageQuotaMb;

    const res = await this.api.updateSettings(payload);
    if (res.success) {
      await this.syncWithBackend();
      return true;
    }
    return false;
  }

  /* Formatters & Helpers */
  getTotalStorageBytes() {
    return this.documents.reduce((acc, doc) => acc + (doc.size || 0), 0);
  }

  formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0.00 KB';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  detectFileType(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    if (['pdf'].includes(ext)) return 'PDF';
    if (['doc', 'docx'].includes(ext)) return 'DOCX';
    if (['png', 'jpg', 'jpeg', 'webp', 'svg'].includes(ext)) return 'IMAGE';
    if (['txt', 'md', 'csv', 'json'].includes(ext)) return 'TEXT';
    return 'FILE';
  }

  suggestCategory(filename) {
    const lower = filename.toLowerCase();
    // Rule-based categorization strictly according to Part 5:
    // - Assignment, Notes, Exam -> Academic
    // - Research, Paper, Journal -> Research
    // - Project, Report, Development -> Projects
    // - Personal, Certificate -> Personal
    // - Invoice, Budget -> Business
    // - Other unmatched documents -> Other
    if (['assignment', 'notes', 'exam', 'syllabus', 'course', 'lecture', 'academic'].some(w => lower.includes(w))) return 'Academic';
    if (['research', 'paper', 'journal', 'thesis', 'study', 'abstract'].some(w => lower.includes(w))) return 'Research';
    if (['project', 'report', 'development', 'plan', 'spec', 'architecture'].some(w => lower.includes(w))) return 'Projects';
    if (['personal', 'certificate', 'passport', 'resume', 'cv', 'id', 'tax'].some(w => lower.includes(w))) return 'Personal';
    if (['invoice', 'budget', 'bill', 'contract', 'agreement', 'receipt', 'financial'].some(w => lower.includes(w))) return 'Business';
    return this.settings.defaultCategory || 'Other';
  }
}

window.stateManager = new StateManager();
