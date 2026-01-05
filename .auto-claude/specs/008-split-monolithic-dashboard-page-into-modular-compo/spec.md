# Split monolithic Dashboard page into modular components

## Overview

The file web/src/app/page.tsx has grown to 785 lines and contains 7 separate components (StatCard, ScoreRing, TrafficBar, IdeaRow, ScoreBreakdownPanel, TrafficLegend, Dashboard). This violates the single responsibility principle and makes the code difficult to maintain, test, and navigate.

## Rationale

Large monolithic files increase cognitive load, make code reviews harder, complicate unit testing, and often lead to merge conflicts. React best practices recommend keeping components small and focused on a single concern.

---
*This spec was created from ideation and is pending detailed specification.*
