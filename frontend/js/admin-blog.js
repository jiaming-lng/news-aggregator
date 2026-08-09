/**
 * TechNews 博客管理 - 文章 CRUD + 编辑器
 */

(function () {
  'use strict';

  var $ = function (s) { return document.querySelector(s); };

  // ---- 带认证的请求封装 ----
  function authHeaders(extra) {
    var headers = Object.assign({}, extra || {});
    var token = localStorage.getItem('technews_token');
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return headers;
  }

  var state = {
    editingId: null,  // null = 新建, number = 编辑中
    posts: []
  };

  var dom = {
    postList: $('#postList'),
    editorPanel: $('#editorPanel'),
    emptyState: $('#emptyState'),
    btnNewPost: $('#btnNewPost'),
    btnSaveDraft: $('#btnSaveDraft'),
    btnPublish: $('#btnPublish'),
    btnDelete: $('#btnDelete'),
    btnCancel: $('#btnCancel'),
    editorTitle: $('#editorTitle'),
    postTitle: $('#postTitle'),
    postCategory: $('#postCategory'),
    postAuthor: $('#postAuthor'),
    postExcerpt: $('#postExcerpt'),
    postContent: $('#postContent'),
    postPreview: $('#postPreview'),
    toast: $('#toast')
  };

  function showToast(msg, type) {
    type = type || 'info';
    dom.toast.textContent = msg;
    dom.toast.className = 'toast ' + type + ' show';
    clearTimeout(dom.toast._timer);
    dom.toast._timer = setTimeout(function () {
      dom.toast.classList.remove('show');
    }, 2500);
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }

  function formatTime(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleString('zh-CN');
  }

  function getCategoryName(cat) {
    var map = { tech: '科技', ai: 'AI', opensource: '开源' };
    return map[cat] || cat;
  }

  // ---- 文章列表 ----
  async function loadPostList() {
    try {
      var resp = await fetch('/api/blog/posts?status=all&page=1&limit=100');
      var res = await resp.json();
      if (!res.success) throw new Error('加载失败');

      state.posts = res.data.posts;
      renderPostList();
    } catch (err) {
      dom.postList.innerHTML = '<p style="color: #dc2626; padding: 20px;">加载失败: ' + escapeHtml(err.message) + '</p>';
    }
  }

  function renderPostList() {
    if (state.posts.length === 0) {
      dom.postList.innerHTML = '<div class="empty-state" style="padding: 40px 20px;">' +
        '<div class="empty-text">还没有文章</div>' +
        '<div class="empty-hint">点击「新建文章」开始写第一篇博客</div>' +
        '</div>';
      return;
    }

    dom.postList.innerHTML = state.posts.map(function (post) {
      var statusClass = post.status === 'published' ? 'success' : 'running';
      var statusText = post.status === 'published' ? '已发布' : '草稿';
      return '<div class="post-list-item' + (state.editingId === post.id ? ' active' : '') + '" data-id="' + post.id + '">' +
        '<div class="post-list-title">' + escapeHtml(post.title) + '</div>' +
        '<div class="post-list-meta">' +
          '<span class="status-badge ' + statusClass + '">' + statusText + '</span>' +
          '<span class="post-list-date">' + formatTime(post.created_at) + '</span>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  // 点击列表项编辑
  dom.postList.addEventListener('click', function (e) {
    var item = e.target.closest('.post-list-item');
    if (item) {
      var id = parseInt(item.dataset.id, 10);
      if (!isNaN(id)) editPost(id);
    }
  });

  // ---- 编辑器 ----
  function showEditor() {
    dom.editorPanel.style.display = '';
    dom.emptyState.style.display = 'none';
    updatePreview();
  }

  function hideEditor() {
    dom.editorPanel.style.display = 'none';
    dom.emptyState.style.display = '';
    state.editingId = null;
    clearForm();
    renderPostList();
  }

  function clearForm() {
    dom.postTitle.value = '';
    dom.postCategory.value = 'tech';
    dom.postAuthor.value = 'TechNews';
    dom.postExcerpt.value = '';
    dom.postContent.value = '';
    dom.postPreview.innerHTML = '';
    dom.btnDelete.style.display = 'none';
    dom.editorTitle.textContent = '新建文章';
  }

  function editPost(id) {
    var post = state.posts.find(function (p) { return p.id === id; });
    if (!post) return;

    state.editingId = id;
    dom.postTitle.value = post.title || '';
    dom.postCategory.value = post.category || 'tech';
    dom.postAuthor.value = post.author || 'TechNews';
    dom.postExcerpt.value = post.excerpt || '';
    dom.postContent.value = post.content || '';
    dom.editorTitle.textContent = '编辑文章';
    dom.btnDelete.style.display = '';
    showEditor();
    renderPostList();
  }

  // 新建文章
  dom.btnNewPost.addEventListener('click', function () {
    state.editingId = null;
    clearForm();
    showEditor();
  });

  // 取消
  dom.btnCancel.addEventListener('click', hideEditor);

  // 实时预览
  dom.postContent.addEventListener('input', updatePreview);

  function updatePreview() {
    var content = dom.postContent.value;
    dom.postPreview.innerHTML = content || '<p style="color: var(--text-muted);">在上方输入内容后这里会显示预览...</p>';
  }

  // 编辑器工具栏
  document.querySelector('.editor-toolbar').addEventListener('click', function (e) {
    var btn = e.target.closest('button[data-action]');
    if (!btn) return;
    var action = btn.dataset.action;
    var textarea = dom.postContent;
    var start = textarea.selectionStart;
    var end = textarea.selectionEnd;
    var selected = textarea.value.substring(start, end);
    var before = textarea.value.substring(0, start);
    var after = textarea.value.substring(end);
    var insertion = '';

    switch (action) {
      case 'bold': insertion = '<strong>' + (selected || '加粗文本') + '</strong>'; break;
      case 'italic': insertion = '<em>' + (selected || '斜体文本') + '</em>'; break;
      case 'h2': insertion = '\n<h2>' + (selected || '标题') + '</h2>\n'; break;
      case 'h3': insertion = '\n<h3>' + (selected || '小标题') + '</h3>\n'; break;
      case 'link': insertion = '<a href="https://">' + (selected || '链接文本') + '</a>'; break;
      case 'code': insertion = '\n<pre><code>' + (selected || '代码') + '</code></pre>\n'; break;
      case 'ul': insertion = '\n<ul>\n  <li>' + (selected || '列表项') + '</li>\n</ul>\n'; break;
      case 'ol': insertion = '\n<ol>\n  <li>' + (selected || '列表项') + '</li>\n</ol>\n'; break;
      case 'p': insertion = '<p>' + (selected || '段落文本') + '</p>\n'; break;
    }

    textarea.value = before + insertion + after;
    textarea.focus();
    textarea.selectionStart = start + insertion.length;
    textarea.selectionEnd = start + insertion.length;
    updatePreview();
  });

  // 保存
  function collectData(status) {
    return {
      title: dom.postTitle.value.trim(),
      content: dom.postContent.value,
      excerpt: dom.postExcerpt.value.trim(),
      author: dom.postAuthor.value.trim() || 'TechNews',
      category: dom.postCategory.value,
      status: status
    };
  }

  function validate(data) {
    if (!data.title) {
      showToast('请输入标题', 'error');
      dom.postTitle.focus();
      return false;
    }
    if (!data.content) {
      showToast('请输入内容', 'error');
      dom.postContent.focus();
      return false;
    }
    return true;
  }

  async function savePost(status) {
    var data = collectData(status);
    if (!validate(data)) return;

    try {
      var resp, res;
      if (state.editingId) {
        // 更新
        resp = await fetch('/api/blog/posts/' + state.editingId, {
          method: 'PUT',
          headers: authHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify(data)
        });
        res = await resp.json();
        if (!res.success) throw new Error(res.error || '保存失败');
        showToast('文章已' + (status === 'published' ? '发布' : '存为草稿'), 'success');
      } else {
        // 新建
        resp = await fetch('/api/blog/posts', {
          method: 'POST',
          headers: authHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify(data)
        });
        res = await resp.json();
        if (!res.success) throw new Error(res.error || '创建失败');
        state.editingId = res.data.id;
        dom.editorTitle.textContent = '编辑文章';
        dom.btnDelete.style.display = '';
        showToast('文章已' + (status === 'published' ? '发布' : '存为草稿'), 'success');
      }

      await loadPostList();
    } catch (err) {
      showToast('保存失败: ' + err.message, 'error');
    }
  }

  dom.btnSaveDraft.addEventListener('click', function () { savePost('draft'); });
  dom.btnPublish.addEventListener('click', function () { savePost('published'); });

  // 删除
  dom.btnDelete.addEventListener('click', async function () {
    if (!state.editingId) return;
    if (!confirm('确定删除这篇文章吗？此操作不可撤销。')) return;

    try {
      var resp = await fetch('/api/blog/posts/' + state.editingId, { method: 'DELETE', headers: authHeaders() });
      var res = await resp.json();
      if (!res.success) throw new Error(res.error || '删除失败');

      showToast('文章已删除', 'success');
      hideEditor();
      await loadPostList();
    } catch (err) {
      showToast('删除失败: ' + err.message, 'error');
    }
  });

  // 启动
  function init() {
    // 登录检查：未登录引导登录，不加载数据
    if (window.TechNewsAuth && !window.TechNewsAuth.isLoggedIn()) {
      var list = dom.postList;
      if (list) {
        list.innerHTML = '<p style="color: var(--text-muted); padding: 40px; text-align: center;">博客管理需要登录后才能访问 🔒<br><br><button onclick="window.TechNewsAuthModal.open(\'login\')" style="padding: 10px 28px; border-radius: 100px; border: none; background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; cursor: pointer;">去登录</button></p>';
      }
      return;
    }
    loadPostList();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // 登录成功后自动刷新后台数据
  document.addEventListener('auth:stateChanged', function () {
    if (window.TechNewsAuth && window.TechNewsAuth.isLoggedIn()) {
      location.reload();
    }
  });
})();
