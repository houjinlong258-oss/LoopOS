"""Fusion judge — compares multi-model outputs and produces a JudgeReport."""

from __future__ import annotations

from loopos.fusion.models import JudgeReport, ModelResponse


class FusionJudge:
    """Compare outputs from multiple models and produce a JudgeReport.

    This is a heuristic mock implementation — no real LLM calls.
    """

    def judge(
        self,
        request_id: str,
        responses: list[ModelResponse],
    ) -> JudgeReport:
        """Analyze multiple model responses and synthesize findings."""
        if not responses:
            return JudgeReport(
                request_id=request_id,
                confidence=0.0,
            )

        contents = [r.content for r in responses]

        consensus = self._find_consensus(contents)
        contradictions = self._find_contradictions(contents)
        unique_insights = self._find_unique(contents)

        # Strengths and weaknesses (mock heuristic based on length/detail)
        strengths: dict[str, list[str]] = {}
        weaknesses: dict[str, list[str]] = {}
        for resp in responses:
            s: list[str] = []
            w: list[str] = []
            if len(resp.content) > 200:
                s.append("detailed_response")
            else:
                w.append("brief_response")
            if resp.latency_ms < 500:
                s.append("fast")
            strengths[resp.model_id] = s
            weaknesses[resp.model_id] = w

        confidence = min(1.0, len(consensus) / max(1, len(consensus) + len(contradictions)))

        return JudgeReport(
            request_id=request_id,
            consensus=consensus,
            contradictions=contradictions,
            unique_insights=unique_insights,
            model_strengths=strengths,
            model_weaknesses=weaknesses,
            confidence=confidence,
            recommended_source_ids=[r.model_id for r in responses if len(r.content) > 100],
        )

    def _find_consensus(self, contents: list[str]) -> list[str]:
        """Find common themes across responses (mock: shared words)."""
        if len(contents) < 2:
            return ["single_source"]
        word_sets = [set(c.lower().split()) for c in contents]
        common = word_sets[0]
        for ws in word_sets[1:]:
            common = common & ws
        # Filter out common English words
        common = common - {"the", "a", "an", "is", "are", "and", "or", "to", "of", "in", "for", "it", "this", "that"}
        if common:
            return [f"shared_theme:{','.join(sorted(list(common)[:5]))}"]
        return []

    def _find_contradictions(self, contents: list[str]) -> list[str]:
        """Find contradictions (mock: detect "not"/"no" disagreements)."""
        contradictions: list[str] = []
        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                # Very simple heuristic
                if ("yes" in contents[i].lower() and "no" in contents[j].lower()) or \
                   ("no" in contents[i].lower() and "yes" in contents[j].lower()):
                    contradictions.append(f"disagreement:response_{i}_vs_{j}")
        return contradictions

    def _find_unique(self, contents: list[str]) -> list[str]:
        """Find content unique to one response (mock: unique long words)."""
        if len(contents) < 2:
            return []
        insights: list[str] = []
        for i, content in enumerate(contents):
            words = set(content.lower().split())
            others = set()
            for j, other in enumerate(contents):
                if i != j:
                    others.update(other.lower().split())
            unique = words - others - {"the", "a", "an", "is", "are", "and", "or"}
            unique_long = [w for w in unique if len(w) > 5]
            if unique_long:
                insights.append(f"unique_from_response_{i}:{','.join(unique_long[:3])}")
        return insights
