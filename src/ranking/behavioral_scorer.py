class BehavioralScorer:
    def __init__(self):
        pass

    def calculate_score(self, job_reqs, candidate_profile) -> float:
        """
        Calculate behavioral score (25% weight)
        Measures engagement, github commits, etc.
        """
        commits = candidate_profile.github_commits_30d or 0
        if commits > 100:
            score = 10.0
        elif commits > 50:
            score = 8.0
        elif commits > 10:
            score = 6.0
        else:
            score = 4.0
            
        return score
