# Mermaid Diagram Style Guide

<!-- Include this init header at the top of each diagram for consistent styling -->

## 🎨 House Style

Use this initialization block at the start of every Mermaid diagram for consistent styling:

```mermaid
%%{init: {
  "theme": "neutral",
  "themeVariables": {
    "fontFamily": "Inter, ui-sans-serif, system-ui",
    "primaryColor": "#0ea5e9",
    "primaryBorderColor": "#0ea5e9",
    "primaryTextColor": "#0b1220",
    "lineColor": "#6b7280",
    "secondaryColor": "#f1f5f9",
    "tertiaryColor": "#e2e8f0"
  }
}}%%
```

## 📋 Usage Guidelines

### Diagram Types
- **Flowcharts**: Use `flowchart TD` (top-down) for processes, `flowchart LR` (left-right) for pipelines
- **Sequence Diagrams**: Use `sequenceDiagram` for runtime interactions
- **Class Diagrams**: Use `classDiagram` for data models and relationships
- **State Diagrams**: Use `stateDiagram-v2` for lifecycle flows

### Styling Rules
- **Colors**: Minimal use; rely on Material theme defaults
- **IDs**: Use semantic names (e.g., `WebAPI`, `Worker`, `findings-engine`)
- **Labels**: Keep concise but descriptive
- **Direction**: Prefer top-down for hierarchical flows, left-right for sequential processes

### Custom Classes
Define custom styling classes sparingly:
```text
classDef box stroke:#0ea5e9,stroke-width:2px,fill:#f8fafc,color:#0b1220;
classDef tool fill:#eef,stroke:#88f,stroke-width:1px;
classDef role fill:#e2e8f0,stroke:#0ea5e9,stroke-width:2px;
```

## 🔧 Integration

Each diagram should include the init block at the top since Mermaid doesn't support external imports. Copy the init block from this file to maintain consistency across all diagrams.
```
```
