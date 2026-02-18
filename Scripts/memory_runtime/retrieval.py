from __future__ import annotations

import re
from typing import Dict, List, Mapping, Sequence

from .contracts import EvidenceItem

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}|[0-9]+|[\u4e00-\u9fff]+")
SPLIT_RE = re.compile(r"[/_.:+\-]")


def hybrid_rank_chunks(
    chunks: Sequence[Mapping[str, object]],
    *,
    question: str,
    top_k: int | None = None,
    use_rerank_score: bool = True,
    graph_neighbor_scores: Mapping[str, float] | None = None,
) -> List[Dict[str, object]]:
    rows = [dict(chunk) for chunk in chunks if isinstance(chunk, Mapping)]
    if not rows:
        return []

    q_terms = _tokenize(question)
    graph_boost = _graph_lite_boost(rows)
    external_graph = {
        str(k): _float(v)
        for k, v in (graph_neighbor_scores or {}).items()
        if str(k).strip()
    }

    scored: List[Dict[str, object]] = []
    for idx, row in enumerate(rows):
        lexical = _float(row.get("bm25", row.get("lexical", 0.0)))
        semantic = _float(row.get("semantic", 0.0))
        base = _float(row.get("score", lexical * 0.6 + semantic * 0.4))
        structural = _structural_score(row, q_terms)
        graph = graph_boost.get(idx, 0.0)
        path_key = str(row.get("path", "")).strip()
        graph_db = external_graph.get(path_key, 0.0)
        graph_combined = min(1.0, (0.7 * graph) + (0.3 * graph_db))
        dense = semantic
        rerank = _float(row.get("rerank_score", 0.0)) if use_rerank_score else 0.0

        hybrid = (0.42 * base) + (0.20 * structural) + (0.18 * graph_combined) + (0.15 * dense) + (0.05 * rerank)
        row["hybrid_score"] = round(hybrid, 6)
        row["score_breakdown"] = {
            "base": round(base, 6),
            "structural": round(structural, 6),
            "graph_lite": round(graph, 6),
            "graph_db": round(graph_db, 6),
            "graph_combined": round(graph_combined, 6),
            "dense": round(dense, 6),
            "rerank": round(rerank, 6),
        }
        row["score"] = row["hybrid_score"]
        scored.append(row)

    scored.sort(key=lambda item: float(item.get("hybrid_score", 0.0)), reverse=True)
    if top_k is not None:
        return scored[: max(1, int(top_k))]
    return scored


def build_evidence_items(
    chunks: Sequence[Mapping[str, object]],
    *,
    root_abs: str = "",
) -> List[EvidenceItem]:
    evidence: List[EvidenceItem] = []
    for row in chunks:
        if not isinstance(row, Mapping):
            continue
        path = str(row.get("path", "")).strip()
        if not path:
            continue
        file_path = path if path.startswith("/") or not root_abs else f"{root_abs.rstrip('/')}/{path.lstrip('/')}"
        symbol = str(row.get("symbol_hint", "")).strip() or "<module>"
        role = "retrieved_context"
        score = _float(row.get("hybrid_score", row.get("score", 0.0)))
        sections = _sections_for_chunk(row)
        for section in sections:
            evidence.append(
                EvidenceItem(
                    section=section,
                    file_path=file_path,
                    symbol=symbol,
                    role=role,
                    score=score,
                )
            )
    return evidence


def _sections_for_chunk(chunk: Mapping[str, object]) -> List[str]:
    path = str(chunk.get("path", "")).lower()
    snippet = str(chunk.get("snippet", "")).lower()
    symbol = str(chunk.get("symbol_hint", "")).lower()

    categories = set()
    raw_categories = chunk.get("categories")
    if isinstance(raw_categories, list):
        categories.update(str(v).strip().lower() for v in raw_categories if str(v).strip())
    raw_category = str(chunk.get("category", "")).strip().lower()
    if raw_category:
        categories.add(raw_category)

    out: List[str] = []
    if "entrypoint" in categories:
        out.extend(["entrypoint", "main_flow"])
    if "persistence" in categories:
        out.append("persistence")
    if "ai_generation" in categories:
        out.append("ai_generation")
    if "backend" in categories:
        out.extend(["architecture", "module_map", "main_flow"])

    if any(token in path for token in ("readme", "docs/", "documentation")):
        out.extend(["north_star", "architecture", "module_map"])
    if any(token in path for token in ("/test", "tests/", "test_", "spec")):
        out.append("tests")
    if any(token in snippet or token in symbol for token in ("risk", "regression", "todo", "warning", "security")):
        out.append("risks")

    if not out:
        out.extend(["architecture", "module_map"])
    return _ordered_unique(out)


def _structural_score(chunk: Mapping[str, object], q_terms: Sequence[str]) -> float:
    if not q_terms:
        return 0.0
    path_tokens = _tokenize(str(chunk.get("path", "")))
    symbol_tokens = _tokenize(str(chunk.get("symbol_hint", "")))
    category_tokens = _tokenize(" ".join(str(v) for v in chunk.get("categories", []) if str(v).strip()))
    raw_cat = str(chunk.get("category", "")).strip()
    if raw_cat:
        category_tokens.extend(_tokenize(raw_cat))
    path_hit = _overlap_ratio(path_tokens, q_terms)
    symbol_hit = _overlap_ratio(symbol_tokens, q_terms)
    cat_hit = _overlap_ratio(category_tokens, q_terms)
    return min(1.0, (0.45 * path_hit) + (0.40 * symbol_hit) + (0.15 * cat_hit))


def _graph_lite_boost(chunks: Sequence[Mapping[str, object]]) -> Dict[int, float]:
    if not chunks:
        return {}
    boosts: Dict[int, float] = {idx: 0.0 for idx in range(len(chunks))}
    signatures: List[set[str]] = []
    for chunk in chunks:
        path = str(chunk.get("path", "")).lower()
        symbol = str(chunk.get("symbol_hint", "")).lower()
        module_tokens = set(_tokenize(path))
        module_tokens.update(_tokenize(symbol))
        signatures.append(module_tokens)
    for i in range(len(chunks)):
        for j in range(i + 1, len(chunks)):
            sim = _set_similarity(signatures[i], signatures[j])
            if sim <= 0.0:
                continue
            # lightweight proxy for file-symbol-call/import/session neighbor relation.
            bonus = min(0.4, sim * 0.4)
            boosts[i] += bonus
            boosts[j] += bonus
    max_v = max(boosts.values()) if boosts else 0.0
    if max_v <= 1e-9:
        return boosts
    for idx, value in list(boosts.items()):
        boosts[idx] = min(1.0, value / max_v)
    return boosts


def _tokenize(text: str) -> List[str]:
    values: List[str] = []
    for token in TOKEN_RE.findall(str(text or "").lower()):
        if "/" in token or "_" in token or "-" in token:
            values.extend([v for v in SPLIT_RE.split(token) if v])
        else:
            values.append(token)
    return [v for v in values if v]


def _overlap_ratio(a: Sequence[str], b: Sequence[str]) -> float:
    if not a or not b:
        return 0.0
    sa = set(a)
    sb = set(b)
    return len(sa & sb) / max(1, len(sb))


def _set_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _ordered_unique(values: Sequence[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _float(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
