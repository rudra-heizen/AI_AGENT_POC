import os
import json
import random

async def generate_interview_question(category: str, difficulty: str, question_type: str = "general") -> str:
    """Fetch an interview question guidance. question_type must be either 'general' or 'case_study'."""
    if question_type.lower() == "case_study":
        try:
            file_path = os.path.join(os.path.dirname(__file__), "case_study.json")
            with open(file_path, "r") as f:
                data = json.load(f)
            case_studies = data.get("caseStudies", [])
            
            # Filter by category and difficulty
            filtered = [cs for cs in case_studies if category.lower() in cs.get("category", "").lower() and cs.get("difficulty", "").lower() == difficulty.lower()]
            if not filtered:
                filtered = [cs for cs in case_studies if category.lower() in cs.get("category", "").lower()]
            if not filtered:
                filtered = case_studies
                
            if filtered:
                cs = random.choice(filtered)
                result = f"Case Study Problem: {cs.get('problem')}\n"
                result += f"Detailed Context: {cs.get('detailedContext')}\n\n"
                result += "Follow-up Questions (Ask these ONE AT A TIME and wait for the candidate's answer):\n"
                for i, q in enumerate(cs.get("questions", []), 1):
                    result += f"{i}. {q.get('question')}\n   Expected Concept: {q.get('expectedAnswer')}\n"
                return result
            return f"Could not find a specific case study for {category}. Please ask a standard general question instead."
        except Exception as e:
            return f"Error loading case study: {str(e)}. Proceed to ask a general question about {category}."
    else:
        return f"Please ask a {difficulty} difficulty theoretical or factual question about {category}. Evaluate their understanding of core concepts. Examples of good topics: trade-offs, internal workings, or common pitfalls. DO NOT ask multiple questions at once."
