## 2026-02-14 - Button Loading State & Error Handling
**Learning:** Users lack visibility into async operations on the "Calculate" button, leading to potential frustration or double-submission.
**Action:** Implemented a loading state (disabled + spinner) and a dedicated error message container with `role="alert"` for accessibility. This pattern should be standard for all async form submissions.
