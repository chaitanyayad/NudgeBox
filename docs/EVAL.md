# LLM Evaluation Results (Phase C)

## Before Hardening (Task 7 Baseline)
- **Accuracy:** 87.5%
- **Prompt Injection Resilience:** 100%
- **Latency:** ~5.6 seconds per email (cold start)
- **Why it failed:** The model classified a cancellation email ("We are canceling the recruiter call") as `False`, because the prompt strictly instructed it to only mark scheduled events as true.

## After Hardening (Task 8)
- **Accuracy:** 100%
- **Prompt Injection Resilience:** 100%
- **Latency:** ~1.8 seconds per email (warm start cache)

### What Changed?
1. **Instruction Update:** Explicitly added cancellations and reschedules as valid events.
2. **Few-Shot Update:** Added an explicit cancellation example to the system prompt.
3. **Confidence Gate (Defense in Depth):** Added a post-processing validation step in Python. If the model's confidence is `< 0.6`, the system flags `needs_review = True`.
4. **Domain Extraction:** Added post-processing to safely extract the domain from the event link to prevent parsing errors.
