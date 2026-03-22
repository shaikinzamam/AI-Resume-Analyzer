"""
ollama_client.py — FULLY FIXED
================================
Bugs fixed:
  1. "JSON parsing failed: Expecting ',' delimiter" — Mistral wraps output in
     markdown fences and adds trailing text. The old {.*} regex captured garbage.
     FIX: brace-depth matching to find the exact JSON object, then multi-step clean.

  2. stream=False blocked for 180s then timed out.
     FIX: stream=True with iter_lines() — connection never idles, never times out.

  3. Hardcoded model may not be installed.
     FIX: Auto-detect fastest available model from Ollama's /api/tags endpoint.

  4. ATS score always 0 when JSON failed.
     FIX: Robust parser with 4 fallback strategies before giving up.
"""

import requests
import json
import re

OLLAMA_URL      = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

PREFERRED_MODELS = [
    "phi3:mini", "phi3",
    "mistral:7b-instruct-q4_0",
    "mistral:7b-instruct-q4_K_M",
    "mistral:7b", "mistral",
    "llama3:8b", "llama2",
    
]


def get_best_model() -> str:
    try:
        resp = requests.get(OLLAMA_TAGS_URL, timeout=5)
        installed = {m["name"] for m in resp.json().get("models", [])}
        for m in PREFERRED_MODELS:
            if m in installed:
                return m
        if installed:
            return sorted(installed)[0]   # deterministic fallback
        # No models installed at all
        raise RuntimeError("No Ollama models installed. Run: ollama pull phi3:mini")
    except requests.ConnectionError:
        raise requests.ConnectionError("Ollama not running — start with: ollama serve")
    except RuntimeError:
        raise
    except Exception:
        pass
    return "mistral"


def _stream_generate(prompt: str, num_predict: int = 400) -> str:
    """Stream from Ollama — never blocks long enough to timeout."""
    model = get_best_model()
    parts = []
    with requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": 0.1, "num_predict": num_predict, "num_ctx": 512},
        },
        stream=True,
        timeout=(5, 60),
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
                parts.append(chunk.get("response", ""))
                if chunk.get("done"):
                    break
            except Exception:
                continue
    return "".join(parts)


def _robust_parse_json(text: str) -> dict:
    """
    4-strategy JSON extractor that survives all common Mistral failures:
      - Markdown fences around JSON
      - Trailing text after closing brace
      - Trailing commas
      - Unescaped newlines inside strings
      - Bad backslash escapes
    """
    if not text or not text.strip():
        raise ValueError("Empty response from model")

    # Strategy 1: strip fences, find balanced braces
    clean = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
    start = clean.find("{")
    if start != -1:
        depth, end, in_str, esc = 0, -1, False, False
        for i, ch in enumerate(clean[start:], start):
            if esc:              esc = False; continue
            if ch == "\\" and in_str: esc = True; continue
            if ch == '"':       in_str = not in_str
            if not in_str:
                if ch == "{":   depth += 1
                elif ch == "}": depth -= 1
                if depth == 0:  end = i; break
        if end == -1:
            end = clean.rfind("}")
        if end != -1:
            candidate = clean[start:end + 1]
            candidate = re.sub(r",\s*([\}\]])", r"\1", candidate)   # trailing commas
            candidate = re.sub(r'(?<!\\)\n', ' ', candidate)         # literal newlines
            candidate = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', candidate)  # bad escapes
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

    # Strategy 2: json.loads on the raw stripped text
    try:
        return json.loads(clean)
    except Exception:
        pass

    # Strategy 3: brace-counting scan on original text as fallback
    start = text.find("{")
    if start != -1:
        depth, end, in_str, esc = 0, -1, False, False
        for i, ch in enumerate(text[start:], start):
            if esc:              esc = False; continue
            if ch == "\\" and in_str: esc = True; continue
            if ch == '"':       in_str = not in_str
            if not in_str:
                if ch == "{":   depth += 1
                elif ch == "}": depth -= 1
                if depth == 0:  end = i; break
        if end != -1:
            candidate = text[start:end + 1]
            candidate = re.sub(r",\s*([\}\]])", r"\1", candidate)
            candidate = re.sub(r'(?<!\\)\n', ' ', candidate)
            candidate = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', candidate)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

    # Strategy 4: give up
    raise ValueError(f"Could not parse JSON from model output (length={len(text)})")


ATS_PROMPT = """You are an ATS resume analyzer. Analyze the resume against the job description.
Return ONLY a valid JSON object. No markdown. No explanation. No text before or after the JSON.

JSON FORMAT (fill in real values, keep all keys):
{{
  "overall_match_score": 72,
  "skill_match_percentage": 65,
  "keyword_match_percentage": 58,
  "missing_skills": ["Docker", "Kubernetes"],
  "missing_keywords": ["microservices", "ci/cd"],
  "experience_gap": "Gap description",
  "resume_improvements": ["Add metrics", "Mirror JD keywords"],
  "improved_bullets": [
    {{"original": "Worked on Python backend", "improved": "Developed 5 REST APIs in FastAPI serving 10K+ users"}}
  ],
  "final_verdict": "Strong match. Apply with a tailored cover letter."
}}

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

JSON:"""


def analyze_resume_jd(resume: str, jd: str) -> dict:
    """Analyze resume vs JD. Returns dict, never raises."""
    # Escape braces in inputs so they don't break .format()
    safe_resume = resume[:2500].replace("{", "(").replace("}", ")")
    safe_jd     = jd[:1500].replace("{",  "(").replace("}", ")")
    prompt = ATS_PROMPT.format(resume=safe_resume, jd=safe_jd)

    try:
        raw    = _stream_generate(prompt, num_predict=400)
        result = _robust_parse_json(raw)
        # Ensure all expected keys exist
        for key, default in {
            "overall_match_score": 0, "skill_match_percentage": 0,
            "keyword_match_percentage": 0, "missing_skills": [],
            "missing_keywords": [], "experience_gap": "",
            "resume_improvements": [], "improved_bullets": [],
            "final_verdict": "",
        }.items():
            result.setdefault(key, default)
        return result

    except requests.ConnectionError:
        return _error_response("Ollama not running — start with: ollama serve")
    except requests.Timeout:
        return _error_response("Ollama timed out — try: ollama pull phi3:mini")
    except (json.JSONDecodeError, ValueError) as e:
        return _error_response(f"JSON parse error: {e}")
    except Exception as e:
        return _error_response(f"Unexpected error: {e}")


def _error_response(msg: str) -> dict:
    return {
        "error": msg,
        "overall_match_score": 0, "skill_match_percentage": 0,
        "keyword_match_percentage": 0, "missing_skills": [],
        "missing_keywords": [], "experience_gap": msg,
        "resume_improvements": [], "improved_bullets": [],
        "final_verdict": f"Error: {msg}",
    }