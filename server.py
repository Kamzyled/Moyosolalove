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
  "What’s the first thing you noticed about me?",
  "If we could go anywhere together, where would you take me?",
  "What song reminds you of me?",
  "What’s your favorite memory with me?",
  "Do you prefer hugs or kisses from me?",
  "If I cooked for you, what would you want me to make?",
  "What nickname would you give me?",
  "Which outfit of mine do you like most?",
  "If we danced together, what song should play?",
  "What’s the sweetest thing I’ve ever said to you?",
  "Would you rather hold my hand or look into my eyes?",
  "What movie would we watch together on a rainy day?",
  "Which emoji reminds you of me?",
  "If you could buy me one gift right now, what would it be?",
  "What color do you think suits me best?",
  "What pet name would you like me to call you?",
  "What food would we share on a date?",
  "Which time of day do you enjoy talking to me most?",
  "If I got sad, how would you cheer me up?",
  "What’s your favorite compliment I’ve given you?",
  "Would you rather cuddle under a blanket or take a walk with me?",
  "Which romantic place would you take me to?",
  "What flavor of ice cream reminds you of me?",
  "If we were in a movie, what would our love story be called?",
  "Which song should be ‘our song’?",
  "What do you think I dream about?",
  "Would you write me a love letter or sing me a song?",
  "What’s your favorite thing I say to you?",
  "If we could time travel, where would we go together?",
  "What’s the cutest thing I’ve ever done?",
  "Which flower reminds you of me?",
  "Would you rather travel with me to the beach or mountains?",
  "What’s the first word that comes to your mind when you see me?",
  "What’s your favorite way I make you smile?",
  "Which celebrity couple are we most like?",
  "If I was sick, what would you do for me?",
  "Would you rather slow dance or laugh together?",
  "Which dessert would we share on a date?",
  "What’s my most attractive feature?",
  "Which outfit would you pick for me to wear on a date?",
  "What’s one secret you’d tell only me?",
  "What’s your favorite way I say your name?",
  "Would you rather spend a day talking or doing activities together?",
  "What’s a song lyric that reminds you of us?",
  "Which drink should we share on a date?",
  "If we were in a book, what would the title be?",
  "What’s the funniest thing I’ve said to you?",
  "Would you rather watch the sunset or sunrise with me?",
  "What’s your favorite time we spent together?",
  "What scent reminds you of me?",
  "Would you rather get a handwritten note or a surprise gift from me?",
  "Which season do you think is most romantic for us?",
  "What’s your favorite nickname I use for you?",
  "Which romantic movie scene reminds you of us?",
  "Would you rather plan a date or be surprised by me?",
  "What’s the cutest thing you imagine me doing?",
  "If we took a photo right now, what pose would we do?",
  "Which fruit reminds you of me?",
  "What would our dream home look like?",
  "What’s the nicest thing you’d cook for me?",
  "If I could sing you one song, what should it be?",
  "Which animal reminds you of me?",
  "Would you rather dance in the rain or talk under the stars with me?",
  "What’s my best personality trait?",
  "If I made you a playlist, what would it be called?",
  "Which romantic gesture do you like most?",
  "Would you rather take a long walk or a short trip with me?",
  "What’s your favorite way to spend the evening with me?",
  "What’s something small that makes you think of me?",
  "Would you rather sit beside me or across from me on a date?",
  "Which gift would mean the most to you from me?",
  "What’s one dream you have for us?",
  "Would you rather whisper or text sweet things to me?",
  "Which holiday would you like to spend together?",
  "What’s the sweetest thing you imagine me doing for you?",
  "Would you rather have matching outfits or matching jewelry?",
  "Which romantic place do you want to visit with me?",
  "What’s your favorite compliment to give me?",
  "If I disappeared for a day, what would you miss most?",
  "Which photo of me do you like the most?",
  "Would you rather sit in silence or talk endlessly with me?",
  "Which drink would we toast to our love with?",
  "What would our wedding theme be?",
  "Which fictional couple are we most like?",
  "What’s your favorite way I show you I care?",
  "Would you rather get a song dedicated or a letter written by me?",
  "What’s my cutest habit?",
  "Which flower would you give me?",
  "What’s one promise you’d make to me?",
  "Would you rather share a blanket or a meal with me?",
  "What’s your favorite laugh moment we’ve shared?",
  "If we danced, who would lead?",
  "Which romantic city should we visit together?",
  "What’s one word that describes our connection?",
  "Would you rather spend a day inside or outside with me?",
  "What’s your favorite thing I do without knowing?",
  "Which smell would you choose to be ‘our scent’?",
  "What’s the best compliment I’ve ever given you?",
  "Would you rather watch fireworks or stargaze with me?"

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
