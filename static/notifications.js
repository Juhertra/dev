// Placeholder for centralized notification helpers.
// Phase 1: keep behavior unchanged; migrate duplicates later.
window.showNotification = window.showNotification || function (text, type) {
  try {
    // Log notifications to server in production
    // Could send to logging service here
  } catch (e) {}
};


