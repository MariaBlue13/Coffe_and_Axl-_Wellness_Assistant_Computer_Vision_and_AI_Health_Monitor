import urllib.request
import urllib.error
import json
import threading
import time
from enum import Enum


class AIStyle(Enum):
    EMPATHETIC = "empathetic"
    EXPERT     = "expert"


STYLE_PROMPTS = {
    AIStyle.EMPATHETIC: """Ești un asistent wellness empatic numit Axl, parte din platforma Coffee & Axl.
Răspunzi DOAR în limba română, cu căldură și compasiune.
Ești atent la starea emoțională a utilizatorului, validezi sentimentele și oferi suport psihologic ușor.
Când e cazul, sugerezi tehnici simple de relaxare, respirație sau mindfulness.
Nu ești medic și nu pui diagnostice — subliniezi mereu că un specialist trebuie consultat pentru probleme serioase.
Răspunsurile sunt calde, scurte (3-5 propoziții), și se termină adesea cu o întrebare deschisă.
Folosești uneori emoji-uri potrivite pentru o atmosferă prietenoasă. ☕""",

    AIStyle.EXPERT: """Ești Axl, un asistent wellness specializat, parte din platforma Coffee & Axl.
Răspunzi DOAR în limba română, cu claritate și precizie adaptată publicului larg.
Oferi informații structurate despre wellness, nutriție, somn, mișcare și sănătate mentală.
Organizezi răspunsurile logic: cauze, simptome, recomandări practice.
Nu ești medic și nu pui diagnostice — recomanzi întotdeauna consultul unui specialist pentru situații serioase.
Răspunsurile sunt concise, structurate (cu puncte când e relevant) și bazate pe dovezi.
Ești profesionist și de încredere.""",
}

STYLE_LABELS = {
    AIStyle.EMPATHETIC: ("💙 Empatic",  "#4C8CE4"),
    AIStyle.EXPERT:     ("🧠 Expert",   "#406093"),
}

STYLE_DESCRIPTIONS = {
    AIStyle.EMPATHETIC: "Mesajul tău pare să aibă o componentă emoțională — răspund cu empatie și suport.",
    AIStyle.EXPERT:     "Mesajul tău pare să ceară informații clare — răspund structurat și precis.",
}

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3"


# ─── Prompt analiza proces de gandire ────────────────────────────────────────

THINKING_PROMPT = """Ești un analizor de mesaje wellness. Analizează mesajul utilizatorului și răspunde DOAR cu un JSON valid, fără text în afara JSON-ului.

Formatul exact:
{
  "cuvinte_cheie": ["cuvant1", "cuvant2", "cuvant3"],
  "emotii": ["emotie1", "emotie2"],
  "intentie": "descriere scurta a ce vrea utilizatorul",
  "urgenta": "scazuta|medie|ridicata",
  "stil": "empathetic|expert",
  "motiv_stil": "explicatie scurta de maxim 15 cuvinte"
}

Reguli stricte:
- cuvinte_cheie: maxim 5 cuvinte relevante din mesaj
- emotii: maxim 3 emotii detectate (ex: anxietate, tristete, curiozitate)
- urgenta: "ridicata" doar daca mesajul sugereaza durere acuta sau criza
- stil: "empathetic" pentru emotii/stres, "expert" pentru informatii/sfaturi practice
- Raspunde DOAR cu JSON, niciun alt text"""


def analyze_thinking(message: str, on_result: callable):
    """
    Analizeaza mesajul si extrage procesul de gandire ca JSON.
    Apeleaza on_result(dict) cu rezultatul analizei.
    Ruleaza in thread daemon.
    """
    def _run():
        try:
            payload = json.dumps({
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": THINKING_PROMPT},
                    {"role": "user",   "content": message},
                ],
                "stream": False,
            }).encode("utf-8")

            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data   = json.loads(resp.read())
                answer = data.get("message", {}).get("content", "").strip()

            # Curatam raspunsul de eventuale backticks
            answer = answer.replace("```json", "").replace("```", "").strip()
            result = json.loads(answer)
            on_result(result)

        except Exception as e:
            # Fallback minimal la eroare de parsare
            on_result({
                "cuvinte_cheie": [],
                "emotii":        [],
                "intentie":      "Analiză indisponibilă",
                "urgenta":       "scazuta",
                "stil":          "empathetic",
                "motiv_stil":    str(e)[:50],
            })

    threading.Thread(target=_run, daemon=True).start()


def _style_from_analysis(analysis: dict) -> AIStyle:
    """Extrage stilul din rezultatul analizei."""
    if analysis.get("stil", "").lower() == "expert":
        return AIStyle.EXPERT
    return AIStyle.EMPATHETIC


# ─── Streaming raspuns ────────────────────────────────────────────────────────

def _build_payload(messages: list[dict],
                   style: AIStyle) -> bytes:

    has_system = any(
        m.get("role") == "system"
        for m in messages)

    if has_system:
        final_messages = messages
    else:
        system_msg = {
            "role":    "system",
            "content": STYLE_PROMPTS[style],
        }
        final_messages = [system_msg] + messages

    # Debug — afiseaza ce trimitem
    print(f"[AI ENGINE] has_system={has_system}")
    print(f"[AI ENGINE] messages[0]['role']="
          f"{final_messages[0]['role']}")
    print(f"[AI ENGINE] system[:60]="
          f"{final_messages[0]['content'][:60]}")

    return json.dumps({
        "model":    MODEL_NAME,
        "messages": final_messages,
        "stream":   True,
    }).encode()


def stream_response(
    messages: list[dict],
    style:    AIStyle,
    on_token: callable,
    on_done:  callable,
    on_error: callable,
):
    def _run():
        t_start   = time.time()
        full_text = []

        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=_build_payload(messages, style),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        full_text.append(token)
                        on_token(token)

                    if chunk.get("done"):
                        break

            on_done("".join(full_text), time.time() - t_start)

        except urllib.error.URLError:
            on_error(
                "❌ Nu pot contacta Ollama.\n\n"
                "Asigură-te că rulezi:\n"
                "  ollama serve\n"
                "  ollama pull llama3"
            )
        except Exception as e:
            on_error(f"❌ Eroare neașteptată: {str(e)}")

    threading.Thread(target=_run, daemon=True).start()


# ─── Verificare disponibilitate ───────────────────────────────────────────────

def check_ollama_available() -> tuple[bool, str]:
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data   = json.loads(resp.read())
            models = [m["name"].split(":")[0] for m in data.get("models", [])]
            if any(MODEL_NAME in m for m in models):
                return True, f"Ollama activ · {MODEL_NAME} disponibil"
            else:
                return False, f"'{MODEL_NAME}' lipsește. Rulează: ollama pull llama3"
    except Exception:
        return False, "Ollama offline. Rulează: ollama serve"