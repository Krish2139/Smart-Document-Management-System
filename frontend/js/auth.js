/**
 * Authentication & User Session Controller
 * Manages Sign In, Registration, JWT Sessions, and Header Profile UI.
 */

class AuthManager {
  constructor() {
    this.api = window.apiService;
    this.currentUser = this.api.getUser();
    this.activeTab = 'login'; // 'login' or 'register'
    this.init();
  }

  async init() {
    this.renderHeaderUser();
    this.renderAuthPage();
    this.bindEvents();

    // Verify session validity if token exists
    if (this.api.getToken()) {
      try {
        const res = await this.api.getMe();
        if (res.success && res.data) {
          this.currentUser = res.data;
          this.api.setUser(res.data);
          this.renderHeaderUser();
          if (window.settingsController) {
            window.settingsController.populateSettings();
          }
          if (window.navigationManager) {
            window.navigationManager.updateSidebarAuthVisibility();
          }
        } else if (res.status === 401) {
          // Token expired or invalid
          this.api.clearAuth();
          this.currentUser = null;
          this.renderHeaderUser();
          if (window.settingsController) {
            window.settingsController.populateSettings();
          }
          if (window.navigationManager) {
            window.navigationManager.updateSidebarAuthVisibility();
            window.navigationManager.navigateTo('login');
          }
        }
      } catch (e) {
        console.warn('Session verification skipped:', e);
      }
    } else {
      this.currentUser = null;
      this.renderHeaderUser();
      if (window.navigationManager) {
        window.navigationManager.updateSidebarAuthVisibility();
        window.navigationManager.navigateTo('login');
      }
    }
  }

  bindEvents() {
    // Topbar Sign In & Sign Up buttons (delegated)
    document.addEventListener('click', (e) => {
      // Open login modal
      if (e.target.closest('#btn-open-login') || e.target.closest('.btn-auth-signin')) {
        this.openAuthModal('login');
      }
      // Open register modal
      if (e.target.closest('#btn-open-register') || e.target.closest('.btn-auth-signup')) {
        this.openAuthModal('register');
      }
      // Close dropdown when clicking outside
      const dropdown = document.getElementById('user-dropdown-menu');
      const badge = document.getElementById('user-profile-badge');
      if (dropdown && dropdown.classList.contains('show') && !e.target.closest('#user-profile-badge') && !e.target.closest('#user-dropdown-menu')) {
        dropdown.classList.remove('show');
      }
    });

    // Close auth modal bindings
    const authBackdrop = document.getElementById('auth-modal-backdrop');
    const authCloseBtn = document.getElementById('auth-modal-close');
    if (authCloseBtn) {
      authCloseBtn.addEventListener('click', () => this.closeAuthModal());
    }
    if (authBackdrop) {
      authBackdrop.addEventListener('click', (e) => {
        if (e.target === authBackdrop) this.closeAuthModal();
      });
    }
  }

