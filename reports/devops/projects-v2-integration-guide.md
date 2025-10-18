# Projects v2 Integration - PAT Creation Guide

## Step 1: Create Fine-Grained Personal Access Token

### GitHub Settings Navigation
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"

### Token Configuration
- **Token name**: `dev-projects-v2-integration`
- **Expiration**: 90 days (recommended for security)
- **Resource owner**: Select the user/org that owns the Project board
- **Repository access**: Select "Selected repositories" → Choose this repository (`Juhertra/dev`)

### Required Permissions
```
Repository permissions:
├── Contents: Read
├── Issues: Read and write
├── Pull requests: Read and write
└── Projects: Read and write (Projects v2)
```

### Save Token
- Click "Generate token"
- **IMPORTANT**: Copy the token string immediately (it won't be shown again)

## Step 2: Get Projects v2 GraphQL ID

### Method 1: From GitHub UI
1. Navigate to your Projects v2 board
2. Look at the URL: `https://github.com/users/{username}/projects/{number}`
3. The GraphQL ID format is: `PVT_kwDO{base64-encoded-number}`

### Method 2: Using GitHub CLI
```bash
gh api graphql -f query='
{
  user(login: "Juhertra") {
    projectsV2(first: 10) {
      nodes {
        id
        title
        number
      }
    }
  }
}'
```

### Method 3: From Project Settings
1. Go to Project → Settings → General
2. The Project ID is shown in the URL or settings

## Step 3: Configure Repository Secrets

### Navigate to Secrets
1. Go to: https://github.com/Juhertra/dev/settings/secrets/actions
2. Click "New repository secret"

### Add PROJECTS_TOKEN
- **Name**: `PROJECTS_TOKEN`
- **Secret**: `<PAT from step 1>`
- Click "Add secret"

### Add PROJECTS_V2_ID
- **Name**: `PROJECTS_V2_ID`
- **Secret**: `<GraphQL ID from step 2>`
- Click "Add secret"

## Step 4: Verify Workflow Permissions

### Current Configuration
- **Default workflow permissions**: Read
- **Individual workflow permissions**: Explicitly set in `project-sync.yml`

### Required Permissions in Workflow
```yaml
permissions:
  contents: read
  issues: write
  pull-requests: write
  projects: write
```

## Step 5: Test Integration

### Test Project Sync
1. Create a test issue or PR
2. Verify it appears in the Projects v2 board
3. Check workflow runs successfully

### Verify Labels
- Issues/PRs should be automatically labeled
- Project sync should add items to the board

## Security Notes

### PAT Security
- Store PAT securely (password manager recommended)
- Set appropriate expiration (90 days)
- Use minimal required permissions
- Monitor token usage in GitHub settings

### Repository Security
- Secrets are encrypted at rest
- Only accessible to workflows with explicit permissions
- Audit trail available in Actions logs

## Troubleshooting

### Common Issues
1. **"Resource not accessible"**: Check PAT permissions and resource owner
2. **"Project not found"**: Verify PROJECTS_V2_ID format
3. **"Workflow permissions denied"**: Ensure workflow has explicit permissions

### Verification Commands
```bash
# Check secrets exist
gh api repos/Juhertra/dev/actions/secrets

# Test PAT permissions
gh api graphql -H "Authorization: token $PROJECTS_TOKEN" -f query='{ viewer { login } }'

# Verify project access
gh api graphql -H "Authorization: token $PROJECTS_TOKEN" -f query='{ node(id: "$PROJECTS_V2_ID") { ... on ProjectV2 { title } } }'
```

---
**Configuration Date**: October 16, 2025  
**DevOps Lead**: Hernan Trajtemberg  
**Status**: Ready for owner configuration
