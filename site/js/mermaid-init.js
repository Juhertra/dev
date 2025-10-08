(function () {
  function init() {
    if (window.mermaid && document.querySelector('.mermaid')) {
      mermaid.initialize({ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' });
      mermaid.init(undefined, document.querySelectorAll('.mermaid'));
    }
  }
  document.addEventListener('DOMContentLoaded', init);
  if (window.document$) { window.document$.subscribe(init); }
})();
