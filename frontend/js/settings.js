/**
 * Settings View Controller
 */
class SettingsController {
  constructor() {
    this.state = window.stateManager;
    this.activeTab = 'profile';
    this.init();
  }

  init() {
    this.bindEvents();
    this.populateSettings();
    this.state.subscribe(() => this.populateSettings());
  }

  bindEvents() {
    // Tabs
    const tabs = document.querySelectorAll('.settings-tab[data-tab]');
    tabs.forEach(tab => {
      tab.addEventListener('click', (e) => {
        e.preventDefault();
        const target = tab.getAttribute('data-tab');
        this.switchTab(target);
      });
    });

    // Profile form save
    const profileForm = document.getElementById('settings-profile-form');
    if (profileForm) {
      profileForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const nameInput = document.getElementById('settings-name');
        const emailInput = document.getElementById('settings-email');
        const name = nameInput ? nameInput.value.trim() : '';
        const email = emailInput ? emailInput.value.trim() : '';

        if (!name || !email) {
          window.app.showToast('Please provide both full name and email.', 'error');
          return;
        }

        const saveBtn = profileForm.querySelector('button[type="submit"]');
        if (saveBtn) {
          saveBtn.disabled = true;
          saveBtn.textContent = 'Saving...';
        }

        // Update authenticated user on backend if logged in
        if (window.apiService && window.apiService.getToken()) {
          try {
            const res = await window.apiService.updateProfile({ full_name: name, email: email });
            if (res.success && res.data) {
              window.apiService.setUser(res.data);
              if (window.authManager) {
                window.authManager.currentUser = res.data;
                window.authManager.renderHeaderUser();
              }
              window.app.showToast('Profile updated successfully!', 'success');
            } else {
              const errMsg = res.data?.error?.message || res.data?.detail || res.error || 'Failed to update profile.';
              window.app.showToast(errMsg, 'error');
            }
          } catch (err) {
            console.error('Profile update error:', err);
            window.app.showToast('Failed to update profile.', 'error');
          } finally {
            if (saveBtn) {
              saveBtn.disabled = false;
              saveBtn.textContent = 'Save Profile Changes';
            }
          }
        } else {
          if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save Profile Changes';
          }
          window.app.showToast('Please sign in to update your profile.', 'error');
        }

        const userNameEl = document.querySelector('.user-name');
        if (userNameEl) userNameEl.textContent = name;
      });
    }

    // Preferences toggles & defaults
    const autoCatToggle = document.getElementById('settings-toggle-autocat');
    const dupDetectToggle = document.getElementById('settings-toggle-dupdetect');
    const defaultCatSelect = document.getElementById('settings-default-category');

    if (autoCatToggle) {
      autoCatToggle.addEventListener('change', (e) => {
        this.state.updateSettings({ autoCategorize: e.target.checked });
        window.app.showToast(`Auto-categorization ${e.target.checked ? 'enabled' : 'disabled'}.`, 'info');
      });
    }

    if (dupDetectToggle) {
      dupDetectToggle.addEventListener('change', (e) => {
        this.state.updateSettings({ duplicateDetection: e.target.checked });
        window.app.showToast(`Duplicate detection ${e.target.checked ? 'enabled' : 'disabled'}.`, 'info');
      });
    }

    if (defaultCatSelect) {
      defaultCatSelect.addEventListener('change', (e) => {
        this.state.updateSettings({ defaultCategory: e.target.value });
        window.app.showToast(`Default category set to "${e.target.value}".`, 'info');
      });
    }

    // Security password change form
    const securityForm = document.getElementById('settings-security-form');
    if (securityForm) {
      securityForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const curr = document.getElementById('sec-curr-pwd').value;
        const newPwd = document.getElementById('sec-new-pwd').value;
        const confPwd = document.getElementById('sec-conf-pwd').value;

        if (!curr || !newPwd || !confPwd) {
          window.app.showToast('Please fill in all password fields.', 'error');
          return;
        }

        if (newPwd !== confPwd) {
          window.app.showToast('New passwords do not match.', 'error');
          return;
        }

        if (newPwd.length < 6) {
          window.app.showToast('New password must be at least 6 characters.', 'error');
          return;
        }

        const secBtn = securityForm.querySelector('button[type="submit"]');
        if (secBtn) {
          secBtn.disabled = true;
          secBtn.textContent = 'Updating...';
        }

        if (window.apiService && window.apiService.getToken()) {
          try {
            const res = await window.apiService.changePassword(curr, newPwd);
            if (res.success) {
              document.getElementById('sec-curr-pwd').value = '';
              document.getElementById('sec-new-pwd').value = '';
              document.getElementById('sec-conf-pwd').value = '';
              window.app.showToast('Password updated successfully!', 'success');
            } else {
              const msg = res.data?.error?.message || res.data?.detail || res.error || 'Failed to update password. Current password may be incorrect.';
              window.app.showToast(msg, 'error');
            }
          } catch (err) {
            window.app.showToast('Failed to change password.', 'error');
          } finally {
            if (secBtn) {
              secBtn.disabled = false;
              secBtn.textContent = 'Update Password';
            }
          }
        } else {
          document.getElementById('sec-curr-pwd').value = '';
          document.getElementById('sec-new-pwd').value = '';
          document.getElementById('sec-conf-pwd').value = '';
          if (secBtn) {
            secBtn.disabled = false;
            secBtn.textContent = 'Update Password';
          }
          window.app.showToast('Password updated.', 'success');
        }
      });
    }
  }

  switchTab(tabId) {
    this.activeTab = tabId;

    document.querySelectorAll('.settings-tab').forEach(tab => {
      if (tab.getAttribute('data-tab') === tabId) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    });

    document.querySelectorAll('.settings-section-panel').forEach(panel => {
      if (panel.id === `settings-panel-${tabId}`) {
        panel.style.display = 'block';
      } else {
        panel.style.display = 'none';
      }
    });
  }

  async populateSettings() {
    let currentUser = (window.apiService && window.apiService.getUser()) || (window.authManager && window.authManager.currentUser);

    // If authenticated, always fetch fresh profile from /api/auth/me to guarantee accurate user details
    if (window.apiService && window.apiService.getToken()) {
      try {
        const meRes = await window.apiService.getMe();
        if (meRes.success && meRes.data) {
          currentUser = meRes.data;
          window.apiService.setUser(currentUser);
          if (window.authManager) {
            window.authManager.currentUser = currentUser;
            window.authManager.renderHeaderUser();
          }
        }
      } catch (err) {
        console.warn('Could not refresh profile in Settings:', err);
      }
    }

    const s = this.state.getSettings();

    const nameInput = document.getElementById('settings-name');
    const emailInput = document.getElementById('settings-email');
    const roleSelect = document.getElementById('settings-role');
    const autoCatToggle = document.getElementById('settings-toggle-autocat');
    const dupDetectToggle = document.getElementById('settings-toggle-dupdetect');
    const defaultCatSelect = document.getElementById('settings-default-category');

    if (nameInput) {
      if (currentUser && currentUser.full_name) {
        nameInput.value = currentUser.full_name;
      } else if (currentUser && currentUser.username) {
        nameInput.value = currentUser.username;
      } else {
        nameInput.value = '';
      }
    }

    if (emailInput) {
      if (currentUser && currentUser.email) {
        emailInput.value = currentUser.email;
      } else {
        emailInput.value = '';
      }
    }

    if (roleSelect) roleSelect.value = (currentUser && currentUser.role) || s.role || 'User';
    if (autoCatToggle) autoCatToggle.checked = !!s.autoCategorize;
    if (dupDetectToggle) dupDetectToggle.checked = !!s.duplicateDetection;

    if (defaultCatSelect) {
      const categories = this.state.getCategories();
      defaultCatSelect.innerHTML = categories.map(c => 
        `<option value="${c.name}" ${c.name === s.defaultCategory ? 'selected' : ''}>${c.name}</option>`
      ).join('');
    }

    // Storage info tab values
    const totalBytes = this.state.getTotalStorageBytes();
    const quotaBytes = (s.storageQuotaMb || 500) * 1024 * 1024;
    const usagePercent = Math.min(100, Math.round((totalBytes / quotaBytes) * 100));

    const storageUsageText = document.getElementById('settings-storage-usage-text');
    const storageUsageBar = document.getElementById('settings-storage-bar');
    if (storageUsageText) storageUsageText.textContent = `${this.state.formatBytes(totalBytes)} of ${s.storageQuotaMb} MB (${usagePercent}%)`;
    if (storageUsageBar) storageUsageBar.style.width = `${Math.max(2, usagePercent)}%`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.settingsController = new SettingsController();
});
