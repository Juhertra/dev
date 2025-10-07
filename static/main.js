
// Ensure TPL exists early for any consumers
try { window.TPL = window.TPL || { all: [], selected: [], recent: [] }; } catch(_){}
const THEME_KEY = 'demo_theme';
const getTheme = () => localStorage.getItem(THEME_KEY) || 'dark';
const setTheme = t => {
  localStorage.setItem(THEME_KEY, t);
  document.documentElement.classList.toggle('light', t === 'light');
  const b = document.getElementById('theme');
  if (b) b.textContent = t === 'light' ? '🌙' : '☀️';
};

function flash(btn, text, cls) {
  if (!btn) return;
  const orig = btn.getAttribute('data-label') || btn.textContent;
  btn.setAttribute('data-label', orig);
  btn.disabled = true;
  if (cls) btn.classList.add(cls);
  btn.textContent = text;
  setTimeout(() => {
    btn.textContent = btn.getAttribute('data-label') || orig;
    btn.disabled = false;
    if (cls) btn.classList.remove(cls);
  }, 1100);
}
function flashSuccess(btn, text) { flash(btn, text || '✓ Done', 'ok'); }
function flashError(btn, text)   { flash(btn, text || '✗ Error', 'err'); }

function copyWithFeedback(text, btn){
  navigator.clipboard.writeText(text).then(
    () => showNotification('Copied to clipboard', 'success'),
    () => showNotification('Copy failed', 'error')
  );
}

function copyUrlWithFeedback(url, btn) {
  // Enhanced URL copy with toast notification
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(
      () => {
        showToast('Copied!', 'success');
      },
      () => {
        // Fallback to textarea method
        copyWithFallback(url);
        showToast('Copied!', 'success');
      }
    );
  } else {
    // Fallback for older browsers
    copyWithFallback(url);
    showToast('Copied!', 'success');
  }
}

// Deep linking for drawers
function handleDrawerHash() {
  const hash = window.location.hash;
  if (!hash || !hash.startsWith('#')) return;
  
  const params = new URLSearchParams(hash.substring(1));
  
  if (params.get('drawer')) {
    setTimeout(() => {
      const drawerType = params.get('drawer');
      const method = params.get('method') || 'GET';
      const url = params.get('url') || '';
      const path = params.get('path') || '';
      
      if (drawerType === 'preview' && url) {
        // Trigger preview drawer
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/p/${getPid()}/sitemap/endpoint-preview`;
        form.style.display = 'none';
        
        const urlInput = document.createElement('input');
        urlInput.name = 'url';
        urlInput.value = url;
        
        const methodInput = document.createElement('input');
        methodInput.name = 'method';
        methodInput.value = method;
        
        form.appendChild(urlInput);
        form.appendChild(methodInput);
        document.body.appendChild(form);
        
        // Use HTMX to load drawer content
        htmx.ajax('POST', form.action, {
          target: '#panel-body',
          swap: 'innerHTML',
          values: { url: url, method: method }
        });
        
        openPanelWith('Preview', method, path, url);
        document.body.removeChild(form);
      } else if (drawerType === 'runs' && url) {
        // Trigger runs drawer
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/p/${getPid()}/sitemap/endpoint-runs`;
        form.style.display = 'none';
        
        const urlInput = document.createElement('input');
        urlInput.name = 'url';
        urlInput.value = url;
        
        const methodInput = document.createElement('input');
        methodInput.name = 'method';
        methodInput.value = method;
        
        form.appendChild(urlInput);
        form.appendChild(methodInput);
        document.body.appendChild(form);
        
        // Use HTMX to load drawer content
        htmx.ajax('POST', form.action, {
          target: '#panel-body',
          swap: 'innerHTML',
          values: { url: url, method: method }
        });
        
        openPanelWith('Runs', method, path, url);
        document.body.removeChild(form);
      }
    }, 100); // Small delay to ensure page is loaded
  }
}

// Auto-trigger drawer opening on page load
document.addEventListener('DOMContentLoaded', function() {
  handleDrawerHash();
});

// Also handle hash changes
window.addEventListener('hashchange', handleDrawerHash);

// Toast notification system
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toast.setAttribute('role', 'alert');
  
  container.appendChild(toast);
  
  // Trigger animation
  setTimeout(() => toast.classList.add('show'), 10);
  
  // Auto remove after 3 seconds
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => container.removeChild(toast), 300);
  }, 3000);
}

        function copyCurlWithFeedback(curl, btn) {
          // Enhanced cURL copy with toast notification
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(curl).then(
              () => {
                showToast('Copied!', 'success');
              },
              () => {
                // Fallback to textarea method
                copyWithFallback(curl);
                showToast('Copied!', 'success');
              }
            );
          } else {
            // Fallback for older browsers
            copyWithFallback(curl);
            showToast('Copied!', 'success');
          }
        }

function copyWithFallback(text) {
  // Fallback copy method using textarea trick
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.left = '-999999px';
  textarea.style.top = '-999999px';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  try {
    document.execCommand('copy');
    showNotification('Copied to clipboard', 'success');
  } catch (err) {
    showNotification('Copy failed', 'error');
    console.error('Copy failed:', err);
  } finally {
    document.body.removeChild(textarea);
  }
}

function getPid(){
  return (window.APP_CTX && window.APP_CTX.pid) || '';
}

function expandAll(){ document.querySelectorAll('details.spec').forEach(d=>d.open=true) }
function collapseAll(){ document.querySelectorAll('details.spec').forEach(d=>d.open=false) }
function toggleDetails(btn, postUrl, specId, safeId, index){
  const id = `det-${safeId}-${index}`, el = document.getElementById(id);
  if(!el) return;
  if(el.innerHTML.trim()){ el.innerHTML=''; btn.textContent='Details'; return; }
  btn.textContent='Close';
  htmx.ajax('POST', postUrl, {target:'#'+id, swap:'innerHTML', values:{pid: getPid(), spec_id:specId, index:index}});
}
function checkAllInTable(safeId, check){ document.querySelectorAll(`#tbl-${safeId} input[name=sel]`).forEach(cb=>cb.checked=!!check) }
function qDetails(btn, targetId, postUrl, qid){
  const el = document.getElementById(targetId);
  if (!el) return;
  if (el.innerHTML.trim()) { el.innerHTML=''; btn.textContent='Preview'; return; }
  btn.textContent='Close';
  htmx.ajax('POST', postUrl, { target:'#'+targetId, swap:'innerHTML', values:{qid} });
}

