import sys
from parser import ResumeParser
from llm_analyzer import analyze_resume

parser = ResumeParser()

file = sys.argv[1]

result = parser.parse(file)

print(result)

print(analyze_resume(result["raw_text"]))
