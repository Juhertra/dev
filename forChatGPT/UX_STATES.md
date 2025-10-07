# UX States - Drawer Components

## Preview Drawer States

### Required Context Props
```javascript
const previewDrawerProps = {
  endpoint: {
    method: 'GET',
    url: 'https://api.example.com/users',
    path: '/users'
  },
  dossier: {
    total_runs: 3,
    latest_run: {
      run_id: 'run-123',
      findings: 2,
      worst: 'medium',
      finished_at: '2024-01-15T10:45:00Z'
    },
    history: [/* run history array */]
  },
  coverage: {
    last_tested: '2024-01-15T10:45:00Z',
    test_frequency: 'daily',
    risk_score: 6.5
  }
};
```

### Loading State
```html
<div class="drawer loading">
  <header>
    <span class="method skeleton">GET</span>
    <span class="url skeleton">Loading endpoint...</span>
  </header>
  <div class="drawer-content">
    <div class="skeleton-section">
      <div class="skeleton-line"></div>
      <div class="skeleton-line short"></div>
    </div>
    <div class="skeleton-section">
      <div class="skeleton-line"></div>
      <div class="skeleton-line"></div>
      <div class="skeleton-line short"></div>
    </div>
  </div>
</div>
```

### Empty State (No Test History)
```html
<div class="drawer empty-state">
  <header>
    <span class="method GET">GET</span>
    <span class="url">https://api.example.com/users</span>
  </header>
  <div class="drawer-content">
    <div class="empty-state-content">
      <div class="empty-icon">🔍</div>
      <h3>No Test History</h3>
      <p>This endpoint hasn't been tested yet.</p>
      <button class="btn-primary" onclick="startScan()">
        Run Security Scan
      </button>
    </div>
  </div>
</div>
```

### Success State (With Data)
```html
<div class="drawer success">
  <header>
    <span class="method GET">GET</span>
    <span class="url">https://api.example.com/users</span>
    <span class="status-indicator success">Tested</span>
  </header>
  <div class="drawer-content">
    <div class="coverage-stats">
      <div class="stat">
        <span class="label">Last Tested</span>
        <span class="value">2 hours ago</span>
      </div>
      <div class="stat">
        <span class="label">Findings</span>
        <span class="value critical">2</span>
      </div>
      <div class="stat">
        <span class="label">Risk Score</span>
        <span class="value medium">6.5/10</span>
      </div>
    </div>
    
    <div class="test-history">
      <h3>Recent Tests</h3>
      <div class="run-item">
        <span class="run-id">run-20240115-1045</span>
        <span class="timestamp">2 hours ago</span>
        <span class="findings-count critical">2 findings</span>
      </div>
    </div>
    
    <div class="actions">
      <button class="btn-secondary" onclick="viewRuns()">
        View All Runs
      </button>
      <button class="btn-primary" onclick="startScan()">
        Run New Scan
      </button>
    </div>
  </div>
</div>
```

### Error State
```html
<div class="drawer error">
  <header>
    <span class="method GET">GET</span>
    <span class="url">https://api.example.com/users</span>
    <span class="status-indicator error">Error</span>
  </header>
  <div class="drawer-content">
    <div class="error-content">
      <div class="error-icon">⚠️</div>
      <h3>Unable to Load Endpoint Data</h3>
      <p class="error-message">Dossier file corrupted or missing</p>
      <div class="error-details">
        <code>GET_https_api_example_com_users.json</code>
      </div>
      <button class="btn-primary" onclick="retryLoad()">
        Retry
      </button>
    </div>
  </div>
</div>
```

## Runs Drawer States

### Required Context Props
```javascript
const runsDrawerProps = {
  endpoint: {
    method: 'GET',
    url: 'https://api.example.com/users',
    canonical_key: 'GET https://api.example.com/users'
  },
  runs: [
    {
      run_id: 'run-123',
      started_at: '2024-01-15T10:30:00Z',
      finished_at: '2024-01-15T10:45:00Z',
      findings: 2,
      worst: 'medium',
      templates_count: 8,
      duration_ms: 900000
    }
  ],
  total_runs: 3
};
```

### Loading State
```html
<div class="drawer loading">
  <header>
    <h2>Run History for GET https://api.example.com/users</h2>
  </header>
  <div class="drawer-content">
    <div class="runs-list">
      <div class="run-item skeleton">
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
        <div class="skeleton-line short"></div>
      </div>
      <div class="run-item skeleton">
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
        <div class="skeleton-line short"></div>
      </div>
    </div>
  </div>
</div>
```

### Empty State (No Runs)
```html
<div class="drawer empty-state">
  <header>
    <h2>Run History for GET https://api.example.com/users</h2>
  </header>
  <div class="drawer-content">
    <div class="empty-state-content">
      <div class="empty-icon">📊</div>
      <h3>No Test Runs</h3>
      <p>This endpoint hasn't been scanned yet.</p>
      <button class="btn-primary" onclick="startScan()">
        Start First Scan
      </button>
    </div>
  </div>
</div>
```

