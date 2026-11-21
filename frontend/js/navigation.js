/**
 * Navigation Module
 * Controls page switching across application sections with authentication routing guards.
 */
class NavigationManager {
  constructor() {
    this.navLinks = document.querySelectorAll('.nav-link[data-page]');
    this.pageViews = document.querySelectorAll('.page-view');
    this.pageTitleElement = document.getElementById('topbar-page-title');
    this.currentPage = 'login';

    this.pageTitles = {
      dashboard: 'Dashboard Overview',
      documents: 'All Documents',
      upload: 'Upload Document',
      categories: 'Document Categories',
      activity: 'Activity History',
      settings: 'System Settings',
      auth: 'Account & Sign In',
      login: 'Sign In to SmartDoc',
      register: 'Create SmartDoc Account'
    };

    this.init();
  }

  isAuthenticated() {
    const hasToken = !!(window.apiService && window.apiService.getToken());
    const hasUser = !!((window.authManager && window.authManager.currentUser) || (window.apiService && window.apiService.getUser()));
    return hasToken && hasUser;
  }

  updateSidebarAuthVisibility() {
    const authLink = document.getElementById('sidebar-auth-link');
    if (authLink) {
      authLink.style.display = this.isAuthenticated() ? 'none' : 'flex';
    }
  }

  init() {
    this.bindEvents();

    const isLoggedIn = this.isAuthenticated();
    const initialHash = window.location.hash.replace('#', '');

    if (!isLoggedIn) {
      // First start or logged out: always open sign in or register page
      const target = (initialHash === 'register') ? 'register' : 'login';
      this.navigateTo(target);
    } else {
      // Logged in: navigate to requested valid page or default to dashboard
      if (initialHash && this.pageTitles[initialHash] && initialHash !== 'login' && initialHash !== 'register' && initialHash !== 'auth') {
        this.navigateTo(initialHash);
      } else {
        this.navigateTo('dashboard');
      }
    }

    this.updateSidebarAuthVisibility();

    window.addEventListener('hashchange', () => {
      const page = window.location.hash.replace('#', '');
      if (page && this.pageTitles[page] && page !== this.currentPage) {
        this.navigateTo(page);
      }
    });
  }

  bindEvents() {
    this.navLinks.forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const targetPage = link.getAttribute('data-page');
        this.navigateTo(targetPage);
      });
    });
  }

  navigateTo(pageId) {
    if (!this.pageTitles[pageId]) return;

    const isLoggedIn = this.isAuthenticated();
    const isAuthPage = (pageId === 'login' || pageId === 'register' || pageId === 'auth');

    // Route guard: if not logged in and attempting to visit a protected section, redirect to login
    if (!isLoggedIn && !isAuthPage) {
      if (window.app && typeof window.app.showToast === 'function') {
        window.app.showToast('Please sign in to access your dashboard and documents.', 'info');
      }
      pageId = 'login';
    }

    // Route guard: if logged in and attempting to visit login/register, redirect to dashboard
    if (isLoggedIn && isAuthPage) {
      pageId = 'dashboard';
    }

    this.currentPage = pageId;
    const viewId = (pageId === 'login' || pageId === 'register' || pageId === 'auth') ? 'auth' : pageId;

    // Update active nav link
    this.navLinks.forEach(link => {
      if (link.getAttribute('data-page') === viewId) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    // Update page view visibility
    this.pageViews.forEach(view => {
      if (view.id === `page-${viewId}`) {
        view.classList.add('active');
      } else {
        view.classList.remove('active');
      }
    });

    // Update sidebar auth link visibility
    this.updateSidebarAuthVisibility();

    // If navigating to auth/login/register, ensure auth page view is rendered with the right tab
    if (viewId === 'auth' && window.authManager) {
      const tab = pageId === 'register' ? 'register' : 'login';
      window.authManager.activeTab = tab;
      window.authManager.renderAuthPage();
    }

    // If navigating to settings, ensure settings page is populated with latest user data
    if (viewId === 'settings' && window.settingsController) {
      window.settingsController.populateSettings();
    }

    // If navigating to upload, ensure upload category options are fresh
    if (viewId === 'upload' && window.uploadController) {
      window.uploadController.populateCategoryOptions();
    }

    // If navigating to dashboard, ensure dashboard stats are re-rendered for this user
    if (viewId === 'dashboard' && window.dashboardController) {
      window.dashboardController.render();
    }

    // Update Topbar page title
    if (this.pageTitleElement) {
      this.pageTitleElement.textContent = this.pageTitles[pageId];
    }

    // Update URL hash without scroll
    if (window.location.hash !== `#${pageId}`) {
      history.replaceState(null, null, `#${pageId}`);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.navigationManager = new NavigationManager();
});