const FILTER_KEY='openapi_ui_method_filters';
const DEFAULT_FILTERS = ["GET","POST","PUT","DELETE","PATCH"];
function getFilters(){
  try{ return JSON.parse(localStorage.getItem(FILTER_KEY) || JSON.stringify(DEFAULT_FILTERS)); }
  catch(_){ return [...DEFAULT_FILTERS]; }
}
function syncFilterChips(){
  const active = new Set(getFilters());
  for (const m of DEFAULT_FILTERS){
    document.querySelectorAll(`.tag[data-m="${m}"]`).forEach(el=>{
      el.classList.toggle('active', active.has(m));
    });
  }
}
function setFilters(arr){
  localStorage.setItem(FILTER_KEY, JSON.stringify(arr));
  syncFilterChips();
  applyFilters();
}
function toggleFilter(m){
  const s = new Set(getFilters());
  if(s.has(m)) s.delete(m); else s.add(m);
  setFilters([...s]);
}
function resetFilters(){ setFilters([...DEFAULT_FILTERS]); }
function applyFilters(){
  const active = new Set(getFilters());
  document.querySelectorAll('tr.op-row').forEach(tr=>{
    const method = tr.getAttribute('data-method');
    const show = active.has(method);
    tr.style.display = show ? '' : 'none';
    const nxt = tr.nextElementSibling;
    if(nxt && nxt.classList.contains('op-details-row')){ nxt.style.display = show ? '' : 'none'; }
  });
  syncFilterChips();
}

// Site Map filter functions
function applySitemapFilters(containerId = 'sitemap') {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  // Get active method filters
  const activeMethods = new Set(getFilters());
  
  // Get status filter
  const statusFilter = container.querySelector('.status-filter.active')?.dataset.status || 'all';
  
  // Get vulns filter
  const vulnsFilter = container.querySelector('.vulns-filter.active')?.dataset.vulns || 'all';
  
  // Get search term
  const searchInput = document.getElementById('smap-search');
  const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
  
  // Apply filters to endpoint rows
  container.querySelectorAll('tr.endpoint-row').forEach(tr => {
    const method = tr.getAttribute('data-m');
    const status = tr.getAttribute('data-status');
    const hasVulns = tr.getAttribute('data-hasvulns') === '1';
    
    let show = true;
    
    // Method filter
    if (activeMethods.size > 0 && !activeMethods.has(method)) {
      show = false;
    }
    
    // Status filter
    if (statusFilter !== 'all' && status !== statusFilter) {
      show = false;
    }
    
    // Vulns filter
    if (vulnsFilter === 'has-vulns' && !hasVulns) {
      show = false;
    }
    
    // Search filter
    if (searchTerm) {
      const pathCell = tr.querySelector('.path');
      const path = pathCell ? pathCell.textContent.toLowerCase() : '';
      if (!path.includes(searchTerm)) {
        show = false;
      }
    }
    
    tr.style.display = show ? '' : 'none';
  });
  
  // Update filter button states
  container.querySelectorAll('.status-filter').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.status === statusFilter);
  });
  
  container.querySelectorAll('.vulns-filter').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.vulns === vulnsFilter);
  });
}

function toggleSitemapStatusFilter(button) {
  const container = button.closest('#sitemap');
  if (!container) return;
  
  const status = button.dataset.status;
  const currentActive = container.querySelector('.status-filter.active');
  
  if (currentActive) {
    currentActive.classList.remove('active');
  }
  
  if (currentActive !== button) {
    button.classList.add('active');
  }
  
  applySitemapFilters();
}

function toggleSitemapVulnsFilter(button) {
  const container = button.closest('#sitemap');
  if (!container) return;
  
  const vulns = button.dataset.vulns;
  const currentActive = container.querySelector('.vulns-filter.active');
  
  if (currentActive) {
    currentActive.classList.remove('active');
  }
  
  if (currentActive !== button) {
    button.classList.add('active');
  }
  
  applySitemapFilters();
}

document.addEventListener('DOMContentLoaded', ()=>{
  setTheme(getTheme());
  syncFilterChips();
  setTimeout(applyFilters,0);
  setTimeout(applySitemapFilters,0);
  // Global error handler for production
  try {
    window.onerror = function(msg, src, lineno, colno, err){
      // Log errors to server in production
      try { 
        // Could send to logging service here
      } catch(_) {}
    };
  } catch(_) {}
});

document.addEventListener('htmx:afterSwap', (e)=>{
  if (e.target && (e.target.id === 'specs' || (e.target.closest && e.target.closest('#specs')))) {
    syncFilterChips();
    setTimeout(applyFilters,0);
  }
  if (e.target && (e.target.id === 'sitemap-content' || (e.target.closest && e.target.closest('#sitemap-content')))) {
    setTimeout(applySitemapFilters,0);
  }
});

document.addEventListener('htmx:responseError', function(ev){
  const elt = ev.detail.elt;
  if (elt && elt.tagName === 'BUTTON') showNotification('Request failed', 'error');
});

// Listen for server-triggered notifications via HX-Trigger { notify: [{type,message}] }
document.addEventListener('htmx:afterOnLoad', function(ev){
  try {
    const hdr = ev && ev.detail && ev.detail.xhr ? ev.detail.xhr.getResponseHeader('HX-Trigger') : null;
    if (!hdr) return;
    const data = JSON.parse(hdr);
    const items = data && data.notify;
    if (Array.isArray(items)) {
      items.forEach(it => {
        if (it && it.message) {
          showNotification(it.message, it.type === 'error' ? 'error' : (it.type || 'info'));
        }
      });
    }
  } catch(_){ /* no-op */ }
});

// Drawer helpers (one copy only, exported globally)
window.openPanelWith = openPanelWith;
window.closePanel = closePanel;
let __lastDrawerTrigger = null;

