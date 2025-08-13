# server.py
import os, json, time, random, string, threading
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static", template_folder="templates")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
GAMES_FILE = os.path.join(DATA_DIR, "games.json")
_LOCK = threading.Lock()

# ---------------- Utilities ----------------
def load_games():
    if not os.path.exists(GAMES_FILE):
        return {}
    try:
        with open(GAMES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_games(g):
    tmp = GAMES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(g, f, ensure_ascii=False, indent=2)
    os.replace(tmp, GAMES_FILE)

def new_code():
    # 6-digit numeric code (easy to share)
    return "".join(random.choice(string.digits) for _ in range(6))

# Default question set (Player1 answers truth, Player2 guesses)
DEFAULT_QUESTIONS = [
    "Your favorite color?",
    "Favorite food?",
    "Dream vacation spot?",
    "Morning or night person?",
    "Favorite music artist?",
    "Cats or dogs?",
    "Go-to comfort movie?",
    "Sweet or spicy?",
    "Ideal weekend activity?",
    "One word that describes you?"
]

# ---------------- Routes ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"ok": True, "time": time.time()})

@app.route("/api/create", methods=["POST"])
def api_create():
    """
    Player1 creates a room.
    Body: { ownerName: string, editionName: string (optional, e.g., 'Moyosola') }
    Returns: { code, game }
    """
    body = request.get_json() or {}
    owner = (body.get("ownerName") or "Player 1").strip()[:40]
    edition = (body.get("editionName") or "Moyosola").strip()[:60]

    with _LOCK:
        games = load_games()
        code = new_code()
        while code in games:
            code = new_code()
        games[code] = {
            "code": code,
            "edition": edition,
            "createdAt": time.time(),
            "ownerName": owner,
            "p1": {"name": owner, "answers": {}, "ready": False},
            "p2": {"name": None, "ready": False},
            "questions": DEFAULT_QUESTIONS,
            "phase": "p1_answer",  # p1_answer -> p2_guess -> done
            "currentIndex": 0,
            "score": 0,
            "maxScore": len(DEFAULT_QUESTIONS)
        }
        save_games(games)

    return jsonify({"code": code, "game": games[code]})

@app.route("/api/join", methods=["POST"])
def api_join():
    """
    Player2 joins with code.
    Body: { code, name }
    """
    body = request.get_json() or {}
    code = (body.get("code") or "").strip()
    name = (body.get("name") or "Player 2").strip()[:40]

    with _LOCK:
        games = load_games()
        game = games.get(code)
        if not game:
            return jsonify({"error": "Game not found"}), 404
        if game["p2"]["name"] is None:
            game["p2"]["name"] = name
            save_games(games)
        return jsonify({"game": game})

@app.route("/api/state", methods=["POST"])
def api_state():
    """
    Get full state for a code.
    Body: { code }
    """
    body = request.get_json() or {}
    code = (body.get("code") or "").strip()
    with _LOCK:
        games = load_games()
        game = games.get(code)
        if not game:
            return jsonify({"error": "Game not found"}), 404
        return jsonify({"game": game})

@app.route("/api/p1/answer", methods=["POST"])
def api_p1_answer():
    """
    Player1 submits an answer for current question index.
    Body: { code, answer }
    When P1 finishes all, phase -> p2_guess
    """
    body = request.get_json() or {}
    code = (body.get("code") or "").strip()
    answer = (body.get("answer") or "").strip()[:80]

    with _LOCK:
        games = load_games()
        game = games.get(code)
        if not game:
            return jsonify({"error": "Game not found"}), 404
        if game["phase"] != "p1_answer":
            return jsonify({"error": "Not in Player 1 answer phase"}), 400

        idx = game["currentIndex"]
        q_len = len(game["questions"])
        game["p1"]["answers"][str(idx)] = answer
        if idx + 1 >= q_len:
            game["phase"] = "p2_guess"
            game["currentIndex"] = 0
            game["p1"]["ready"] = True
        else:
            game["currentIndex"] += 1

        save_games(games)
        return jsonify({"game": game})

@app.route("/api/p2/guess", methods=["POST"])
def api_p2_guess():
    """
    Player2 submits a guess for current question index.
    Body: { code, guess }
    Scores +1 if matches Player1's answer (case-insensitive, trimmed).
    When finished all, phase -> done
    """
    body = request.get_json() or {}
    code = (body.get("code") or "").strip()
    guess = (body.get("guess") or "").strip()[:80]

    with _LOCK:
        games = load_games()
        game = games.get(code)
        if not game:
            return jsonify({"error": "Game not found"}), 404
        if game["phase"] != "p2_guess":
            return jsonify({"error": "Not in Player 2 guess phase"}), 400

        idx = game["currentIndex"]
        q_len = len(game["questions"])
        p1_answer = (game["p1"]["answers"].get(str(idx)) or "").strip().lower()
        if guess.strip().lower() == p1_answer and p1_answer != "":
            game["score"] += 1

        if idx + 1 >= q_len:
            game["phase"] = "done"
        else:
            game["currentIndex"] += 1

        save_games(games)
        return jsonify({"game": game})

@app.route("/api/reset", methods=["POST"])
def api_reset():
    """
    Soft reset a finished game to p2_guess phase (for replay with same answers)
    Body: { code }
    """
    body = request.get_json() or {}
    code = (body.get("code") or "").strip()
    with _LOCK:
        games = load_games()
        game = games.get(code)
        if not game:
            return jsonify({"error": "Game not found"}), 404
        game["phase"] = "p2_guess"
        game["currentIndex"] = 0
        game["score"] = 0
        save_games(games)
        return jsonify({"game": game})

# Static file for PWA icon or future assets (optional)
@app.route("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico", mimetype="image/x-icon")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
