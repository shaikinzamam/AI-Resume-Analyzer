"""
app.py — AI Resume Analyzer  v5.0
All routes:
  GET  /                        → serve frontend
  GET  /api/health
  POST /api/parse               → parse resume file
  POST /api/analyze-with-jd     → ATS match analysis
  POST /api/build-resume        → SSE streaming resume builder
  POST /api/build-resume-sync   → sync fallback
  POST /api/interview/start     → generate interview questions (instant)
  POST /api/interview/evaluate  → score & feedback on answer (instant)
  POST /api/test                → quick LLM test
  GET  /api/history             → last 10 sessions
"""

from flask import Flask, request, jsonify, Response, stream_with_context, render_template, send_from_directory

try:
    from flask_cors import CORS
except ImportError:
    class CORS:
        def __init__(self, app, **kwargs):
            @app.after_request
            def _cors(response):
                response.headers["Access-Control-Allow-Origin"]  = "*"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
                response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
                return response

import os
import re
import json
import threading
import queue
import uuid
from datetime import datetime

from parser import ResumeParser
from llm_analyzer import analyze_resume_with_jd, analyze_resume
from Resume_builder import build_resume_for_jd

app = Flask(__name__)
CORS(app)

# ── Config ─────────────────────────────────────────────────────────────────────
UPLOAD_FOLDER  = "uploads"
HISTORY_FOLDER = "history"
ALLOWED_EXT    = {"pdf", "docx", "txt"}
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

os.makedirs(UPLOAD_FOLDER,  exist_ok=True)
os.makedirs(HISTORY_FOLDER, exist_ok=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def unique_upload_path(original_filename):
    ext  = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else "bin"
    name = "{}.{}".format(uuid.uuid4().hex, ext)
    return os.path.join(UPLOAD_FOLDER, name)


def safe_remove(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def save_history(data):
    name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
    path = os.path.join(HISTORY_FOLDER, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return name


# ── Error handlers ─────────────────────────────────────────────────────────────

@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({"error": "File too large. Maximum upload size is 5 MB."}), 413


# ── Frontend ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    # index.html lives in the templates/ subfolder
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)) or os.getcwd(), "templates")
    return send_from_directory(base, "index.html")


# ── Health ─────────────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


# ── Parse ──────────────────────────────────────────────────────────────────────

@app.route("/api/parse", methods=["POST"])
def parse():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file. Use PDF, DOCX, or TXT"}), 400

    path = unique_upload_path(file.filename)
    try:
        file.save(path)
        parser    = ResumeParser()
        parsed    = parser.parse(path)
        ai_result = analyze_resume(parsed["raw_text"])
        result    = dict(parsed, llm_summary=ai_result.get("result", {}))
        save_history(result)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": "Processing failed: {}".format(e)}), 500
    finally:
        safe_remove(path)


# ── Analyze with JD ────────────────────────────────────────────────────────────

@app.route("/api/analyze-with-jd", methods=["POST"])
def analyze_with_jd():
    path = None
    try:
        resume_text     = ""
        job_description = ""

        if request.is_json:
            data            = request.get_json()
            resume_text     = data.get("resume_text", "")
            job_description = data.get("job_description", "")
        elif "file" in request.files:
            file = request.files["file"]
            if not file.filename or not allowed_file(file.filename):
                return jsonify({"error": "Invalid file"}), 400
            path = unique_upload_path(file.filename)
            file.save(path)
            parser      = ResumeParser()
            parsed      = parser.parse(path)
            resume_text = parsed["raw_text"]
            safe_remove(path)
            path = None
            job_description = request.form.get("job_description", "")
        else:
            return jsonify({"error": "No resume provided"}), 400

        if not resume_text:
            return jsonify({"error": "Resume text is empty"}), 400
        if not job_description:
            return jsonify({"error": "Job description is required"}), 400

        result = analyze_resume_with_jd(resume_text, job_description)
        save_history({
            "timestamp":     datetime.now().isoformat(),
            "analysis_type": "jd_match",
            "result":        result,
        })
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": "Analysis failed: {}".format(e)}), 500
    finally:
        if path:
            safe_remove(path)


# ── Build Resume — SSE streaming ───────────────────────────────────────────────

