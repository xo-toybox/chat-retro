# Self-Portrait v2 Evaluation

Comparison of `self-portrait.md` (v1) vs `self-portrait-v2.md` with epistemic guardrails.

## Background

Critiques of v1 output identified systematic blind spots:
- **Channel bias**: Analysis sees questions asked, not competencies exercised
- **Frame assumptions**: Defaults to certain mental models without acknowledging alternatives
- **Surface vs. cause**: Identifies patterns without modeling underlying drivers
- **Claim scope**: Implies "who you are" when data only supports "who you are when uncertain"

v2 added:
- Epistemic frame section (acknowledge data limitations upfront)
- Negative space per theme (what's absent given the topic)
- Frame statement before archetype (make interpretive lens explicit)
- Stratified surprises (high-confidence / tentative / invisible competencies)
- Methodology footer (data scope and limitations)

## Evaluation Criteria

| Criterion | Description |
|-----------|-------------|
| Epistemic honesty | Acknowledges what the data can't show |
| Frame awareness | States interpretive lens, acknowledges alternatives |
| Negative space | Surfaces what's NOT in the data |
| Confidence stratification | Separates strong signals from tentative patterns |
| Output quality | Not bloated, still insightful |

## Results

| Criterion | v1 | v2 | Verdict |
|-----------|-----|-----|---------|
| Epistemic honesty | Implied | Explicit frame: "uncertainty moments, not complete picture" | Improved |
| Frame awareness | None | States frame before archetype + alternative acknowledged | Improved |
| Negative space | Only in Surprises | Per-theme: "invisible competencies—you know them cold" | Improved |
| Confidence stratification | None | Surprises split into 3 tiers | Improved |
| Methodology note | None | Data scope + 5 explicit limitations | Improved |
| Output length | ~2500 words | ~2800 words (+12%) | Acceptable |

## Qualitative Notes

**Hits:**
- Epistemic frame reframes the entire analysis honestly
- Per-theme negative space produced novel insights
- Methodology note caught real limitations (browsing tool inflation, platform bias)
- Confidence stratification useful for distinguishing signal from noise

**Misses:**
- Alternative frame acknowledgment in Archetype feels slightly forced
- Dimensions section unchanged from what v1 would produce

## Verdict

v2 is measurably better on all criteria. Epistemic guardrails produced more honest, nuanced output without excessive bloat.

## Files

- Template: `src/chat_retro/template_prompts/self-portrait-v2.md`
- Output: `.chat-retro-runtime/outputs/self-portrait-v2.md`
- Baseline: `src/chat_retro/template_prompts/self-portrait.md`
