import time
import asyncio
import json
from src.api.schemas import RankedCandidate, TalentRankCandidate, RoleCapabilityMap
from src.llm_client import evaluate_candidate_async, evaluate_candidate_full

class CandidateRanker:
    def __init__(self):
        pass

    async def _evaluate_single(self, job_dict: dict, cand_dict: dict, cand_name: str) -> RankedCandidate:
        eval_result = await evaluate_candidate_async(
            json.dumps(job_dict),
            json.dumps(cand_dict)
        )
        sem_score = float(eval_result.get("semantic_match", 5.0))
        traj_score = float(eval_result.get("career_trajectory", 5.0))
        behav_score = float(eval_result.get("behavioral_signals", 5.0))
        cult_score = float(eval_result.get("cultural_fit", 5.0))
        reasoning = eval_result.get("reasoning", "LLM Evaluation completed.")

        overall = (sem_score * 0.35) + (traj_score * 0.25) + (behav_score * 0.25) + (cult_score * 0.15)
        recommendation = "STRONG HIRE" if overall >= 8.0 else ("CONSIDER" if overall >= 6.0 else "PASS")

        return RankedCandidate(
            name=cand_name,
            overall_score=round(overall, 2),
            semantic_match=round(sem_score, 2),
            career_trajectory=round(traj_score, 2),
            behavioral_signals=round(behav_score, 2),
            cultural_fit=round(cult_score, 2),
            recommendation=recommendation,
            reasoning=reasoning
        )

    async def rank_candidates(self, job, candidates):
        start_time = time.time()
        job_dict = job.model_dump()

        tasks = []
        for cand in candidates:
            cand_dict = cand.model_dump()
            tasks.append(self._evaluate_single(job_dict, cand_dict, cand.name))

        results = await asyncio.gather(*tasks)
        results = list(results)
        results.sort(key=lambda x: x.overall_score, reverse=True)

        proc_time = int((time.time() - start_time) * 1000)
        return {"ranked_candidates": results, "processing_time_ms": proc_time}

    async def build_recruiter_dashboard(
        self, job_id: str, role_title: str, candidates: list, job_profile: dict
    ) -> dict:
        """
        Build the full recruiter dashboard with TalentRank composite scores.
        Each candidate must have: name, email, profile dict, assessment_percentage.
        """
        start_time = time.time()

        async def _rank_one(idx: int, cand: dict) -> dict:
            profile = cand.get("profile", {})
            test_pct = float(cand.get("assessment_percentage", 0.0))
            result = await evaluate_candidate_full(profile, job_profile, test_pct)

            composite = result.get("composite_score", 0.0)
            sem_fit = result.get("resume_semantic_match", 0.0)
            velocity = result.get("career_velocity", 0.0)
            test_score = result.get("ai_test_score", 0.0)
            cap_map_raw = result.get("role_capability_map", [])

            recommendation = (
                "STRONG HIRE" if composite >= 80 else
                "CONSIDER" if composite >= 60 else "PASS"
            )

            cap_map = [
                RoleCapabilityMap(
                    skill=c.get("skill", "Unknown"),
                    level=c.get("level", "Intermediate"),
                    verified_by=c.get("verified_by", "Resume")
                ) for c in cap_map_raw
            ]

            return TalentRankCandidate(
                rank=0,  # assigned after sort
                name=result.get("name", cand.get("name", "Unknown")),
                email=result.get("email", cand.get("email", "")),
                composite_score=composite,
                resume_semantic_match=sem_fit,
                ai_test_score=test_score,
                career_velocity=velocity,
                role_capability_map=cap_map,
                recommendation=recommendation,
                system_recommendation=result.get("system_recommendation", "")
            )

        tasks = [_rank_one(i, c) for i, c in enumerate(candidates)]
        ranked = list(await asyncio.gather(*tasks))
        ranked.sort(key=lambda x: x.composite_score, reverse=True)
        for i, r in enumerate(ranked):
            r.rank = i + 1

        proc_time = int((time.time() - start_time) * 1000)
        return {
            "job_id": job_id,
            "role_title": role_title,
            "evaluated_candidates_count": len(ranked),
            "processing_time_ms": proc_time,
            "ranked_shortlist": ranked
        }
