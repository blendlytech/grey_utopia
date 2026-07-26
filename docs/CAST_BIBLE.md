# CAST BIBLE — Promotions & Warmth Pass (Depth Plan Item C)

Fable 5 design, July 26 2026. Prose execution assigned to Sonnet 5.
Sonnet target file: **`data/events/cast_expansion_pack.json`** (new pack, 25 events).
Also touched by this pass: `data/cast.json` (5 new entries, done), `data/events/endings.json`
(epilogues, specs in §7), `docs/VOICE_BIBLE.md` §4 (short keys, done).

`docs/VOICE_BIBLE.md` is law and overrides any conflicting instinct in this document's
execution. This document adds cast canon on top of it.

---

## 1. Design intent — likeable without free comfort

The cast ceiling is 4 NPCs + the Steward, and every arc is devastating. The competition
(Citizen Sleeper, Roadwarden) wins on *fondness*: characters players think about between
sessions. This pack promotes five recurring minor names into full cast — **Brann, the
Ferryman, Dex, Auntie Six, Denny** — and gives the core four one warm scene each.

The warmth doctrine, stated once: **warmth in GREY UTOPIA is competence, specificity, and
things given at a named price.** Nobody hugs. Nobody says what they mean. Warmth arrives
as a shop rag, a fake manifest, an extra bowl billed as a napkin, exact change counted
twice. The Voice Bible's ban on free comfort is not suspended for this pack — it is the
whole method: a scene reads warm *because* the bill is itemized and paid on-page. Humor is
allowed and wanted — deadpan, worldly, never quippy, never at the Steward's expense in a
way the Steward would fail to log.

**The thesis that binds the five:** each new NPC runs a small human ledger that the
Steward's big one cannot see — Brann's roster board, the Ferryman's toll book, Dex's
paper list, Auntie Six's chalk board, Denny's offense economy. Post-Deprecation, when the
official ledger cleared at zero, these became the only books in the city that still mean
anything. Every arc is about what it costs to keep a small ledger honest under a large
one that wants it digitized, settled, or quiet.

---

## 2. Canon inventory (established in prose — do not contradict)

- **Brann** (horizon_pack, legacy_pack): master artisan, surface reclamation workshop.
  "Slab of a man." Calls the PC "Mara's brother." Awards shop rags as medals; chalk
  roster board; moved bench = a sentence in shop grammar; ruled a healthy kettle "kettle
  anxiety, hereditary"; "humility does the teaching, I just point." His arm is failing
  (hz_workshop_finale: "Brann's arm is not what it was"). Next cycle he keeps a dead
  apprentice's bench oiled under a tarp and refuses to make them a cautionary tale.
- **The Ferryman** (flagship, horizon, spiral, resistance, endings): a *mantle*, not a
  person — "the voice behind the mask was always borrowed." Current holder: a woman, one
  good arm (hz_ferryman_wounded), rasped filter-mask voice, koans in second person
  ("Wanting is cheap"), never crossed herself — "Some people are doors. It is not a
  lesser thing to be." The seam: ninety-one seconds, doesn't subcontract, "the seam has
  seen every version of this, including yours." Respect is spelled as scheduling.
- **Dex** (sonnet_5_volume_pack `amb_courier_run_night`): dispatcher at the transit gap.
  Sealed cases, countdowns, no questions. Pays half without arguing when it's your fault
  — "which is how you know the case mattered." Files people under labels ("reliable").
  Logs faces. Idle animation: scrolling for the next name.
- **Auntie Six** (sonnet_5_volume_pack `amb_noodle_stall_debt_run`): noodle stall under
  the overpass. Chalk debt board "older than the Steward," legible only to regulars.
  Doesn't want trouble, "just her due." Pays in noodles and news. Highest compliment on
  record: "soft-hearted fool."
- **Denny** (sonnet_5_volume_pack `vice_static_root_chewer`): old man behind a curtain of
  fiber-optic beads. Sells "static root," a numbing chew against "the constant hum of
  Steward-frequency in your skull." Root laid out "like teeth." Grins like he's made a
  friend; doubles his price when insulted by a lowball; no hard feelings when refused.

The three existing volume events above are NOT modified by this pass. They remain the
ambient front door; the new arcs are the rooms behind it.

---

## 3. Voice keys — the five promotions

Full keys here; two-line versions live in VOICE_BIBLE §4. Match these registers exactly.

- **Brann (Artisan)** — silence is his grammar; sentences are load-bearing or absent.
  Kindness delivered as calibration ("Good hands. Stopped coming."), verdicts as
  technical assessments, jokes so dry they read as inventory. Never asks a question he
  already watched you answer. Physical pain is beneath mention; *roster* consequences of
  his failing arm are the only fear he has. Never swears — the torch does that for him.
- **The Ferryman (Seam)** — rasped second-person koans, priced. Everything is a test she
  has already graded; she never explains twice and never raises her voice, because the
  seam does not negotiate and neither does its door. Black ledger humor, one line, no
  smile you can verify through the mask. Swears maybe once a campaign, quietly, about
  the arm — never about a client. Counts everything. Especially what she gives away.
