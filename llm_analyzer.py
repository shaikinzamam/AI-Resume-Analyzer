import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi"

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        return match.group()
    return None


def sanitize(data):
    # Fix professional summary if model returns email
    if "@" in data.get("professional_summary", ""):
        data["professional_summary"] = (
            "B.Tech CSE student with hands-on experience in Python, Generative AI, "
            "LLMs, FastAPI, and RAG systems. Built multiple AI-powered projects and "
            "seeking an AI/GenAI/Python internship."
        )

    # Ensure minimum list sizes
    defaults = {
        "strengths": ["Python", "Generative AI", "FastAPI"],
        "weaknesses": ["Limited production deployment", "Needs more cloud experience"],
        "missing_skills": ["Docker", "Kubernetes"],
        "suggested_job_roles": ["Python Intern", "GenAI Intern", "AI Engineer Intern"]
    }

    for k, v in defaults.items():
        if k not in data or not data[k]:
            data[k] = v

    return data


def analyze_resume(text):

    prompt = f"""
You are an AI resume analyzer.

Return ONLY valid JSON:

{{
"professional_summary": "",
"strengths": ["a","b","c"],
"weaknesses": ["a","b"],
"missing_skills": ["a","b"],
"suggested_job_roles": ["a","b","c"]
}}

Rules:
- Never use email as summary
- Always infer skills
- No empty arrays
- No explanations

Resume:
{text[:2000]}
"""

    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=300
        )

        raw = r.json().get("response", "")

        cleaned = extract_json(raw)

        if not cleaned:
            return {"error": "Model failed JSON", "raw": raw}

        data = json.loads(cleaned)

        data = sanitize(data)

        return {"result": data}

    except Exception as e:
        return {"error": str(e)}
import re
from collections import Counter

