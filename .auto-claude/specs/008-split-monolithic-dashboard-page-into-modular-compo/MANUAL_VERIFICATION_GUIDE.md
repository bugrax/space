# Manual Verification Guide - Dashboard Component Refactoring

**Subtask:** 5.2 - Visual Verification
**Date:** 2026-01-05
**Status:** Ready for Manual Testing

---

## Overview

All dashboard components have been successfully extracted from the monolithic `page.tsx` file (reduced from 785 to 340 lines). This guide provides a comprehensive checklist for manual verification to ensure all components render correctly with proper styling and functionality.

## Prerequisites

Before starting verification:
- [ ] Backend API server is running (if required)
- [ ] Environment variables are configured (check `.env.local` if needed)
- [ ] Dependencies are installed (`npm install` in the `web/` directory)

## Starting the Dev Server

```bash
cd web
npm run dev
```

The application should start on `http://localhost:3000` (or next available port).

---

## Verification Checklist

### 1. Initial Page Load

- [ ] **Dashboard page loads without errors**
  - Open browser DevTools Console (F12)
  - Navigate to `http://localhost:3000`
  - Verify no console errors or warnings
  - Check Network tab for failed requests

- [ ] **Page renders within reasonable time**
  - Page should load within 2-3 seconds
  - Loading states should display appropriately

### 2. Stat Cards (Top Section)

Verify all four stat cards in the top row display correctly:

- [ ] **Ideas Analyzed Card**
  - Shows total number of ideas
  - Displays "+X this week" change indicator
  - Flask icon visible with purple background
  - Card has subtle glow effect

- [ ] **Avg. Score Card**
  - Shows average score value
  - Displays change indicator
  - Trophy icon visible with blue background
  - Proper styling and layout

- [ ] **High Potential Card**
  - Shows count of high potential ideas
  - Displays change indicator
  - Zap icon visible with yellow background
  - Proper styling and layout

- [ ] **Recently Added Card**
  - Shows count of recent ideas
  - Displays time period (e.g., "Last 7 days")
  - Clock icon visible with green background
  - Proper styling and layout

### 3. Ideas Table

Verify the main ideas table displays correctly:

- [ ] **Table Header**
  - All column headers visible: Product/URL, Category, MRR, Score, Traffic, Author, Date, Actions
  - Headers are properly styled
  - Text alignment is correct

- [ ] **Table Rows (IdeaRow Components)**
  - All ideas are listed in rows
  - Each row displays complete information
  - Rows have hover effects (subtle highlighting)
  - Selected row has distinct styling (background color change)

### 4. Score Rings (ScoreRing Component)

Verify score visualization in the Score column:

- [ ] **Ring Color Coding**
  - High scores (≥75): Green ring (#00FF88)
  - Medium-high scores (≥50): Blue ring (#00D4FF)
  - Medium-low scores (≥30): Yellow ring (#FFB800)
  - Low scores (<30): Red ring (#FF4757)

- [ ] **Ring Display**
  - SVG circles render properly
  - Score number centered in ring
  - Ring fills proportionally to score
  - Smooth rendering without pixelation

### 5. Traffic Bars (TrafficBar Component)

Verify traffic source visualization in the Traffic column:

- [ ] **Bar Segments**
  - Organic traffic: Green segment
  - Paid traffic: Blue segment
  - Social traffic: Purple segment
  - Direct traffic: Yellow segment

- [ ] **Bar Behavior**
  - Segments are proportionally sized based on percentage
  - Segments have rounded corners
  - Tooltips show on hover (source name and percentage)
  - "N/A" displays for ideas without traffic data

### 6. Traffic Legend (TrafficLegend Component)

Below the ideas table:

- [ ] **Legend Display**
  - Horizontal layout with four items
  - Each item shows colored dot and label
  - Colors match TrafficBar segments:
    - Organic: Green dot
    - Paid: Blue dot
    - Social: Purple dot
    - Direct: Yellow dot
  - Proper spacing and alignment

### 7. Interactive Elements

#### Row Selection
- [ ] **Click on any idea row**
  - Row background changes to indicate selection
  - Score breakdown panel appears on the right side
  - Only one row selected at a time
  - Clicking same row again deselects it

#### External Links
- [ ] **Globe icon (Product URL)**
  - Opens product website in new tab
  - Clicking doesn't select the row
  - Icon has hover effect

- [ ] **Twitter icon (Tweet)**
  - Opens tweet link in new tab
  - Clicking doesn't select the row
  - Icon has hover effect

#### Favorite Button
- [ ] **Star icon**
  - Clicking toggles favorite status
  - Filled star when favorited
  - Outline star when not favorited
  - Clicking doesn't select the row
  - Yellow color (#FFB800) when favorited

### 8. Score Breakdown Panel (ScoreBreakdownPanel Component)

When an idea row is selected:

- [ ] **Panel Appears**
  - Slides in from the right side
  - Smooth animation
  - Doesn't cause layout shift in main content

- [ ] **Panel Header**
  - "Score Breakdown" title visible
  - Close button (X) in top-right corner
  - Close button closes the panel

- [ ] **Overall Score Section**
  - Large ScoreRing displays overall score
  - "OVERALL SCORE" label
  - Score number centered in ring
  - Ring color matches score value

- [ ] **Score Components**
  - Four score breakdown bars:
    - Traction Score (with bar graph)
    - Growth Score (with bar graph)
    - Traffic Score (with bar graph)
    - Simplicity Score (with bar graph)
  - Each bar shows percentage/score
  - Bars are color-coded
  - Bar width represents the score value

- [ ] **Engagement Metrics**
  - Impressions count with Eye icon
  - Retweets count with Repeat icon
  - Replies count with MessageCircle icon
  - Likes count with Heart icon
  - All icons properly styled

### 9. Search and Filter (If Implemented)

If search/filter functionality exists in the Dashboard component:

- [ ] **Search Input**
  - Search field visible
  - Can type search queries
  - Table filters results in real-time
  - Clearing search shows all results

- [ ] **Filter Controls**
  - Filter buttons/dropdowns visible
  - Filters work correctly
  - Can combine multiple filters
  - Clear filter button works

### 10. Responsive Behavior

Test at different screen sizes:

- [ ] **Desktop (>1024px)**
  - All components visible and properly spaced
  - Score breakdown panel doesn't overlap main content
  - Table columns all visible

- [ ] **Tablet (768px-1024px)**
  - Layout adjusts appropriately
  - Components remain readable
  - No horizontal scrolling issues

- [ ] **Mobile (<768px)**
  - Components stack/reflow appropriately
  - Touch targets are adequate size
  - Panel may overlay main content (acceptable)

### 11. Data Loading States

- [ ] **Initial Load**
  - Loading indicator shows while fetching data
  - No flash of empty content
  - Smooth transition to loaded state

- [ ] **Empty State**
  - If no data, appropriate message displays
  - No broken UI elements

- [ ] **Error State**
  - If API fails, error message displays
  - UI doesn't break

---

## Common Issues to Check For

### Visual Issues
- ❌ Components not rendering
- ❌ Missing styles (plain HTML appearance)
- ❌ Broken layouts or overlapping elements
- ❌ Icons not displaying
- ❌ Wrong colors or color schemes
- ❌ Text overflow or truncation issues
- ❌ Misaligned elements

### Functional Issues
- ❌ Clicking actions selects row when it shouldn't
- ❌ Unable to select rows
- ❌ Panel doesn't open on row selection
- ❌ Panel doesn't close
- ❌ Links don't open in new tabs
- ❌ Favorite toggle doesn't work
- ❌ Data not loading from API

### Console Errors
- ❌ TypeScript errors
- ❌ React hydration errors
- ❌ Import/module resolution errors
- ❌ Missing component prop warnings
- ❌ Key prop warnings in lists

---

## Expected Behavior Summary

After the refactoring:
1. **Functionality is identical** to the previous monolithic version
2. **All visual styling is preserved** (components use the same CSS module)
3. **Performance is same or better** (no performance regressions)
4. **No new console warnings or errors**
5. **All interactive elements work as expected**

---

## Troubleshooting

If you encounter issues:

1. **Check Browser Console** for error messages
2. **Verify imports** - ensure all @ path aliases resolve correctly
3. **Check CSS Module** - ensure `page.module.css` is still in place
4. **Clear Next.js cache** - delete `.next` folder and rebuild
5. **Check environment variables** - ensure API_BASE_URL is set if needed
6. **Review recent commits** - check git log for changes

---

## Reporting Issues

If any verification item fails, document:
- [ ] What failed (be specific)
- [ ] Steps to reproduce
- [ ] Browser/device being used
- [ ] Console error messages (if any)
- [ ] Screenshots (if visual issue)

---

## Sign-Off

Once all verification items pass:

- [ ] All acceptance criteria met
- [ ] No console errors or warnings
- [ ] All components render with proper styling
- [ ] All interactive elements functional
- [ ] Ready to mark subtask 5.2 as completed

**Verified by:** _________________
**Date:** _________________
**Notes:** _________________