@app.route("/api/build-resume", methods=["POST"])
def build_resume():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data            = request.get_json()
    resume_text     = data.get("resume_text", "").strip()
    job_description = data.get("job_description", "").strip()

    if not resume_text:
        return jsonify({"error": "resume_text is required"}), 400
    if not job_description:
        return jsonify({"error": "job_description is required"}), 400

    result_q = queue.Queue()

    def worker():
        try:
            result_q.put(("done", build_resume_for_jd(resume_text, job_description)))
        except Exception as e:
            result_q.put(("error", str(e)))

    @stream_with_context
    def generate():
        import time
        yield "data: {}\n\n".format(json.dumps({"status": "started", "message": "Received request, starting AI rewrite..."}))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        steps = [
            "Parsing resume structure...",
            "Analysing job description keywords...",
            "Rewriting bullets with strong action verbs...",
            "Injecting ATS keywords into summary...",
            "Optimising skills section...",
            "Building professional summary...",
            "Generating final resume sections...",
            "Creating DOCX file...",
        ]
        step = 0
        while t.is_alive():
            time.sleep(5)
            msg = steps[min(step, len(steps) - 1)]
            yield "data: {}\n\n".format(json.dumps({"status": "progress", "message": msg}))
            step += 1

        try:
            status, payload = result_q.get(timeout=10)
        except queue.Empty:
            yield "data: {}\n\n".format(json.dumps({"status": "error", "message": "Worker thread did not return"}))
            return

        if status == "done":
            try:
                save_history({
                    "timestamp":      datetime.now().isoformat(),
                    "analysis_type":  "resume_builder",
                    "keywords_added": payload.get("rewritten", {}).get("ats_keywords_added", []),
                })
            except Exception:
                pass
            yield "data: {}\n\n".format(json.dumps({"status": "done", "result": payload}))
        else:
            yield "data: {}\n\n".format(json.dumps({"status": "error", "message": payload}))

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )


# ── Build Resume — sync fallback ───────────────────────────────────────────────

@app.route("/api/build-resume-sync", methods=["POST"])
def build_resume_sync():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        data            = request.get_json()
        resume_text     = data.get("resume_text", "").strip()
        job_description = data.get("job_description", "").strip()
        if not resume_text:
            return jsonify({"error": "resume_text required"}), 400
        if not job_description:
            return jsonify({"error": "job_description required"}), 400
        result = build_resume_for_jd(resume_text, job_description)
        save_history({"timestamp": datetime.now().isoformat(), "analysis_type": "resume_builder"})
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": "Build failed: {}".format(e)}), 500



# ── Question Generator — Resume vs JD ─────────────────────────────────────────