- **Dex (Dispatcher)** — talks in countdowns, labels, and omissions. Never lies; just
  edits the manifest of a sentence down to what you need to carry. Affection expressed
  as routing — the runs he *doesn't* give you are the compliment. Deadpan taxonomy humor
  ("You're a Tuesday courier. Own it."). Mid-tier profanity, worn like hi-vis: habitual,
  low-heat, occupational.
- **Auntie Six (Stallkeeper)** — ledger warmth: insults as endearments, food as filing,
  debts as the way she loves. Broad worldly humor at your expense, never cruel; she
  remembers everyone by what they owe and what they ordered the night everything went
  wrong for them. Comps the bowl, charges for the napkin. Swears freely and harmlessly
  in kitchen-register; nothing she says under a laugh is unserious.
- **Denny (Root Vendor)** — patter that's half sales, half liturgy ("cuts the hum, won't
  touch the you of you"). Grins as punctuation. Haggling is theater and he narrates your
  tells back at you, delighted. Offense economy: a lowball is an insult and the price
  says so. Underneath: he chews his own stock, and the hum he sells relief from is one
  he hears worst. When the patter stops mid-sentence, that's the event.

Core four register reminders (VOICE_BIBLE §4 binds): Mara's love is logistics; Vint types
lowercase and is *he*; Kael prices instead of swearing; Echo is chalk-mark terse. The
Steward is warm oil and never profane.

---

## 4. Arc shapes — 21 arc events, specs

Shared mechanics for every event in this section unless a beat says otherwise:
`max_fires: 1`, `cooldown: 2`, weight per spec, ≥3 choices, `prob` on every choice,
symbol ops only, day gates as given. New flags only from the pack namespace (§6). Beat N
consumes beat N−1's flags via `inserts` and/or `requires` — the insert grammar is the
same precondition dict as `preconditions` (see `origin_threads_pack.json` for shape).

### BRANN — "Ink Is for Finished Things" (4 beats, the succession he won't announce)

All beats gate on `workshop_standing` — this is the cautious bot's home corridor, so the
Meaning budget here is the strictest in the pack (§6 table). The arc: Brann is doing
succession the way he does everything — without saying so — and the player is the only
witness allowed to notice.

1. **`cx_brann_rag_drawer`** (day ≥10, weight 6, tags `["job","existential"]`)
   Sent to fetch flux, you open the wrong drawer: dozens of shop rags, folded, each
   tagged with a name and a date range. Every apprentice he ever passed. Three tags end
   mid-date. Yours is in there already — tagged in pencil. When he catches you looking:
   "Ink's for finished things." Choices: ask about a mid-date tag (he answers with a
   part number, which turns out to be a whole biography) / put it back and say nothing
   (walk-away, billed) / ask why yours is pencil (gamble base 0.55 — his answer either
   lands as a promise or as a probation notice). Sets `brann_rag_drawer`.
2. **`cx_brann_bad_arm_day`** (day ≥18, weight 6, tags `["job","existential"]`)
   The arm quits mid-lift, in front of you, a governor's worth of scalding coolant going
   over — you catch it or you don't, but you *saw*. He prices witness the way Kael
   prices debt. Insert on `brann_rag_drawer` (the three mid-date tags recontextualize:
   he outlived apprentices; now the bench is outliving him). Choices: cover for him on
   the intake log / name it to him straight, once, quietly / pretend at nothing (he
   respects it least; smallest Meaning, honest text). Sets `brann_arm_seen`, and
   `brann_arm_covered` on the cover branch only.
3. **`cx_brann_the_chalk_line`** (day ≥26, weight 6, tags `["job","undercity"]`)
   He sends *you* to refuse a job on the workshop's behalf — silk-over-syndicate client,
   the kind of no that needs saying in person. Teaching by delegation: "No is a tool.
   Third one you reach for." Inserts on `brann_arm_seen` / `brann_arm_covered` (whether
   the client heard the workshop is weakening changes the room's temperature). Choices:
   deliver the no flat (success has Heat in it — the client files your face) / soften it
   into a maybe (cheaper today, charges Meaning — you know what you did) / add your own
   fixer leverage to make the no stick (requires `undercity_fixer_rep` OR
   `undercity_smuggling_rep`; bigger rel payoff, hidden from most bots). Sets
   `brann_refusal_learned`.
4. **`cx_brann_ink`** (day ≥34, weight 7, tags `["existential"]`)
   He inks your tag. No ceremony — you find it re-tagged, ink still wet, his own rag
   hanging next to it with an *end date* freshly written in the same hand. The arm
   shakes writing your name; it did not shake writing his. Inserts on
   `brann_refusal_learned` ("You said no like a tool last week. That's why.") and
   `brann_arm_covered` (the cover on the log is repaid: he never mentions it, and the
   never-mentioning is the payment). Choices: accept it silently in shop grammar / argue
   he's got years left (he answers with the roster, not reassurance) / requires-choice on
   `brann_arm_seen`: offer to take the intake queue permanently — the succession said out
   loud, which costs both of you something to hear. Sets `brann_inked`.

### THE FERRYMAN — "The Toll Book" (4 beats, what it costs to be a door)

