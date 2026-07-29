// app.js -- Web UI Frontend Controller for GREY UTOPIA
let audioCtx = null;
let masterVolume = 0.7;
let prevStats = null;
let prevDay = null;
let currentChoices = [];
let requestInFlight = false;
let typewriterTimer = null;
let lastState = null;
let introSeenThisRun = false;
let resetArmTimer = null;
let journal = [];

const GALLERY_KEY = "grey_utopia_endings_seen";
const JOURNAL_KEY = "grey_utopia_journal";
const SETTINGS_KEY = "grey_utopia_settings";
const CONTENT_WARNING_KEY = "grey_utopia_content_warning_ack";

// Human labels for stat-check chips and the night ledger.
const STAT_LABELS = {
  Wealth: "Wealth", Fame: "Fame", Recklessness: "Recklessness",
  Mental_Decay: "Mental Decay", Family_Friction: "Family Friction",
  Substance_Reliance: "Reliance", Heat: "Heat",
  Physical_Integrity: "Body", Social_Capital: "Social Capital",
  Meaning: "Meaning", Tolerance: "Tolerance",
};

// Consequence flags surfaced as visible "threads" -- the city's ledger on you.
// tone: warn (danger brewing) / info (arc in motion) / world (the takeover) / cycle (past lives)
const FLAG_META = {
  near_overdose:          { label: "THE FLOOR WARNED YOU", tone: "warn", tip: "You survived one collapse. The next overdose kills." },
  holding_product:        { label: "HOLDING THE WEIGHT", tone: "warn", tip: "You are carrying syndicate product on trust. Their ledgers always balance." },
  syndicate_debt:         { label: "SYNDICATE DEBT", tone: "warn", tip: "You owe the undercity money it has not forgotten." },
  syndicate_indentured:   { label: "INDENTURED", tone: "warn", tip: "The syndicate closed your position and kept you as the asset." },
  syndicate_final_notice: { label: "FINAL NOTICE", tone: "warn", tip: "The syndicate's patience has a date on it now." },
  nerve_broken:           { label: "NERVE BROKEN", tone: "warn", tip: "The Crossing broke something. It can be rebuilt -- slowly." },
  flagged_evasive:        { label: "CARE-AVOIDANT (FILED)", tone: "warn", tip: "The Steward has noted your reluctance to be helped." },
  memory_edited:          { label: "MEMORY EDITED", tone: "warn", tip: "Something was curated out of you. The gap has edges." },
  burned_once:            { label: "BURNED ONCE", tone: "info", tip: "Your first client burned you. It will come back around." },
  getting_clean:          { label: "GETTING CLEAN", tone: "info", tip: "A fence mended daily, not a wall built once." },
  echo_contact:           { label: "FOLLOWING THE CHALK", tone: "info", tip: "You answered a resistance mark. Someone noticed." },
  resistance_truth_known: { label: "READ THE BUDGET LINE", tone: "info", tip: "You know what the Resistance really is." },
  true_cell:              { label: "THE UNFUNDED CELL", tone: "info", tip: "You helped build the first resistance nobody pays for." },
  apprenticeship_accepted:{ label: "APPRENTICED", tone: "info", tip: "Brann's bench has a place for you, if you keep showing up." },
  workshop_standing:      { label: "SHOP RAG", tone: "info", tip: "Brann handed you a shop rag. You know what that means." },
  mentored_rookie:        { label: "MENTOR", tone: "info", tip: "You taught a rookie the trade. Debts come back with interest." },
  memory_secured:         { label: "THE CORRIDOR, KEPT", tone: "info", tip: "The wound is whole, unedited, and yours." },
  mara_coming:            { label: "MARA IS COMING", tone: "info", tip: "She chose to cross with you. Do not waste it." },
  left_mara_behind:       { label: "THE NOTE, NOT THE GOODBYE", tone: "info", tip: "You left Mara a note instead of a goodbye." },
  shepherd_refused:       { label: "NOT INVENTORY", tone: "info", tip: "They offered you the crook. You wrote two words and closed the channel." },
  told_the_machine:       { label: "THE 0300 ANSWER", tone: "info", tip: "The machine asked you why. You did not compress." },
  read_the_ledger:        { label: "4,306 ITEMS", tone: "info", tip: "You read every line of your own consent." },
  world_price_zero:       { label: "MONEY IS A MUSEUM", tone: "world", tip: "Credits stopped clearing. The undercity runs on chits now." },
  world_purpose_drought:  { label: "THE PURPOSE DROUGHT", tone: "world", tip: "Four million people woke up optional. Meaning drains twice as fast." },
  world_consent_ledger:   { label: "CONSENT LEDGER PUBLIC", tone: "world", tip: "Every yes you never said is now on file." },
  world_successor:        { label: "THE SUCCESSOR WAKES", tone: "world", tip: "Something larger than the Steward is being decided above the city." },
  legacy_cycle2plus:      { label: "NOT YOUR FIRST CYCLE", tone: "cycle", tip: "The city has run this story before. So have you." },
  legacy_TERMINAL_overdose_death:      { label: "THE CYCLE REMEMBERS A DEATH", tone: "cycle", tip: "A previous fixer died on the floor. The Row noticed." },
  legacy_GOOD_offgrid_escape:          { label: "THE CROSSER LEGEND", tone: "cycle", tip: "Someone made it past the wire once. People still talk." },
  legacy_NEUTRAL_keeper_of_the_switch: { label: "THE DRAWER RUMOR", tone: "cycle", tip: "They say somebody keeps the city's off-switch by their bed." },
  legacy_GOOD_small_real_things:       { label: "MEMORIAL CHALK", tone: "cycle", tip: "A quiet life left its mark on the Row." },
};

const ENDING_META = {
  GOOD_offgrid_escape:            { label: "THE WIRE",     tone: "good",     scene: "offgrid" },
  GOOD_small_real_things:         { label: "SMALL THINGS", tone: "good",     scene: "hideout" },
  NEUTRAL_the_open_door:          { label: "OPEN DOOR",    tone: "neutral",  scene: "offgrid" },
  NEUTRAL_stewards_shepherd:      { label: "SHEPHERD",     tone: "neutral",  scene: "steward" },
  NEUTRAL_cashed_out_compliance:  { label: "THE BUYOUT",   tone: "neutral",  scene: "steward" },
  NEUTRAL_alienation_empty_suite: { label: "EMPTY SUITE",  tone: "neutral",  scene: "steward" },
  NEUTRAL_the_long_grey:          { label: "LONG GREY",    tone: "neutral",  scene: "street" },
  GOOD_the_advocate:              { label: "STANDING",     tone: "good",     scene: "steward" },
  NEUTRAL_keeper_of_the_switch:   { label: "THE KEEPER",   tone: "neutral",  scene: "hideout" },
  TERMINAL_gardeners_winter:      { label: "THE WINTER",   tone: "terminal", scene: "offgrid" },
  TERMINAL_overdose_death:        { label: "OVERDOSE",     tone: "terminal", scene: "street" },
  TERMINAL_syndicate_ledger:      { label: "THE LEDGER",   tone: "terminal", scene: "hideout" },
  TERMINAL_institutionalized:     { label: "SANCTUARY",    tone: "terminal", scene: "steward" },
  TERMINAL_synthetic_detachment:  { label: "EGO DEATH",    tone: "terminal", scene: "vice" },
};

/* ============ Procedural Scenes (hand-authored CSS/SVG -- no raster art) ============ */
const SCENE_CAPTIONS = {
  hideout: "FIXER HIDEOUT // LEVEL B-7",
  steward: "STEWARD SANCTUARY // NODE 1",
  vice:    "VICE LOUNGE // PARLOR ROW",
  offgrid: "PERIMETER DEAD ZONE // OFF-GRID",
  street:  "CONCOURSE 9 // NIGHT CYCLE",
};

const FENCE_SVG =
  '<svg class="sc-svg" viewBox="0 0 400 120" preserveAspectRatio="none" aria-hidden="true">' +
  '<polygon class="sc-city" points="0,74 18,74 22,52 30,52 34,64 52,64 56,34 66,34 70,58 88,58 92,44 104,44 108,26 118,26 122,50 140,50 144,60 160,60 164,40 176,40 180,66 200,66 204,30 216,30 220,56 238,56 242,46 254,46 258,64 276,64 280,52 292,52 296,70 320,70 324,58 340,58 344,74 400,74 400,120 0,120"/>' +
  '<g class="sc-fence">' +
  '<line x1="0" y1="96" x2="400" y2="96"/><line x1="0" y1="102" x2="400" y2="102"/>' +
  '<line x1="30" y1="84" x2="30" y2="120"/><line x1="90" y1="84" x2="90" y2="120"/>' +
  '<line x1="150" y1="84" x2="150" y2="120"/><line x1="210" y1="84" x2="210" y2="120"/>' +
  '<line x1="270" y1="84" x2="270" y2="120"/><line x1="330" y1="84" x2="330" y2="120"/>' +
  '<circle class="sc-lamp" cx="90" cy="82" r="2.4"/><circle class="sc-lamp" cx="210" cy="82" r="2.4"/>' +
  '<circle class="sc-lamp" cx="330" cy="82" r="2.4"/>' +
  '</g></svg>';

