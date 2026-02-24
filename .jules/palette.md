## 2024-05-21 - [Native Form Validation]
**Learning:** This project relies on vanilla HTML/CSS without a JS framework for form validation. The `:invalid` pseudo-class combined with HTML5 constraint attributes (`min`, `max`, `type`) provides immediate visual feedback without complex JS logic.
**Action:** Prioritize HTML5 constraint attributes and CSS `:invalid` styling over custom JS validation to maintain simplicity and accessibility.

## 2024-05-22 - [Contextual Unit Conversion]
**Learning:** In engineering domains like flight dynamics, users mentally toggle between systems (SI vs. Aviation). Providing real-time, approximate conversions (e.g., m/s → kts) directly within the label or helper text bridges this cognitive gap effectively.
**Action:** When designing for technical domains, identify primary vs. familiar units and offer non-intrusive conversion hints to reduce mental math load. Placing these hints within the `<label>` ensures screen readers announce the context immediately.