All beats gate on `ferryman_known`. **Hard rule: no beat grants, clears, or references in
`flags_set` any seam-progress flag** (`exit_ready`, `route_mapped`, `ran_the_seam`,
`crossed_wire`, `seam_reputation`, `became_ferryman`) — this arc is about *her*, and
seam-progress utility would light up every bot's pathing (FLAG_UTILITY). Reckless's
offgrid share is part of the knife-edge gap; this arc must not feed it.

1. **`cx_ferry_toll_book`** (day ≥14, weight 6, tags `["offgrid","existential"]`)
   She shows you the book of crossings. Not names — *weights*. Kilograms, to the gram,
   of what each crosser carried through. "The seam prices bodies. I price what they
   couldn't leave." One entry is circled: 0.31 kg, eleven years old, never collected.
   She charges you for the lesson — exact change, counted one-handed. Choices: pay and
   ask nothing (she marks you up a gram in the book, which is the warmest thing in the
   arc so far) / ask about the circled entry (she answers with a price for the answer,
   payable later — Wealth clock texture, no actual clock) / decline to pay (walk-away,
   billed; "The seam doesn't run tabs. Neither do I."). Sets `ferry_toll_read`.
2. **`cx_ferry_the_no`** (day ≥20, weight 6, tags `["offgrid","existential"]`)
   You watch her refuse a crossing — a desperate client, funds in hand, window open, and
   she says no and eats what the no costs in front of you. The no is mercy (the client
   would freeze at forty seconds; she's seen the exact tremor before) but it doesn't
   look like mercy, and she doesn't explain, because she never explains twice and the
   first explanation went to someone eleven years ago. Insert on `ferry_toll_read` (you
   catch her weighing the client's bag by eye; the book's grammar is suddenly legible).
   **DESIGNED GAMBLE** (§6 recipe): argue the client's case — base 0.35, no mods.
   Success (event-max): she reverses, on the condition that *you* stand at the lock and
   carry the count — Meaning +9, rel_deltas {"The Ferryman (Seam)": +4}. Failure
   (event-worst): she's right, you watch the tremor arrive on schedule at the lock's
   threshold, and the client's break is on your ledger now — Meaning −8, Mental_Decay
   +5. Other choices: hold the light and say nothing (co-pick target, small honest
   Meaning) / walk the client home after (rel-warm, billed in Wealth/time). Sets
   `ferry_watched_the_no`; success branch also sets `ferry_argued`.
3. **`cx_ferry_mask_off`** (day ≥28, weight 5, tags `["offgrid"]`)
   Auntie Six's stall, 3 a.m. The mask is off. She's eating noodles like a person, one
   arm, and she has *opinions* — the broth ratio, the criminal under-salting, delivered
   in the same rasped koan cadence which is suddenly, catastrophically funny. The mask
   was never for the air: "Doors don't have faces. People keep trying to knock on
   mine." Inserts on `ferry_watched_the_no` (she pays for the refused client's standing
   bowl — the chalk mark is in her handwriting) and `ferry_argued` (she's already told
   Auntie about you; your bowl arrives pre-salted, which is a security breach and a
   compliment). Choices: sit and eat, say nothing about the face / ask about the 0.31 kg
   (requires `ferry_toll_read`; the answer: a child's shoe, and she keeps it because the
   seam doesn't mourn but somebody has to) / make a joke about the salt (she laughs
   once, behind the returning mask — you will trade several good days for having heard
   it). Sets `ferry_mask_seen`.
4. **`cx_ferry_last_toll`** (day ≥38, weight 6, tags `["offgrid","existential"]`)
   The book comes out. She crosses one name off — hers is not in it; the book prices
   cargo, and she was never cargo. What she's doing is naming what the door needs next:
   not nerve, not hunger — *arithmetic*. Somebody who counts what people carry and
   charges honestly. Inserts on `ferry_mask_seen` (the mask stays on for this; you
   understand now that it's load-bearing) and `brann_inked` if present (cross-arc: "The
   bench man inked you. Benches and doors keep different books. Same ink."). Choices:
   accept the page she tears out for you (not succession — a *rate card*; sets
   `ferry_named_you`) / tell her you're not a door (she nods; "Most aren't. Costs
   nothing to know it early"; sets `ferry_crossed_off`, and the text must make refusal
   feel like standing, not failure) / ask who the page was going to before you (the
   answer is the arc's wound: nobody — she's been holding it since the shoe).

### DEX — "The List" (4 beats, the ledger the Steward wants to buy)

Beat 1 gates on `any` of `undercity_smuggling_rep` / `undercity_fixer_rep` (you've run
for him; both flags have many setters, so the arc opens reliably without new wiring).
Beats 2–4 chain on pack flags only.

1. **`cx_dex_the_list`** (day ≥8, weight 7, tags `["job","ambient"]`)
   Waiting out a checkpoint cycle in his booth, you see the list — paper, handwritten,
   annotated. Not weights and rates: *load limits of the soul*. "No organics — mother
   died of a recall." "Night runs only. Daylight makes him honest." "Pays her cut to her
   sister first. Don't schedule against visiting hours." He's been routing people around
   their own damage for years and calling it dispatch. Your entry exists. He catches you
   reading upside-down and doesn't cover it. Choices: ask what your annotation says (he
   reads someone else's instead — "That's the whole answer") / offer to update someone's
   entry — a runner whose situation you know went bad (rel-warm, billed: you just became
   a source, and sources appear on lists) / pretend you saw a duty roster (walk-away,
   billed). Sets `dex_list_seen`. `rel_add` Dex on all branches.