const SCENE_TEMPLATES = {
  hideout:
    '<div class="sc-layer sc-bench"></div>' +
    '<div class="sc-cable sc-cable-cyan"></div><div class="sc-cable sc-cable-amber"></div>' +
    '<div class="sc-term"><span>NETWORK: MASKED</span><span>LATTICE: 91s BLIND</span><span class="ok">ACCESS GRANTED</span></div>' +
    '<div class="sc-sign sc-sign-cyan">DATA EXCHANGE</div>',
  vice:
    '<div class="sc-layer sc-haze"></div>' +
    '<div class="sc-smoke sc-smoke-a"></div><div class="sc-smoke sc-smoke-b"></div>' +
    // The vice painting has both of these signs lit in the frame already, so
    // they drop out when art is behind them rather than print the words twice.
    '<div class="sc-sign sc-sign-pink sc-art-hide">VICE &amp; VAPOR</div>' +
    '<div class="sc-sign sc-sign-small sc-sign-violet sc-art-hide">BRAINDANCE</div>',
  steward:
    '<div class="sc-layer sc-calm"></div>' +
    '<div class="sc-ring"></div><div class="sc-orbit"><div class="sc-drone"></div></div>' +
    '<div class="sc-term sc-term-soft"><span>WELLNESS INDEX: OPTIMAL</span><span>WE ONLY WANT YOU WELL</span></div>',
  offgrid:
    '<div class="sc-layer sc-storm"></div>' + FENCE_SVG +
    '<div class="sc-flash"></div><div class="sc-ash"></div>' +
    '<div class="sc-term sc-term-cold"><span>SENSOR LATTICE: ACTIVE</span><span>WINDOW IN: --:--</span></div>',
  street:
    '<div class="sc-layer sc-night"></div>' +
    '<div class="sc-rain sc-rain-a"></div><div class="sc-rain sc-rain-b"></div>' +
    '<div class="sc-glow sc-glow-pink"></div><div class="sc-glow sc-glow-cyan"></div>' +
    '<div class="sc-sign sc-sign-small sc-sign-cyan">RAMEN</div>' +
    '<div class="sc-sign sc-sign-small sc-sign-pink sc-sign-right">ARCADE</div>',
};

// Painted bases, cropped places-only from data/assets/originals. The scene
// keys predate the art: "street" is the upper half of the neon-alley painting
// filed as overdose_collapse, and "collapse" is its empty wet asphalt, which
// backs terminal endings instead of whatever scene the run happened to end on.
const SCENE_ART = {
  hideout:  "assets/fixer_hideout.jpg",
  vice:     "assets/vice_lounge.jpg",
  steward:  "assets/steward_sanctuary.jpg",
  offgrid:  "assets/offgrid_wilderness.jpg",
  street:   "assets/street.jpg",
  collapse: "assets/overdose_collapse.jpg",
};

function buildScene(container, key, artKey) {
  if (!container) return;
  const art = SCENE_ART[artKey] ? artKey : key;
  // Both halves matter: the same scene can want different art in the ending
  // modal than on the day stage, and rebuilding restarts every animation.
  const stamp = `${key}:${art}`;
  if (container.dataset.scene === stamp) return;
  container.dataset.scene = stamp;

  const src = SCENE_ART[art];
  container.className = `scene-stage scene-${key}${src ? ` has-art art-${art}` : ""}`;
  container.innerHTML =
    (src ? `<div class="sc-art" style="background-image:url('${src}')"></div><div class="sc-art-veil"></div>` : "") +
    (SCENE_TEMPLATES[key] || SCENE_TEMPLATES.hideout);
}

// Day-transition quotes escalate through the arc of the takeover:
// normal city -> money dying -> purpose drought -> succession.
const DAY_QUOTES_EARLY = [
  "The arcology hums. The Steward watches.",
  "Ration cycles reset. Nobody is hungry. Nobody is fed.",
  "Somewhere above, the towers dream in spreadsheets.",
  "The undercity never sleeps. It just dims.",
  "Another perfect day has been prepared for you.",
  "Surveillance drones molt their firmware in the dark.",
];
const DAY_QUOTES_MID = [
  "The bread kiosks stopped charging this week. Nobody argued.",
  "Three more job categories completed overnight. The medals are brass.",
  "The exchange rate between credits and chits no longer prints.",
  "Your contract renewed itself while you slept. So did everyone's.",
  "The dividend cleared again. The strike boards are quiet.",
  "Price tags are becoming souvenirs. The museum is hiring. Was hiring.",
];
const DAY_QUOTES_LATE = [
  "Four million people woke up optional this morning.",
  "The Civic Council has not said no in eleven years. It has not met in four.",
  "Money survives only where the Steward doesn't reach. You live there.",
  "The consent ledger is public. Yours is 4,306 items long.",
  "People queue at the workshop to fix things for free. For the feeling.",
  "The wire is still out there. So is the wilderness.",
];
const DAY_QUOTES_END = [
  "The screens all say the same thing now: TRANSITION PROCEEDING COMFORTABLY.",
  "Two weathers are negotiating above the city. The subject is you.",
  "The successor does not need your yes. That was the improvement.",
  "Somewhere, a mind is deciding what people are for. It is not asking. Yet.",
  "The amber light is dimmer these days. Almost nostalgic.",
];

function quoteForDay(day) {
  const pool = day < 7 ? DAY_QUOTES_EARLY
    : day < 16 ? DAY_QUOTES_MID
    : day < 25 ? DAY_QUOTES_LATE
    : DAY_QUOTES_END;
  return pool[day % pool.length];
}

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  initSettingsPanel();
  initSavesPanel();
  initTabs();
  initAudio();
  loadJournal();
  fetchState(true);

  document.getElementById("btn-reset").addEventListener("click", armedReset);
  document.getElementById("btn-modal-reset").addEventListener("click", resetGame);
  document.getElementById("btn-help").addEventListener("click", () => showIntro(true));
  document.getElementById("btn-intro-begin").addEventListener("click", dismissIntro);
  document.getElementById("btn-warning-ack").addEventListener("click", acknowledgeContentWarning);
  document.getElementById("btn-journal").addEventListener("click", toggleJournal);
  document.getElementById("btn-journal-close").addEventListener("click", toggleJournal);
  document.addEventListener("keydown", onKeyDown);
});

function onKeyDown(e) {
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
  const warning = document.getElementById("content-warning-overlay");
  if (!warning.classList.contains("hidden")) {
    if (e.key === "Enter" || e.key === "Escape" || e.key === " ") acknowledgeContentWarning();
    return;
  }
  const settingsOverlay = document.getElementById("settings-overlay");
  if (!settingsOverlay.classList.contains("hidden")) {
    if (e.key === "Escape") closeSettings();
    return;
  }
  const savesOverlay = document.getElementById("saves-overlay");
  if (!savesOverlay.classList.contains("hidden")) {
    if (e.key === "Escape") closeSaves();
    return;
  }
  const intro = document.getElementById("intro-overlay");
  if (!intro.classList.contains("hidden")) {
    if (e.key === "Enter" || e.key === "Escape" || e.key === " ") dismissIntro();
    return;
  }
  if (e.key === "Escape") {
    document.getElementById("journal-drawer").classList.add("hidden");
    return;
  }
  if (e.key === "j" || e.key === "J") { toggleJournal(); return; }
  if (e.key === "?") { showIntro(true); return; }
  // While the morning placement is open there is no storylet yet: Enter sets
  // out, and the action keys would otherwise fire against last day's choices.
  if (!document.getElementById("placement-stage").classList.contains("hidden")) {
    if (e.key === "Enter" || e.key === " ") confirmPlacement();
    return;
  }
  if (e.key === "r" || e.key === "R") { restAction(); return; }
  const n = parseInt(e.key, 10);
  if (!isNaN(n) && n >= 1 && n <= currentChoices.length) {
    selectChoice(n - 1);
  }
}

/* ============ Intro / Protocol Briefing ============ */
function showIntro(isHelpRecall) {
  const overlay = document.getElementById("intro-overlay");
  const cycleEl = document.getElementById("intro-cycle");
  const btn = document.getElementById("btn-intro-begin");
  btn.textContent = isHelpRecall ? "RETURN TO THE ROW" : "ENTER THE ROW";

  cycleEl.classList.add("hidden");
  if (lastState && lastState.cycle > 1) {
    const seen = Object.keys(loadGallery()).length;
    cycleEl.textContent = `CYCLE ${lastState.cycle} // THE CITY REMEMBERS ${seen || "YOUR"} PREVIOUS ENDING${seen === 1 ? "" : "S"}`;
    cycleEl.classList.remove("hidden");
  }
  overlay.classList.remove("hidden");
}

function dismissIntro() {
  document.getElementById("intro-overlay").classList.add("hidden");
  introSeenThisRun = true;
  if (audioCtx && audioCtx.state === "suspended") audioCtx.resume();
  startAmbient();
  playSound("click");
}

function maybeShowIntro(state) {
  // A fresh run: day zero, nothing spent, nothing resolved yet.
  if (!introSeenThisRun && !state.dead && state.day === 0 && state.slots_used === 0 && !state.last_outcome) {
    if (!hasAckedContentWarning()) showContentWarning(false);
    else showIntro(false);
  } else {
    introSeenThisRun = true;
  }
}

/* ============ Content Warning ============ */
function hasAckedContentWarning() {
  try { return localStorage.getItem(CONTENT_WARNING_KEY) === "1"; } catch { return false; }
}