function openPanelWith(title, method, path, url) {
  __lastDrawerTrigger = document.activeElement;
  const panel = document.getElementById('panel');
  const overlay = document.getElementById('panel-overlay');
  const titleEl = document.getElementById('panel-title');
  const chip = document.getElementById('panel-chip');
  const urlEl = document.getElementById('panel-url-display');
  if (titleEl) titleEl.textContent = path || title || 'Details';
  if (chip){
    const m = (method || 'GET').toUpperCase();
    chip.className = 'chip ' + m;
    chip.textContent = m;
  }
  if (urlEl){
    if (url) { urlEl.style.display='block'; urlEl.textContent=url; }
    else { urlEl.style.display='none'; urlEl.textContent=''; }
  }
  if (panel) panel.style.transform = 'translateX(0)';
  if (overlay) overlay.style.display = 'block';
}
function closePanel() {
  const panel = document.getElementById('panel');
  const overlay = document.getElementById('panel-overlay');
  if (panel) panel.style.transform = 'translateX(100%)';
  if (overlay) overlay.style.display = 'none';
  const body = document.getElementById('panel-body');
  if (body) body.innerHTML = '';
  if (__lastDrawerTrigger && typeof __lastDrawerTrigger.focus === 'function') {
    __lastDrawerTrigger.focus();
  }
}
function startPanelResize(ev){
  const panel = document.getElementById('panel'); if (!panel) return;
  let resizing = true, startX = ev.clientX, startW = panel.getBoundingClientRect().width;
  function onMove(e){ if (!resizing) return; const dx = startX - e.clientX; let w = Math.max(360, Math.min(900, startW + dx)); panel.style.width = w+'px'; }
  function onUp(){ resizing = false; document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); }
  document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp); ev.preventDefault();
}

// Copy helper for panel header
function copyPanelPrimary(btn){
  const body = document.getElementById('panel-body');
  if (!body) return;
  // Prefer existing inner "Copy curl" button so we reuse the exact payload
  const curlBtn = Array.from(body.querySelectorAll('button')).find(b=>/copy curl/i.test(b.textContent||''));
  if (curlBtn){ curlBtn.click(); return; }
  // Fallbacks: focused textarea, first pre, or raw text
  const focused = document.activeElement;
  if (focused && focused.tagName === 'TEXTAREA'){ copyWithFeedback(focused.value, btn); return; }
  const pre = body.querySelector('pre');
  const txt = pre ? pre.innerText : body.innerText;
  copyWithFeedback(txt, btn);
}

function copyPanelCurl(btn){
  const body = document.getElementById('panel-body');
  if (!body) return;
  // Prefer embedded curl payload
  const curlScript = body.querySelector('#panel-curl');
  if (curlScript && curlScript.textContent.trim()){
    copyWithFeedback(curlScript.textContent.trim(), btn);
    return;
  }
  // Fallback to inner Copy curl button
  const inner = Array.from(body.querySelectorAll('button')).find(b=>/copy curl/i.test(b.textContent||''));
  if (inner){ inner.click(); return; }
  // Last resort: generic
  copyPanelPrimary(btn);
}

function copyPanelUrl(btn){
  // Prefer value placed in header display container
  let s = document.getElementById('panel-url-display');
  let url = s && s.textContent ? s.textContent.trim() : '';
  if (!url){
    // Fallback to body-provided #panel-url
    s = document.getElementById('panel-url');
    url = s && s.textContent ? s.textContent.trim() : '';
  }
  if (url){ copyWithFeedback(url, btn); return; }
  // Fallback to panel title text (may be path only)
  const t = document.getElementById('panel-title');
  if (t && t.textContent){ copyWithFeedback(t.textContent, btn); return; }
}

// Enhanced keyboard shortcuts for drawers
document.addEventListener('keydown', (e)=>{
  // ESC closes drawer
  if (e.key === 'Escape') {
    closePanel();
    return;
  }
  
  // Enter triggers primary action when focus isn't in an input
  if (e.key === 'Enter' && !e.target.matches('input, textarea, select')) {
    const primaryBtn = document.getElementById('primary-action');
    if (primaryBtn && !primaryBtn.disabled) {
      e.preventDefault();
      primaryBtn.click();
    }
  }
});

// Auto-open drawer when #panel-body is updated by HTMX
document.addEventListener('htmx:afterSwap', (e)=>{
  if (e && e.target && e.target.id === 'panel-body'){
    try {
      const snippet = (document.getElementById('panel-body')?.innerHTML||'').slice(0,80);
    } catch(_){ }
    const panel = document.getElementById('panel');
    const overlay = document.getElementById('panel-overlay');
    if (panel) panel.style.transform = 'translateX(0)';
    if (overlay) overlay.style.display = 'block';
  }
});

// --- compatibility shims (avoid breaking older templates) ---
if (typeof copyPanelPrimary !== "function" && typeof copyPanelUrl === "function") {
  window.copyPanelPrimary = function(btn){ copyPanelUrl(btn); };
}

// --- Phase 4: Keyboard Shortcuts (Desktop Only) ---
function initKeyboardShortcuts() {
  // Only enable on desktop (not mobile/touch devices)
  if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
    return;
  }
  
  document.addEventListener('keydown', function(e) {
    // Only handle Ctrl+number combinations
    if (!e.ctrlKey || e.altKey || e.shiftKey || e.metaKey) return;
    
    const pid = getPid();
    if (!pid) return; // No project context
    
    // Prevent default browser behavior for Ctrl+1-7
    if (e.key >= '1' && e.key <= '7') {
      e.preventDefault();
      
      const shortcuts = {
        '1': 'web.project_open',      // API Explorer
        '2': 'web.site_map_page',      // Site Map  
        '3': 'web.queue_page',         // Test Queue
        '4': 'web.active_testing_page', // Active Testing
        '5': 'web.sends_page',         // History (Sends)
        '6': 'web.findings_page',      // Vulnerabilities
        '7': 'web.patterns_page'       // Detection Rules
      };
      
      const route = shortcuts[e.key];
      if (route) {
        // Use HTMX for navigation to avoid full page reload
        const url = `/p/${pid}/${route.split('.')[1].replace('_page', '')}`;
        window.location.href = url;
      }
    }
  });
}

// Initialize shortcuts when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initKeyboardShortcuts);
} else {
  initKeyboardShortcuts();
}

// ============================================================
// Enhanced Grouping System Functions
// ============================================================

let groupBy = 'rule';
let sourceFilter = 'all';