class StandaloneLLMAnalyzer:
    """
    A rule-based resume analyzer that works without Ollama.
    Analyzes resume text using keyword matching and heuristics.
    """
    
    def __init__(self):
        # Skill categories
        self.tech_skills = {
            'python', 'java', 'javascript', 'c++', 'react', 'node', 'django', 
            'flask', 'fastapi', 'sql', 'mongodb', 'docker', 'kubernetes', 
            'aws', 'azure', 'gcp', 'tensorflow', 'pytorch', 'scikit-learn',
            'pandas', 'numpy', 'git', 'linux', 'html', 'css', 'typescript',
            'spring', 'angular', 'vue', 'redis', 'postgresql', 'mysql',
            'graphql', 'rest api', 'microservices', 'ci/cd', 'jenkins',
            'llm', 'genai', 'rag', 'langchain', 'hugging face', 'openai',
            'machine learning', 'deep learning', 'nlp', 'computer vision',
            'data science', 'data analysis', 'statistics', 'tableau', 'power bi'
        }
        
        self.soft_skills = {
            'leadership', 'communication', 'teamwork', 'problem solving',
            'critical thinking', 'time management', 'project management',
            'collaboration', 'presentation', 'analytical', 'creative'
        }
        
        # Missing skills suggestions
        self.trending_skills = [
            'Docker', 'Kubernetes', 'CI/CD', 'Cloud (AWS/Azure/GCP)',
            'System Design', 'Testing (Unit/Integration)', 
            'Agile/Scrum', 'GraphQL', 'Microservices'
        ]
        
        # Job role keywords
        self.job_roles = {
            'Python Developer': ['python', 'django', 'flask', 'fastapi'],
            'Full Stack Developer': ['react', 'node', 'javascript', 'mongodb', 'sql'],
            'Data Scientist': ['python', 'machine learning', 'pandas', 'tensorflow', 'statistics'],
            'AI/ML Engineer': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'nlp'],
            'GenAI Engineer': ['llm', 'genai', 'rag', 'langchain', 'openai'],
            'DevOps Engineer': ['docker', 'kubernetes', 'aws', 'ci/cd', 'jenkins'],
            'Backend Developer': ['python', 'java', 'sql', 'api', 'microservices'],
            'Frontend Developer': ['react', 'javascript', 'html', 'css', 'typescript'],
            'Data Analyst': ['sql', 'python', 'tableau', 'power bi', 'excel'],
            'Cloud Engineer': ['aws', 'azure', 'gcp', 'docker', 'kubernetes']
        }
    
    def extract_skills(self, text):
        """Extract skills from resume text"""
        text_lower = text.lower()
        
        found_tech = []
        found_soft = []
        
        for skill in self.tech_skills:
            if skill in text_lower:
                found_tech.append(skill.title())
        
        for skill in self.soft_skills:
            if skill in text_lower:
                found_soft.append(skill.title())
        
        return found_tech, found_soft
    
    def suggest_job_roles(self, tech_skills):
        """Suggest job roles based on skills"""
        text_lower = ' '.join(tech_skills).lower()
        
        role_scores = {}
        for role, keywords in self.job_roles.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                role_scores[role] = score
        
        # Sort by score and return top 4
        sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)
        return [role for role, _ in sorted_roles[:4]]
    
    def identify_weaknesses(self, text, tech_skills):
        """Identify potential weaknesses"""
        text_lower = text.lower()
        weaknesses = []
        
        # Check for common weakness indicators
        if len(tech_skills) < 3:
            weaknesses.append("Limited technical skill diversity mentioned")
        
        if 'experience' not in text_lower or 'year' not in text_lower:
            weaknesses.append("Experience duration not clearly specified")
        
        if 'project' not in text_lower and 'built' not in text_lower:
            weaknesses.append("Few concrete project examples provided")
        
        if not any(word in text_lower for word in ['achieved', 'improved', 'increased', 'reduced']):
            weaknesses.append("Lacks quantifiable achievements and impact metrics")
        
        if not any(word in text_lower for word in ['team', 'collaborate', 'leadership']):
            weaknesses.append("Limited evidence of teamwork and collaboration")
        
        # Return top 3 weaknesses
        return weaknesses[:3] if weaknesses else ["Consider adding more specific details"]
    
    def suggest_missing_skills(self, found_skills):
        """Suggest skills to add"""
        found_lower = [s.lower() for s in found_skills]
        
        missing = []
        for skill in self.trending_skills:
            if skill.lower() not in found_lower:
                missing.append(skill)
        
        return missing[:4]  # Return top 4
    
    def generate_summary(self, text, tech_skills, soft_skills):
        """Generate professional summary"""
        text_lower = text.lower()
        
        # Detect education level
        education = "professional"
        if 'b.tech' in text_lower or 'bachelor' in text_lower:
            education = "Bachelor's degree holder"
        elif 'm.tech' in text_lower or 'master' in text_lower:
            education = "Master's degree holder"
        elif 'phd' in text_lower or 'doctorate' in text_lower:
            education = "Ph.D. holder"
        
        # Detect experience level
        experience = "early career professional"
        if 'intern' in text_lower or 'fresher' in text_lower:
            experience = "aspiring professional"
        elif re.search(r'\d+\s*\+?\s*years?', text_lower):
            years_match = re.search(r'(\d+)\s*\+?\s*years?', text_lower)
            if years_match:
                years = int(years_match.group(1))
                if years < 2:
                    experience = "early career professional"
                elif years < 5:
                    experience = "mid-level professional"
                else:
                    experience = "experienced professional"
        
        # Build summary
        top_skills = ', '.join(tech_skills[:4]) if tech_skills else "various technologies"
        
        summary = f"{education} and {experience} with demonstrated expertise in {top_skills}."
        
        if soft_skills:
            summary += f" Strong {soft_skills[0].lower()} and {soft_skills[1].lower() if len(soft_skills) > 1 else 'communication'} abilities."
        
        return summary
    
    def analyze(self, resume_text):
        """Main analysis function"""
        try:
            tech_skills, soft_skills = self.extract_skills(resume_text)
            
            # Generate all components
            professional_summary = self.generate_summary(resume_text, tech_skills, soft_skills)
            strengths = (tech_skills[:5] + soft_skills[:2])[:5]  # Top 5 skills as strengths
            weaknesses = self.identify_weaknesses(resume_text, tech_skills)
            missing_skills = self.suggest_missing_skills(tech_skills)
            job_roles = self.suggest_job_roles(tech_skills)
            
            # Ensure minimum items
            if not strengths:
                strengths = ["Technical aptitude", "Quick learner", "Problem solver"]
            if not weaknesses:
                weaknesses = ["Consider adding more details"]
            if not missing_skills:
                missing_skills = ["Docker", "Cloud platforms", "Testing frameworks"]
            if not job_roles:
                job_roles = ["Software Developer", "Technical Intern", "IT Professional"]
            
            return {
                "result": {
                    "professional_summary": professional_summary,
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "missing_skills": missing_skills,
                    "suggested_job_roles": job_roles
                }
            }
        
        except Exception as e:
            return {
                "error": f"Analysis failed: {str(e)}"
            }


def analyze_resume(text):
    """
    Main function to analyze resume - compatible with the existing API
    """
    analyzer = StandaloneLLMAnalyzer()
    return analyzer.analyze(text)


# Test the analyzer
if __name__ == "__main__":
    sample_text = """
    John Doe
    john@email.com
    
    B.Tech in Computer Science Engineering
    
    Skills: Python, JavaScript, React, SQL, Machine Learning, Flask
    
    Experience:
    - Built a chatbot using NLP
    - Developed REST APIs with Flask
    - Created data visualization dashboards
    
    Strong communication and teamwork skills.
    """
    
    result = analyze_resume(sample_text)
    print("Analysis Result:")
    print("-" * 50)
    if "result" in result:
        for key, value in result["result"].items():
            print(f"\n{key.upper()}:")
            if isinstance(value, list):
                for item in value:
                    print(f"  • {item}")
            else:
                print(f"  {value}")
    else:
        print(f"Error: {result.get('error')}")