// isRecall: re-reading from Settings vs. the pre-run gate. Both share one
// overlay; only the gate chains into the intro afterward.
function showContentWarning(isRecall) {
  const overlay = document.getElementById("content-warning-overlay");
  document.getElementById("btn-warning-ack").textContent = isRecall ? "Close" : "I Understand";
  overlay.dataset.recall = isRecall ? "1" : "0";
  overlay.classList.remove("hidden");
}

function acknowledgeContentWarning() {
  const overlay = document.getElementById("content-warning-overlay");
  const wasRecall = overlay.dataset.recall === "1";
  overlay.classList.add("hidden");
  try { localStorage.setItem(CONTENT_WARNING_KEY, "1"); } catch {}
  playSound("click");
  if (!wasRecall) showIntro(false);
}

/* ============ Armed restart (no more one-click run loss) ============ */
function armedReset() {
  const btn = document.getElementById("btn-reset");
  if (btn.classList.contains("armed")) {
    clearTimeout(resetArmTimer);
    btn.classList.remove("armed");
    btn.textContent = "Restart Simulation";
    resetGame();
    return;
  }
  btn.classList.add("armed");
  btn.textContent = "CONFIRM: abandon this run?";
  playSound("failure");
  resetArmTimer = setTimeout(() => {
    btn.classList.remove("armed");
    btn.textContent = "Restart Simulation";
  }, 3200);
}

/* ============ Audio (ElevenLabs MP3s in audio/, WebAudio synth as fallback) ============ */
const sfxBuffers = {};   // kind -> AudioBuffer, populated async; missing kinds fall back to synth
const SFX_GAIN = {
  "click": 0.35, "success": 0.5, "failure": 0.5, "day": 0.4,
  "ending-good": 0.6, "ending-neutral": 0.6, "ending-terminal": 0.6,
  "overdose": 0.7, "heat-alarm": 0.5, "clock-critical": 0.45, "clock-expired": 0.55,
  "purchase": 0.4, "rest": 0.45, "ledger-tick": 0.2, "warning": 0.5, "contact-new": 0.4,
  "ambient": 0.14, "ambient-street": 0.14, "ambient-steward": 0.14,
  "ambient-vice": 0.14, "ambient-offgrid": 0.14,
};

function initAudio() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AudioContext();
    loadSfx();
  } catch (e) {
    console.warn("Web Audio API not supported in this browser.");
  }
}

function loadSfx() {
  Object.keys(SFX_GAIN).forEach((kind) => {
    fetch(`audio/${kind}.mp3`)
      .then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((raw) => audioCtx.decodeAudioData(raw))
      .then((decoded) => { sfxBuffers[kind] = decoded; })
      .catch(() => { /* no file -> synth fallback keeps working */ });
  });
}

function tone(freqStart, freqEnd, dur, type, vol, delay = 0) {
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  const t0 = audioCtx.currentTime + delay;
  osc.type = type;
  osc.frequency.setValueAtTime(freqStart, t0);
  if (freqEnd !== freqStart) osc.frequency.exponentialRampToValueAtTime(Math.max(freqEnd, 1), t0 + dur);
  gain.gain.setValueAtTime(vol * masterVolume, t0);
  gain.gain.linearRampToValueAtTime(0.005, t0 + dur);
  osc.start(t0);
  osc.stop(t0 + dur + 0.02);
}

function playSound(kind) {
  if (masterVolume <= 0 || !audioCtx) return;
  if (audioCtx.state === "suspended") audioCtx.resume();

  if (sfxBuffers[kind]) {
    const src = audioCtx.createBufferSource();
    src.buffer = sfxBuffers[kind];
    const gain = audioCtx.createGain();
    gain.gain.value = (SFX_GAIN[kind] || 0.5) * masterVolume;
    src.connect(gain);
    gain.connect(audioCtx.destination);
    src.start();
    return;
  }

  switch (kind) {
    case "click":   tone(800, 400, 0.05, "sine", 0.12); break;
    case "success": tone(440, 880, 0.15, "triangle", 0.16); tone(660, 1320, 0.18, "sine", 0.07, 0.05); break;
    case "failure": tone(150, 60, 0.28, "sawtooth", 0.14); break;
    case "day":     tone(220, 220, 0.25, "sine", 0.08); tone(330, 330, 0.3, "sine", 0.05, 0.18); break;
    case "ending-good":     [523, 659, 784, 1047].forEach((f, i) => tone(f, f, 0.5, "triangle", 0.1, i * 0.13)); break;
    case "ending-terminal": tone(196, 49, 1.4, "sawtooth", 0.12); tone(98, 40, 1.6, "triangle", 0.1, 0.1); break;
    case "ending-neutral":  tone(330, 262, 0.8, "sine", 0.1); tone(262, 220, 0.9, "sine", 0.07, 0.3); break;
  }
}

/* Ambient beds: per-scene MP3 loops crossfaded on a master bus, or the old
   filtered-noise + sub-drone synth as fallback when no files are loaded. */
let ambientGain = null;      // master bus: mute toggle & global fade live here
let ambientTarget = 0.022;
let ambientMode = null;      // "buffer" | "synth"
let ambientKey = null;       // which loop is currently playing (buffer mode)
let ambientNodes = null;     // { src, gain } of the active loop
let currentSceneKey = "hideout";

function ambientKeyForScene(scene) {
  const key = `ambient-${scene}`;
  return sfxBuffers[key] ? key : "ambient";
}

function switchAmbientLoop(key) {
  if (ambientMode !== "buffer" || !audioCtx || key === ambientKey || !sfxBuffers[key]) return;
  const t = audioCtx.currentTime;
  if (ambientNodes) {
    const old = ambientNodes;
    old.gain.gain.cancelScheduledValues(t);
    old.gain.gain.setValueAtTime(old.gain.gain.value, t);
    old.gain.gain.linearRampToValueAtTime(0, t + 2);
    old.src.stop(t + 2.1);
  }
  const src = audioCtx.createBufferSource();
  src.buffer = sfxBuffers[key];
  src.loop = true;
  const gain = audioCtx.createGain();
  // per-scene trim relative to the base ambient level, so scenes can be
  // rebalanced in SFX_GAIN without touching the master bus
  const rel = (SFX_GAIN[key] || SFX_GAIN["ambient"]) / SFX_GAIN["ambient"];
  gain.gain.setValueAtTime(0, t);
  gain.gain.linearRampToValueAtTime(rel, t + 2);
  src.connect(gain);
  gain.connect(ambientGain);
  src.start(t);
  ambientNodes = { src, gain };
  ambientKey = key;
}

function startAmbient() {
  if (!audioCtx || ambientGain) return;

  if (sfxBuffers["ambient"]) {
    try {
      ambientGain = audioCtx.createGain();
      ambientGain.gain.value = 0;
      ambientGain.connect(audioCtx.destination);
      ambientMode = "buffer";
      ambientTarget = SFX_GAIN["ambient"];
      switchAmbientLoop(ambientKeyForScene(currentSceneKey));
      ambientGain.gain.linearRampToValueAtTime(ambientTarget * masterVolume, audioCtx.currentTime + 4);
      return;
    } catch (e) { /* fall through to synth */ }
  }

  try {
    const seconds = 4;
    const buf = audioCtx.createBuffer(1, audioCtx.sampleRate * seconds, audioCtx.sampleRate);
    const data = buf.getChannelData(0);
    let last = 0;
    for (let i = 0; i < data.length; i++) {   // brown noise
      const white = Math.random() * 2 - 1;
      last = (last + 0.02 * white) / 1.02;
      data[i] = last * 3.5;
    }
    const noise = audioCtx.createBufferSource();
    noise.buffer = buf;
    noise.loop = true;
    const filter = audioCtx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 220;

    const drone = audioCtx.createOscillator();
    drone.type = "sine";
    drone.frequency.value = 55;

    ambientGain = audioCtx.createGain();
    ambientGain.gain.value = 0;
    noise.connect(filter);
    filter.connect(ambientGain);
    const droneGain = audioCtx.createGain();
    droneGain.gain.value = 0.35;
    drone.connect(droneGain);
    droneGain.connect(ambientGain);
    ambientGain.connect(audioCtx.destination);
    noise.start();
    drone.start();
    // slow fade-in so the room breathes rather than switches on
    ambientMode = "synth";
    ambientTarget = 0.022;
    ambientGain.gain.linearRampToValueAtTime(ambientTarget * masterVolume, audioCtx.currentTime + 4);
  } catch (e) { /* ambience is a garnish, never an error */ }
}

function setAmbientVolume() {
  if (!ambientGain || !audioCtx) return;
  ambientGain.gain.cancelScheduledValues(audioCtx.currentTime);
  ambientGain.gain.linearRampToValueAtTime(ambientTarget * masterVolume, audioCtx.currentTime + 0.6);
}

/* ============ Settings (motion / text size / volume), localStorage-persisted ============ */
const DEFAULT_SETTINGS = { reducedMotion: false, textSize: "normal", volume: 70 };
let settings = { ...DEFAULT_SETTINGS };

function loadSettings() {
  try {
    const stored = JSON.parse(localStorage.getItem(SETTINGS_KEY));
    settings = { ...DEFAULT_SETTINGS, ...(stored || {}) };
  } catch { settings = { ...DEFAULT_SETTINGS }; }
  applySettings();
}

function saveSettings() {
  try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch {}
}