### Success State (With Runs)
```html
<div class="drawer success">
  <header>
    <h2>Run History for GET https://api.example.com/users</h2>
    <span class="run-count">3 runs</span>
  </header>
  <div class="drawer-content">
    <div class="runs-list">
      <div class="run-item completed">
        <div class="run-meta">
          <span class="run-id">run-20240115-1045</span>
          <span class="timestamp">2 hours ago</span>
          <span class="status completed">Completed</span>
        </div>
        <div class="run-stats">
          <span class="findings critical">2 findings</span>
          <span class="templates">8 templates</span>
          <span class="duration">15 min</span>
        </div>
        <div class="run-actions">
          <button class="btn-small" onclick="viewDetails('run-20240115-1045')">
            View Details
          </button>
          <button class="btn-small" onclick="copyArtifact('run-20240115-1045')">
            Copy cURL
          </button>
        </div>
      </div>
      
      <div class="run-item completed">
        <div class="run-meta">
          <span class="run-id">run-20240114-1430</span>
          <span class="timestamp">1 day ago</span>
          <span class="status completed">Completed</span>
        </div>
        <div class="run-stats">
          <span class="findings success">0 findings</span>
          <span class="templates">5 templates</span>
          <span class="duration">15 min</span>
        </div>
        <div class="run-actions">
          <button class="btn-small" onclick="viewDetails('run-20240114-1430')">
            View Details
          </button>
        </div>
      </div>
    </div>
    
    <div class="drawer-actions">
      <button class="btn-primary" onclick="startScan()">
        Run New Scan
      </button>
    </div>
  </div>
</div>
```

### Error State
```html
<div class="drawer error">
  <header>
    <h2>Run History for GET https://api.example.com/users</h2>
  </header>
  <div class="drawer-content">
    <div class="error-content">
      <div class="error-icon">⚠️</div>
      <h3>Unable to Load Run History</h3>
      <p class="error-message">Endpoint not found in dossiers</p>
      <div class="error-details">
        <code>GET https://api.example.com/users</code>
      </div>
      <button class="btn-primary" onclick="retryLoad()">
        Retry
      </button>
    </div>
  </div>
</div>
```

## CSS Skeleton Loading

### Skeleton Animation (`static/skeleton.css`)
```css
.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

.skeleton-line {
  height: 1rem;
  margin: 0.5rem 0;
  border-radius: 4px;
}

.skeleton-line.short {
  width: 60%;
}

.skeleton-section {
  margin: 1rem 0;
}

@keyframes loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Loading states */
.drawer.loading .skeleton-line {
  background: #f0f0f0;
  color: transparent;
}

.drawer.loading .skeleton-line::before {
  content: "Loading...";
  color: #999;
}
```

## Error Message Templates

### Common Error Messages
```javascript
const ERROR_MESSAGES = {
  DOSSIER_NOT_FOUND: {
    title: "No Test History Found",
    message: "This endpoint hasn't been tested yet.",
    action: "Start First Scan",
    icon: "🔍"
  },
  DOSSIER_CORRUPTED: {
    title: "Data Corruption Detected",
    message: "Endpoint data file is corrupted or invalid.",
    action: "Reset Data",
    icon: "⚠️"
  },
  NETWORK_ERROR: {
    title: "Connection Failed",
    message: "Unable to connect to the server.",
    action: "Retry",
    icon: "🌐"
  },
  PERMISSION_DENIED: {
    title: "Access Denied",
    message: "You don't have permission to view this data.",
    action: "Request Access",
    icon: "🔒"
  },
  TIMEOUT: {
    title: "Request Timeout",
    message: "The request took too long to complete.",
    action: "Retry",
    icon: "⏱️"
  }
};

function showErrorState(errorType, details = {}) {
  const error = ERROR_MESSAGES[errorType];
  return `
    <div class="error-content">
      <div class="error-icon">${error.icon}</div>
      <h3>${error.title}</h3>
      <p class="error-message">${error.message}</p>
      ${details.code ? `<div class="error-details"><code>${details.code}</code></div>` : ''}
      <button class="btn-primary" onclick="${error.action.toLowerCase().replace(' ', '')}()">
        ${error.action}
      </button>
    </div>
  `;
}
```

## State Management JavaScript

### Drawer State Manager (`static/drawer_states.js`)
```javascript
class DrawerStateManager {
  constructor() {
    this.states = new Map();
  }
  
  setState(drawerId, state, data = {}) {
    this.states.set(drawerId, { state, data, timestamp: Date.now() });
    this.render(drawerId, state, data);
  }
  
  getState(drawerId) {
    return this.states.get(drawerId);
  }
  
  render(drawerId, state, data) {
    const drawer = document.getElementById(drawerId);
    if (!drawer) return;
    
    // Remove existing state classes
    drawer.className = drawer.className.replace(/\b(loading|success|error|empty-state)\b/g, '');
    
    // Add new state class
    drawer.classList.add(state);
    
    // Update content based on state
    switch (state) {
      case 'loading':
        drawer.innerHTML = this.renderLoadingState(data);
        break;
      case 'success':
        drawer.innerHTML = this.renderSuccessState(data);
        break;
      case 'error':
        drawer.innerHTML = this.renderErrorState(data);
        break;
      case 'empty-state':
        drawer.innerHTML = this.renderEmptyState(data);
        break;
    }
  }
  
  renderLoadingState(data) {
    return `
      <header>
        <span class="method skeleton">${data.method || 'GET'}</span>
        <span class="url skeleton">Loading...</span>
      </header>
      <div class="drawer-content">
        <div class="skeleton-section">
          <div class="skeleton-line"></div>
          <div class="skeleton-line short"></div>
        </div>
      </div>
    `;
  }
  
  renderSuccessState(data) {
    // Implementation based on drawer type
    return this.renderPreviewSuccess(data) || this.renderRunsSuccess(data);
  }
  
  renderErrorState(data) {
    return showErrorState(data.errorType, data.details);
  }
  
  renderEmptyState(data) {
    return `
      <div class="empty-state-content">
        <div class="empty-icon">${data.icon || '📊'}</div>
        <h3>${data.title || 'No Data'}</h3>
        <p>${data.message || 'No data available.'}</p>
        ${data.action ? `<button class="btn-primary" onclick="${data.action}()">${data.actionText}</button>` : ''}
      </div>
    `;
  }
}

// Global instance
window.drawerStateManager = new DrawerStateManager();
```
