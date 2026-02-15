## 2026-02-14 - Button Loading State & Error Handling
**Learning:** Users lack visibility into async operations on the "Calculate" button, leading to potential frustration or double-submission.
**Action:** Implemented a loading state (disabled + spinner) and a dedicated error message container with `role="alert"` for accessibility. This pattern should be standard for all async form submissions.

## 2026-02-15 - HTML Step Attribute & Validation
**Learning:** Using `step="100"` for UI convenience (spinner increments) inadvertently blocks valid inputs like "1524" due to native browser validation.
**Action:** Use `step="any"` for physics inputs where precise values are allowed, even if large steps are convenient for spinners.
