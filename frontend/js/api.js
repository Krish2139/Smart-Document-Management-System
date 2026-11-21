/**
 * Reusable REST API Client for Smart Document Manager
 * Connects frontend controllers directly to FastAPI backend endpoints.
 */

const API_BASE_URL = window.location.origin.startsWith('http') 
  ? window.location.origin 
  : 'http://127.0.0.1:8000';

class ApiService {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
    this.apiPrefix = '/api';
  }

  /**
   * Token and user session management
   */
  getToken() {
    return localStorage.getItem('smartdoc_token');
  }

  setToken(token) {
    if (token) {
      localStorage.setItem('smartdoc_token', token);
    } else {
      localStorage.removeItem('smartdoc_token');
    }
  }

  getUser() {
    try {
      const u = localStorage.getItem('smartdoc_user');
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  }

  setUser(user) {
    if (user) {
      localStorage.setItem('smartdoc_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('smartdoc_user');
    }
  }

  clearAuth() {
    localStorage.removeItem('smartdoc_token');
    localStorage.removeItem('smartdoc_user');
  }

  /**
   * Universal fetch wrapper with latency tracking and structured error handling
   */
  async request(endpoint, options = {}) {
    const startTime = performance.now();
    const url = `${this.baseUrl}${this.apiPrefix}${endpoint}`;

    try {
      const headers = { ...options.headers };

      // Auto-attach JWT Bearer token if present
      const token = this.getToken();
      if (token && !headers['Authorization']) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Only set Content-Type to JSON if not uploading FormData
      if (!(options.body instanceof FormData) && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
      }

      const response = await fetch(url, {
        ...options,
        headers,
      });

      const latencyMs = Math.round(performance.now() - startTime);

      // Handle file downloads
      if (options.isDownload) {
        if (!response.ok) {
          throw new Error(`Download failed with status ${response.status}`);
        }
        const blob = await response.blob();
        return { success: true, status: response.status, latencyMs, blob };
      }

      const data = await response.json();

      return {
        success: response.ok,
        status: response.status,
        latencyMs,
        data,
      };
    } catch (error) {
      const latencyMs = Math.round(performance.now() - startTime);
      console.error(`API request error on ${endpoint}:`, error);
      return {
        success: false,
        status: 0,
        latencyMs,
        error: error.message || 'Network connection failure',
      };
    }
  }

  /* 0. Authentication Endpoints */
  async login(usernameOrEmail, password) {
    const res = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username_or_email: usernameOrEmail, password }),
    });
    if (res.success && res.data && res.data.access_token) {
      this.setToken(res.data.access_token);
      this.setUser(res.data.user);
    }
    return res;
  }

  async register(userData) {
    const res = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
    if (res.success && res.data && res.data.access_token) {
      this.setToken(res.data.access_token);
      this.setUser(res.data.user);
    }
    return res;
  }

  async getMe() {
    return this.request('/auth/me');
  }

  async updateProfile(profileData) {
    const res = await this.request('/auth/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData),
    });
    if (res.success && res.data) {
      this.setUser(res.data);
    }
    return res;
  }

  async changePassword(currentPassword, newPassword) {
    return this.request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  }

  async logout() {
    const res = await this.request('/auth/logout', { method: 'POST' });
    this.clearAuth();
    return res;
  }

  /* 1. Health Endpoint */
  async checkHealth() {
    return this.request('/health');
  }

  /* 2. Documents Endpoints */
  async getDocuments(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/documents${query ? '?' + query : ''}`);
  }

  async searchDocuments(keyword, params = {}) {
    const qParams = new URLSearchParams({ q: keyword, ...params }).toString();
    return this.request(`/documents/search?${qParams}`);
  }

  async getDocument(id) {
    return this.request(`/documents/${id}`);
  }

  async uploadDocument(file, category = '') {
    const formData = new FormData();
    formData.append('file', file);
    if (category) {
      formData.append('category', category);
    }
    return this.request('/documents', {
      method: 'POST',
      body: formData,
    });
  }

  async uploadBatch(files, category = '') {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    if (category) {
      formData.append('category', category);
    }
    return this.request('/documents/batch', {
      method: 'POST',
      body: formData,
    });
  }

  async deleteDocument(id) {
    return this.request(`/documents/${id}`, {
      method: 'DELETE',
    });
  }

  async updateDocumentCategory(id, categoryName) {
    return this.request(`/documents/${id}/category`, {
      method: 'PATCH',
      body: JSON.stringify({ category_name: categoryName }),
    });
  }

  async getDocumentMetadata(id) {
    return this.request(`/documents/${id}/metadata`);
  }

  async downloadDocument(id) {
    return this.request(`/documents/${id}/download`, {
      isDownload: true,
    });
  }

  getPreviewUrl(id) {
    return `${this.baseUrl}${this.apiPrefix}/documents/${id}/preview`;
  }

  getDownloadUrl(id) {
    return `${this.baseUrl}${this.apiPrefix}/documents/${id}/download`;
  }

  /* 3. Categories Endpoints */
  async getCategories() {
    return this.request('/categories');
  }

  async createCategory(data) {
    return this.request('/categories', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateCategory(id, data) {
    return this.request(`/categories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteCategory(id, reassignTo = 'Other') {
    const query = new URLSearchParams({ reassign_to: reassignTo }).toString();
    return this.request(`/categories/${id}?${query}`, {
      method: 'DELETE',
    });
  }

  /* 4. Dashboard Statistics Endpoint */
  async getDashboardStatistics() {
    return this.request('/dashboard/statistics');
  }

  /* 5. Activities Endpoint */
  async getActivities(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/activities${query ? '?' + query : ''}`);
  }

  /* 6. Settings Endpoints */
  async getSettings() {
    return this.request('/settings');
  }

  async updateSettings(data) {
    return this.request('/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }
}

// Export singleton instance
window.apiService = new ApiService();