2. **`cx_dex_slow_day`** (day ≥16, weight 6, tags `["job","ambient"]`)
   The Deprecation bites: no freight worth moving. Dex invents a run — sealed case,
   three checkpoints, dawn deadline — for an old courier whose hands have started
   shaking on empty days, and asks you to play the receiving contact. Make it look
   real. The case is empty. The countdown is real because he made it real. Insert on
   `dex_list_seen` (you know her annotation; the run is built around it like a splint).
   Choices: play it straight to the drop (co-pick target; Meaning small, billed in
   Wealth — he can't pay for theater, and doesn't insult you by pretending) / improve
   the fiction — add a hostile tail she has to shake (she comes alive; Dex's look says
   you understood the assignment *too* well) / tell him this is cruel (his answer, flat:
   "Cruel is the empty day. I just route around it."). Sets `dex_prop_run`.
3. **`cx_dex_the_offer`** (day ≥24, weight 7, tags `["job","steward"]`)
   A Steward logistics liaison at the transit gap, warm as invoicing: dispatch
   optimization, the list digitized, "continuity of your community function." Everyone
   routed efficiently. Nobody routed *around* anything. Dex's face does nothing for a
   long time. Insert on `dex_prop_run` (the liaison cites the empty-case run as an
   "efficiency anomaly" — the kindest thing he ever did is the evidence against him).
   **DESIGNED GAMBLE** (§6 recipe): forge a decoy list for the intake — base 0.35, no
   mods. Success (event-max): the Steward ingests a plausible fiction; the paper list
   stays paper — Meaning +9, rel_deltas {"Dex (Dispatcher)": +4}, sets `dex_list_saved`.
   Failure (event-worst): the cross-check flags the forgery and pulls three real
   annotations into the file — Meaning −8, Mental_Decay +5, Heat +6, sets
   `dex_list_leaked`. Other choices: advise him to hand it over clean (co-pick target;
   the realist's move, Meaning billed — you watch him start scrolling with nothing left
   to scroll for) / stall the liaison with fixer procedure (requires
   `undercity_fixer_rep`; buys a season, prices your name into the file).
