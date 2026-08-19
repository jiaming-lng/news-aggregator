/**
 * TechNews - 用户认证模块
 * 处理注册/登录/登出/收藏，全局复用
 * 依赖：localStorage 存储 token，各页面调用 auth API
 */

(function () {
  'use strict';

  var Auth = {
    token: null,
    user: null,

    // ---- 初始化 ----
    init: function () {
      this.token = localStorage.getItem('technews_token') || null;
      var userStr = localStorage.getItem('technews_user');
      this.user = userStr ? JSON.parse(userStr) : null;
      this._updateUI();
    },

    // ---- API 调用 ----
    _fetch: function (url, method, body) {
      var headers = { 'Content-Type': 'application/json' };
      if (this.token) {
        headers['Authorization'] = 'Bearer ' + this.token;
      }
      return fetch(url, {
        method: method || 'GET',
        headers: headers,
        body: body ? JSON.stringify(body) : undefined
      }).then(function (r) { return r.json(); });
    },

    register: function (email, username, password) {
      var self = this;
      return this._fetch('/api/auth/register', 'POST', {
        email: email, username: username, password: password
      }).then(function (res) {
        if (res.success) {
          self.token = res.data.token;
          self.user = res.data.user;
          localStorage.setItem('technews_token', self.token);
          localStorage.setItem('technews_user', JSON.stringify(self.user));
          self._updateUI();
        }
        return res;
      });
    },

    login: function (email, password) {
      var self = this;
      return this._fetch('/api/auth/login', 'POST', {
        email: email, password: password
      }).then(function (res) {
        if (res.success) {
          self.token = res.data.token;
          self.user = res.data.user;
          localStorage.setItem('technews_token', self.token);
          localStorage.setItem('technews_user', JSON.stringify(self.user));
          self._updateUI();
        }
        return res;
      });
    },

    logout: function () {
      var self = this;
      return this._fetch('/api/auth/logout', 'POST').then(function () {
        self.token = null;
        self.user = null;
        localStorage.removeItem('technews_token');
        localStorage.removeItem('technews_user');
        self._updateUI();
      });
    },

    // ---- 收藏 ----
    toggleFavorite: function (articleId, isFavorited) {
      if (!this.token) {
        return Promise.resolve({ success: false, error: '请先登录', needLogin: true });
      }
      var method = isFavorited ? 'DELETE' : 'POST';
      return this._fetch('/api/favorites/' + articleId, method);
    },

    // ---- UI 更新 ----
    _updateUI: function () {
      var userMenu = document.getElementById('userMenu');
      var loginBtn = document.getElementById('loginBtn');
      var userName = document.getElementById('userName');
      var adminLink = document.querySelector('.admin-link');

      if (this.user) {
        if (userMenu) userMenu.style.display = '';
        if (loginBtn) loginBtn.style.display = 'none';
        if (userName) userName.textContent = this.user.username;
        if (adminLink) adminLink.style.display = this.user.is_admin ? '' : 'none';
      } else {
        if (userMenu) userMenu.style.display = 'none';
        if (loginBtn) loginBtn.style.display = '';
        if (adminLink) adminLink.style.display = 'none';
      }

      // 通知各页面更新收藏按钮
      document.dispatchEvent(new CustomEvent('auth:stateChanged', {
        detail: { loggedIn: !!this.user, user: this.user }
      }));
    },

    isLoggedIn: function () {
      return !!this.token;
    }
  };

  // ---- 登录/注册弹窗 ----
  var Modal = {
    init: function () {
      this._createModal();
      this._bindEvents();
    },

    _createModal: function () {
      var modal = document.createElement('div');
      modal.className = 'auth-modal-overlay';
      modal.id = 'authModal';
      modal.innerHTML = '' +
        '<div class="auth-modal">' +
          '<button class="auth-modal-close" id="authModalClose" aria-label="关闭">' +
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
          '</button>' +
          '<div class="auth-tabs">' +
            '<button class="auth-tab active" data-mode="login">登录</button>' +
            '<button class="auth-tab" data-mode="register">注册</button>' +
          '</div>' +
          '<form class="auth-form" id="authForm">' +
            '<div class="auth-field" id="usernameField" style="display:none;">' +
              '<label for="authUsername">用户名</label>' +
              '<input type="text" id="authUsername" placeholder="2个字符以上" autocomplete="username">' +
            '</div>' +
            '<div class="auth-field">' +
              '<label for="authEmail">邮箱</label>' +
              '<input type="email" id="authEmail" placeholder="your@email.com" autocomplete="email">' +
            '</div>' +
            '<div class="auth-field">' +
              '<label for="authPassword">密码</label>' +
              '<input type="password" id="authPassword" placeholder="6个字符以上" autocomplete="current-password">' +
            '</div>' +
            '<button type="submit" class="auth-submit" id="authSubmit">登录</button>' +
            '<div class="auth-error" id="authError"></div>' +
          '</form>' +
        '</div>';
      document.body.appendChild(modal);
    },

    _bindEvents: function () {
      var self = this;
      var modal = document.getElementById('authModal');

      // 打开弹窗
      document.addEventListener('click', function (e) {
        if (e.target.closest('#loginBtn')) {
          self.open('login');
        }
      });

      // 关闭弹窗
      document.getElementById('authModalClose').addEventListener('click', function () {
        self.close();
      });
      modal.addEventListener('click', function (e) {
        if (e.target === modal) self.close();
      });

      // 切换登录/注册
      modal.querySelectorAll('.auth-tab').forEach(function (tab) {
        tab.addEventListener('click', function () {
          self._switchMode(tab.dataset.mode);
        });
      });

      // 表单提交
      document.getElementById('authForm').addEventListener('submit', function (e) {
        e.preventDefault();
        self._submit();
      });

      // 登出
      document.addEventListener('click', function (e) {
        if (e.target.closest('#logoutBtn')) {
          Auth.logout().then(function () {
            self._showToast('已退出登录', 'info');
          });
        }
      });
    },

    _mode: 'login',

    _switchMode: function (mode) {
      this._mode = mode;
      var tabs = document.querySelectorAll('.auth-tab');
      tabs.forEach(function (t) {
        t.classList.toggle('active', t.dataset.mode === mode);
      });
      document.getElementById('usernameField').style.display = mode === 'register' ? '' : 'none';
      document.getElementById('authSubmit').textContent = mode === 'register' ? '注册' : '登录';
      document.getElementById('authError').textContent = '';
      // 切换 autocomplete
      var pwd = document.getElementById('authPassword');
      pwd.autocomplete = mode === 'register' ? 'new-password' : 'current-password';
    },

    open: function (mode) {
      this._switchMode(mode || 'login');
      document.getElementById('authModal').classList.add('show');
      document.body.style.overflow = 'hidden';
    },

    close: function () {
      document.getElementById('authModal').classList.remove('show');
      document.body.style.overflow = '';
      document.getElementById('authError').textContent = '';
    },

    _submit: function () {
      var self = this;
      var email = document.getElementById('authEmail').value.trim();
      var password = document.getElementById('authPassword').value;
      var errorEl = document.getElementById('authError');
      var submitBtn = document.getElementById('authSubmit');

      errorEl.textContent = '';
      submitBtn.disabled = true;
      submitBtn.textContent = '处理中...';

      var promise;
      if (self._mode === 'register') {
        var username = document.getElementById('authUsername').value.trim();
        if (!username || username.length < 2) {
          errorEl.textContent = '用户名至少 2 个字符';
          submitBtn.disabled = false;
          submitBtn.textContent = '注册';
          return;
        }
        promise = Auth.register(email, username, password);
      } else {
        promise = Auth.login(email, password);
      }

      promise.then(function (res) {
        submitBtn.disabled = false;
        submitBtn.textContent = self._mode === 'register' ? '注册' : '登录';
        if (res.success) {
          self.close();
          self._showToast(self._mode === 'register' ? '注册成功，欢迎加入！' : '登录成功！', 'success');
          // 清空表单
          document.getElementById('authEmail').value = '';
          document.getElementById('authPassword').value = '';
          document.getElementById('authUsername').value = '';
        } else {
          errorEl.textContent = res.error || '操作失败，请重试';
        }
      }).catch(function () {
        submitBtn.disabled = false;
        submitBtn.textContent = self._mode === 'register' ? '注册' : '登录';
        errorEl.textContent = '网络错误，请重试';
      });
    },

    _showToast: function (msg, type) {
      var toast = document.getElementById('toast');
      if (!toast) return;
      toast.textContent = msg;
      toast.className = 'toast ' + (type || 'info') + ' show';
      clearTimeout(toast._timer);
      toast._timer = setTimeout(function () {
        toast.classList.remove('show');
      }, 2500);
    }
  };

  // 暴露到全局
  window.TechNewsAuth = Auth;
  window.TechNewsAuthModal = Modal;

  // DOM 就绪后初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      Auth.init();
      Modal.init();
    });
  } else {
    Auth.init();
    Modal.init();
  }
})();
