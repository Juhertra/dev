/**
 * VulnsBulk - Minimal selection model and HTMX helpers for bulk triage operations
 */
window.VulnsBulk = {
  state: {
    selected: new Set()
  },

  init() {
    this.bindEvents();
    this.updateUI();
  },

  bindEvents() {
    // Select all checkbox
    const selectAll = document.getElementById('sel-all');
    if (selectAll) {
      selectAll.addEventListener('change', (e) => {
        this.toggleSelectAll(e.target.checked);
      });
    }

    // Individual row checkboxes
    document.addEventListener('change', (e) => {
      if (e.target.classList.contains('row-sel')) {
        this.toggleRowSelection(e.target);
      }
    });

    // Clear selection button
    const clearBtn = document.getElementById('clear-selection');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        this.clearSelection();
      });
    }

    // Suppression panel toggle
    const suppressBtn = document.getElementById('suppress-btn');
    const suppressPanel = document.getElementById('suppress-panel');
    const cancelSuppress = document.getElementById('cancel-suppress');
    
    if (suppressBtn && suppressPanel) {
      suppressBtn.addEventListener('click', () => {
        suppressPanel.style.display = suppressPanel.style.display === 'none' ? 'block' : 'none';
      });
    }

    if (cancelSuppress && suppressPanel) {
      cancelSuppress.addEventListener('click', () => {
        suppressPanel.style.display = 'none';
      });
    }

    // HTMX event listeners
    document.body.addEventListener('htmx:afterSwap', (e) => {
      if (e.target.id === 'vulns-list') {
        // Clear selection after server refresh
        this.clearSelection();
        this.updateUI();
      }
    });

    document.body.addEventListener('htmx:beforeRequest', (e) => {
      // Show loading indicator
      const indicator = document.querySelector('.hx-indicator');
      if (indicator) {
        indicator.style.display = 'block';
      }
    });

    document.body.addEventListener('htmx:afterRequest', (e) => {
      // Hide loading indicator
      const indicator = document.querySelector('.hx-indicator');
      if (indicator) {
        indicator.style.display = 'none';
      }
    });
  },

  toggleSelectAll(checked) {
    const rowCheckboxes = document.querySelectorAll('.row-sel');
    rowCheckboxes.forEach(checkbox => {
      checkbox.checked = checked;
      const index = parseInt(checkbox.dataset.index);
      if (checked) {
        this.state.selected.add(index);
      } else {
        this.state.selected.delete(index);
      }
    });
    this.updateUI();
  },

  toggleRowSelection(checkbox) {
    const index = parseInt(checkbox.dataset.index);
    if (checkbox.checked) {
      this.state.selected.add(index);
    } else {
      this.state.selected.delete(index);
    }
    this.updateSelectAllState();
    this.updateUI();
  },

  updateSelectAllState() {
    const selectAll = document.getElementById('sel-all');
    const rowCheckboxes = document.querySelectorAll('.row-sel');
    
    if (!selectAll || !rowCheckboxes.length) return;

    const totalRows = rowCheckboxes.length;
    const selectedCount = this.state.selected.size;

    if (selectedCount === 0) {
      selectAll.checked = false;
      selectAll.indeterminate = false;
    } else if (selectedCount === totalRows) {
      selectAll.checked = true;
      selectAll.indeterminate = false;
    } else {
      selectAll.checked = false;
      selectAll.indeterminate = true;
    }
  },

  clearSelection() {
    this.state.selected.clear();
    
    // Uncheck all checkboxes
    const selectAll = document.getElementById('sel-all');
    const rowCheckboxes = document.querySelectorAll('.row-sel');
    
    if (selectAll) {
      selectAll.checked = false;
      selectAll.indeterminate = false;
    }
    
    rowCheckboxes.forEach(checkbox => {
      checkbox.checked = false;
    });

    // Hide suppression panel
    const suppressPanel = document.getElementById('suppress-panel');
    if (suppressPanel) {
      suppressPanel.style.display = 'none';
    }

    this.updateUI();
  },

  updateUI() {
    const bulkBar = document.getElementById('bulk-bar');
    const bulkCount = document.getElementById('bulk-count');
    
    if (!bulkBar || !bulkCount) return;

    const selectedCount = this.state.selected.size;
    
    if (selectedCount > 0) {
      bulkBar.style.display = 'block';
      bulkCount.textContent = `${selectedCount} selected`;
      
      // Add visual selection state to rows
      this.updateRowSelectionStates();
    } else {
      bulkBar.style.display = 'none';
    }
  },

  updateRowSelectionStates() {
    const rows = document.querySelectorAll('.vuln-row');
    rows.forEach(row => {
      const checkbox = row.querySelector('.row-sel');
      if (checkbox) {
        const index = parseInt(checkbox.dataset.index);
        if (this.state.selected.has(index)) {
          row.classList.add('row--selected');
        } else {
          row.classList.remove('row--selected');
        }
      }
    });
  },

  buildPayload(action) {
    const indices = Array.from(this.state.selected).map(Number);
    const payload = {
      indices,
      action,
      filters: this.currentFilters()
    };

    // Add action-specific value
    switch (action) {
      case 'set_status':
        payload.value = document.getElementById('bulk-status')?.value || '';
        break;
      case 'set_owner':
        payload.value = document.getElementById('bulk-owner')?.value || '';
        break;
      case 'add_tag':
        payload.value = document.getElementById('bulk-tag')?.value || '';
        break;
      case 'remove_tag':
        payload.value = document.getElementById('bulk-tag')?.value || '';
        break;
      case 'suppress':
        const reason = document.getElementById('suppress-reason')?.value || '';
        const duration = document.getElementById('suppress-duration')?.value || '';
        const scope = document.getElementById('suppress-scope')?.value || 'this';
        
        if (!reason) {
          alert('Suppression reason is required');
          return null;
        }

        payload.value = {
          reason,
          scope
        };

        // Add until date if not permanent
        if (duration !== 'permanent') {
          const days = parseInt(duration.replace('d', ''));
          const until = new Date();
          until.setDate(until.getDate() + days);
          payload.value.until = until.toISOString();
        }
        break;
      case 'unsuppress':
        // No additional value needed
        break;
    }

    return JSON.stringify(payload);
  },

  currentFilters() {
    // Read current filter state from the page
    const filters = {};
    
    const statusFilter = document.getElementById('status-filter');
    if (statusFilter && statusFilter.value) {
      filters.status = statusFilter.value;
    }
    
    const hideSuppressed = document.getElementById('hide-suppressed');
    if (hideSuppressed) {
      filters.hide_suppressed = hideSuppressed.checked;
    }
    
    // Add any other existing filters here
    
    return filters;
  }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.VulnsBulk.init();
});