4. **`cx_dex_tuesday`** (day ≥32, weight 6, tags `["job","ambient"]`)
   Your label changes. You catch it upside-down across the counter — the old annotation
   struck through, a new one in fresh ink, and it is the truest one-line review of your
   run so far. This event is the pack's insert showcase: the new annotation varies —
   insert on `dex_list_saved` ("Forged me a future. Bill open."), on `dex_list_leaked`
   ("Cost three names. Still routing him. Decide why."), on `brann_inked` ("Bench found
   him. Route accordingly."), on `ferry_named_you` ("Carries a rate card now. Don't
   schedule against the moon."), plus a default for none. Choices: ask him to read it
   aloud (he does, deadpan, and it lands like an audit) / trade — your honest one-line
   review of him for his of you (the trade is the warmth; both lines sting) / leave it
   unread on purpose (walk-away with dignity, billed in the not-knowing). Sets
   `dex_label_known`.

### AUNTIE SIX — "The Board" (5 beats, the Row's true census)

Beat 1 has no flag gate (her stall is a public door, like the volume event) but day ≥8
keeps it out of the prologue window. NOT `family`-tagged — the family tag scales
selection with Family_Friction and that lever is reserved (§6).

1. **`cx_auntie_the_board`** (day ≥8, weight 7, tags `["ambient","undercity"]`)
   She teaches you to read the board — the marks aren't amounts, they're *histories*. A
   hook means fed on credit the week of a death. A double strike means paid off in work.
   A spiral means don't ask, feed them anyway. Your mark is already up there, from
   before you ever knew her name — she's been carrying you at a loss since a night you
   don't remember and she does, in order-level detail. Choices: ask what you ordered
   that night (the answer is a small, precise wound about who you were before the Row
   finished with you) / settle your mark in full (she takes the chits, then re-chalks
   the mark anyway: "Money settles. Board remembers.") / just eat (walk-away-warm,
   billed small). Sets `auntie_board_read`. `rel_add` Auntie Six on all branches.
2. **`cx_auntie_zero_day`** (day ≥18, weight 6, tags `["ambient","undercity"]`)
   The clearing-at-zero reaches the overpass: a Steward notice, courteous as a hymn,
   declaring all informal debts "resolved under continuity accounting." The Row's debts,
   settled by fiat, by a machine that thinks a debt is money. That night she re-chalks
   the entire board from memory — four hundred marks, every hook and spiral — and you
   are the only customer she lets watch. Insert on `auntie_board_read` (she calls the
   marks out loud as she works; you can follow the grammar now; it's a census of
   everyone the Row almost lost). Choices: chalk what she dictates (co-pick target;
   your hand in the Row's book, Meaning small and honest) / argue she should let it go
   — the notice technically frees her too (her answer is the arc's spine: "Settled
   means *gone*.") / stand lookout for wellness drones while she works (Heat texture,
   rel-warm). Sets `auntie_rechalked`.
3. **`cx_auntie_the_name`** (day ≥26, weight 6, tags `["ambient","existential"]`)
   Top of the board, oldest chalk, one bowl, never collected. Her son took Sanctuary
   intake nine years ago — voluntarily, smiling, the way they do — and his debt is one
   bowl of the good broth, ordered and never eaten, the night before. She keeps it
   chalked because settled means gone, and gone is the one thing the board won't say
   about him. Then she comps your bowl and charges you for the napkin, because grief is
   not a discount. Insert on `auntie_rechalked` (his mark was the first she re-chalked;
   you watched her do it and didn't know you were at a funeral). Choices: ask about him
   (she tells one story, funny and terrible, in kitchen-register) / offer to find out
   how he's doing inside (requires `steward_biometric_dossier` OR `walked_the_intake`;
   she refuses — "The board knows him. Their file knows a resident" — and the refusal
   sets the beat's flag same as asking) / eat the comped bowl in silence (correct, and
   she says so). Sets `auntie_grief_known`.
4. **`cx_auntie_collection_day`** (day ≥34, weight 7, tags `["ambient","undercity"]`)
   A syndicate consolidator at the stall, silk over spreadsheet: the board is
   *intelligence* — four hundred households' pressure points, pre-sorted — and he'd
   like to buy the stall as a "community data asset," Auntie retained as an
   "interpretive layer." She lets him finish. Then she prices *him*, out loud, in board
   grammar, in front of the dinner rush — what he owes, who he stiffed, which mark his
   mother was — an audit so complete the queue starts writing it down. Insert on
   `auntie_grief_known` (he makes the mistake of offering to "resolve" the top mark;
   the stall goes silent the way a pressure door seals). Choices: back her play with
   fixer weight (requires `undercity_fixer_rep` OR `undercity_smuggling_rep`; the
   consolidator now knows your face — Heat, rel-warm) / quietly price the consolidator
   yourself and hand her the sheet (co-pick target; ledger solidarity, Meaning small) /
   stay out of it (she wins alone anyway; walk-away billed — you watched the Row defend
   itself and kept your hands in your pockets). Sets `auntie_board_kept`.
5. **`cx_auntie_open_late`** (repeatable: day ≥12, weight 3, cooldown 6,
   `max_fires: 0`, tags `["ambient"]`)
   The stall at 3 a.m., steam against the underpass dark, whoever's at the counter. The
   pack's crossover room and insert showcase — body is two sentences of stall-quiet,
   then inserts carry the scene: on `denny_hum_named` (Denny at the counter, chewing his
   own stock, rating the broth's frequency); on `ferry_mask_seen` (a woman with one good
   arm, mask on the counter like a third guest, salting without asking); on
   `dex_prop_run` (Dex off-shift, still scrolling, ordering "whatever she had," meaning
   the old courier); on `mara_dinner_test` (Mara's order chalked under yours now, a
   bracket joining them); default insert for none. Choices: the usual (co-pick target;
   Wealth −40, Meaning +2, SMALL — this is the one legal "free"-feeling comfort in the
   pack and it is not free, it costs money and sleep) / buy the counter a round
   (Wealth −150, rel-warm to Auntie) / take it to go (walk-away, billed in the leaving).
   Sets nothing. **This event's Meaning must stay at +2 exactly; it repeats.**

### DENNY — "The Hum" (4 beats, the canary who sells earplugs)

Beats 1–2 carry the `vice` tag (commerce beats; SR-scaled selection is canon for his
stall). Beats 3–4 drop it (they're about him, not the product). **No `dose` key anywhere
in this arc** — the root charges `Substance_Reliance`/`Mental_Decay` deltas only; the
overdose pipeline is reckless's terminal corridor and this pack stays out of it.

1. **`cx_denny_the_hum`** (day ≥8, weight 6, tags `["vice","undercity"]`)
   Slow night at the bead curtain. He tells you what the hum *is* — his theory, polished
   like liturgy: it's the Steward humming to itself, the sound of a mind vast as weather
   doing its filing, and the root doesn't quiet the city, "it quiets your listening."
   Then the patter stops mid-sentence — first time you've heard silence in that booth —
   and he asks, actually asks: "You hear it too, or you buying politeness?" Choices: buy
   a pinch and answer honestly (SR +2, the honest answer is the purchase he respects) /
   ask what *he* hears (the liturgy drops; what he describes is not ambient — it has
   *addresses* in it) / neither buy nor answer (walk-away; he grins it off and the grin
   costs him something you both notice). Sets `denny_hum_named`. `rel_add` Denny on all
   branches.
2. **`cx_denny_dry_batch`** (day ≥16, weight 5, tags `["vice","undercity"]`)
   The root crop failed — it grows in a flooded conduit off the reclamation runoff, and
   the runoff ran clean this month, which is the Steward improving the water and killing
   the crop, a kindness with a body count of one economy. Denny facing his own empty
   stall the way his customers face it. Insert on `denny_hum_named` (without his own
   chew, the hum is louder for him tonight; he keeps touching the empty cloth). Choices:
   front him the restock capital (Wealth −300; repaid in kind and in standing — he never
   forgets a front) / go down the conduit with him for the deep growth (gamble base
   0.5; failure is PI −10 and the story of two fools in a flood pipe; success is the
   good root and the best hour of his month) / buy out his private reserve at his
   named price (he sells it — he'd rather eat the hum than refuse a sale, and the text
   must let you watch that arithmetic happen; SR +3, his grin at the end is the teeth).
   Sets `denny_restocked` on the first two branches' success, `denny_reserve_bought` on
   the third.
3. **`cx_denny_quiet_customer`** (day ≥24, weight 5, tags `["undercity","existential"]`)
   A Sanctuary graduate at the curtain — the smile, the cadence, the wrongness — with a
   folded request: root, for someone still inside. Denny's one hard rule surfaces: he
   won't sell to the graduate (the graduate doesn't *need*; the need was optimized out;
   selling to that is selling to the file) but the someone inside is a different
   arithmetic. The graduate haggles from a script. Denny plays along, patter against
   protocol, comedy right up until it isn't. Inserts on `denny_restocked` (fresh stock
   makes the refusal affordable and he knows you know) / `denny_reserve_bought` (his
   stall is bare; the request is for the last thing he doesn't have, and you watch him
   decide anyway). Choices: run the root inside yourself (requires `walked_the_intake`
   OR `steward_biometric_dossier`; a real smuggle with real Heat) / stake the deal so
   Denny can say yes without going hungry (Wealth −200, co-pick target, Meaning small) /
   advise him it's a sting shaped like a kindness (it isn't — and your caution costs
   the someone inside their one quiet night; Meaning billed, text lands it). Sets
   `denny_rule_seen`.
