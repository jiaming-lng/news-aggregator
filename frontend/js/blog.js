/**
 * TechNews 博客列表页
 */

(function () {
  'use strict';

  var state = {
    category: 'all',
    page: 1,
    limit: 10,
    totalPages: 1
  };

  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return document.querySelectorAll(s); };

  var dom = {
    blogList: $('#blogList'),
    pagination: $('#blogPagination'),
    catBtns: $$('.blog-cat-btn'),
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
    var date = new Date(dateStr);
    var now = new Date();
    var diffMs = now - date;
    var diffDay = Math.floor(diffMs / 86400000);
    if (diffDay < 1) return '今天';
    if (diffDay < 7) return diffDay + ' 天前';
    return dateStr.slice(0, 10);
  }

  function getCategoryName(cat) {
    var map = { tech: '科技', ai: 'AI', opensource: '开源' };
    return map[cat] || cat;
  }

  function renderPostCard(post) {
    return '<article class="blog-post-card">' +
      '<div class="blog-post-header">' +
        '<span class="category-tag ' + post.category + '">' + getCategoryName(post.category) + '</span>' +
        '<span class="blog-post-date">' + formatTime(post.created_at) + '</span>' +
      '</div>' +
      '<a href="/blog/' + post.id + '" class="blog-post-title-link">' +
        '<h2 class="blog-post-title">' + escapeHtml(post.title) + '</h2>' +
      '</a>' +
      '<p class="blog-post-excerpt">' + escapeHtml(post.excerpt || '暂无摘要') + '</p>' +
      '<div class="blog-post-meta">' +
        '<span class="meta-item">by ' + escapeHtml(post.author) + '</span>' +
        '<span class="meta-item">' + (post.views || 0) + ' views</span>' +
      '</div>' +
    '</article>';
  }

  function renderEmpty() {
    dom.blogList.innerHTML =
      '<div class="empty-state">' +
        '<div class="empty-text">暂无博客文章</div>' +
        '<div class="empty-hint">去管理后台写一篇吧</div>' +
      '</div>';
  }

  function renderPagination() {
    if (state.totalPages <= 1) {
      dom.pagination.innerHTML = '';
      return;
    }
    var html = '';
    var disabledPrev = state.page <= 1 ? ' disabled' : '';
    html += '<button class="page-btn" data-page="' + (state.page - 1) + '"' + disabledPrev + '>上一页</button>';
    for (var i = 1; i <= state.totalPages; i++) {
      var cls = i === state.page ? 'page-btn active' : 'page-btn';
      html += '<button class="' + cls + '" data-page="' + i + '">' + i + '</button>';
    }
    var disabledNext = state.page >= state.totalPages ? ' disabled' : '';
    html += '<button class="page-btn" data-page="' + (state.page + 1) + '"' + disabledNext + '>下一页</button>';
    dom.pagination.innerHTML = html;
  }

  async function loadPosts() {
    dom.blogList.innerHTML =
      '<div class="loading-indicator"><div class="spinner"></div><div>正在加载...</div></div>';

    try {
      var params = new URLSearchParams({
        status: 'published',
        category: state.category,
        page: String(state.page),
        limit: String(state.limit)
      });
      var resp = await fetch('/api/blog/posts?' + params);
      var res = await resp.json();

      if (!res.success) throw new Error('加载失败');

      var data = res.data;
      state.totalPages = data.total_pages;

      if (data.posts.length === 0) {
        renderEmpty();
      } else {
        dom.blogList.innerHTML = data.posts.map(renderPostCard).join('');
      }
      renderPagination();
    } catch (err) {
      dom.blogList.innerHTML =
        '<div class="error-state">' +
          '<div class="error-text">' + escapeHtml(err.message) + '</div>' +
          '<button class="btn-retry" data-action="retry">重新加载</button>' +
        '</div>';
    }
  }

  // 事件绑定
  dom.catBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      dom.catBtns.forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      state.category = btn.dataset.category;
      state.page = 1;
      loadPosts();
    });
  });

  dom.pagination.addEventListener('click', function (e) {
    var btn = e.target.closest('.page-btn');
    if (btn && !btn.disabled) {
      var page = parseInt(btn.dataset.page, 10);
      if (!isNaN(page) && page !== state.page) {
        state.page = page;
        loadPosts();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }
  });

  dom.blogList.addEventListener('click', function (e) {
    var retry = e.target.closest('[data-action="retry"]');
    if (retry) loadPosts();
  });

  // 启动
  loadPosts();
})();
