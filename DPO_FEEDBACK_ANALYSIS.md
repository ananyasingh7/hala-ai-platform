# DPO Feedback Loop Analysis (HalaAI Platform UI)

Date: 2026-01-19

## Scope
This document summarizes the product and UI-side analysis for adding thumbs-up/down feedback, optional user corrections, and downstream alignment tuning for the HalaAI engine.

## Good
- Thumbs-down with a correction produces a clean preference pair.
- The UI can capture corrections inline with minimal friction.
- The sessions sidebar already maps well to feedback collection and replay.

## Bad / Risks
- Thumbs-up alone does not provide a rejected response for DPO.
- If you do not store full prompt context, the data will be noisy.
- Corrections can drift style unless you constrain tone or editing format.
- Small batches can cause regressions if trained too often.

## Constraints
- Only Mac Studio M4 is available for training.
- Current engine fine-tuning is SFT via MLX, not DPO.
- UI should remain lightweight and minimal.

## Options
1) **M4-only SFT (recommended now)**
   - Thumbs-down corrections become SFT examples.
   - Thumbs-up becomes optional SFT data (lower weight).
   - Nightly training only after data threshold.

2) **True DPO later**
   - Export preference pairs to a GPU-capable DPO trainer.
   - Import LoRA adapters back into HalaAI.

3) **Hybrid immediate biasing**
   - Inject corrected responses into memory for instant improvements.
   - Use training later when dataset size is sufficient.

## Proposed Solution (UI + workflow)
- Add thumbs-up/down to each assistant message.
- On thumbs-down, require a corrected response.
- Log:
  - prompt, assistant response, correction, system prompt,
  - session history window, tool/search context, adapter used.
- Provide a nightly job to export curated pairs.

## Recommended UI Details
- Keep the feedback controls unobtrusive (icons on assistant bubbles).
- Inline correction input when thumbs-down is selected.
- Optional: quick reason dropdown (fact, tone, safety, incomplete).

## Next Steps
- Add feedback endpoints in HalaAI.
- Extend UI to send feedback events.
- Build an export script and nightly schedule.