function switchGroup(mode) {
  groupBy = mode;
  // Update active button
  document.querySelectorAll('.filter-btn[data-group]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.group === mode);
  });
  
  // Re-request the same page with ?group=mode to get server-side grouping
  const url = new URL(window.location.href);
  url.searchParams.set('group', mode);
  window.location.href = url.toString();
}

function filterSource(src) {
  sourceFilter = src;
  
  // Update active button
  document.querySelectorAll('.filter-btn[data-source]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.source === src);
  });
  
  // Filter findings by source
  document.querySelectorAll('.finding-item').forEach(el => {
    const s = el.dataset.source || 'detector';
    el.style.display = (src === 'all' || src === s) ? 'block' : 'none';
  });
  
  // Update group visibility
  document.querySelectorAll('.finding-group').forEach(group => {
    const items = group.querySelectorAll('.finding-item');
    const visibleItems = Array.from(items).filter(item => item.style.display !== 'none');
    group.style.display = visibleItems.length > 0 ? 'block' : 'none';
  });
}

function bulkTriageGroup(groupKey, status) {
  if (!status) return;
  
  const pid = getPid();
  if (!pid) {
    showNotification('No project ID found', 'error');
    return;
  }
  
  fetch(`/p/${pid}/findings/triage-group`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ group_key: groupKey, status })
  })
  .then(r => r.json())
  .then(res => {
    if (res.success) {
      showNotification(res.message || 'Bulk triage completed successfully', 'success');
      setTimeout(() => location.reload(), 1000);
    } else {
      showNotification(res.error || 'Bulk triage failed', 'error');
    }
  })
  .catch(err => {
    console.error('Bulk triage error:', err);
    showNotification('Bulk triage failed: ' + err.message, 'error');
  });
}

function exportGroup(groupKey) {
  const pid = getPid();
  if (!pid) {
    showNotification('No project ID found', 'error');
    return;
  }
  
  const url = `/p/${pid}/findings/export-group?key=${encodeURIComponent(groupKey)}`;
  window.open(url, '_blank');
}

function addGroupToQueue(groupKey) {
  const pid = getPid();
  if (!pid) {
    showNotification('No project ID found', 'error');
    return;
  }
  
  fetch(`/p/${pid}/findings/queue-group`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ group_key: groupKey })
  })
  .then(r => r.json())
  .then(res => {
    if (res.success) {
      showNotification(res.message || 'Endpoints added to queue successfully', 'success');
    } else {
      showNotification(res.error || 'Failed to add endpoints to queue', 'error');
    }
  })
  .catch(err => {
    console.error('Queue group error:', err);
    showNotification('Failed to add endpoints to queue: ' + err.message, 'error');
  });
}

// ============================================================
// Template Management System
// ============================================================

// --- Notification System ---
let notificationQueue = [];
let isProcessingQueue = false;

function showNotification(message, type = 'info') {
  // Add to queue
  notificationQueue.push({ message, type, timestamp: Date.now() });
  
  // Process queue if not already processing
  if (!isProcessingQueue) {
    processNotificationQueue();
  }
}

