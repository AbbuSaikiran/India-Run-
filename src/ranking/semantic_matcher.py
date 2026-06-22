class SemanticMatcher:
    def __init__(self):
        pass

    def calculate_score(self, job_reqs, candidate_profile) -> float:
        """
        Calculate semantic match (35% weight)
        Based on algorithm:
        semantic_score = (
            (matching_skills / total_required) * 60 +
            (candidate_years / required_years) * 20 +
            domain_match * 20
        ) / 100
        """
        required_skills = set(s.lower() for s in job_reqs.required_skills)
        candidate_skills = set(s.lower() for s in candidate_profile.skills)
        
        if not required_skills:
            skill_score = 60.0
        else:
            matching_skills = len(required_skills.intersection(candidate_skills))
            skill_score = (matching_skills / len(required_skills)) * 60.0
            
        req_years = job_reqs.years_experience_min or 1
        cand_years = candidate_profile.years_experience or 0
        year_score = min((cand_years / req_years) * 20.0, 20.0)
        
        # Simple domain match mock
        domain_score = 20.0 
        
        total_score = (skill_score + year_score + domain_score)
        # Normalize to 0-100 scale (out of 100 internally, then we can map it to 10 for final)
        return min(total_score, 100.0) / 10.0  # Return 0-10 score