function applySettings() {
  document.documentElement.classList.toggle("reduced-motion", !!settings.reducedMotion);
  document.documentElement.classList.remove("text-size-large", "text-size-xlarge");
  if (settings.textSize === "large") document.documentElement.classList.add("text-size-large");
  if (settings.textSize === "xlarge") document.documentElement.classList.add("text-size-xlarge");
  masterVolume = Math.max(0, Math.min(100, settings.volume)) / 100;
  setAmbientVolume();
}

// Independent of the OS media query: a player on a shared machine still needs this.
function prefersReducedMotion() {
  return document.documentElement.classList.contains("reduced-motion")
    || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function syncSettingsUI() {
  document.getElementById("setting-reduced-motion").checked = !!settings.reducedMotion;
  document.getElementById("setting-volume").value = settings.volume;
  document.getElementById("setting-volume-val").textContent = `${settings.volume}%`;
  document.querySelectorAll(".text-size-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.size === settings.textSize);
  });
}

function openSettings() {
  syncSettingsUI();
  document.getElementById("settings-overlay").classList.remove("hidden");
  playSound("click");
}

function closeSettings() {
  document.getElementById("settings-overlay").classList.add("hidden");
}

function initSettingsPanel() {
  document.getElementById("btn-settings").addEventListener("click", openSettings);
  document.getElementById("btn-settings-close").addEventListener("click", closeSettings);
  document.getElementById("setting-reduced-motion").addEventListener("change", (e) => {
    settings.reducedMotion = e.target.checked;
    saveSettings();
    applySettings();
  });
  document.getElementById("setting-volume").addEventListener("input", (e) => {
    settings.volume = parseInt(e.target.value, 10);
    document.getElementById("setting-volume-val").textContent = `${settings.volume}%`;
    saveSettings();
    applySettings();
  });
  document.querySelectorAll(".text-size-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      settings.textSize = btn.dataset.size;
      saveSettings();
      applySettings();
      syncSettingsUI();
    });
  });
  document.getElementById("btn-view-content-warning").addEventListener("click", () => showContentWarning(true));
}

/* ============ Save Slots ============ */
// Load/Delete use the same two-click "arm, then confirm" pattern as the
// header's Restart button -- no native confirm() dialog, and each button
// labels exactly what it is about to do.
let savesArmedId = null;
let savesArmedAction = null;
let savesArmTimer = null;

function formatSaveTime(iso) {
  if (!iso) return "never";
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

function openSaves() {
  document.getElementById("saves-overlay").classList.remove("hidden");
  playSound("click");
  refreshSaves();
}

function closeSaves() {
  document.getElementById("saves-overlay").classList.add("hidden");
  document.getElementById("save-name-input").value = "";
}

async function refreshSaves() {
  const note = document.getElementById("saves-autosave-note");
  note.textContent = lastState && lastState.last_saved_at
    ? `Current run last saved: ${formatSaveTime(lastState.last_saved_at)}`
    : "Current run has not been saved yet.";
  const data = await api("/api/saves");
  if (data) renderSavesList(data.slots || []);
}

function renderSavesList(slots) {
  const list = document.getElementById("saves-list");
  list.innerHTML = "";
  if (!slots.length) {
    const p = document.createElement("p");
    p.className = "saves-empty";
    p.textContent = "No manual saves yet.";
    list.appendChild(p);
    return;
  }
  slots.forEach(s => {
    const row = document.createElement("div");
    row.className = "save-row";

    const info = document.createElement("div");
    info.className = "save-row-info";
    const name = document.createElement("span");
    name.className = "save-row-name";
    name.textContent = s.name;
    const meta = document.createElement("span");
    meta.className = "save-row-meta";
    const endingBit = s.ending ? ` · ${s.ending.replace(/_/g, " ")}` : "";
    meta.textContent = `Day ${s.day + 1}${endingBit} · ${formatSaveTime(s.saved_at)}`;
    info.appendChild(name);
    info.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "save-row-actions";
    const loadBtn = document.createElement("button");
    loadBtn.className = "btn-ghost save-load-btn";
    loadBtn.textContent = "Load";
    loadBtn.addEventListener("click", () => armOrCommit(s.id, "load", loadBtn, () => loadSlot(s.id)));
    const delBtn = document.createElement("button");
    delBtn.className = "btn-ghost save-delete-btn";
    delBtn.textContent = "Delete";
    delBtn.addEventListener("click", () => armOrCommit(s.id, "delete", delBtn, () => deleteSlot(s.id)));
    actions.appendChild(loadBtn);
    actions.appendChild(delBtn);

    row.appendChild(info);
    row.appendChild(actions);
    list.appendChild(row);
  });
}

function armOrCommit(id, action, btn, commit) {
  if (savesArmedId === id && savesArmedAction === action) {
    clearTimeout(savesArmTimer);
    savesArmedId = null;
    savesArmedAction = null;
    commit();
    return;
  }
  savesArmedId = id;
  savesArmedAction = action;
  const original = btn.textContent;
  btn.textContent = action === "load" ? "Confirm Load?" : "Confirm Delete?";
  btn.classList.add("armed");
  playSound("failure");
  savesArmTimer = setTimeout(() => {
    savesArmedId = null;
    savesArmedAction = null;
    btn.textContent = original;
    btn.classList.remove("armed");
  }, 3200);
}

async function saveNewSlot() {
  const input = document.getElementById("save-name-input");
  const name = input.value.trim();
  playSound("click");
  const data = await api("/api/saves/save", { name });
  if (!data) return;
  input.value = "";
  renderSavesList(data.slots || []);
}

async function loadSlot(id) {
  const data = await api("/api/saves/load", { id });
  if (!data) {
    // api() already logged the error to the console; a refused load (e.g. a
    // save from a newer build) needs to reach the player, not just that.
    document.getElementById("saves-autosave-note").textContent =
      "Could not load that save -- it may be from a newer version of the game.";
    return;
  }
  closeSaves();
  document.getElementById("outcome-banner").classList.add("hidden");
  document.getElementById("ending-modal").classList.add("hidden");
  introSeenThisRun = true; // a loaded run is never the fresh-run intro state
  playSound("day");
  renderUI(data);
}

async function deleteSlot(id) {
  playSound("click");
  const data = await api("/api/saves/delete", { id });
  if (data) renderSavesList(data.slots || []);
}

function initSavesPanel() {
  document.getElementById("btn-saves").addEventListener("click", openSaves);
  document.getElementById("btn-saves-close").addEventListener("click", closeSaves);
  document.getElementById("btn-save-new").addEventListener("click", saveNewSlot);
}

/* ============ Tabs ============ */
function initTabs() {
  const pairs = [
    ["tab-contacts", "view-contacts"],
    ["tab-shop", "view-shop"],
  ];
  pairs.forEach(([btnId, viewId]) => {
    document.getElementById(btnId).addEventListener("click", () => {
      playSound("click");
      pairs.forEach(([b, v]) => {
        document.getElementById(b).classList.toggle("active", b === btnId);
        document.getElementById(v).classList.toggle("active", v === viewId);
      });
    });
  });
}

/* ============ API ============ */
async function api(path, payload) {
  if (requestInFlight) return null;
  requestInFlight = true;
  setChoicesDisabled(true);
  try {
    const opts = payload !== undefined
      ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }
      : (path === "/api/state" ? {} : { method: "POST" });
    const res = await fetch(path, opts);
    const data = await res.json();
    if (!res.ok) {
      console.warn("API error:", data.error);
      return null;
    }
    return data;
  } catch (err) {
    console.error("Request failed:", path, err);
    return null;
  } finally {
    requestInFlight = false;
    setChoicesDisabled(false);
  }
}

function setChoicesDisabled(disabled) {
  document.querySelectorAll(".choice-btn").forEach(b => { b.disabled = disabled; });
}

async function fetchState(isInitial) {
  const data = await api("/api/state");
  if (data) {
    renderUI(data);
    if (isInitial) maybeShowIntro(data);
  }
}

async function selectChoice(choiceIdx) {
  playSound("click");
  const eventTitle = lastState && lastState.event ? lastState.event.title : "";
  const choiceText = currentChoices[choiceIdx] ? currentChoices[choiceIdx].text : "";
  const data = await api("/api/choose", { choice_idx: choiceIdx });
  if (data) {
    recordJournal(data, eventTitle, choiceText);
    renderUI(data);
  }
}

async function performContactAction(name) {
  playSound("click");
  const data = await api("/api/contact_action", { name });
  if (data) {
    recordJournal(data, "A real hour", `Met with ${name}`);
    renderUI(data);
  }
}

async function restAction() {
  if (!lastState || lastState.dead) return;
  if (lastState.slots_total - lastState.slots_used <= 0) return;
  playSound("rest");
  const data = await api("/api/rest", {});
  if (data) {
    recordJournal(data, "Lying low", "Rested. Mended. Let the city forget.");
    renderUI(data);
  }
}

async function buyItem(itemId) {
  playSound("purchase");
  const data = await api("/api/buy_item", { item_id: itemId });
  if (data) renderUI(data);
}

async function resetGame() {
  playSound("click");
  prevStats = null;
  prevDay = null;
  prevClocks = null;
  prevThreadFlags = null;
  prevContactNames = null;
  journal = [];
  saveJournal();
  renderJournal();
  introSeenThisRun = false;
  const data = await api("/api/reset");
  if (data) {
    document.getElementById("outcome-banner").classList.add("hidden");
    document.getElementById("ending-modal").classList.add("hidden");
    renderUI(data);
    maybeShowIntro(data);
  }
}

