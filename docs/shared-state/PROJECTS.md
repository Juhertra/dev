# SecFlow Project Board

## Project Information

- **Project Name**: SecFlow
- **Project URL**: https://github.com/users/Juhertra/projects/3
- **GraphQL Node ID**: `PVT_kwHOApaM0c4BF3jm` (redacted: `PVT_kwHOApaM0c4BF***`)
- **Owner**: Juhertra (User Project)
- **Project Number**: 3

## Required Fields

### Status Field (Required)
- **Field Type**: Single Select
- **Options**:
  - Todo
  - In Progress  
  - Blocked
  - Done

### Optional Fields (Recommended)
- **Priority**: Single Select (P0, P1, P2, P3)
- **Type**: Single Select (feat, bug, chore, docs, spike)

## Setup Instructions

1. **Add Status Field**: 
   - Open the project in GitHub UI
   - Click "+" to add a new field
   - Select "Single select" field type
   - Name it "Status"
   - Add options: Todo, In Progress, Blocked, Done

2. **Configure Repository Secret**:
   - Add `PROJECTS_V2_ID` secret to repository settings
   - Value: `PVT_kwHOApaM0c4BF3jm`

3. **Verify Integration**:
   - Test journal-to-issues workflow creates issues
   - Test project-status-sync workflow updates status
   - Verify auto-labeling works correctly

## Workflow Integration

- **Journal-to-Issues**: Automatically creates issues from handoff events
- **Project Status Sync**: Updates project status based on issue/PR labels
- **Auto-labeling**: Applies status labels based on file paths

## Security Notes

- The GraphQL Node ID is sensitive and should be kept secure
- Only repository administrators should have access to PROJECTS_V2_ID secret
- Project permissions are managed through GitHub's project access controls
