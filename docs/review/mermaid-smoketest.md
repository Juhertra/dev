---
title: "Mermaid Smoketest"
author: "SecFlow Documentation Team"
version: "1.0"
date: "2025-10-08"
---

# Mermaid Smoketest

This page tests that Mermaid diagrams are rendering correctly using the superfences + local Mermaid approach.

## 🧪 Test Diagram

```mermaid
flowchart LR
  A[Start] --> B[Process]
  B --> C[End]
```

## ✅ Expected Result

You should see a flowchart diagram above with three boxes connected by arrows.

## 🔄 Sequence Diagram Test

```mermaid
sequenceDiagram
    participant A as Alice
    participant B as Bob
    A->>B: Hello Bob, how are you?
    B-->>A: Great!
    A-)B: See you later!
```

## 📊 Class Diagram Test

```mermaid
classDiagram
    class Animal {
        +String name
        +int age
        +makeSound()
    }
    class Dog {
        +String breed
        +bark()
    }
    Animal <|-- Dog
```

## 🎯 State Diagram Test

```mermaid
stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]
```

## 📈 Expected Results

All four diagrams above should render as interactive Mermaid diagrams, not as code blocks.
```