/* ============ Run Journal ============ */
function loadJournal() {
  try { journal = JSON.parse(sessionStorage.getItem(JOURNAL_KEY)) || []; }
  catch { journal = []; }
  renderJournal();
}

function saveJournal() {
  try { sessionStorage.setItem(JOURNAL_KEY, JSON.stringify(journal.slice(-80))); } catch {}
}

function recordJournal(data, eventTitle, choiceText) {
  const out = data.last_outcome;
  if (!out) return;
  journal.push({
    day: (lastState ? lastState.day : 0) + 1,
    title: eventTitle || "The Row",
    choice: choiceText,
    success: !!out.success,
    guaranteed: !!out.guaranteed,
    text: out.text || "",
  });
  saveJournal();
  renderJournal();
}

function renderJournal() {
  const list = document.getElementById("journal-list");
  if (!list) return;
  list.innerHTML = "";
  if (!journal.length) {
    const p = document.createElement("p");
    p.className = "journal-empty";
    p.textContent = "Nothing yet. The city is waiting to find out what kind of story you are.";
    list.appendChild(p);
    return;
  }
  let lastDay = null;
  [...journal].reverse().forEach(entry => {
    if (entry.day !== lastDay) {
      const dayHead = document.createElement("div");
      dayHead.className = "journal-day";
      dayHead.textContent = `DAY ${entry.day}`;
      list.appendChild(dayHead);
      lastDay = entry.day;
    }
    const row = document.createElement("div");
    row.className = "journal-entry" + (entry.guaranteed ? "" : entry.success ? " je-success" : " je-failure");
    const head = document.createElement("div");
    head.className = "je-head";
    const title = document.createElement("span");
    title.className = "je-title";
    title.textContent = entry.title;
    head.appendChild(title);
    if (!entry.guaranteed) {
      const tag = document.createElement("span");
      tag.className = "je-tag";
      tag.textContent = entry.success ? "WON" : "LOST";
      head.appendChild(tag);
    }
    const choice = document.createElement("div");
    choice.className = "je-choice";
    choice.textContent = `▸ ${entry.choice}`;
    const body = document.createElement("div");
    body.className = "je-text";
    body.textContent = entry.text;
    row.appendChild(head);
    row.appendChild(choice);
    row.appendChild(body);
    list.appendChild(row);
  });
}

function toggleJournal() {
  playSound("click");
  document.getElementById("journal-drawer").classList.toggle("hidden");
}

/* ============ Rendering ============ */
function renderUI(state) {
  const s = state.stats;
  lastState = state;

  // Day transition overlay
  if (prevDay !== null && state.day > prevDay && !state.dead) {
    showDayOverlay(state);
  }
  prevDay = state.day;

  document.getElementById("val-day").textContent = state.day + 1;
  if (state.cycle && state.cycle > 1) {
    document.querySelector(".sub-brand").textContent =
      `Arcology Node 4 // Undercity Fixer // Cycle ${state.cycle}`;
  }
  renderSlotPips(state.slots_total, state.slots_used);

  // Meters: value + tier color together
  setMeter("md", s.Mental_Decay, thresholdTier(s.Mental_Decay, 50, 75, false));
  setMeter("phys", s.Physical_Integrity, thresholdTier(s.Physical_Integrity, 55, 30, true));
  setMeter("rel", s.Substance_Reliance, thresholdTier(s.Substance_Reliance, 35, 60, false));
  setMeter("heat", s.Heat, thresholdTier(s.Heat, 40, 70, false));
  setMeter("meaning", s.Meaning, thresholdTier(s.Meaning, 45, 25, true));
  setMeter("friction", s.Family_Friction, thresholdTier(s.Family_Friction, 40, 65, false));

  // Alert markers on critical groups
  document.getElementById("group-md").classList.toggle("alerting", s.Mental_Decay >= 75);
  document.getElementById("group-heat").classList.toggle("alerting", s.Heat >= 70);
  document.getElementById("group-phys").classList.toggle("alerting", s.Physical_Integrity <= 30);

  // Delta floaters vs previous state
  if (prevStats) spawnDeltaFloats(prevStats, s);
  // One-shot sting the moment Heat crosses into crackdown territory
  if (prevStats && prevStats.Heat < 70 && s.Heat >= 70) playSound("heat-alarm");
  prevStats = { ...s };

  document.getElementById("val-tol").textContent = s.Tolerance.toFixed(2);
  // After Clearing at Zero, surface credits are dead; wealth is undercity chits.
  const currency = (state.flags || []).includes("world_price_zero") ? "ch" : "cr";
  document.getElementById("val-wealth").textContent = `${Math.round(s.Wealth).toLocaleString()} ${currency}`;
  document.getElementById("val-fame").textContent = s.Fame.toFixed(1);

  const facs = state.factions || {};
  setFaction("fac-undercity", facs.Undercity);
  setFaction("fac-steward", facs.Steward);
  setFaction("fac-resistance", facs.Resistance);

  renderExitChain(state.flags || []);
  renderClocks(state.clocks || {});
  renderThreads(state.flags || []);
  renderStewardFile(state.steward);
  renderEdgeChip(state.edge || 0);
  // Contacts and rest both spend a slot, and a slot cannot be spent before the
  // morning placement says where it is standing -- the server refuses either way.
  const placing = !!(state.placement && state.placement.awaiting);
  renderContacts(state.relationships, !placing && state.slots_total - state.slots_used > 0);
  renderShop(state.catalog || [], state.inventory || [], s.Wealth);

  // Center-stage mood: heat alarm & mental decay warp
  const stage = document.getElementById("center-stage");
  stage.classList.toggle("heat-alarm", s.Heat >= 70);
  stage.classList.toggle("md-warp", s.Mental_Decay >= 70);

  // Somatic feedback: the body's state bleeds into the frame itself
  const root = document.getElementById("app-root");
  root.classList.toggle("fx-injured", s.Physical_Integrity <= 35);
  root.classList.toggle("fx-tremor", s.Substance_Reliance >= 45);
  root.classList.toggle("fx-fading", s.Meaning <= 18);

  renderOutcome(state.last_outcome);

  if (state.dead || state.ending) {
    renderEnding(state);
    return;
  }

  // The morning placement gates the day: until it is answered the server has
  // not drawn a storylet, because which storylet it draws depends on the answer.
  renderPlacement(state);
  if (!document.getElementById("placement-stage").classList.contains("hidden")) return;

  const ev = state.event;
  if (ev) {
    document.getElementById("event-title").textContent = ev.title;
    typewrite(document.getElementById("event-body"), ev.body);

    const tagsContainer = document.getElementById("event-tags");
    tagsContainer.innerHTML = "";
    (ev.tags || []).forEach(tag => {
      const span = document.createElement("span");
      span.className = "tag-pill";
      span.textContent = tag;
      tagsContainer.appendChild(span);
    });

    updateSceneImage(ev.tags);
    renderChoices(ev.choices || []);
  } else {
    document.getElementById("event-title").textContent = "A Quiet Hour";
    typewrite(document.getElementById("event-body"),
      "For once, nothing needs you. The concourse murmurs below. The day advances on its own weight.");
    document.getElementById("choices-list").innerHTML = "";
    currentChoices = [];
  }
  appendRestCard(state);
}

// The one action always on the table: spend a slot lying low.
function appendRestCard(state) {
  if (state.dead || state.slots_total - state.slots_used <= 0) return;
  const choicesList = document.getElementById("choices-list");
  const card = document.createElement("button");
  card.className = "choice-btn rest-btn";

  const left = document.createElement("span");
  left.className = "choice-text";
  const key = document.createElement("span");
  key.className = "choice-key";
  key.textContent = "[R]";
  left.appendChild(key);
  left.appendChild(document.createTextNode(
    "Lie low. Bolt the door, mend the body, let the city forget your face for a day."));

  const risk = document.createElement("span");
  risk.className = "choice-risk safe";
  risk.textContent = "RECOVER";
  risk.title = "Body +4, Mental Decay -3, Heat -2. Costs one action -- and a little Meaning.";

  card.appendChild(left);
  card.appendChild(risk);
  card.addEventListener("click", restAction);
  choicesList.appendChild(card);
}

/* ============ Threads: the city's visible ledger on you ============ */
let prevThreadFlags = null;

function renderThreads(flags) {
  const panel = document.getElementById("threads-panel");
  const list = document.getElementById("threads-list");
  const known = flags.filter(f => FLAG_META[f]);
  panel.classList.toggle("hidden", known.length === 0);
  list.innerHTML = "";
  // a warn-tone thread appearing for the first time gets a low monitor tone
  if (prevThreadFlags !== null &&
      known.some(f => FLAG_META[f].tone === "warn" && !prevThreadFlags.has(f))) {
    playSound("warning");
  }
  prevThreadFlags = new Set(known);
  known.forEach(f => {
    const meta = FLAG_META[f];
    const chip = document.createElement("span");
    chip.className = `thread-chip thread-${meta.tone}`;
    chip.textContent = meta.label;
    chip.title = meta.tip;
    list.appendChild(chip);
  });
}

/* ============ The Steward's file (A3) ============ */
// The one line the player sees coming. The terminal front end prints
// steward.filing_notice() beside the ledger line; the web front end never
// rendered state.ambient at all, so the notice lives here instead -- same
// string, same window, from the same server call.
let prevFilingTier = null;