def _generate_questions(resume_text, job_description):
    """Compare resume vs JD. Return targeted questions with category/why/tip."""
    import re
    res_lower = resume_text.lower()
    jd_lower  = job_description.lower()
    SKILLS = {
        "Python":["python"],"FastAPI":["fastapi"],"Flask":["flask"],"Django":["django"],
        "REST API":["rest api","restful"],"Node.js":["node.js","nodejs"],
        "React":["react"],"JavaScript":["javascript"],"TypeScript":["typescript"],
        "Docker":["docker"],"Kubernetes":["kubernetes","k8s"],
        "AWS":["aws","ec2","s3","lambda","amazon web"],"GCP":["gcp","google cloud"],"Azure":["azure"],
        "CI/CD":["ci/cd","github actions","jenkins","gitlab ci"],
        "PostgreSQL":["postgresql","postgres"],"MongoDB":["mongodb","mongo"],"Redis":["redis"],
        "SQL":["sql","mysql","sqlite"],"LangChain":["langchain"],
        "RAG":["rag","retrieval augmented","retrieval-augmented"],"LLM":["llm","large language model"],
        "OpenAI":["openai","gpt"],"Ollama":["ollama"],
        "Vector DB":["faiss","chromadb","pinecone","vector store","vector database"],
        "Machine Learning":["machine learning","scikit","sklearn"],
        "Deep Learning":["deep learning","tensorflow","pytorch"],"NLP":["nlp","natural language"],
        "Pandas/NumPy":["pandas","numpy"],"Git":["git","github","version control"],
        "Microservices":["microservice"],"Streamlit":["streamlit"],
        "Selenium":["selenium","playwright"],"Automation":["n8n","zapier","rpa"],
    }
    jd_needs = [s for s,kws in SKILLS.items() if any(k in jd_lower  for k in kws)]
    res_has  = [s for s,kws in SKILLS.items() if any(k in res_lower for k in kws)]
    matched  = [s for s in jd_needs if s in res_has]
    gaps     = [s for s in jd_needs if s not in res_has]
    bonus    = [s for s in res_has  if s not in jd_needs]

    projects = []
    for line in resume_text.replace("\r\n","\n").split("\n"):
        line = line.strip()
        if not line or (line.isupper() and len(line.split()) <= 3): continue
        if re.search(r"(built|developed|created|designed|system|chatbot|application|platform|dashboard|tool)", line, re.IGNORECASE):
            name = re.sub(r"(github\s*[:\-]\s*https?://\S+|git\s+link\s*[:\-]\s*https?://\S+)", "", line, flags=re.IGNORECASE)
            name = re.sub(r"^[\-\u2022*\d.]+\s*", "", name).strip()
            if 5 < len(name) < 90: projects.append(name[:80])
        if len(projects) >= 3: break

    role = ""
    for line in job_description.replace("\r\n","\n").split("\n")[:10]:
        line = line.strip()
        if re.search(r"(engineer|developer|analyst|scientist|intern|associate|lead|specialist)", line, re.IGNORECASE) and len(line) < 80:
            role = line; break

    questions = []
    questions.append({"question":"Why are you the right fit for this {} role, and which project best demonstrates that?".format(role or "position"),"category":"Role Fit","why":"Every interview opens here. Tests self-awareness and alignment with the JD.","tip":"Name 2 skills from the JD you have, link one project that proves it, say why the company excites you."})

    MATCHED_Q = {
        "Python":("Walk through the most complex Python project you built — architecture, patterns, and performance decisions.","Python is a core JD requirement."),
        "FastAPI":("How did you structure a production FastAPI service? Cover async, Pydantic, dependency injection, auth, and error handling.","FastAPI is explicitly required."),
        "Flask":("How did you organise a Flask app for scale? Talk blueprints, config management, and error handling.","Flask is listed as required."),
        "RAG":("Explain your RAG pipeline — chunking, embedding model, retrieval method, and how you reduced hallucinations.","RAG is a key JD requirement."),
        "LangChain":("What chains or agents did you build with LangChain? How did you manage memory and tool-calling failures?","LangChain is listed in the JD."),
        "LLM":("How did you integrate an LLM into a product? Cover prompt engineering, streaming, latency, cost, and fallbacks.","LLM integration is central to this role."),
        "Docker":("Walk through containerising an app — Dockerfile best practices, multi-stage builds, and compose setup.","Docker is a listed requirement."),
        "Kubernetes":("How have you used Kubernetes? Cover deployments, services, config maps, resource limits, and pod failures.","Kubernetes is required by the JD."),
        "AWS":("Which AWS services have you used in production? Describe the architecture, IAM, and cost management.","AWS is a JD requirement."),
        "SQL":("Describe the most complex SQL query or schema you designed and how you optimised it.","Strong SQL is required."),
        "MongoDB":("How did you design a MongoDB schema? Cover indexing and aggregation pipelines.","MongoDB is listed in the JD."),
        "React":("Describe a React app you built — state management, performance, and component architecture.","React is a core JD requirement."),
        "Machine Learning":("Walk through an ML project: data prep, model selection, evaluation, deployment, and drift monitoring.","ML is a core JD skill."),
        "REST API":("How do you design a REST API for high traffic? Cover versioning, auth, rate limiting, and docs.","API design is a key requirement."),
        "CI/CD":("Describe a CI/CD pipeline you built — stages, failure handling, and deploy strategy.","CI/CD is listed in the JD."),
        "Microservices":("How did you design microservices? Cover inter-service communication and partial failure handling.","Microservices architecture is required."),
        "Vector DB":("How did you choose and use a vector database? Cover indexing and similarity search tuning.","Vector DB is required for this role."),
    }
    count = 0
    for skill in matched[:6]:
        if skill in MATCHED_Q and count < 3:
            q,why = MATCHED_Q[skill]
            questions.append({"question":q,"category":"Matched Skill — {}".format(skill),"why":why,"tip":"You listed {} — give a specific example with numbers.".format(skill)})
            count += 1

    GAP_Q = {
        "Docker":"Docker is on the JD but not on your resume. Have you done any containerisation work?",
        "Kubernetes":"The JD mentions Kubernetes. What do you know about container orchestration?",
        "AWS":"The JD requires AWS. What cloud platforms have you used and how would that transfer?",
        "FastAPI":"The JD requires FastAPI. You have Flask — what are the key differences?",
        "React":"The JD requires React but it is not on your resume. What frontend experience do you have?",
        "CI/CD":"The JD expects CI/CD experience. Have you worked with any automated pipelines?",
        "TypeScript":"The JD requires TypeScript. How comfortable are you with static typing?",
        "Machine Learning":"The JD requires ML. What data science background do you have?",
        "SQL":"Strong SQL is required but is not prominent on your resume. What database experience do you have?",
        "Microservices":"The JD requires microservices. Have you worked with distributed systems?",
        "Vector DB":"The JD requires vector DB experience. Have you worked with embeddings or similarity search?",
        "LangChain":"LangChain is required but not on your resume. Have you used any LLM orchestration frameworks?",
    }
    gap_count = 0
    for skill in gaps[:5]:
        if skill in GAP_Q and gap_count < 2:
            questions.append({"question":GAP_Q[skill],"category":"Skill Gap — {}".format(skill),"why":"{} is required by the JD but not on your resume. Interviewers will probe this.".format(skill),"tip":"Be honest. Show a learning plan or related experience. Never bluff."})
            gap_count += 1

    for proj in projects[:2]:
        questions.append({"question":"Walk me through {} — the problem, tech choices, hardest challenge, and what you would improve today.".format(proj),"category":"Project Deep-Dive","why":"This project is on your resume. Interviewers will ask deep technical follow-ups.","tip":"STAR: the problem, your role, what you built and why, measurable outcome."})

    ai_needed    = any(s in matched+jd_needs for s in ["RAG","LLM","LangChain","OpenAI","Vector DB","Ollama"])
    infra_needed = any(s in matched+jd_needs for s in ["Docker","AWS","Kubernetes","CI/CD","Microservices"])
    if ai_needed:
        questions.append({"question":"Design an AI document assistant for 50,000 daily users. Cover ingestion, chunking, embedding, vector storage, retrieval, LLM calls, caching, and cost control.","category":"System Design","why":"The JD requires AI system design. Tests whether you can architect at scale.","tip":"Full flow: upload to chunk to embed to store to retrieve to prompt to LLM to cache. Mention latency and cost at each step."})
    elif infra_needed:
        questions.append({"question":"Design a zero-downtime deployment pipeline for microservices on Kubernetes. Cover build, test, canary release, rollback, and monitoring.","category":"System Design","why":"The JD requires cloud and infra design skills.","tip":"Docker build to registry to Helm chart to K8s rolling update to health checks to canary to alerts to rollback."})
    else:
        questions.append({"question":"Design a REST API backend for 100K daily active users. Cover DB schema, caching, auth, rate limiting, and horizontal scaling.","category":"System Design","why":"System design is tested in most engineering interviews.","tip":"DB schema and indexes, Redis cache, JWT auth, rate limit middleware, load balancer, read replicas."})

    questions.append({"question":"Tell me about a time something you built had a bug or failed in production. What broke, how did you find it, how did you fix it, and what did you change?","category":"Behavioural","why":"Tests ownership, debugging maturity, and learning from failures.","tip":"Use STAR. End strong: what monitoring or process you added to prevent recurrence."})

    return {"questions":questions[:10],"matched":matched,"gaps":gaps,"bonus":bonus[:6],"match_pct":round(len(matched)/max(len(jd_needs),1)*100)}


