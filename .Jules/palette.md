# Palette's Journal

## 2025-10-26 - Empty State Pattern
**Learning:** Users are often overwhelmed by empty dashes or "0" values on initial load. Replacing these with a dedicated "Empty State" container that provides a clear call-to-action ("Ready for Analysis") significantly improves the initial impression and guides the user.
**Action:** When designing data-heavy views, always consider the "zero data" state. Hide result containers until data is available, and use the space to educate or guide the user.

## 2026-02-17 - Clipboard Interaction Feedback
**Learning:** For actions like "Copy to Clipboard", immediate visual confirmation (changing icon/text to "Copied!") is crucial because the action is invisible. Users feel uncertain without this explicit feedback.
**Action:** Always pair clipboard actions with a temporary state change (e.g., green checkmark, "Copied!" text) that reverts automatically after a short delay (2s).

## 2026-05-20 - Focus Management after Async Actions
**Learning:** Simply unhiding content is insufficient for accessibility. Screen reader users may not realize new content has appeared, and keyboard users may have to tab extensively to reach it.
**Action:** Use `element.focus({ preventScroll: true })` combined with `scrollIntoView` to guide both visual and assistive technology focus to the new content immediately.

## 2026-10-27 - Power User Shortcuts
**Learning:** Adding keyboard shortcuts (like `Cmd+Enter` for form submission) significantly improves the workflow for power users, but they are often undiscoverable.
**Action:** Always surface keyboard shortcuts visually (e.g., using a subtle badge or tooltip) and programmatically via `aria-keyshortcuts` to ensure discoverability and accessibility.

## 2026-11-20 - Stale Results Visualization
**Learning:** When input parameters are modified after a successful calculation, leaving the old results fully visible can lead to dangerous misinterpretation. Users assume the visible data reflects the current configuration.
**Action:** Implement a "Stale State" by visually dimming outdated results (opacity/grayscale) and adding a clear warning label ("Recalculate"). This forces the user to acknowledge the discrepancy before proceeding.

## 2026-11-21 - Button State and Rich Content
**Learning:** Overwriting a button's `textContent` to show a loading state (e.g., "Calculating...") permanently destroys any inner HTML structure, such as keyboard shortcut hints or icons, making them disappear when the original text is restored.
**Action:** When updating a button's state that contains child elements, use `innerHTML` to save and restore the content, rather than `textContent`, to preserve embedded UX enhancements.

## 2026-11-22 - Visual Feedback for Auto-Filled Forms
**Learning:** When inputs are automatically filled (like via a "Preset" button), users often fail to notice exactly which values changed, especially in complex forms. This lack of immediate feedback can cause uncertainty.
**Action:** Always provide brief, non-intrusive visual feedback (like a quick background color flash via CSS keyframes) when programmatically updating input values. This draws the user's eye directly to the change without requiring manual interaction.

## 2026-11-23 - High-Luminance Accent Colors
**Learning:** When using bright, high-luminance accent colors (like cyan or yellow) as backgrounds for interactive elements, using white text (#fff) causes severe contrast failures (often below 2:1).
**Action:** Always verify contrast ratios for new design tokens. Use dark text (e.g., `var(--text-color)`) on high-luminance backgrounds to maintain readability and meet accessibility standards.

## 2026-03-10 - Custom Checkbox Input Accessibility
**Learning:** Custom UI toggle switches (often implemented as a hidden `input[type="checkbox"]` with adjacent styled `span` elements) inherently lose browser-default focus indicators. Furthermore, visually adjacent text (`span`s) does not automatically serve as an accessible name for screen readers, unlike a properly associated `label`.
**Action:** Always add explicit `:focus-visible` styles to the visual target (e.g., `.toggle:focus-visible + .slider`) when hiding the native input. Additionally, ensure the input has an explicit `aria-label` and consider hiding visually adjacent pseudo-labels with `aria-hidden="true"` to prevent confusing, redundant screen reader announcements.

## 2026-03-23 - State Desync on Custom Toggle Switches
**Learning:** During long-running async operations (like API calls), naturally disabling native inputs (`input:disabled`) is insufficient if custom UI controls (like pseudo-labels acting as toggle switches) remain interactive. This leads to state desynchronization mid-calculation.
**Action:** Always manually manage the disabled state (`aria-disabled`) and apply corresponding JavaScript interaction guards (e.g., early returns on click/keydown) for all non-native custom interactive elements when forms are submitted.

## 2026-11-24 - External Link Predictability
**Learning:** Text links that open in a new tab (`target="_blank"`) without visual or screen reader indication cause user disorientation, as assistive technology users unexpectedly find their back button disabled.
**Action:** Always append visually hidden screen reader text like "(opens in a new tab)" and a visual indicator (like an arrow icon `↗`) to external links to set clear expectations before interaction.

## 2026-11-25 - Input Focus Indicators
**Learning:** Removing default browser outlines without replacing them with a high-contrast alternative causes severe accessibility issues for keyboard users, especially on low-contrast backgrounds.
**Action:** Always provide a strong, high-contrast focus indicator (e.g., a double ring using background and text colors) for text inputs when hiding the native outline.

## 2026-11-26 - JavaScript-Triggered Animation and Reduced Motion
**Learning:** Adding `@media (prefers-reduced-motion: reduce)` to CSS only disables purely CSS-based animations and scroll behaviors. If JavaScript imperatively triggers a behavior like `element.scrollIntoView({ behavior: 'smooth' })`, it bypasses the CSS rule completely, causing unexpected motion for users who explicitly disabled it.
**Action:** Always wrap imperative JavaScript animations and scroll behaviors in a `window.matchMedia('(prefers-reduced-motion: reduce)').matches` check to conditionally apply smooth transitions only when permitted by the user.
## 2026-04-10 - Screen Reader Announcements for Implicit State Changes\n**Learning:** When users trigger UI elements that implicitly update multiple form fields simultaneously (like clicking a Flight Condition Preset), screen reader users are often left unaware of the form updates. Adding a dedicated ARIA live region (like `status-region`) and programmatically announcing the state change (e.g., "Cruise preset applied") significantly improves context and accessibility for non-visual users.\n**Action:** Always implement programmatic ARIA live region announcements whenever a single user interaction causes cascading or batch updates to form fields or application state that aren't inherently self-describing.
