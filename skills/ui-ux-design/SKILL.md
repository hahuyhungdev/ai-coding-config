---
name: ui-ux-design
description: Complete guide for web and mobile UI/UX design. Combines visual aesthetics (anti-AI slop, typography, palettes, layouts) and technical specifications (WCAG contrast, touch targets, animation timings, layout constraints, skeletal loading, responsiveness).
---

# Unified UI/UX Design & Specification Guide

This skill guides the creation of distinctive, production-grade frontend interfaces that are both visually striking (avoiding generic "AI slop" aesthetics) and functionally correct (accessible, comfortable, and responsive).

## 1. Visual Aesthetics & Style (How it Looks)

Before writing UI/style code, commit to a bold aesthetic direction that matches the product context.

- **Tone & Style:** Avoid generic designs. Decide on a clear tone: brutally minimal, editorial/magazine-like, retro-futuristic, luxury/refined, playful, industrial, glassmorphism, or bento grid. Apply it consistently.
- **Typography:** Choose fonts that are beautiful and interesting. Opt for unexpected, characterful font choices. Pair a distinctive display/heading font with a clean, readable body font. Avoid default system fonts or overused choices like Arial or Roboto for custom brand elements.
- **Color & Contrast:** Select cohesive, tailored color palettes. Dominant colors with sharp, deliberate accents outperform timid, evenly-distributed palettes. Use CSS variables or Tailwind tokens for color management.
- **Backgrounds & Visual Depth:** Create atmosphere using gradient meshes, noise/grain textures, layered transparencies, geometric patterns, custom decorative borders, and shadows instead of solid background colors.
- **Anti-AI Slop:** Never use generic cliched visual schemes (e.g., standard bright purple/blue gradients on plain white backgrounds, cookie-cutter layouts, or raw emojis as icons). Always use clean, styled SVG icons (e.g., Heroicons, Lucide).

---

## 2. Technical UX & Ergonomics (How it Works)

All custom layouts and components must conform to standard UX ergonomics and accessibility specifications.

- **Accessibility (WCAG 2.1):**
  - **Color Contrast:** Keep foreground/background text contrast ratio at **4.5:1** minimum for normal text (3:1 for large text).
  - **Keyboard Navigation:** Support tab ordering that matches the visual layout. Interactive elements must display visible focus rings (2–4px focus outlines) and must not rely on hover alone.
  - **Screen Readers:** Use descriptive `alt` text for images and `aria-label` attributes on icon-only controls.
- **Touch & Interaction:**
  - **Touch Target Size:** Interactive targets must be at least **44×44px** (Apple HIG) / **48×48px** (Material Design).
  - **Spacing:** Minimum **8px** gap between adjacent touch targets to prevent accidental taps.
  - **Button Feedback:** Disable submit/action buttons during asynchronous operations and show a loading spinner or progress indicator (never leave a user guessing if a button registered).
- **Layout & Spacing System:**
  - **Spacing Scale:** Use a systematic spacing scale (e.g., 4px/8px increments).
  - **Desktop Width:** Use a consistent container max-width on desktop (e.g., `max-w-6xl` or `max-w-7xl`).
  - **No Horizontal Scroll:** Keep viewport scaling set to `width=device-width, initial-scale=1` (never disable zoom). Content must fit within the horizontal bounds of mobile viewports.
- **Motion & Animations:**
  - **Duration:** Keep micro-interactions between **150ms and 300ms**. Use ease-out for entering and ease-in for exiting elements.
  - **Performance:** Only animate `transform` and `opacity` to avoid triggering DOM reflows. Avoid animating `width`, `height`, `top`, or `left`.
  - **Purpose:** Animation must convey structural relationships (e.g. entering from bottom = modal/deeper, exiting upward = dismiss), not be purely decorative. Respect `prefers-reduced-motion`.
- **Loading & State Feedback:**
  - Use skeleton screens or shimmer placeholders instead of blocking spinners for asynchronous operations taking longer than 1 second to improve perceived performance.

---

## 3. Review Checklist

- Does the interface have a cohesive visual theme?
- Are all body text elements readable (minimum 16px on mobile to avoid iOS auto-zoom)?
- Do all clickable elements have `cursor-pointer` (for web) and visible focus rings?
- Are touch targets comfortable to tap on mobile viewports?
- Is there clear loading/disabled feedback for forms and buttons?
- Does the contrast ratio meet accessibility standards?
