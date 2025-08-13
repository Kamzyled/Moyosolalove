// static/app.js
const $ = (sel) => document.querySelector(sel);
const screens = {
  home: $("#screen-home"),
  create: $("#screen-create"),
  code: $("#screen-code"),
  join: $("#screen-join"),
  p1: $("#screen-p1"),
  p2: $("#screen-p2"),
  result: $("#screen-result"),
};

let state = {
  code: null,
  role: null, // "p1" or "p2"
  name: null,
  game: null,
};

function show(name){
  Object.values(screens).forEach(s=>s.classList.remove("active"));
  screens[name].classList.add("active");
}

function setCodeText(text){
  $("#game-code").textContent = text || "— — — — — —";
}

// ---------- Home buttons ----------
$("#btn-invite").addEventListener("click", ()=> show("create"));
$("#btn-join").addEventListener("click", ()=> show("join"));
$("#back-home-1").addEventListener("click", ()=> show("home"));
$("#back-home-2").addEventListener("click", ()=> show("home"));

// ---------- Create flow ----------
$("#create-go").addEventListener("click", async ()=>{
  const ownerName = $("#create-name").value.trim() || "Player 1";
  const res = await fetch("/api/create",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ownerName, editionName:"Moyosola"})});
  const data = await res.json();
  if(data.code){
    state.code = data.code;
    state.role = "p1";
    state.name = ownerName;
    state.game = data.game;
    setCodeText(state.code);
    show("code");
  } else {
    alert("Could not create game. Try again.");
  }
});

$("#go-p1").addEventListener("click", async ()=>{
  const g = await refreshState();
  if(!g) return;
  if(g.phase !== "p1_answer"){
    alert("Game is not in Player 1 answer phase.");
    return;
  }
  loadP1Question(g);
  show("p1");
});

// ---------- Join flow ----------
$("#join-go").addEventListener("click", async ()=>{
  const name = $("#join-name").value.trim() || "Player 2";
  const code = $("#join-code").value.trim();
  if(!code) return alert("Enter the game code.");
  const res = await fetch("/api/join",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({code, name})});
  const data = await res.json();
  if(data.error){ alert(data.error); return; }
  state.role = "p2";
  state.name = name;
  state.code = code;
  state.game = data.game;
  // If P1 still answering, wait; otherwise go to guessing
  const g = await refreshState();
  if(g.phase === "p2_guess"){
    loadP2Question(g);
    show("p2");
  } else {
    alert("Waiting for Player 1 to finish answering…");
    show("home");
  }
});

// ---------- P1 answering ----------
async function refreshState(){
  if(!state.code) return null;
  const res = await fetch("/api/state",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({code: state.code})});
  const data = await res.json();
  if(data.error) { alert(data.error); return null; }
  state.game = data.game;
  return state.game;
}

function loadP1Question(g){
  const i = g.currentIndex;
  const q = g.questions[i];
  $("#p1-question").textContent = q;
  $("#p1-progress").textContent = `${i+1} / ${g.questions.length}`;
  $("#p1-answer").value = "";
}

$("#p1-submit").addEventListener("click", async ()=>{
  const ans = $("#p1-answer").value.trim();
  if(!ans) return alert("Please enter your answer.");
  const res = await fetch("/api/p1/answer",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({code: state.code, answer: ans})});
  const data = await res.json();
  if(data.error){ alert(data.error); return; }
  const g = data.game;
  if(g.phase === "p2_guess"){
    alert("All set! Tell your friend to join with the code: " + g.code);
    show("home");
  } else {
    loadP1Question(g);
  }
});

// ---------- P2 guessing ----------
function loadP2Question(g){
  const i = g.currentIndex;
  const q = g.questions[i];
  $("#p2-question").textContent = q;
  $("#p2-progress").textContent = `${i+1} / ${g.questions.length}`;
  $("#p2-guess").value = "";
  $("#match-flash").classList.add("hidden");
}

$("#p2-submit").addEventListener("click", async ()=>{
  const guess = $("#p2-guess").value.trim();
  if(!guess) return alert("Enter your guess.");
  const res = await fetch("/api/p2/guess",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({code: state.code, guess})});
  const data = await res.json();
  if(data.error){ alert(data.error); return; }
  const g = data.game;
  // show match flash only if score increased
  // We can’t know previous score here; do a quick refetch to animate at end instead
  if(g.phase === "done"){
    animateResults(g);
    show("result");
  } else {
    loadP2Question(g);
  }
});

// ---------- Results ----------
function animateResults(g){
  const pct = Math.round((g.score / g.maxScore) * 100);
  const fill = $("#meter-fill");
  const label = $("#meter-label");
  fill.style.width = "0%";
  label.textContent = "0%";
  setTimeout(()=>{
    fill.style.width = pct + "%";
    let cur = 0;
    const t = setInterval(()=>{
      cur += 2;
      if(cur >= pct){ cur = pct; clearInterval(t); }
      label.textContent = cur + "%";
    }, 20);
  }, 50);

  const msg = $("#result-message");
  if(pct >= 80) msg.textContent = "Unbreakable Bond! 💎 You two are elite!";
  else if(pct >= 50) msg.textContent = "Strong Connection! 🌟 Keep the vibes!";
  else msg.textContent = "Needs More Adventures! 🌱 Time to create memories!";
}

$("#play-again").addEventListener("click", async ()=>{
  const res = await fetch("/api/reset",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({code: state.code})});
  const data = await res.json();
  if(data.error){ alert(data.error); return; }
  loadP2Question(data.game);
  show("p2");
});
$("#go-home").addEventListener("click", ()=> location.reload());
const [numQuestions, setNumQuestions] = useState(10); // default 10
