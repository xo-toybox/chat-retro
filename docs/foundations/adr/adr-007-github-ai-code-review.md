# ADR-007: AI Code Review Tool Selection

## Status

**Proposed**

## Date

2025-12-28

## Context

Solo dev, want AI code review as a second pair of eyes. Maintain some OSS repos so free tier matters.

I evaluated the following options:

| Tool | Pricing Model | Cost | Architecture |
|------|---------------|------|--------------|
| **CodeRabbit** | Per-seat SaaS | $24-30/dev/month (free for OSS) | GitHub App, hosted |
| **Greptile** | Per-seat SaaS | $30/dev/month (free for OSS) | GitHub App, hosted |
| **OpenAI Codex** | Subscription-bundled | Included in ChatGPT Plus/Pro ($20-200/mo) | GitHub App, credits-based |
| **Claude Code Action** | BYOK (API usage) | ~$3-15/M tokens | GitHub Action, self-hosted runner |
| **OpenHands** | Open-source + BYOK | Free + LLM costs | GitHub Action, self-hosted |
| **GitHub Copilot Code Review** | Per-seat SaaS | Included in Copilot Pro ($10/mo) | Native GitHub integration |
| **Graphite Diamond** | Per-seat SaaS | $15-20/month | Bundled with Graphite |
| **Cursor Bugbot** | Per-seat SaaS | $40/user/month | Cursor IDE integration |
| **Amazon CodeGuru Reviewer** | Usage-based | ~$0.75/100 lines scanned | AWS-native |

### Key Differentiators

**Free for OSS (CodeRabbit, Greptile, OpenHands)**
- Great for public repos and open-source contributions
- Paid upgrade only needed for private repos

**Bundled with Existing Subscriptions (Codex, Copilot)**
- If already paying for ChatGPT Plus/Pro or Copilot, code review may be included
- No incremental cost (within usage limits)

**BYOK / Pay-per-use (Claude Code, OpenHands)**
- Good if you already have API credits
- Costs scale with actual usage—could be cheaper or more expensive than flat rate
- More control over model selection

**Per-seat SaaS (CodeRabbit, Greptile, etc.)**
- $15-40/month for private repos
- Predictable cost, unlimited usage

### Evaluation Criteria

1. **Cost** — Free tier availability, monthly cost for personal use
2. **Review quality** — Bug detection, false positive rate, noise level
3. **Setup friction** — How fast can I get it running on a repo
4. **OSS support** — Free for public repositories
5. **Ecosystem fit** — Tools I'm already paying for (Claude Pro, ChatGPT Plus, Copilot, etc.)

## Decision

[PENDING — Select one of the following templates]

### Option A: Free Tier (CodeRabbit for OSS)

I will use **CodeRabbit** on my public repositories (free) and evaluate whether to pay $24-30/month for private repos.

**Rationale:**
- Free unlimited reviews on public/OSS repos
- Zero config to get started
- Can upgrade later if I want private repo coverage

### Option B: Bundled with Existing Subscription (Codex or Copilot)

I will use **[OpenAI Codex / GitHub Copilot]** since I'm already paying for [ChatGPT Plus/Pro / Copilot Pro].

**Rationale:**
- Already paying for the subscription
- No additional cost (within usage limits)
- One less vendor to manage

### Option C: BYOK with Claude Code Action

I will use **Claude Code GitHub Action** with my existing Anthropic API key.

**Rationale:**
- Already have Anthropic API credits
- Pay only for what I use
- Can use Sonnet for cheap reviews, Opus for complex PRs
- Full control over prompts and behavior

### Option D: Open Source (OpenHands)

I will use **OpenHands** with my existing API keys.

**Rationale:**
- MIT licensed, no vendor lock-in
- BYOK with whatever LLM provider I'm already using
- More control over prompts and behavior

## Consequences

### Positive

- Catch bugs before they become embarrassing
- Learn from review suggestions (like async mentorship)
- Ship with more confidence on solo projects
- Faster iteration on side projects

### Negative

- Another subscription to manage (if paid)
- May develop over-reliance on AI reviews
- Still need human review for critical/production code

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Noisy reviews annoy me | Start with "chill" mode, tune over time |
| API costs spiral (BYOK) | Set billing alerts, use cheaper models |
| Tool disappears/pivots | Stick with well-funded or OSS options |

## References

- CodeRabbit docs: https://docs.coderabbit.ai
- Greptile: https://greptile.com
- Claude Code Action: https://github.com/anthropics/claude-code-action
- OpenHands: https://github.com/All-Hands-AI/OpenHands
- OpenAI Codex: https://developers.openai.com/codex
- GitHub Copilot Code Review: https://docs.github.com/en/copilot/using-github-copilot/code-review/using-copilot-code-review
- Graphite Diamond: https://graphite.dev/features/diamond
- Amazon CodeGuru Reviewer: https://aws.amazon.com/codeguru
- Cursor Bugbot: https://www.cursor.com/bugbot