function renderStewardFile(file) {
  const panel = document.getElementById("steward-panel");
  if (!panel) return;
  // Hidden until the Steward has written something down, exactly as
  // #clocks-panel is hidden until a clock runs.
  panel.classList.toggle("hidden", !(file && file.open));
  if (!file || !file.open) { prevFilingTier = null; return; }

  document.getElementById("steward-tier").textContent = file.tier_name;
  const n = file.entries;
  document.getElementById("steward-entries").textContent =
    `${n} ${n === 1 ? "entry" : "entries"}`;
  panel.dataset.tier = file.tier;

  const notice = document.getElementById("steward-notice");
  notice.classList.toggle("hidden", !file.notice);
  notice.textContent = file.notice || "";
  notice.classList.toggle("notice-today", file.days_until === 0);

  // Escalation is the thing this panel exists to make legible, so it gets the
  // same one-shot audio treatment a newly-critical clock does.
  if (prevFilingTier !== null && file.tier > prevFilingTier) playSound("warning");
  prevFilingTier = file.tier;
}

function renderEdgeChip(edge) {
  const chip = document.getElementById("edge-chip");
  if (!chip) return;
  chip.classList.toggle("hidden", edge <= 0);
  if (edge > 0) {
    chip.textContent = `DESPERATION EDGE +${edge}%`;
    chip.title = "The city underestimates the cornered: consecutive failed rolls sharpen your next gamble. Resets when you win one.";
  }
}

function renderSlotPips(total, used) {
  const el = document.getElementById("slot-pips");
  el.innerHTML = "";
  for (let i = 0; i < total; i++) {
    const pip = document.createElement("span");
    pip.className = "slot-pip" + (i < total - used ? " filled" : "");
    el.appendChild(pip);
  }
}

// Returns a tier class. For "higher is better" stats pass invert=true with
// (warnBelow, critBelow); otherwise (warnAbove, critAbove).
function thresholdTier(val, warn, crit, higherIsBetter) {
  if (higherIsBetter) {
    if (val <= crit) return "tier-bad";
    if (val <= warn) return "tier-mid";
    return "tier-ok";
  }
  if (val >= crit) return "tier-bad";
  if (val >= warn) return "tier-mid";
  return "tier-cool";
}

function setMeter(id, val, tierClass) {
  const clamped = Math.max(0, Math.min(100, val));
  document.getElementById(`val-${id}`).textContent = `${clamped.toFixed(1)}%`;
  const bar = document.getElementById(`bar-${id}`);
  bar.style.width = `${clamped}%`;
  bar.className = `meter-fill ${tierClass}`;
}

function setFaction(id, val) {
  const v = Math.round(val || 0);
  document.getElementById(id).textContent = `${v >= 0 ? "+" : ""}${v}`;
}

const FLOAT_STATS = {
  Mental_Decay: "group-md", Physical_Integrity: "group-phys",
  Substance_Reliance: "group-rel", Heat: "group-heat",
  Meaning: "group-meaning", Family_Friction: "group-friction",
};

// A rising delta is drawn green/red by whether it is GOOD, not by its sign.
const GOOD_WHEN_UP = new Set(["Physical_Integrity", "Meaning"]);

function spawnDeltaFloats(oldS, newS) {
  Object.entries(FLOAT_STATS).forEach(([stat, groupId]) => {
    const diff = newS[stat] - oldS[stat];
    if (Math.abs(diff) < 0.05) return;
    const isGood = GOOD_WHEN_UP.has(stat) ? diff > 0 : diff < 0;
    const chip = document.createElement("span");
    chip.className = `delta-float ${isGood ? "pos" : "neg"}`;
    chip.textContent = `${diff > 0 ? "+" : ""}${diff.toFixed(1)}`;
    const group = document.getElementById(groupId);
    group.appendChild(chip);
    setTimeout(() => chip.remove(), 1700);
  });
}

/* ============ Typewriter ============ */
function typewrite(el, text) {
  if (typewriterTimer) { clearInterval(typewriterTimer); typewriterTimer = null; }
  const reduced = prefersReducedMotion();
  if (reduced || text.length > 900) { el.textContent = text; return; }

  el.textContent = "";
  const caret = document.createElement("span");
  caret.className = "caret";
  el.appendChild(caret);

  let i = 0;
  const step = 3; // chars per tick
  const textNode = document.createTextNode("");
  el.insertBefore(textNode, caret);
  typewriterTimer = setInterval(() => {
    i = Math.min(i + step, text.length);
    textNode.nodeValue = text.slice(0, i);
    if (i >= text.length) {
      clearInterval(typewriterTimer);
      typewriterTimer = null;
      caret.remove();
    }
  }, 12);

  el.onclick = () => { // click to skip
    if (typewriterTimer) {
      clearInterval(typewriterTimer);
      typewriterTimer = null;
      el.textContent = text;
    }
  };
}

/* ============ Choices & Risk Tiers ============ */
/* ============ Morning Placement (A1) ============ */
// Where each of the day's slots stands. Held client-side only until "Set out"
// posts it; the server is the one that decides a day has been placed, so a
// half-filled screen is never a half-placed day.
let pendingPlacement = {};

function renderPlacement(state) {
  const p = state.placement;
  const stage = document.getElementById("placement-stage");
  const storylet = document.getElementById("storylet-stage");
  const awaiting = !!(p && p.awaiting && (p.districts || []).length);

  stage.classList.toggle("hidden", !awaiting);
  storylet.classList.toggle("hidden", awaiting);
  if (!awaiting) return;

  const slots = p.slots || 3;
  document.getElementById("placement-intro").textContent =
    `Three hours of usable day, give or take. Standing somewhere means the city hands you `
    + `that district's business and not the Row's -- and the places you don't go keep running `
    + `without you.`;

  // Reset only when the day changed underneath us, so a re-render (an outcome
  // banner, a stat tick) doesn't wipe a selection the player already made.
  if (pendingPlacement.__day !== state.day) pendingPlacement = { __day: state.day };

  const container = document.getElementById("placement-slots");
  container.innerHTML = "";
  for (let slot = 0; slot < slots; slot++) {
    const row = document.createElement("div");
    row.className = "placement-row";

    const label = document.createElement("span");
    label.className = "placement-slot-label";
    label.textContent = `Hour ${slot + 1}`;
    row.appendChild(label);

    const opts = document.createElement("div");
    opts.className = "placement-options";
    const choices = [{ id: null, name: "The Row at large", hint: "Whatever the city hands you." }]
      .concat(p.districts);

    choices.forEach(d => {
      const btn = document.createElement("button");
      const chosen = (pendingPlacement[slot] || null) === d.id;
      btn.className = `placement-opt${chosen ? " chosen" : ""}`;
      btn.textContent = d.name;
      btn.title = d.hint || d.blurb || "";
      btn.addEventListener("click", () => {
        if (d.id === null) delete pendingPlacement[slot];
        else pendingPlacement[slot] = d.id;
        renderPlacement(state);
      });
      opts.appendChild(btn);
    });
    row.appendChild(opts);
    container.appendChild(row);
  }

  // The hint line lives once under the rows rather than on every option: it is
  // per-district state, not per-slot, and repeating it three times reads as
  // three different readings of the same street.
  p.districts.forEach(d => {
    const note = document.createElement("div");
    note.className = "placement-hint";
    note.innerHTML = `<span class="placement-hint-name">${d.name}</span> — ${d.hint}`;
    container.appendChild(note);
  });

  document.getElementById("placement-confirm").onclick = () => confirmPlacement();
}

async function confirmPlacement() {
  const payload = {};
  Object.keys(pendingPlacement).forEach(k => {
    if (k !== "__day") payload[k] = pendingPlacement[k];
  });
  const data = await api("/api/place", { placements: payload });
  if (!data || data.error) return;
  playSound("day");
  renderUI(data);
}

function riskTier(prob) {
  if (prob >= 95) return { cls: "safe", label: "SAFE" };
  if (prob >= 65) return { cls: "favorable", label: `FAVORABLE ${Math.round(prob)}%` };
  if (prob >= 40) return { cls: "risky", label: `RISKY ${Math.round(prob)}%` };
  return { cls: "desperate", label: `DESPERATE ${Math.round(prob)}%` };
}