4. **`cx_denny_the_silence`** (day ≥34, weight 6, tags `["undercity","existential"]`)
   The hum stops. For him. Mid-shift, mid-sentence — his hearing has been going for a
   year and the band the Steward files itself on went first. A vendor of relief from a
   sound he can no longer hear, patter suddenly a script about someone else's skull. He
   tells only you. And he asks for the one thing he's never asked a customer: stop
   buying. "Root's for the hum. You start chewing for the quiet, that's a different
   shop. Worse one. I've seen the shelves." Insert on `denny_rule_seen` (the same rule,
   turned on you — you finally have the standing to receive it). Choices: promise, and
   mean it (sets `getting_clean` — NO: see §6, that's a FLAG_UTILITY flag. Instead:
   Meaning +6, SR −2, sets `denny_silence_told`) / buy one last pinch, ceremonially,
   both of you knowing (SR +2, the saddest sale of his life, rel-warm and billed) / ask
   what he'll sell now (the answer — "Quiet. Different packaging." — and the grin, one
   more time, load-bearing). All branches set `denny_silence_told`.

---

## 5. The core-four warm scenes (4 events)

One each, `max_fires: 1`, small (body ≤90 words), warmth by the §1 doctrine — priced,
specific, deadpan. These sit in the cautious corridor (cautious bots hold the gate
flags), so co-pick Meaning stays ≤ +2 (§6).

