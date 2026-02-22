# Palette's Journal

## 2025-10-26 - Empty State Pattern
**Learning:** Users are often overwhelmed by empty dashes or "0" values on initial load. Replacing these with a dedicated "Empty State" container that provides a clear call-to-action ("Ready for Analysis") significantly improves the initial impression and guides the user.
**Action:** When designing data-heavy views, always consider the "zero data" state. Hide result containers until data is available, and use the space to educate or guide the user.

## 2026-02-17 - Clipboard Interaction Feedback
**Learning:** For actions like "Copy to Clipboard", immediate visual confirmation (changing icon/text to "Copied!") is crucial because the action is invisible. Users feel uncertain without this explicit feedback.
**Action:** Always pair clipboard actions with a temporary state change (e.g., green checkmark, "Copied!" text) that reverts automatically after a short delay (2s).