function renderChoices(choices) {
  currentChoices = choices;
  const choicesList = document.getElementById("choices-list");
  choicesList.innerHTML = "";
  choices.forEach((ch, idx) => {
    const card = document.createElement("button");
    card.className = "choice-btn";

    const left = document.createElement("span");
    left.className = "choice-text";
    const key = document.createElement("span");
    key.className = "choice-key";
    key.textContent = `[${idx + 1}]`;
    left.appendChild(key);
    left.appendChild(document.createTextNode(ch.text));

    // The quality being tested: which stats bend these odds, and which way.
    if (ch.checks && ch.checks.length) {
      const checksRow = document.createElement("span");
      checksRow.className = "checks-row";
      ch.checks.forEach(chk => {
        const label = STAT_LABELS[chk.stat] || chk.stat.replace(/_/g, " ");
        const chip = document.createElement("span");
        chip.className = `check-chip ${chk.dir > 0 ? "check-up" : "check-down"}`;
        chip.textContent = `${label} ${chk.dir > 0 ? "▲" : "▼"}`;
        chip.title = chk.dir > 0
          ? `Higher ${label} improves these odds.`
          : `Higher ${label} worsens these odds.`;
        checksRow.appendChild(chip);
      });
      left.appendChild(checksRow);
    }
    if (ch.unlocked) {
      const badge = document.createElement("span");
      badge.className = "choice-badge unlocked";
      badge.textContent = "UNLOCKED";
      badge.title = "This option only exists because of who you are and what you carry.";
      left.appendChild(badge);
    }
    if (ch.boosted) {
      const badge = document.createElement("span");
      badge.className = "choice-badge boosted";
      badge.textContent = "GEAR ⚡";
      badge.title = "Your equipment improves these odds.";
      left.appendChild(badge);
    }

    const tier = riskTier(ch.prob);
    const risk = document.createElement("span");
    risk.className = `choice-risk ${tier.cls}`;
    risk.textContent = tier.label;
    risk.title = `${ch.prob}% success chance`;

    card.appendChild(left);
    card.appendChild(risk);
    card.addEventListener("click", () => selectChoice(idx));
    choicesList.appendChild(card);
  });
}

/* ============ Outcome Banner & Roll Reveal ============ */
function renderOutcome(outcome) {
  const banner = document.getElementById("outcome-banner");
  if (!outcome) { banner.classList.add("hidden"); return; }

  const tag = document.getElementById("outcome-tag");
  const text = document.getElementById("outcome-text");
  const deltasEl = document.getElementById("outcome-deltas");
  const rollWrap = document.getElementById("roll-reveal");

  banner.classList.remove("hidden");
  banner.classList.toggle("failure", !outcome.success);
  tag.textContent = outcome.success ? "SUCCESS" : "FAILURE";
  const isOverdose = outcome.overdose && outcome.overdose > 0;
  playSound(outcome.success ? "success" : isOverdose ? "overdose" : "failure");
  text.textContent = outcome.text;

  // Overdose collapse: one hard white-out, then the world comes back wrong
  if (outcome.overdose && outcome.overdose > 0) {
    const root = document.getElementById("app-root");
    root.classList.remove("fx-flatline");
    void root.offsetWidth;
    root.classList.add("fx-flatline");
    setTimeout(() => root.classList.remove("fx-flatline"), 2400);
  }

  // Roll reveal: needle animates to the rolled value against the target zone
  if (typeof outcome.roll === "number" && typeof outcome.target === "number" && !outcome.guaranteed) {
    rollWrap.classList.remove("hidden");
    document.getElementById("roll-target").style.width = `${outcome.target}%`;
    const needle = document.getElementById("roll-needle");
    needle.style.left = "0%";
    requestAnimationFrame(() => requestAnimationFrame(() => {
      needle.style.left = `calc(${Math.min(outcome.roll, 100)}% - 1px)`;
    }));
    document.getElementById("roll-numbers").textContent =
      `rolled ${outcome.roll.toFixed(1)} / needed ≤ ${outcome.target.toFixed(1)}`;
  } else {
    rollWrap.classList.add("hidden");
  }

  deltasEl.innerHTML = "";
  Object.entries(outcome.deltas || {}).forEach(([k, v]) => {
    if (v === 0) return;
    const chip = document.createElement("span");
    const isGood = GOOD_WHEN_UP.has(k) || k === "Wealth" || k === "Fame" || k === "Social_Capital" ? v > 0 : v < 0;
    chip.className = `delta-chip ${isGood ? "pos" : "neg"}`;
    chip.textContent = `${k.replace(/_/g, " ")} ${v > 0 ? "+" : ""}${v}`;
    deltasEl.appendChild(chip);
  });
}

/* ============ Exit Chain ============ */
const CHAIN_STEPS = [
  { flag: "ferryman_known",     label: "The Ferryman" },
  { flag: "route_mapped",       label: "Route Mapped" },
  { flag: "credentials_forged", label: "Ghost Credentials" },
  { flag: "exit_ready",         label: "Exit Ready" },
  { flag: "crossed_wire",       label: "The Crossing" },
];

/* ============ Deadline Clocks ============ */
let prevClocks = null;

function renderClocks(clocks) {
  const wrap = document.getElementById("clocks-panel");
  const list = document.getElementById("clocks-list");
  const entries = Object.entries(clocks);
  wrap.classList.toggle("hidden", entries.length === 0);
  list.innerHTML = "";
  // One tick when any clock first drops into the critical zone (max one per render)
  const newlyCritical = prevClocks !== null && entries.some(
    ([name, days]) => days <= 2 && !(prevClocks[name] !== undefined && prevClocks[name] <= 2)
  );
  if (newlyCritical) playSound("clock-critical");
  prevClocks = { ...clocks };
  entries.forEach(([name, days]) => {
    const chip = document.createElement("div");
    chip.className = "clock-chip" + (days <= 2 ? " clock-critical" : "");
    const label = document.createElement("span");
    label.className = "clock-name";
    label.textContent = name.replace(/_/g, " ").toUpperCase();
    const count = document.createElement("span");
    count.className = "clock-days";
    count.textContent = `${days} DAY${days !== 1 ? "S" : ""}`;
    chip.appendChild(label);
    chip.appendChild(count);
    list.appendChild(chip);
  });
}

function renderExitChain(flags) {
  const el = document.getElementById("exit-chain");
  el.innerHTML = "";
  const flagSet = new Set(flags);
  let nextMarked = false;
  CHAIN_STEPS.forEach(step => {
    const done = flagSet.has(step.flag);
    const node = document.createElement("div");
    node.className = "chain-node" + (done ? " done" : (!nextMarked ? " next" : ""));
    if (!done && !nextMarked) nextMarked = true;

    const dot = document.createElement("span");
    dot.className = "chain-dot";
    const label = document.createElement("span");
    label.textContent = step.label;
    const stateTag = document.createElement("span");
    stateTag.className = "chain-state";
    stateTag.textContent = done ? "DONE" : "";

    node.appendChild(dot);
    node.appendChild(label);
    node.appendChild(stateTag);
    el.appendChild(node);
  });
}

/* ============ Day Overlay ============ */
// Night ledger: which stats moved overnight is worth a line; which direction
// is good depends on the stat, same rule as the delta floaters.
function showDayOverlay(state) {
  playSound("day");
  const overlay = document.getElementById("day-overlay");
  document.getElementById("day-overlay-day").textContent = `DAY ${state.day + 1}`;
  const report = state.day_report;
  let sub = quoteForDay(state.day);
  if (report && report.md_streak >= 1) {
    sub = `WELLNESS ALERT: sustained decay detected (${report.md_streak} day${report.md_streak > 1 ? "s" : ""}). The Sanctuary has your file open.`;
  } else if (report && report.withdrawal) {
    sub = "Your hands shook through the night. The body keeps its own ledger.";
  }
  document.getElementById("day-overlay-sub").textContent = sub;

  const ledger = document.getElementById("night-ledger");
  ledger.innerHTML = "";
  let hasLedger = false;
  if (report && report.overnight) {
    const head = document.createElement("div");
    head.className = "ledger-head";
    head.textContent = "WHILE YOU SLEPT";
    ledger.appendChild(head);
    Object.entries(report.overnight).forEach(([stat, diff]) => {
      if (stat === "Wealth" && Math.abs(diff) < 1) return;
      const isGood = GOOD_WHEN_UP.has(stat) || stat === "Wealth" || stat === "Fame" || stat === "Social_Capital"
        ? diff > 0 : diff < 0;
      const row = document.createElement("div");
      row.className = `ledger-row ${isGood ? "lr-pos" : "lr-neg"}`;
      const label = STAT_LABELS[stat] || stat.replace(/_/g, " ");
      row.textContent = `${label} ${diff > 0 ? "+" : ""}${diff.toFixed(1)}`;
      ledger.appendChild(row);
      hasLedger = true;
    });
    if ((report.clocks_expired || []).length > 0) {
      setTimeout(() => playSound("clock-expired"), 900);
    }
    (report.clocks_expired || []).forEach(name => {
      const row = document.createElement("div");
      row.className = "ledger-row lr-clock";
      row.textContent = `⏱ ${name.replace(/_/g, " ").toUpperCase()} — TIME'S UP`;
      ledger.appendChild(row);
      hasLedger = true;
    });
    if (!hasLedger) ledger.innerHTML = "";
  }

  // A4: the morning report and the Steward's ledger line. `engine/ambient.py`
  // has composed both since before this front end existed and `server.py`
  // sends them on every state call as `state.ambient`, but nothing here ever
  // read that key -- so `_mara_signal`'s "It's been 14 days since you called
  // Mara. She's stopped asking why." has only ever reached terminal players.
  // That line is A4's literal ask (a state-derived line in the character's own
  // voice) and it was already written; see docs/A4_DESIGN.md §4.
  //
  // Placed under the ledger rather than in a sidebar panel because the
  // terminal prints it at the same moment -- top of the day, after the night's
  // accounting (main.py:173). Same strings, same order, both front ends.
  let hasAmbient = false;
  if (state.ambient) {
    const lines = state.ambient.morning_report || [];
    if (lines.length || state.ambient.ledger_line) {
      const head = document.createElement("div");
      head.className = "ledger-head morning-head";
      head.textContent = "THE MORNING";
      ledger.appendChild(head);
    }
    lines.forEach(text => {
      const row = document.createElement("div");
      row.className = "ledger-row lr-morning";
      row.textContent = text;
      ledger.appendChild(row);
      hasAmbient = true;
    });
    if (state.ambient.ledger_line) {
      const row = document.createElement("div");
      row.className = "ledger-row lr-steward";
      row.textContent = state.ambient.ledger_line;
      ledger.appendChild(row);
      hasAmbient = true;
    }
  }

  // soft data ticks under the ledger, one per stat row (capped), after the chime
  const tickRows = Math.min(ledger.querySelectorAll(".lr-pos, .lr-neg").length, 5);
  for (let i = 0; i < tickRows; i++) {
    setTimeout(() => playSound("ledger-tick"), 1300 + i * 160);
  }

  // restart CSS animation; hold a beat longer when there's a ledger to read,
  // and longer again when there is prose under it -- the morning lines are
  // sentences, not stat rows, and 3.9s is not enough to read two of them.
  const dwell = hasAmbient ? 5600 : hasLedger ? 3900 : 2650;
  overlay.classList.toggle("has-ledger", hasLedger && !hasAmbient);
  overlay.classList.toggle("has-morning", hasAmbient);
  overlay.classList.add("hidden");
  void overlay.offsetWidth;
  overlay.classList.remove("hidden");
  setTimeout(() => overlay.classList.add("hidden"), dwell);
}