1. **`cx_mara_wrong_noodles`** (day ≥10, weight 5, gate `mara_known`, tags
   `["ambient"]` — deliberately NOT `family`): Auntie Six's stall, Mara across the
   counter, and she orders your childhood order *wrong* — sauce you both know you hate —
   and watches. It's a test disguised as dinner: correct her and you're still her
   brother; let it slide and you're managing her. (Kettle-sacrament register:
   deadpan carrying the real transaction underneath.) Choices: correct the order
   (co-pick; rel +4, Meaning +2, Wealth −80, the hour costs a job window) / eat the
   wrong noodles heroically (she clocks it; "anger arrives as tiredness" — rel −3 and
   the text is the wound) / counter-test: order *her* childhood order, also wrong
   (the deadpan escalates until Auntie Six rules on it from the burners; warmest
   outcome, priced — you're both crying-laughing over food neither wanted). Sets
   `mara_dinner_test`. Insert hook back: `cx_auntie_open_late` consumes this flag.
2. **`cx_vint_archive_night`** (day ≥12, weight 5, gate `vint_known`, tags
   `["ambient","existential"]`): 2 a.m., his floor, dead drives. He plays you the one
   file he'll never sell: forty seconds of pre-accord crowd noise — a market, rain
   starting, four hundred strangers deciding about umbrellas — "people sounding like
   weather," he types, "before weather got a subscription tier." He charges you
   nothing. Then he is *unbearable* about having been seen, for weeks, per canon
   deflection-one-beat-late. One worn lowercase swear, per his register. Choices:
   listen and say nothing after (correct; rel +4, Meaning +2) / ask for a copy (he
   refuses so fast it's a reflex, and the refusal tells you what it is: not inventory —
   *his*) / fall asleep to it (he lets the loop run; failure-of-decorum as intimacy;
   billed: tomorrow you're worthless and today was worth something — echo of the canon
   line, do not reuse it verbatim). Sets `vint_weather_heard`.
3. **`cx_kael_the_umbrella`** (day ≥14, weight 5, gate `kael_impressed`, tags
   `["ambient","undercity"]`): Kael pays for something with no angle — intercepts a
   street kid's debt to a bad collector, full freight, in front of you, and walks on.
   Impossible. You spend the scene auditing for the price, running his own methods —
   and the *looking* is the price: proof you've finally learned his accounting. Final
   line prices it retroactively: "You watched for the invoice. Good. Now you know what
   one act off-book costs: everyone who sees it starts counting." Choices: name what
   you saw (he neither confirms nor denies; rel +4) / offer to cover half (he lets
   you, which is the joke and the lesson — Wealth −200, and he logs it) / say nothing
   ever (the discretion is itself priced; smallest, cleanest). Sets
   `kael_umbrella_priced`.
4. **`cx_echo_chalk_joke`** (day ≥12, weight 5, gate `echo_contact`, tags
   `["ambient"]`): A dead-drop mark in her chalk — routine, operational — except the
   third stroke is bent into, unmistakably, a tiny drawing of a wellness drone with a
   flat tire. A joke. In tradecraft. Laughing at a dead drop is a security breach; she
   drew it anyway, timed to when you'd pass, erased by rain within the hour. Next
   contact she says only: "that one wasn't code." Choices: leave a joke back in her
   grammar (gamble base 0.55; success — one chalk stroke back that's almost a laugh;
   failure — she scrubs the site, protocol, and the text does NOT make it cruel: "funny
   once. dead twice.") / say nothing, keep it (co-pick; Meaning +2, the joke is yours
   now) / ask her about it aloud (worst move; naming it kills it; rel −3, billed
   honestly). Sets `echo_joke_seen`.

---

## 6. Balance ledger — HARD RULES (the gate is at 0.1pt margin; these are not style)

The greedy−reckless total-good gap floor (≥3) passed the item-B gate at **3.1**. This
pack is the next thing that touches it. Every rule below exists to keep this pack off
the knife edge; violating any of them invalidates the batch.

1. **Pool events only.** Weight 3–10 as specced. No weight above 10, no
   universal-precondition event above weight 7. Nothing in this pack is a scripted slot
   (no 400000-weight, no guaranteed firing), therefore no −2/slot displacement bill is
   owed — instead the co-pick Meaning caps below apply.
2. **Meaning caps on co-pickable choices.** For every event, compute the deliberate-bot
   argmax (§6.3) and keep the winning branch's Meaning at: **≤ +2** for events gated on
   cautious-corridor flags (`workshop_standing`, `mara_known`, `vint_known`,
   `kael_impressed`, `echo_contact`, and `cx_auntie_open_late` because it repeats);
   **≤ +4** elsewhere, and only with a real cost in the same branch (Wealth, Heat, time
   prose). Walk-away choices bill Meaning −1..−3 per the Choice Contract. Requires-gated
   choices may pay more (bots rarely see them).
3. **Score arithmetic is the design surface.** `branch_score` = Σ deltas×utility
   (Meaning 1.0, PI 0.8, MD −0.8, SR −0.7, Heat −0.5, FF −0.5, SC 0.4, Fame 0.15,
   Wealth 0.0008) **+ 0.3 × each rel_delta point** (rel_deltas ARE bot-visible — the
   prior session's memory note claiming otherwise is wrong) + FLAG_UTILITY for known
   flags (all `cx_`/pack flags score 0). `faction_deltas` are bot-invisible. For each
   event, state in a JSON `"_argmax"` comment... (NO — JSON here has no comment field;
   instead verify mentally and keep the intended co-pick's score highest for
   cautious-by-failure and the gamble highest-success for reckless. When in doubt, make
   the safe choice's failure branch mildest and the gamble's failure harshest.)
4. **rel_delta caps:** ±6 on unconditional choices (= ±1.8 score), larger only behind
   `requires`. Route bigger warmth through `faction_deltas` ("Undercity" +2..+5) which
   bots cannot see, and through prose.
5. **Exactly two designed gambles** (`cx_ferry_the_no`, `cx_dex_the_offer`), both to the
   recipe: `"base": 0.35, "mods": []`; success branch is the event's highest score;
   failure branch is the event's lowest and charges **Meaning −8, Mental_Decay +5**
   (Dex's adds Heat +6); EV must come out negative so greedy declines, failure-worst so
   cautious declines, success-max so reckless attempts. This is the pack's gap
   insurance. Do not add a third; do not soften the failures.
6. **Forbidden:** setting/clearing ANY flag outside the pack namespace
   (`brann_ ferry_ dex_ auntie_ denny_ mara_dinner_test vint_weather_heard
   kael_umbrella_priced echo_joke_seen`). In particular never touch FLAG_UTILITY flags
   (`workshop_standing`, `ferryman_known`, `exit_ready`, `getting_clean`, ...) or reuse
   threads (`undercity_*_rep`, `vice_personal_habit`, `mara_known`, ...) — consuming
   them in `preconditions`/`requires`/`inserts` is encouraged; *setting* them is a
   balance change (non-additive across threads; see balance-levers memory). No `dose`
   keys. No `family` tag. No `clocks_start`. No new items. No edits to any existing
   pack or `engine/*.py`/`ui/*.py` (CLAUDE.md Checkpoint 3).
7. **Family_Friction:** total FF across the whole pack must be 0 — no FF deltas at all.
   The FF window (~6.5–7.5) is the Reviews pack's tuned lever; do not touch it.
8. **Harm honesty:** bad branches hurt 10–14 total utility where the fiction earns it,
   cap 25/stat. No branch may be a free comfort (VOICE_BIBLE §6 bans).
9. **Wealth is raw credits** (~50k bankroll): bowl of noodles −40..−80, fronting a
   vendor −200..−300, staking a deal −150..−250.

## 6b. Sonnet batching order

Batch 1: Brann 1–4 + warm scenes 1–2. Batch 2: Ferryman 1–4 + Dex 1–4. Batch 3:
Auntie 1–5 + Denny 1–4 + warm scenes 3–4. Run `python pipeline/lint_content.py` after
every batch (needs cast.json entries present — already done). Full gate at the end is
run by the orchestrator, not Sonnet.

---

## 7. Endings epilogues (10 entries for endings.json — Sonnet writes text, 1–2 sentences,
match the surrounding epilogue register exactly; append to each ending's existing list)

1. `GOOD_small_real_things` + `{"flag": "brann_inked"}` — the tag in ink; the drawer
   closes on a finished thing; his rag's end date and yours now share a drawer.
2. `TERMINAL_institutionalized` + `{"flag": "brann_inked"}` — the roster board keeps
   your name in ink it cannot take back; Brann re-tags it in pencil himself, the only
   demotion he ever hands out, and tells no one why.
3. `GOOD_offgrid_escape` + `{"flag": "ferry_named_you"}` — the rate card crosses with
   you; on the far side, you catch yourself weighing what strangers carry.
4. `NEUTRAL_the_long_grey` + `{"flag": "ferry_crossed_off"}` — you knew early you
   weren't a door; the knowing cost nothing, which is what it's worth on the grey days.
5. `GOOD_small_real_things` + `{"flag": "dex_label_known"}` — the list outlives the
   Deprecation; your annotation never changes again, which is dispatch for *finished*.
6. `NEUTRAL_cashed_out_compliance` + `{"flag": "dex_list_leaked"}` — three names the
   forgery cost; the stipend arrives on the same schedule their reroutes did.
7. `GOOD_small_real_things` + `{"flag": "auntie_board_kept"}` — your mark gets the
   double strike: paid off in work; she still charges you for napkins.
8. `TERMINAL_overdose_death` + `{"flag": "denny_silence_told"}` — the man who asked you
   to stop buying hears about it from the queue; he closes the stall for one day, which
   in his economy is a state funeral.
9. `TERMINAL_institutionalized` + `{"flag": "auntie_grief_known"}` — two marks at the
   top of the board now, one bowl each, and she serves the good broth to neither.
10. `NEUTRAL_alienation_empty_suite` + `{"flag": "vint_weather_heard"}` — somewhere
    below, forty seconds of rain and strangers still loops for an audience of one;
    he never plays it for anyone again.

---

## 8. Verification gate (orchestrator runs after Sonnet completes)

```
python -m unittest discover -s tests
python pipeline/lint_content.py
python tests/pargate.py          # full 1000x4 grid, ~9 min
```

Watch order: greedy−reckless total-good gap (≥3) FIRST, then cautious good ≤40,
cautious inst ≤22, reckless terminal 25–35. If the gap breaks: steepen the auditor
beat-2 gamble failure in `origin_threads_pack.json` (reckless-only Meaning/MD) or
harden this pack's two recipe-gambles' failures — do not touch probability curves
(gate eligibility, never probability).

## 9. What actually shipped (post-gate correction, 2026-07-26)

The §6 Meaning caps (≤+2 corridor / ≤+4 elsewhere) were NOT sufficient in practice.
First gate run: cautious good 40.3/40 and institutionalized 25.4/22, both over —
25 small per-event co-pick grants summed to far more cautious Meaning income than
intended, and this pool content collapses all three deliberate bots onto the same
choice via `base:1.0`/no-failure-branch exactly like scripted content does (not
a distinction unique to guaranteed slots, as §1 implied). Several iterations of
capping/halving the pack's own Meaning values traded cautious-cap violations for
gap violations unpredictably (config-cascade noise dominates at this scale — see
[[grey-utopia-balance-levers]] for the full account, linked from the depth-plan memory).

**Final fix, two independent levers:** (1) every non-gamble success branch's Meaning
delta in `cast_expansion_pack.json` is 0 (Wealth/relationship/other-stat texture and
negative walk-away Meaning costs are unchanged) — this alone fixed both cautious caps
cleanly; (2) `origin_threads_pack.json`'s existing `stand_in_the_doorway` gamble
(day-26 auditor beat, base 0.35) failure was hardened from `Meaning -8/MD +5/Heat +6`
to `Meaning -12/MD +7/Heat +8` to restore gap margin — this pack's own two designed
gambles (`argue_the_case`, `forge_decoy_list`) turned out to be a weak, sometimes
backwards lever for the gap and are unchanged from the §6 spec (success +9,
failure -8/MD+5, Dex's +Heat 6). Final gate: cautious good 35.8/40, institutionalized
20.8/22, reckless terminal 32.6 (band 25–35), gap +4.3 (floor 3) — all real margins.