  /**
   * Render Topbar User Menu based on current auth state
   */
  renderHeaderUser() {
    const container = document.getElementById('header-user-container');
    if (!container) return;

    if (this.currentUser) {
      // Logged in UI: show user profile badge AND a direct "Sign Out" / "Switch User" button
      const initials = this.getInitials(this.currentUser.full_name || this.currentUser.username);

      container.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <div class="user-profile-badge-wrapper" style="position: relative;">
            <div class="user-profile-badge" id="user-profile-badge" title="Signed in as ${this.escapeHtml(this.currentUser.full_name || this.currentUser.username)} (click for menu)">
              <div class="avatar-circle">${initials}</div>
              <div style="display: flex; flex-direction: column; align-items: flex-start; line-height: 1.2;">
                <span class="user-name" style="font-weight: 600; font-size: 0.85rem;">${this.escapeHtml(this.currentUser.full_name || this.currentUser.username)}</span>
              </div>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-left: 2px; opacity: 0.7;">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </div>

            <!-- Dropdown Menu -->
            <div class="user-dropdown-menu" id="user-dropdown-menu">
              <div class="dropdown-header">
                <div class="dropdown-avatar">${initials}</div>
                <div class="dropdown-user-info">
                  <strong>${this.escapeHtml(this.currentUser.full_name || this.currentUser.username)}</strong>
                  <span style="color: var(--text-muted); font-size: 0.8rem;">@${this.escapeHtml(this.currentUser.username)}</span>
                  <span style="color: var(--text-secondary); font-size: 0.75rem;">${this.escapeHtml(this.currentUser.email)}</span>
                </div>
              </div>
              <div class="dropdown-divider"></div>
              <a href="#settings" class="dropdown-item" onclick="window.authManager.closeDropdown(); if(window.navigationManager) window.navigationManager.navigateTo('settings');">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="3"></circle>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                </svg>
                Profile & Settings
              </a>
              <button class="dropdown-item" onclick="window.authManager.openAuthModal('login');">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="8.5" cy="7.5" r="4"></circle>
                  <line x1="20" y1="8" x2="20" y2="14"></line>
                </svg>
                Switch Account / Sign In As Another User
              </button>
              <div class="dropdown-divider"></div>
              <button class="dropdown-item text-danger" onclick="window.authManager.handleLogout()">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                  <polyline points="16 17 21 12 16 7"></polyline>
                  <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                Sign Out
              </button>
            </div>
          </div>

          <button class="btn btn-secondary btn-sm" id="btn-quick-signout" onclick="window.authManager.handleLogout()" title="Sign out / Switch account">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
            Sign Out
          </button>
        </div>
      `;

      // Toggle dropdown on badge click
      const badgeEl = document.getElementById('user-profile-badge');
      const menuEl = document.getElementById('user-dropdown-menu');
      if (badgeEl && menuEl) {
        badgeEl.addEventListener('click', (e) => {
          e.stopPropagation();
          menuEl.classList.toggle('show');
        });
      }
    } else {
      // Logged out UI: show prominent Sign In / Log In and Sign Up buttons
      container.innerHTML = `
        <div class="auth-buttons-group" style="display: flex; gap: 0.5rem; align-items: center;">
          <button class="btn btn-primary btn-sm btn-auth-signin" id="btn-open-login" title="Sign In or Log In to your account" style="box-shadow: 0 2px 8px rgba(124, 58, 237, 0.25);">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
              <polyline points="10 17 15 12 10 7"></polyline>
              <line x1="15" y1="12" x2="3" y2="12"></line>
            </svg>
            <span>Sign In / Log In</span>
          </button>
          <button class="btn btn-secondary btn-sm btn-auth-signup" id="btn-open-register" title="Create a new account">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="8.5" cy="7.5" r="4"></circle>
              <line x1="20" y1="8" x2="20" y2="14"></line>
              <line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
            <span>Sign Up</span>
          </button>
        </div>
      `;
    }
  }

  closeDropdown() {
    const dropdown = document.getElementById('user-dropdown-menu');
    if (dropdown) dropdown.classList.remove('show');
  }

  /**
   * Open the Sign In / Register Modal Dialog
   */
  openAuthModal(initialTab = 'login') {
    this.closeDropdown();
    this.activeTab = initialTab;

    // If currently on auth page view, simply toggle tab
    if (window.navigationManager && (window.navigationManager.currentPage === 'auth' || window.navigationManager.currentPage === 'login' || window.navigationManager.currentPage === 'register')) {
      this.switchTab(initialTab);
      return;
    }

    // If not authenticated, navigate directly to auth page
    if (!this.currentUser && window.navigationManager) {
      window.navigationManager.navigateTo(initialTab);
      return;
    }

    const backdrop = document.getElementById('auth-modal-backdrop');
    if (!backdrop) return;

    this.renderModalContent();
    backdrop.style.display = 'flex';
    // Slight tick to trigger CSS opacity transition
    setTimeout(() => {
      backdrop.classList.add('open');
    }, 10);
  }

  closeAuthModal() {
    const backdrop = document.getElementById('auth-modal-backdrop');
    if (backdrop) {
      backdrop.classList.remove('open');
      setTimeout(() => {
        backdrop.style.display = 'none';
      }, 200);
    }
  }

  switchTab(tab) {
    this.activeTab = tab;
    this.renderModalContent();
    this.renderAuthPage();
    if (window.navigationManager) {
      window.navigationManager.currentPage = tab;
      if (window.navigationManager.pageTitleElement) {
        window.navigationManager.pageTitleElement.textContent = window.navigationManager.pageTitles[tab] || 'Account & Sign In';
      }
      if (window.location.hash !== `#${tab}`) {
        history.replaceState(null, null, `#${tab}`);
      }
    }
  }

  togglePassword(target, optBtnId) {
    let input = null;
    let btn = null;

    if (typeof target === 'string') {
      input = document.getElementById(target);
      btn = optBtnId ? document.getElementById(optBtnId) : null;
    } else if (target && (target.nodeType || target.tagName)) {
      btn = target;
      const wrapper = btn.closest('.password-input-wrapper') || btn.parentElement;
      input = wrapper ? wrapper.querySelector('input') : null;
    }

    if (!input) return;

    if (input.type === 'password') {
      input.type = 'text';
      if (btn) {
        btn.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
            <line x1="1" y1="1" x2="23" y2="23"></line>
          </svg>`;
        btn.setAttribute('title', 'Hide password');
      }
    } else {
      input.type = 'password';
      if (btn) {
        btn.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>`;
        btn.setAttribute('title', 'Show password');
      }
    }
  }

  /**
   * Render internal content of Auth Modal
   */
  renderModalContent() {
    const bodyEl = document.getElementById('auth-modal-body');
    if (!bodyEl) return;
    bodyEl.innerHTML = this.getAuthFormHtml();
  }

  /**
   * Render dedicated full-page auth card if page exists
   */
  renderAuthPage() {
    const pageCard = document.getElementById('auth-page-card');
    if (!pageCard) return;
    pageCard.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem;">
        <div class="brand-icon-wrapper" style="width: 36px; height: 36px; border-radius: 10px;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
        </div>
        <div>
          <h2 class="auth-card-title" style="margin-bottom: 0;">${this.activeTab === 'login' ? 'Sign In to SmartDoc' : 'Create SmartDoc Account'}</h2>
        </div>
      </div>
      ${this.getAuthFormHtml()}
    `;
  }

  /**
   * Generate Auth Form HTML (Shared between Modal & Page View)
   */
  getAuthFormHtml() {
    if (this.activeTab === 'login') {
      return `
        <!-- Modern Segmented Tabs -->
        <div class="auth-segmented-control">
          <button type="button" class="auth-segmented-btn active" onclick="window.authManager.switchTab('login')">Sign In</button>
          <button type="button" class="auth-segmented-btn" onclick="window.authManager.switchTab('register')">Create Account</button>
        </div>

        <form id="form-auth-login" onsubmit="window.authManager.handleLoginSubmit(event)">
          <div id="auth-error-alert" class="alert alert-danger" style="display: none; margin-bottom: 1rem; font-size: 0.88rem; border-radius: 10px;"></div>

          <div class="form-group">
            <label class="form-label" for="login-identifier">Username or Email</label>
            <input type="text" id="login-identifier" class="form-control" placeholder="e.g. user or user@example.com" required autocomplete="username">
          </div>

          <div class="form-group">
            <label class="form-label" for="login-password">Password</label>
            <div class="password-input-wrapper">
              <input type="password" id="login-password" class="form-control" placeholder="Enter your password" required autocomplete="current-password">
              <button type="button" class="btn-toggle-pwd" onclick="window.authManager.togglePassword(this)" title="Show / Hide Password">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              </button>
            </div>
          </div>

          <button type="submit" class="btn-auth-primary" id="btn-login-submit" style="width: 100%; justify-content: center; padding: 0.85rem; font-size: 0.95rem; margin-top: 0.25rem;">
            Sign In
          </button>
        </form>

        <div style="text-align: center; margin-top: 1.25rem; font-size: 0.9rem; color: #64748b;">
          Don't have an account? 
          <a href="javascript:void(0)" onclick="window.authManager.switchTab('register')" style="color: #8b5cf6; font-weight: 600; text-decoration: none;">Create Account</a>
        </div>
      `;
    } else {
      return `
        <!-- Modern Segmented Tabs -->
        <div class="auth-segmented-control">
          <button type="button" class="auth-segmented-btn" onclick="window.authManager.switchTab('login')">Sign In</button>
          <button type="button" class="auth-segmented-btn active" onclick="window.authManager.switchTab('register')">Create Account</button>
        </div>

        <form id="form-auth-register" onsubmit="window.authManager.handleRegisterSubmit(event)">
          <div id="auth-error-alert" class="alert alert-danger" style="display: none; margin-bottom: 1rem; font-size: 0.88rem; border-radius: 10px;"></div>

          <div class="form-group">
            <label class="form-label" for="reg-fullname">Full Name</label>
            <input type="text" id="reg-fullname" class="form-control" placeholder="e.g. Sarah Connor" required>
          </div>

          <div class="form-group">
            <label class="form-label" for="reg-email">Email Address</label>
            <input type="email" id="reg-email" class="form-control" placeholder="e.g. sarah@example.com" required>
          </div>

          <div class="form-group">
            <label class="form-label" for="reg-username">Username</label>
            <input type="text" id="reg-username" class="form-control" placeholder="e.g. sconnor" required pattern="^[a-zA-Z0-9_-]{3,50}$" title="At least 3 alphanumeric characters">
          </div>

          <div class="form-group">
            <label class="form-label" for="reg-password">Password</label>
            <div class="password-input-wrapper">
              <input type="password" id="reg-password" class="form-control" placeholder="At least 6 characters" required minlength="6">
              <button type="button" class="btn-toggle-pwd" onclick="window.authManager.togglePassword(this)" title="Show / Hide Password">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              </button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="reg-confirm-password">Confirm Password</label>
            <div class="password-input-wrapper">
              <input type="password" id="reg-confirm-password" class="form-control" placeholder="Repeat your password" required minlength="6">
              <button type="button" class="btn-toggle-pwd" onclick="window.authManager.togglePassword(this)" title="Show / Hide Password">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              </button>
            </div>
          </div>

          <button type="submit" class="btn-auth-primary" id="btn-register-submit" style="width: 100%; justify-content: center; padding: 0.85rem; font-size: 0.95rem; margin-top: 0.5rem;">
            Create Account
          </button>
        </form>

        <div style="text-align: center; margin-top: 1.25rem; font-size: 0.9rem; color: #64748b;">
          Already have an account? 
          <a href="javascript:void(0)" onclick="window.authManager.switchTab('login')" style="color: #8b5cf6; font-weight: 600; text-decoration: none;">Sign in here</a>
        </div>
      `;
    }
  }

  showAuthError(message) {
    const alertEls = document.querySelectorAll('#auth-error-alert');
    alertEls.forEach(el => {
      el.textContent = message;
      el.style.display = 'block';
    });
    if (window.app && typeof window.app.showToast === 'function') {
      window.app.showToast(message, 'error', 4500);
    }
  }

  async handleLoginSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const identInput = form.querySelector('#login-identifier') || document.getElementById('login-identifier');
    const passInput = form.querySelector('#login-password') || document.getElementById('login-password');
    const btn = form.querySelector('#btn-login-submit') || document.getElementById('btn-login-submit');

    const identifier = identInput.value.trim();
    const password = passInput.value;

    if (!identifier || !password) {
      this.showAuthError('Please fill in both fields.');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Signing In...';

    const res = await this.api.login(identifier, password);
    btn.disabled = false;
    btn.textContent = 'Sign In to SmartDoc';

    if (res.success && res.data) {
      this.currentUser = res.data.user;
      this.renderHeaderUser();
      this.closeAuthModal();
      if (window.settingsController) {
        window.settingsController.populateSettings();
      }
      if (window.app) {
        window.app.showToast(`Welcome back, ${this.currentUser.full_name || this.currentUser.username}!`, 'success');
      }
      // Clear previous cached user documents & stats before fresh sync
      if (window.stateManager) {
        window.stateManager.documents = [];
        window.stateManager.activities = [];
        window.stateManager.dashboardStats = null;
        window.stateManager.syncWithBackend();
      }
      if (window.navigationManager) {
        window.navigationManager.updateSidebarAuthVisibility();
        window.navigationManager.navigateTo('dashboard');
      }
    } else {
      const msg = res.data?.error?.message || res.data?.detail || res.error || 'Login failed. Please check your credentials.';
      this.showAuthError(msg);
    }
  }

  async handleRegisterSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const fullnameInput = form.querySelector('#reg-fullname') || document.getElementById('reg-fullname');
    const usernameInput = form.querySelector('#reg-username') || document.getElementById('reg-username');
    const emailInput = form.querySelector('#reg-email') || document.getElementById('reg-email');
    const passInput = form.querySelector('#reg-password') || document.getElementById('reg-password');
    const confirmInput = form.querySelector('#reg-confirm-password') || document.getElementById('reg-confirm-password');
    const btn = form.querySelector('#btn-register-submit') || document.getElementById('btn-register-submit');

    const fullName = fullnameInput.value.trim();
    const username = usernameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passInput.value;
    const confirm = confirmInput.value;

    if (password !== confirm) {
      this.showAuthError('Passwords do not match.');
      return;
    }

    if (password.length < 6) {
      this.showAuthError('Password must be at least 6 characters long.');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Creating Account...';

    const res = await this.api.register({
      full_name: fullName,
      username: username,
      email: email,
      password: password,
      role: 'user'
    });

    btn.disabled = false;
    btn.textContent = 'Create Account';

    if (res.success && res.data) {
      this.currentUser = res.data.user;
      this.renderHeaderUser();
      this.closeAuthModal();
      if (window.settingsController) {
        window.settingsController.populateSettings();
      }
      if (window.app) {
        window.app.showToast(`Welcome to SmartDoc, ${this.currentUser.full_name}! Account created.`, 'success');
      }
      if (window.stateManager) {
        window.stateManager.documents = [];
        window.stateManager.activities = [];
        window.stateManager.dashboardStats = null;
        window.stateManager.syncWithBackend();
      }
      if (window.navigationManager) {
        window.navigationManager.updateSidebarAuthVisibility();
        window.navigationManager.navigateTo('dashboard');
      }
    } else {
      const msg = res.data?.error?.message || res.data?.detail || res.error || 'Registration failed. Username or email may already be registered.';
      this.showAuthError(msg);
    }
  }

  async handleLogout() {
    this.closeDropdown();
    await this.api.logout();
    this.currentUser = null;
    this.renderHeaderUser();
    if (window.settingsController) {
      window.settingsController.populateSettings();
    }
    if (window.app) {
      window.app.showToast('You have been signed out successfully.', 'info');
    }
    if (window.stateManager) {
      window.stateManager.documents = [];
      window.stateManager.activities = [];
      window.stateManager.dashboardStats = null;
      window.stateManager.syncWithBackend();
    }
    if (window.navigationManager) {
      window.navigationManager.updateSidebarAuthVisibility();
      window.navigationManager.navigateTo('login');
    }
  }

  getInitials(name) {
    if (!name) return 'U';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

// Immediate or DOM ready initialization
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.authManager = new AuthManager();
  });
} else {
  window.authManager = new AuthManager();
}

// Global window helpers for direct HTML onclick handlers
window.openAuthModal = function(tab = 'login') {
  if (!window.authManager) {
    window.authManager = new AuthManager();
  }
  window.authManager.openAuthModal(tab);
};

window.closeAuthModal = function() {
  if (window.authManager) {
    window.authManager.closeAuthModal();
  } else {
    const backdrop = document.getElementById('auth-modal-backdrop');
    if (backdrop) {
      backdrop.classList.remove('open');
      backdrop.style.display = 'none';
    }
  }
};