function processNotificationQueue() {
  if (notificationQueue.length === 0) {
    isProcessingQueue = false;
    return;
  }
  
  isProcessingQueue = true;
  
  // Get the next notification
  const { message, type } = notificationQueue.shift();
  
  // Create notification element
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: var(--card);
    border: 1px solid var(--card-b);
    border-radius: 8px;
    padding: 12px 16px;
    color: var(--fg);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 10000;
    max-width: 400px;
    word-wrap: break-word;
    animation: slideInRight 0.3s ease;
  `;
  
  // Add type-specific styling
  if (type === 'success') {
    notification.style.borderLeft = '4px solid var(--ok)';
  } else if (type === 'error') {
    notification.style.borderLeft = '4px solid var(--err)';
  } else if (type === 'info') {
    notification.style.borderLeft = '4px solid var(--accent)';
  }
  
  notification.textContent = message;
  
  // Add to DOM
  document.body.appendChild(notification);
  
  // Auto-remove after 4 seconds
  setTimeout(() => {
    notification.style.animation = 'slideOutRight 0.3s ease';
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
      // Process next notification after this one is removed
      setTimeout(() => {
        processNotificationQueue();
      }, 100);
    }, 300);
  }, 4000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideInRight {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  @keyframes slideOutRight {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
  }
`;
document.head.appendChild(style);

// --- Selection store (persists during page session) ---
const TPL = { all: [], selected: new Set(JSON.parse(sessionStorage.getItem('tpl_selected') || '[]')), recent: JSON.parse(localStorage.getItem('tpl_recent') || '[]'), page: 1, pageSize: 50, filters: { q: "", cats: new Set(), modalCats: new Set() } };
try { window.TPL = TPL; } catch(_){ }

function persistTplSelection(){
  sessionStorage.setItem('tpl_selected', JSON.stringify([...TPL.selected]));
  // maintain a short "recent" list
  const arr = [...TPL.selected];
  localStorage.setItem('tpl_recent', JSON.stringify(arr.slice(-20)));
  
  // Update the selected templates display
  updateSelectedTemplatesDisplay();
  
  // Update template counts in modals
  updateTemplateCount();
  updateManagerTemplateCount();
}

function updateSelectedTemplatesDisplay(){
  const countEl = document.getElementById('selected-template-count');
  const previewEl = document.getElementById('selected-templates-preview');
  
  if (!countEl || !previewEl) return;
  
  const count = TPL.selected.size;
  countEl.textContent = `${count} template${count !== 1 ? 's' : ''}`;
  
  if (count === 0) {
    previewEl.innerHTML = '<div class="muted" style="text-align:center;padding:8px">No templates selected. Use "Quick Select" or "Advanced Manager" to choose templates.</div>';
  } else {
    // Show all selected templates as individual items
    const selectedTemplates = [];
    TPL.all.forEach(t => {
      if (TPL.selected.has(t.id)) {
        selectedTemplates.push({id: t.id, name: t.name});
      }
    });
    
    // If we have selected templates but they're not in TPL.all yet, show the IDs
    if (selectedTemplates.length === 0 && TPL.selected.size > 0) {
      const selectedIds = Array.from(TPL.selected);
      previewEl.innerHTML = selectedIds.map(id => `
        <div class="selected-template-item">
          <div class="selected-template-name">${id}</div>
          <div class="selected-template-id">${id}</div>
          <div class="selected-template-remove" onclick="removeSelectedTemplate('${id}')">×</div>
        </div>
      `).join('');
    } else {
      previewEl.innerHTML = selectedTemplates.map(t => `
        <div class="selected-template-item">
          <div class="selected-template-name">${t.name}</div>
          <div class="selected-template-id">${t.id}</div>
          <div class="selected-template-remove" onclick="removeSelectedTemplate('${t.id}')">×</div>
        </div>
      `).join('');
    }
  }
}

function removeSelectedTemplate(templateId) {
  TPL.selected.delete(templateId);
  persistTplSelection();
  renderSidePanel();
  renderTemplateTable();
}

function openTemplateSidePanel(){
  const panel = document.getElementById('tpl-sidepanel');
  if (!panel) {
    console.error('tpl-sidepanel element not found');
    return;
  }
  panel.classList.add('open');
  if (!TPL.all.length) loadTemplatesCatalog();
  else renderSidePanel();
}
function closeTemplateSidePanel(){
  document.getElementById('tpl-sidepanel').classList.remove('open');
}

function openTemplateManagerModal(){
  const modal = document.getElementById('tpl-manager-modal');
  if (!modal) {
    console.error('tpl-manager-modal element not found');
    return;
  }
  modal.classList.add('open');
  if (!TPL.all.length) loadTemplatesCatalog().then(()=>{ loadTemplateCategories(); renderTemplateTable(); loadProfiles(); });
  else { loadTemplateCategories(); renderTemplateTable(); loadProfiles(); }
}
function closeTemplateManagerModal(){
  document.getElementById('tpl-manager-modal').classList.remove('open');
}

// Fetch full catalog once (server should return compact JSON)
async function loadTemplatesCatalog(){
  // supports optional server-side category param later
  const res = await fetch(location.pathname.replace(/\/active-testing.*/,'') + '/nuclei/templates?all=1');
  const data = await res.json();
  if (data.success){
    TPL.all = data.templates.map(t => ({
      id: t.id, name: t.name, tags: t.tags || [],
      severity: t.severity || 'info',
      category: t.category || inferCategoryFromTags(t.tags||[]),
      desc: t.description || ''
    }));
  }
}

function inferCategoryFromTags(tags){
  const s = (tags||[]).join(' ').toLowerCase();
  if (s.includes('cve') || /\bcve-\d{4}-\d+\b/.test(s)) return 'cve';
  if (s.includes('misconfig')) return 'misconfig';
  if (s.includes('tech') || s.includes('technology')) return 'tech';
  if (s.includes('api')) return 'api';
  if (s.includes('cloud') || s.includes('aws') || s.includes('gcp') || s.includes('azure')) return 'cloud';
  return 'web';
}

// ---------- Side panel ----------
function renderSidePanel(){
  const q = (document.getElementById('tpl-search').value || "").toLowerCase();
  const cats = new Set([...TPL.filters.cats]);
  const list = document.getElementById('tpl-sidepanel-list');
  list.innerHTML = '';

  const items = TPL.all.filter(t => {
    const hit = !q || (t.name + ' ' + t.id + ' ' + (t.desc || '')).toLowerCase().includes(q);
    const catOk = !cats.size || cats.has(t.category) || (cats.has('recent') && TPL.recent.includes(t.id));
    return hit && catOk;
  }).slice(0, 1000); // Increased limit for better coverage

  // Sort items to show selected templates first
  items.sort((a, b) => {
    const aSelected = TPL.selected.has(a.id);
    const bSelected = TPL.selected.has(b.id);
    if (aSelected && !bSelected) return -1;
    if (!aSelected && bSelected) return 1;
    return 0;
  });

  items.forEach(t => {
    const div = document.createElement('div');
    div.className = 'virtual-item';
    div.innerHTML = `
      <input type="checkbox" ${TPL.selected.has(t.id)?'checked':''} onchange="toggleTpl('${t.id}', this.checked)" style="margin:0;flex-shrink:0">
      <div class="template-info" style="flex:1;min-width:0">
        <div style="font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${t.name}</div>
        <div class="muted" style="font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${t.id}</div>
      </div>
      <div class="template-actions" style="display:flex;align-items:center;gap:4px;flex-shrink:0">
        <span class="tag">${t.severity}</span>
        <span class="tag">${t.category}</span>
      </div>
    `;
    list.appendChild(div);
  });

  document.getElementById('tpl-sidepanel-count').textContent = items.length;
  const selectedCountEl = document.getElementById('tpl-selected-count');
  if (selectedCountEl) selectedCountEl.textContent = TPL.selected.size;
  
  // Update total count
  const totalCountEl = document.getElementById('tpl-total-count');
  if (totalCountEl) totalCountEl.textContent = TPL.all.length.toLocaleString();
}
function filterSidePanelTemplates(){ renderSidePanel(); }

function toggleTplCategory(el){
  const cat = el.dataset.cat;
  if (el.classList.toggle('active')) TPL.filters.cats.add(cat);
  else TPL.filters.cats.delete(cat);
  renderSidePanel();
}

function toggleTpl(id, on){
  if (on) TPL.selected.add(id); else TPL.selected.delete(id);
  persistTplSelection();
}

function selectAllVisibleTemplates(){
  document.querySelectorAll('#tpl-sidepanel-list input[type=checkbox]').forEach(cb => {
    cb.checked = true; TPL.selected.add(cb.nextElementSibling?.querySelector? cb.parentElement.querySelector('.muted').textContent : '');
  });
  // faster: iterate items again
  document.querySelectorAll('#tpl-sidepanel-list .virtual-item .muted').forEach(n => TPL.selected.add(n.textContent));
  persistTplSelection(); renderSidePanel();
}
function deselectAllVisibleTemplates(){
  document.querySelectorAll('#tpl-sidepanel-list .virtual-item .muted').forEach(n => TPL.selected.delete(n.textContent));
  persistTplSelection(); renderSidePanel();
}

// ---------- Modal ----------
function loadTemplateCategories(){
  // Get actual categories from templates with counts
  const categoryCounts = {};
  TPL.all.forEach(t => {
    const cat = t.category || 'unknown';
    categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
  });
  
  // Sort by count (most templates first)
  const sortedCats = Object.entries(categoryCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10); // Show top 10 categories
  
  const holder = document.getElementById('tpl-cats');
  holder.innerHTML = '';
  
  sortedCats.forEach(([cat, count]) => {
    const div = document.createElement('div');
    div.className = 'tag';
    div.textContent = `${cat} (${count.toLocaleString()})`;
    div.dataset.category = cat;
    div.onclick = () => {
      div.classList.toggle('active');
      if (div.classList.contains('active')) TPL.filters.modalCats.add(cat);
      else TPL.filters.modalCats.delete(cat);
      TPL.page = 1; renderTemplateTable();
    };
    holder.appendChild(div);
  });
}

function refreshTemplateTable(){ TPL.page = 1; renderTemplateTable(); }

function renderTemplateTable(){
  const q = (document.getElementById('tpl-modal-search').value || "").toLowerCase();
  const cats = new Set([...TPL.filters.modalCats]);
  let rows = TPL.all.filter(t => {
    const hit = !q || (t.name + ' ' + t.id + ' ' + t.desc).toLowerCase().includes(q);
    const catOk = !cats.size || cats.has(t.category);
    return hit && catOk;
  });

  // Sort rows to show selected templates first
  rows.sort((a, b) => {
    const aSelected = TPL.selected.has(a.id);
    const bSelected = TPL.selected.has(b.id);
    if (aSelected && !bSelected) return -1;
    if (!aSelected && bSelected) return 1;
    return 0;
  });

  const totalPages = Math.max(1, Math.ceil(rows.length / TPL.pageSize));
  if (TPL.page > totalPages) TPL.page = totalPages;
  const start = (TPL.page - 1) * TPL.pageSize;
  rows = rows.slice(start, start + TPL.pageSize);

  const body = document.getElementById('tpl-table-body');
  body.innerHTML = '';
  rows.forEach(t => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="text-align:center;vertical-align:middle"><input type="checkbox" ${TPL.selected.has(t.id)?'checked':''} onchange="toggleTpl('${t.id}', this.checked)" style="margin:0"></td>
      <td style="vertical-align:middle">${t.name}</td>
      <td class="muted" style="vertical-align:middle">${t.id}</td>
      <td style="vertical-align:middle">${(t.tags||[]).slice(0,3).map(tag=>`<span class="tag">${tag}</span>`).join(' ')}</td>
      <td style="vertical-align:middle"><span class="tag">${t.severity}</span></td>
    `;
    body.appendChild(tr);
  });

  document.getElementById('tpl-page-indicator').textContent = `${TPL.page}/${totalPages}`;
  document.getElementById('tpl-selected-count').textContent = TPL.selected.size;
}

function prevTplPage(){ if (TPL.page>1){ TPL.page--; renderTemplateTable(); } }
function nextTplPage(){
  const q = (document.getElementById('tpl-modal-search').value || "").toLowerCase();
  const cats = new Set([...TPL.filters.modalCats]);
  const total = TPL.all.filter(t => {
    const hit = !q || (t.name + ' ' + t.id + ' ' + t.desc).toLowerCase().includes(q);
    const catOk = !cats.size || cats.has(t.category);
    return hit && catOk;
  }).length;
  const pages = Math.max(1, Math.ceil(total / TPL.pageSize));
  if (TPL.page < pages){ TPL.page++; renderTemplateTable(); }
}

function selectAllInTable(){
  document.querySelectorAll('#tpl-table-body input[type=checkbox]').forEach(cb => { cb.checked = true; });
  document.querySelectorAll('#tpl-table-body tr .muted').forEach(n => TPL.selected.add(n.textContent));
  persistTplSelection(); renderTemplateTable();
}
function deselectAllInTable(){
  document.querySelectorAll('#tpl-table-body tr .muted').forEach(n => TPL.selected.delete(n.textContent));
  persistTplSelection(); renderTemplateTable();
}

function clearAllSelectedTemplates(){
  if (TPL.selected.size === 0) {
    showNotification('No templates selected', 'info');
    return;
  }
  
  // Use themed confirmation modal instead of browser confirm
  openClearTemplatesConfirmation();
}

function openClearTemplatesConfirmation(){
  const modal = document.getElementById('clear-templates-modal');
  const countEl = document.getElementById('clear-templates-count');
  
  if (!modal || !countEl) return;
  
  countEl.textContent = TPL.selected.size;
  modal.classList.add('open');
}

function closeClearTemplatesConfirmation(){
  const modal = document.getElementById('clear-templates-modal');
  if (!modal) return;
  
  modal.classList.remove('open');
}

function confirmClearTemplates(){
  TPL.selected.clear();
  persistTplSelection();
  renderTemplateTable();
  renderSidePanel();
  updateSelectedTemplatesDisplay();
  closeClearTemplatesConfirmation();
  showNotification('All selections cleared', 'success');
}

function applyTemplateSelection(){
  // reflect selection onto hidden checkboxes on the config page if you keep them
  closeTemplateManagerModal();
  closeTemplateSidePanel();
  // If your POST /scan expects "templates" array, just read TPL.selected in runActiveScan()
}

// ---------- Profiles (stubs) ----------
function openProfileManager(){
  const modal = document.getElementById('profile-manager-modal');
  if (!modal) return;
  
  modal.classList.add('open');
  loadProfileList();
  updateManagerTemplateCount();
}

function closeProfileManager(){
  const modal = document.getElementById('profile-manager-modal');
  if (!modal) return;
  
  modal.classList.remove('open');
  // Reset form
  document.getElementById('manager-profile-name').value = '';
}

function updateManagerTemplateCount(){
  const countEl = document.getElementById('manager-profile-count');
  if (countEl) {
    countEl.textContent = TPL.selected.size;
  }
}

async function saveProfileFromManager(){
  const nameInput = document.getElementById('manager-profile-name');
  const name = nameInput ? nameInput.value.trim() : '';
  
  if (!name) {
    showNotification('Please enter a profile name', 'error');
    return;
  }
  
  if (TPL.selected.size === 0) {
    showNotification('No templates selected to save', 'error');
    return;
  }
  
  try {
    const response = await fetch(location.pathname.replace(/\/active-testing.*/,'')+'/nuclei/profiles', {
      method:'POST', 
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ name, templates: [...TPL.selected] })
    });
    
    const data = await response.json();
    if (data.success) {
      nameInput.value = '';
      loadProfileList();
      loadProfiles(); // Update the sidebar profiles too
      showNotification(`Profile "${name}" saved successfully (${TPL.selected.size} templates)`, 'success');
    } else {
      showNotification(`Error saving profile: ${data.error}`, 'error');
    }
  } catch (error) {
    showNotification(`Error saving profile: ${error.message}`, 'error');
  }
}

async function saveCurrentSelectionAsProfile(){
  const nameInput = document.getElementById('save-profile-name');
  const name = nameInput ? nameInput.value.trim() : '';
  
  if (!name) {
    showNotification('Please enter a profile name', 'error');
    return;
  }
  
  if (TPL.selected.size === 0) {
    showNotification('No templates selected to save', 'error');
    return;
  }
  
  try {
    const response = await fetch(location.pathname.replace(/\/active-testing.*/,'')+'/nuclei/profiles', {
      method:'POST', 
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ name, templates: [...TPL.selected] })
    });
    
    const data = await response.json();
    if (data.success) {
      nameInput.value = '';
      loadProfileList();
      loadProfiles(); // Update the sidebar profiles too
      loadExistingProfilesForUpdate(); // Update the dropdown in save modal
      showNotification(`Profile "${name}" saved successfully (${TPL.selected.size} templates)`, 'success');
    } else {
      showNotification(`Error saving profile: ${data.error}`, 'error');
    }
  } catch (error) {
    showNotification(`Error saving profile: ${error.message}`, 'error');
  }
}
async function loadProfiles(){
  const res = await fetch(location.pathname.replace(/\/active-testing.*/,'')+'/nuclei/profiles');
  const data = await res.json();
  const holder = document.getElementById('tpl-profiles');
  if (!holder || !data.success) return;
  holder.innerHTML = '';
  
  if (data.profiles.length === 0) {
    holder.innerHTML = '<div class="muted" style="padding:8px;text-align:center">No profiles saved</div>';
    return;
  }
  
  data.profiles.forEach(p => {
    const div = document.createElement('div');
    div.style.display = 'flex';
    div.style.justifyContent = 'space-between';
    div.style.alignItems = 'center';
    div.innerHTML = `
      <span onclick="loadProfile('${p.name}')" style="cursor:pointer;flex:1">${p.name} (${p.count})</span>
      <button class="btn ghost" onclick="deleteProfile('${p.name}')" style="padding:2px 6px;font-size:11px">Delete</button>
    `;
    holder.appendChild(div);
  });
}

async function loadProfileList(){
  const res = await fetch(location.pathname.replace(/\/active-testing.*/,'')+'/nuclei/profiles');
  const data = await res.json();
  const holder = document.getElementById('profile-list');
  if (!holder || !data.success) return;
  holder.innerHTML = '';
  
  if (data.profiles.length === 0) {
    holder.innerHTML = '<div class="muted" style="padding:20px;text-align:center">No profiles saved yet</div>';
    return;
  }
  
  data.profiles.forEach(p => {
    const div = document.createElement('div');
    div.className = 'profile-item';
    div.innerHTML = `
      <div class="profile-info" onclick="loadProfile('${p.name}')">
        <div class="profile-name">${p.name}</div>
        <div class="profile-details">${p.count} templates</div>
      </div>
      <div class="profile-actions">
        <button class="btn ghost" onclick="loadProfile('${p.name}')" style="font-size:12px">Load</button>
        <button class="btn ghost" onclick="deleteProfile('${p.name}')" style="font-size:12px;color:var(--err)">Delete</button>
      </div>
    `;
    holder.appendChild(div);
  });
}

function loadProfile(profileName) {
  fetch(location.pathname.replace(/\/active-testing.*/,'')+`/nuclei/profiles/${encodeURIComponent(profileName)}`)
    .then(r=>r.json()).then(d=>{
      if (d.success){ 
        TPL.selected = new Set(d.templates); 
        persistTplSelection(); 
        renderTemplateTable(); 
        renderSidePanel(); 
        updateSelectedTemplatesDisplay(); // Update the main display
        showNotification(`Loaded profile "${profileName}" with ${d.templates.length} templates`, 'success');
      } else {
        showNotification(`Error loading profile: ${d.error}`, 'error');
      }
    });
}

// Store the profile name to delete
let profileToDelete = null;

function deleteProfile(profileName) {
  profileToDelete = profileName;
  openDeleteConfirmation(profileName);
}

function openDeleteConfirmation(profileName) {
  const modal = document.getElementById('delete-confirmation-modal');
  const nameEl = document.getElementById('delete-profile-name');
  
  if (!modal || !nameEl) return;
  
  nameEl.textContent = profileName;
  modal.classList.add('open');
}

function closeDeleteConfirmation() {
  const modal = document.getElementById('delete-confirmation-modal');
  if (!modal) return;
  
  modal.classList.remove('open');
  profileToDelete = null;
}

function confirmDeleteProfile() {
  if (!profileToDelete) {
    showNotification('No profile selected for deletion', 'error');
    return;
  }
  
  const profileName = profileToDelete;
  
  fetch(location.pathname.replace(/\/active-testing.*/,'')+`/nuclei/profiles/${encodeURIComponent(profileName)}`, {
    method: 'DELETE'
  })
  .then(r=>r.json()).then(d=>{
    if (d.success) {
      showNotification(`Profile "${profileName}" deleted successfully`, 'success');
      loadProfiles(); // Refresh the sidebar profile list
      loadProfileList(); // Refresh the modal profile list
      closeDeleteConfirmation();
    } else {
      showNotification(`Error deleting profile: ${d.error}`, 'error');
    }
  }).catch(err => {
    console.error('Error deleting profile:', err);
    showNotification('Error deleting profile', 'error');
  });
}

function manageProfiles() {
  fetch(location.pathname.replace(/\/active-testing.*/,'')+'/nuclei/profiles')
    .then(r=>r.json()).then(data=>{
      if (data.success && data.profiles.length > 0) {
        const profileList = data.profiles.map(p => `${p.name} (${p.count} templates)`).join('\n');
        const action = prompt(`Available Profiles:\n\n${profileList}\n\nEnter profile name to load, or "DELETE <name>" to delete:`);
        
        if (action) {
            if (action.startsWith('DELETE ')) {
              const profileToDelete = action.substring(7);
              deleteProfile(profileToDelete);
            } else {
              loadProfile(action);
            }
        }
      } else {
        showNotification('No profiles found. Save a profile first by selecting templates and clicking "Save".', 'info');
      }
    }).catch(err => {
      console.error('Error loading profiles:', err);
      showNotification('Error loading profiles', 'error');
    });
}
// ---------- Profile Selection Modal ----------
function openProfileSelection(){
  const modal = document.getElementById('profile-selection-modal');
  if (!modal) return;
  
  modal.classList.add('open');
  loadProfileSelectionList();
}

function closeProfileSelection(){
  const modal = document.getElementById('profile-selection-modal');
  if (!modal) return;
  
  modal.classList.remove('open');
}

// ---------- Save Profile Modal ----------
function openSaveProfile(){
  const modal = document.getElementById('save-profile-modal');
  if (!modal) return;
  
  modal.classList.add('open');
  loadExistingProfilesForUpdate();
  updateTemplateCount();
}

function closeSaveProfile(){
  const modal = document.getElementById('save-profile-modal');
  if (!modal) return;
  
  modal.classList.remove('open');
  // Reset form
  document.getElementById('save-profile-name').value = '';
  document.getElementById('existing-profile-select').value = '';
  document.getElementById('update-profile-btn').disabled = true;
  document.getElementById('existing-profile-info').style.display = 'none';
}

function updateTemplateCount(){
  const countEl = document.getElementById('save-profile-count');
  if (countEl) {
    countEl.textContent = TPL.selected.size;
  }
}

async function loadExistingProfilesForUpdate(){
  const res = await fetch(location.pathname.replace(/\/active-testing.*/,'')+'/nuclei/profiles');
  const data = await res.json();
  const select = document.getElementById('existing-profile-select');
  if (!select || !data.success) return;
  
  // Clear existing options except the first one
  select.innerHTML = '<option value="">Select profile to update...</option>';
  
  data.profiles.forEach(p => {
    const option = document.createElement('option');
    option.value = p.name;
    option.textContent = `${p.name} (${p.count} templates)`;
    select.appendChild(option);
  });
}

function loadExistingProfileForUpdate(){
  const select = document.getElementById('existing-profile-select');
  const updateBtn = document.getElementById('update-profile-btn');
  const infoDiv = document.getElementById('existing-profile-info');
  
  if (!select || !updateBtn || !infoDiv) return;
  
  const selectedProfile = select.value;
  if (selectedProfile) {
    updateBtn.disabled = false;
    infoDiv.style.display = 'block';
    infoDiv.innerHTML = `Selected: <strong>${selectedProfile}</strong> - Click "Update Profile" to save changes`;
  } else {
    updateBtn.disabled = true;
    infoDiv.style.display = 'none';
  }
}

async function updateExistingProfile(){
  const select = document.getElementById('existing-profile-select');
  const profileName = select.value;
  const updateMode = document.querySelector('input[name="update-mode"]:checked').value;
  
  if (!profileName) {
    showNotification('Please select a profile to update', 'error');
    return;
  }
  
  try {
    // Get current profile templates
    const currentRes = await fetch(location.pathname.replace(/\/active-testing.*/,'')+`/nuclei/profiles/${encodeURIComponent(profileName)}`);
    const currentData = await currentRes.json();
    
    if (!currentData.success) {
      showNotification(`Error loading profile: ${currentData.error}`, 'error');
      return;
    }
    
    let finalTemplates;
    if (updateMode === 'replace') {
      // Replace all templates
      finalTemplates = [...TPL.selected];
    } else {
      // Append to existing templates
      const existingTemplates = new Set(currentData.templates);
      const newTemplates = [...TPL.selected];
      finalTemplates = [...new Set([...existingTemplates, ...newTemplates])];
    }
    
    // Save updated profile
    const response = await fetch(location.pathname.replace(/\/active-testing.*/,'')+'/nuclei/profiles', {
      method:'POST', 
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ name: profileName, templates: finalTemplates })
    });
    
    const data = await response.json();
    if (data.success) {
      const action = updateMode === 'replace' ? 'replaced' : 'updated';
      showNotification(`Profile "${profileName}" ${action} successfully (${finalTemplates.length} templates)`, 'success');
      closeSaveProfile();
      loadProfiles(); // Update sidebar
    } else {
      showNotification(`Error updating profile: ${data.error}`, 'error');
    }
  } catch (error) {
    showNotification(`Error updating profile: ${error.message}`, 'error');
  }
}

async function loadProfileSelectionList(){
  const res = await fetch(location.pathname.replace(/\/active-testing.*/,'')+'/nuclei/profiles');
  const data = await res.json();
  const holder = document.getElementById('profile-selection-list');
  if (!holder || !data.success) return;
  
  holder.innerHTML = '';
  
  if (data.profiles.length === 0) {
    holder.innerHTML = '<div class="muted" style="padding:20px;text-align:center">No profiles saved yet</div>';
    return;
  }
  
  data.profiles.forEach(p => {
    const div = document.createElement('div');
    div.className = 'profile-item';
    div.innerHTML = `
      <div class="profile-info" onclick="loadProfileFromSelection('${p.name}')">
        <div class="profile-name">${p.name}</div>
        <div class="profile-details">${p.count} templates</div>
      </div>
    `;
    holder.appendChild(div);
  });
}

function loadProfileFromSelection(profileName) {
  fetch(location.pathname.replace(/\/active-testing.*/,'')+`/nuclei/profiles/${encodeURIComponent(profileName)}`)
    .then(r=>r.json()).then(d=>{
      if (d.success){ 
        TPL.selected = new Set(d.templates); 
        persistTplSelection(); 
        renderTemplateTable(); 
        renderSidePanel(); 
        updateSelectedTemplatesDisplay();
        closeProfileSelection();
        showNotification(`Loaded profile "${profileName}" with ${d.templates.length} templates`, 'success');
      } else {
        showNotification(`Error loading profile: ${d.error}`, 'error');
      }
    });
}

function loadProfilePrompt(){
  // Open the simple profile selection modal
  openProfileSelection();
}

// Template management functions loaded
