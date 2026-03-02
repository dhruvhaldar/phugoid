## 2024-05-21 - [Native Form Validation]
**Learning:** This project relies on vanilla HTML/CSS without a JS framework for form validation. The `:invalid` pseudo-class combined with HTML5 constraint attributes (`min`, `max`, `type`) provides immediate visual feedback without complex JS logic.
**Action:** Prioritize HTML5 constraint attributes and CSS `:invalid` styling over custom JS validation to maintain simplicity and accessibility.

## 2024-05-22 - [Contextual Unit Conversion]
**Learning:** In engineering domains like flight dynamics, users mentally toggle between systems (SI vs. Aviation). Providing real-time, approximate conversions (e.g., m/s → kts) directly within the label or helper text bridges this cognitive gap effectively.
**Action:** When designing for technical domains, identify primary vs. familiar units and offer non-intrusive conversion hints to reduce mental math load. Placing these hints within the `<label>` ensures screen readers announce the context immediately.

## 2026-03-01 - [Skip Links & Keyboard Focus in Neubrutalism]
**Learning:** Custom brutalist UI themes often unintentionally disable native focus rings by overriding browser defaults without providing an alternative. Adding explicit `:focus-visible` styling (using theme-consistent thick borders and inset shadows) is crucial for links, especially utility links like a "Skip to main content" link, to maintain keyboard accessibility without breaking the aesthetic.
**Action:** Always verify keyboard navigation (Tab order) on interactive elements. When building "Skip to content" links, position them absolutely off-screen (`top: -100px`) and move them on-screen dynamically during `:focus`. Apply a global `a:focus-visible` rule using existing design tokens for a consistent focus ring.

## 2026-03-05 - [Enhanced CSS-only Form Validation Feedback]
**Learning:** Using CSS `:invalid` in combination with sibling combinators (`~`) allows for rich, accessible inline validation feedback (e.g., coloring help text red and adding warning icons) entirely without JavaScript, keeping the implementation simple and lightweight.
**Action:** When relying on native HTML validation, extend visual cues beyond just the input border by using `input:invalid ~ .help-text` to ensure the error context itself also draws attention.
