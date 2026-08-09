/**
 * TechNews 博客详情页
 */

(function () {
  'use strict';

  var $ = function (s) { return document.querySelector(s); };
  var container = $('#blogDetailContent');

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }

  function formatTime(dateStr) {
    if (!dateStr) return '';
    var date = new Date(dateStr);
    return date.toLocaleString('zh-CN');
  }

  function getCategoryName(cat) {
    var map = { tech: '科技', ai: 'AI', opensource: '开源' };
    return map[cat] || cat;
  }

  function sanitizeHtml(html) {
    var temp = document.createElement('div');
    temp.innerHTML = html || '';
    var scripts = temp.querySelectorAll('script');
    for (var i = 0; i < scripts.length; i++) { scripts[i].remove(); }
    var all = temp.querySelectorAll('*');
    for (var j = 0; j < all.length; j++) {
      var attrs = all[j].attributes;
      for (var k = attrs.length - 1; k >= 0; k--) {
        if (attrs[k].name.indexOf('on') === 0) {
          all[j].removeAttribute(attrs[k].name);
        }
      }
    }
    return temp.innerHTML;
  }

  function renderPost(post) {
    return '<article class="blog-detail">' +
      '<div class="blog-detail-header">' +
        '<div class="blog-detail-tags">' +
          '<span class="category-tag ' + post.category + '">' + getCategoryName(post.category) + '</span>' +
        '</div>' +
        '<h1 class="blog-detail-title">' + escapeHtml(post.title) + '</h1>' +
        '<div class="blog-detail-meta">' +
          '<span class="meta-item">by ' + escapeHtml(post.author) + '</span>' +
          '<span class="meta-item">' + formatTime(post.created_at) + '</span>' +
          '<span class="meta-item">' + (post.views || 0) + ' views</span>' +
        '</div>' +
      '</div>' +
      '<div class="blog-detail-content">' + sanitizeHtml(post.content) + '</div>' +
      '<div class="blog-detail-footer">' +
        '<a href="/blog" class="btn-back-to-blog">返回博客列表</a>' +
      '</div>' +
    '</article>';
  }

  function renderError(msg) {
    container.innerHTML =
      '<div class="error-state">' +
        '<div class="error-text">' + escapeHtml(msg || '文章不存在') + '</div>' +
        '<a href="/blog" class="btn-retry">返回博客列表</a>' +
      '</div>';
  }

  async function loadPost() {
    // 从 URL 中提取文章 ID: /blog/123
    var pathParts = window.location.pathname.split('/');
    var postId = parseInt(pathParts[pathParts.length - 1], 10);

    if (!postId || isNaN(postId)) {
      renderError('无效的文章 ID');
      return;
    }

    try {
      var resp = await fetch('/api/blog/posts/' + postId);
      if (resp.status === 404) {
        renderError('文章不存在');
        return;
      }
      var res = await resp.json();
      if (!res.success) throw new Error('加载失败');

      container.innerHTML = renderPost(res.data);
      document.title = res.data.title + ' - TechNews 博客';
      // 动态更新 meta description 用于 SEO 和社交分享
      var metaDesc = document.querySelector('meta[name="description"]');
      if (metaDesc && res.data.excerpt) {
        metaDesc.setAttribute('content', res.data.excerpt.slice(0, 160));
      }
      var ogDesc = document.querySelector('meta[property="og:description"]');
      if (ogDesc && res.data.excerpt) {
        ogDesc.setAttribute('content', res.data.excerpt.slice(0, 160));
      }
      var ogTitle = document.querySelector('meta[property="og:title"]');
      if (ogTitle) {
        ogTitle.setAttribute('content', res.data.title + ' - TechNews 博客');
      }
    } catch (err) {
      renderError(err.message);
    }
  }

  loadPost();
})();
