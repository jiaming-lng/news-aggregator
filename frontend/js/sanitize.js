/**
 * TechNews 公共模块 - HTML 消毒
 * 白名单标签 + 白名单属性 + 安全 URL，用于博客内容渲染和编辑器预览
 * 与后端 app.py 的 _sanitize_blog_html 规则保持一致
 */

(function () {
  'use strict';

  var ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'b', 'i', 'u', 's', 'h2', 'h3', 'h4',
    'ul', 'ol', 'li', 'a', 'pre', 'code', 'blockquote', 'hr',
    'span', 'div', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
  ];

  // 通用安全属性（a/img 的 href/src 单独校验）
  var ALLOWED_ATTRS = {
    a: ['href', 'title'],
    img: ['src', 'alt', 'title'],
    th: ['colspan', 'rowspan'],
    td: ['colspan', 'rowspan']
  };

  function isSafeUrl(value, allowedSchemes) {
    var v = String(value || '').trim();
    if (!v) return false;
    var m = v.match(/^([a-zA-Z][a-zA-Z0-9+.-]*):/);
    if (m) {
      return allowedSchemes.indexOf(m[1].toLowerCase()) !== -1;
    }
    return true; // 相对链接（如 /blog/1）安全
  }

  function isAllowedAttr(tag, name, value) {
    if (name.indexOf('on') === 0) return false;      // 事件属性
    if (name === 'style') return false;              // 防止 url(javascript:)
    var allowed = ALLOWED_ATTRS[tag];
    if (!allowed || allowed.indexOf(name) === -1) return false;

    if (name === 'href') {
      return isSafeUrl(value, ['http:', 'https:', 'mailto:']);
    }
    if (name === 'src') {
      return isSafeUrl(value, ['http:', 'https:']);
    }
    return true;
  }

  function sanitizeNode(node) {
    var children = Array.prototype.slice.call(node.children);
    for (var i = 0; i < children.length; i++) {
      var el = children[i];
      var tag = el.tagName.toLowerCase();

      if (ALLOWED_TAGS.indexOf(tag) === -1) {
        // script/iframe 等不允许的标签整体移除（包括其内容）
        el.parentNode.removeChild(el);
        continue;
      }

      var attrs = el.attributes;
      for (var j = attrs.length - 1; j >= 0; j--) {
        var attr = attrs[j];
        if (!isAllowedAttr(tag, attr.name.toLowerCase(), attr.value)) {
          el.removeAttribute(attr.name);
        }
      }

      if (tag === 'a' && el.getAttribute('href')) {
        el.setAttribute('rel', 'noopener noreferrer');
        el.setAttribute('target', '_blank');
      }

      sanitizeNode(el);
    }
  }

  function sanitizeHtml(html) {
    var container = document.createElement('div');
    container.innerHTML = html || '';
    sanitizeNode(container);
    return container.innerHTML;
  }

  window.TechNewsSanitize = {
    sanitizeHtml: sanitizeHtml
  };
})();
