# Measured Startup + Context Savings (2026-02-10)

I built `codex-mem` because the *real* cost in day-to-day AI coding isn’t model quality, it’s context management:

- new sessions start “blank”
- dumping everything into the context window doesn’t scale
- I want retrieval to be evidence-first and reproducible

This page is a snapshot of what I measured locally (with scripts included in this repo).

## 1) Warm Daily Workflow (Memory Only)

This measures `codex-mem`’s **3-layer progressive disclosure retrieval** on a simulated “daily work” dataset (lots of historical memory).

**Result (context payload size):**
- Naive “load full history”: **379,275** tokens (estimate)
- Progressive load (Layer 1 + Layer 2 + Layer 3): **596** tokens (estimate)
- **Context reduction:** **99.84%**

**Result (time-to-first-context):**
- Layer-1 search median: **61.308 ms**
- Full-history load median: **88.397 ms**
- **Speedup:** **1.442x** (Layer-1 is ~30.7% faster vs full-history load)

Source:
- `Documentation/benchmarks/marketing_claims_20260210.json`

Reproduce:
```bash
python3 Scripts/benchmark_marketing_claim.py \
  --root . \
  --out Documentation/benchmarks/marketing_claims_20260210.json
```

## 2) Cold Start Project Onboarding (Codebase Grounding)

For cold start, the bottleneck isn’t “historical memory pruning” (there isn’t much history yet), it’s **codebase grounding**.

This measures `repo_knowledge.py` (the code index used by `codex-mem ask`) on my HopeNote codebase (private repo; results are aggregates only).

**Result (codebase context payload size):**
- Full indexable corpus: **442,312** tokens (estimate)
- Onboarding prompt (top-k=10, module-limit=6): **2,750** tokens (estimate)
- **Context reduction:** **99.38%**

**Result (latency):**
- Index build (one-time per repo): **725 ms**
- Onboarding prompt generation (per question): **100 ms**

Source:
- `Documentation/benchmarks/repo_onboarding_hopenote_20260210.json`

Reproduce on your own repo:
```bash
python3 Scripts/benchmark_repo_onboarding.py \
  --target-root /path/to/your/repo \
  --label "your-repo" \
  --index-dir .codex_knowledge_bench \
  --all-files on \
  --ignore-dir .codex_mem \
  --top-k 10 \
  --module-limit 6 \
  --snippet-chars 1000 \
  --out /tmp/repo_onboarding.json
```

## Notes / Caveats

- Token counts are **estimates**: `ceil(chars / 4)` (same heuristic used by `codex-mem` memory CLI outputs).
- “Full corpus” baselines are useful for quantifying *why* progressive retrieval matters, even though loading everything is not practical in real assistant contexts.
- Indexing is a one-time cost. The win is that follow-up questions stay incremental and evidence-driven instead of “re-learn the entire repo”.