@app.route("/api/questions/generate", methods=["POST"])
@app.route("/api/interview/questions", methods=["POST"])  # alias
def generate_questions():
    """Compare resume vs JD. Return targeted questions instantly. No Ollama."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data            = request.get_json()
    resume_text     = data.get("resume_text", "").strip()
    job_description = data.get("job_description", "").strip()
    if not resume_text:     return jsonify({"error": "resume_text is required"}), 400
    if not job_description: return jsonify({"error": "job_description is required"}), 400
    try:
        return jsonify(_generate_questions(resume_text, job_description)), 200
    except Exception as e:
        return jsonify({"error": "Failed: {}".format(e)}), 500

# ── Test / History ─────────────────────────────────────────────────────────────

@app.route("/api/test", methods=["POST"])
def test():
    data = request.get_json() or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400
    return jsonify(analyze_resume(text))


@app.route("/api/history", methods=["GET"])
def get_history():
    try:
        files = sorted(
            [f for f in os.listdir(HISTORY_FOLDER) if f.endswith(".json")],
            reverse=True,
        )[:10]
        history = []
        for fn in files:
            with open(os.path.join(HISTORY_FOLDER, fn), "r", encoding="utf-8") as f:
                d = json.load(f)
            history.append({
                "filename":  fn,
                "timestamp": d.get("timestamp", fn.replace(".json", "")),
                "type":      d.get("analysis_type", "basic"),
            })
        return jsonify({"history": history}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("AI Resume Analyzer  v5.0")
    print("=" * 60)
    print("http://localhost:5000")
    print("POST /api/parse")
    print("POST /api/analyze-with-jd")
    print("POST /api/build-resume        <- SSE streaming")
    print("POST /api/build-resume-sync   <- sync fallback")
    print("POST /api/questions/generate  <- interview questions (instant)")
    print("POST /api/interview/questions <- interview questions (alias)")
    print("GET  /api/health")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)