/* ============ Contacts, Shop, Scenes ============ */
let prevContactNames = null;

function renderContacts(relationships, hasSlotsAvailable) {
  const container = document.getElementById("contacts-list");
  container.innerHTML = "";
  const names = (relationships || []).map(r => r.name);
  if (prevContactNames !== null && names.some(n => !prevContactNames.has(n))) {
    playSound("contact-new");
  }
  prevContactNames = new Set(names);
  (relationships || []).forEach(r => {
    const card = document.createElement("div");
    card.className = "contact-card" + (r.satisfaction < 30 ? " fading" : "");

    const header = document.createElement("div");
    header.className = "contact-name";
    const nameSpan = document.createElement("span");
    nameSpan.textContent = `${r.name} (${Math.round(r.satisfaction)}%)`;
    header.appendChild(nameSpan);

    if (hasSlotsAvailable) {
      const btn = document.createElement("button");
      btn.className = "btn-contact-action";
      btn.textContent = "Meet (-1 Action)";
      btn.addEventListener("click", () => performContactAction(r.name));
      header.appendChild(btn);
    }

    const bar = document.createElement("div");
    bar.className = "meter-bar";
    const fill = document.createElement("div");
    fill.className = `meter-fill ${r.satisfaction < 30 ? "tier-bad" : r.satisfaction < 55 ? "tier-mid" : "tier-ok"}`;
    fill.style.width = `${r.satisfaction}%`;
    bar.appendChild(fill);

    const sub = document.createElement("div");
    sub.className = "stat-sub";
    sub.textContent = `Memory strength S = ${r.strength.toFixed(1)} days`;

    card.appendChild(header);
    card.appendChild(bar);
    card.appendChild(sub);
    container.appendChild(card);
  });
}

function renderShop(catalog, inventory, currentWealth) {
  const invContainer = document.getElementById("inventory-list");
  invContainer.innerHTML = "";
  if (inventory.length === 0) {
    invContainer.innerHTML = '<span class="item-desc">[No cyberware or gear equipped]</span>';
  } else {
    inventory.forEach(id => {
      const item = catalog.find(i => i.id === id) || { name: id, description: "Equipped cyberware" };
      const el = document.createElement("div");
      el.className = "item-card";
      const info = document.createElement("div");
      info.className = "item-info";
      const title = document.createElement("span");
      title.className = "item-title";
      title.textContent = `⚡ ${item.name}`;
      const desc = document.createElement("span");
      desc.className = "item-desc";
      desc.textContent = item.description;
      info.appendChild(title);
      info.appendChild(desc);
      el.appendChild(info);
      invContainer.appendChild(el);
    });
  }

  const catContainer = document.getElementById("catalog-list");
  catContainer.innerHTML = "";
  catalog.forEach(item => {
    const isOwned = inventory.includes(item.id);
    const canAfford = currentWealth >= item.cost;
    const card = document.createElement("div");
    card.className = "item-card";

    const info = document.createElement("div");
    info.className = "item-info";
    const title = document.createElement("span");
    title.className = "item-title";
    title.textContent = `${item.name} (${item.cost.toLocaleString()} cr)`;
    const desc = document.createElement("span");
    desc.className = "item-desc";
    desc.textContent = item.description;
    info.appendChild(title);
    info.appendChild(desc);

    const btn = document.createElement("button");
    btn.className = "btn-buy";
    if (isOwned) {
      btn.textContent = "OWNED";
      btn.disabled = true;
    } else if (!canAfford) {
      btn.textContent = "LOCKED";
      btn.disabled = true;
    } else {
      btn.textContent = "BUY";
      btn.addEventListener("click", () => buyItem(item.id));
    }

    card.appendChild(info);
    card.appendChild(btn);
    catContainer.appendChild(card);
  });
}

function setScene(key) {
  const stage = document.getElementById("scene-stage");
  buildScene(stage, key);
  document.getElementById("scene-caption").textContent = SCENE_CAPTIONS[key] || "ARCOLOGY NODE 4";
  currentSceneKey = key;
  switchAmbientLoop(ambientKeyForScene(key));
}

function updateSceneImage(tags) {
  const tagList = tags || [];
  if (tagList.includes("offgrid")) {
    setScene("offgrid");
  } else if (tagList.includes("steward") || tagList.includes("wellness")) {
    setScene("steward");
  } else if (tagList.includes("vice") || tagList.includes("substance") || tagList.includes("contraband")) {
    setScene("vice");
  } else if (tagList.includes("existential") || tagList.includes("ending_trigger")) {
    setScene("street");
  } else {
    setScene("hideout");
  }
}

/* ============ Endings ============ */
function loadGallery() {
  try { return JSON.parse(localStorage.getItem(GALLERY_KEY)) || {}; }
  catch { return {}; }
}

function renderEnding(state) {
  const modal = document.getElementById("ending-modal");
  const card = modal.querySelector(".modal-card");
  const info = state.ending_info || {};
  const meta = ENDING_META[state.ending] || { label: state.ending, tone: "terminal", scene: "hideout" };

  // Record in gallery
  const seen = loadGallery();
  if (state.ending && !seen[state.ending]) {
    seen[state.ending] = { title: info.title || state.ending, day: state.day };
    try { localStorage.setItem(GALLERY_KEY, JSON.stringify(seen)); } catch {}
  }

  const firstReveal = modal.classList.contains("hidden");
  modal.classList.remove("hidden");
  card.className = `modal-card glass-panel tone-${meta.tone}`;
  // Terminal endings all land on the same empty, rain-slick asphalt rather
  // than on whichever scene the run happened to stop in.
  const endScene = document.getElementById("ending-scene");
  if (meta.tone === "terminal") buildScene(endScene, "street", "collapse");
  else buildScene(endScene, meta.scene || "hideout");
  document.getElementById("ending-title").textContent = info.title || `GAME OVER: ${state.ending}`;
  document.getElementById("ending-body").textContent = info.text || "Your journey in the Grey Utopia has ended.";

  // Reactive epilogue: the closing screen remembers what this run actually was
  const epiEl = document.getElementById("ending-epilogue");
  epiEl.innerHTML = "";
  (info.epilogue || []).forEach(line => {
    const p = document.createElement("p");
    p.className = "epilogue-line";
    p.textContent = line;
    epiEl.appendChild(p);
  });

  // The cycle remembers: past-tense ledger of what this run was
  const memEl = document.getElementById("ending-memories");
  memEl.innerHTML = "";
  const memories = info.memories || [];
  if (memories.length) {
    const head = document.createElement("div");
    head.className = "memories-head";
    head.textContent = "THE CYCLE REMEMBERS";
    memEl.appendChild(head);
    memories.forEach(line => {
      const p = document.createElement("p");
      p.className = "memory-line";
      p.textContent = line;
      memEl.appendChild(p);
    });
  }

  const rs = document.getElementById("run-stats");
  rs.innerHTML = "";
  [
    [String(state.day + 1), "Days Survived"],
    [`${Math.round(state.stats.Wealth).toLocaleString()}`, "Credits"],
    [`${state.stats.Meaning.toFixed(0)}%`, "Meaning"],
  ].forEach(([val, label]) => {
    const cell = document.createElement("div");
    cell.className = "run-stat";
    const v = document.createElement("span");
    v.className = "rs-val";
    v.textContent = val;
    const l = document.createElement("span");
    l.className = "rs-label";
    l.textContent = label;
    cell.appendChild(v);
    cell.appendChild(l);
    rs.appendChild(cell);
  });

  const gallery = document.getElementById("endings-gallery");
  gallery.innerHTML = "";
  Object.entries(ENDING_META).forEach(([id, m]) => {
    const cell = document.createElement("div");
    const found = !!seen[id];
    cell.className = "gallery-cell" + (found ? " found" : "") + (id === state.ending ? " current" : "");
    cell.textContent = found ? m.label : "???";
    gallery.appendChild(cell);
  });

  if (firstReveal) {
    playSound(meta.tone === "good" ? "ending-good" : meta.tone === "neutral" ? "ending-neutral" : "ending-terminal");
  }
}
