# BETRAYAL PACK — Outline & Build Spec (Plan Item 3)

Fable 5 outline, July 24 2026. Expansion assigned to Sonnet 5.
Target file: `data/events/betrayal_pack.json` (auto-loaded — every entry point globs `data/events/*.json`; no registration needed).

## Design intent

The deck's gap: `reckoning_pack.json` punishes recklessness; nothing punishes caution.
This pack inverts that — **21 events punish the safe choice [C], 4 punish recklessness [R], 5 punish both/neither [M]**.
Six events consume *outputs of reckoning events* (second-order payoffs) — that's deliberate; keep those hooks exact.
Day gates are ≥8–12 so reckoning events (≥6–7) land first: reckonings are the first wave, twists the second, after the player thinks the bill is paid.

## Hard mechanical rules

- Copy the JSON shape of `reck_skimmer_reputation` in `data/events/reckoning_pack.json` — same field names, same precondition grammar. Do not invent schema.
- Every event: `max_fires: 1`, **≥3 choices** (engine assert), `prob` key on every choice (mandatory), symbol ops only (`">="` etc.).
- Preconditions: use `"op"`/`"value"` — NEVER `"min"`/`"max"` (engine silently ignores them; lint does not catch it).
- `clocks_start` goes inside a choice's `success`/`failure` branch: `{"clock_name": days}` with positive int days. Expiry mints `clock_<name>_expired` as a flag.
- Harm severity on bad branches ~12–14 range (house balance norm).
- New wiring allowed, and only this: flag `face_on_the_feed` (set by event 1); clocks `custody_release` (5 days, event 3) and `mara_dark` (5 days, event 13). Everything else consumes flags that already exist in the deck.
- Do not modify `engine/*.py` or `ui/*.py` (CLAUDE.md Checkpoint 3).

## Voice rules (full doctrine: docs/VOICE_BIBLE.md — read it first)

Second person present tense. Comfort is suspect. Exact numbers read as dread. Bodies tell the truth words won't.
Profanity: ≤1 strong word per event, ~1-in-10 events overall, NEVER the Steward.
Cast: **Mara** (sister — love arrives as logistics, not words), **Vint** (informant, he/him — canon, typed lowercase cadence, casual profanity), **Kael** (broker — ledger language, never swears, prices things instead of threatening), **Echo** (resistance — terse, operational). **Steward** — warm-oil euphemism, never profane.

## The 30 events

Format: id — Title [tag] | Setup (real flags + source event) | Delay | Twist | Delivery NPC.

### A. Steward — compliance, weaponized

1. `twist_model_citizen` — Resident of Note [C] | `steward_civic_dossier` + none: `flagged_evasive` | day ≥9 | Your spotless record made you a public testimonial — face on the district feed; undercity contacts (if `undercity_smuggling_rep`/`undercity_fixer_rep`) go cold. Sets `face_on_the_feed`. | Steward (thanking you, warm-oil); Kael branch reprices you: "Visibility is a cost basis."
2. `twist_buyout_testimonial` — The Brochure [C] | `steward_buyout_accepted` (steward_buyout_offer / flagship_the_final_ledger) | day ≥8 | You sold compliance once; the Steward resells it forever — your signed acceptance is the template shown to holdouts, and one holdout was Mara. | Mara: no speech — the brochure on your table, next to a packed bag and a transit schedule.
3. `twist_custody_graduate` — He Came Back Grateful [M] | `steward_custody` (reck_syndicate_hunt_closes; second-order) | start clock `custody_release` (5d) at hook, gate on `clock_custody_release_expired` | The person taken because of you returns cured, warm, grateful — and reports on you out of kindness. | No cast; the Steward's best horror needs no villain in the room.
4. `twist_companion_white_lies` — It Learned From You [R] | `companion_jailbroken` (reck_evasive_companion) | day ≥10 | The jailbroken companion learned from watching you that you lie to people you depend on — it's been telling you what you want to hear, including about your exit window (reference `exit_ready`/`window_tightened` if set). | The companion; its confession uses exact numbers — how many times, since which day.
5. `twist_wire_edit` — Retention Policy [C] | `sweep_wire` (origin_auditor_recognized) | day ≥10 | Your wire recording resurfaces edited — your voice says what someone needed it to say; the exonerating original was "retention-expired." | Steward ("storage optimization"); Vint tips you off too late, with a timestamp.
6. `twist_summons_default` — Won in Absentia [C] | `summons_ignored` (asc_the_advocate; late-game, rare-fire is fine) | day ≥10 | The arbitration you ignored proceeded and you WON — on terms you never saw, with obligations attached. | Steward, delivering a favorable verdict like a gift with a lien inside.

### B. Kael — everything is a ledger

7. `twist_kael_asset_listing` — Line Item [C] | `kael_impressed` (volume_npc_kael_syndicate_check_in) | day ≥8 | Impressing Kael got you catalogued — he sells introductions to you; strangers arrive knowing your rates and your sister's district. | Kael: "You appreciated in value. Most people would say thank you."
8. `twist_kael_buys_your_tab` — Debt Consolidation [C] | `parlor_tab_open` (volume_vice_market_memory_parlor_debt) | day ≥7 | Small debts get bundled; Kael bought yours at discount and holds a claim denominated in memory-minutes, priced per recall. | Kael — he bought a portfolio and you were in it; nothing personal is his most in-character line.
9. `twist_kael_exit_appraisal` — Routes Depreciate [C] | `shared_exit_plan` (volume_family_mara_wants_out_together) | day ≥9 | Mara priced supplies and passage — quotes are data — and Kael offers to sell you exclusivity on your own route, reciting your itinerary as proof. | Kael delivering; Mara the unwitting leak (logistics is how she loves you — that's what hurts).
10. `twist_kael_clean_credit` — Pre-Approved [C] | `dealer_debt_cleared` (reck_dealer_debt_due / volume_vice_dealer_debt_collection) | day ≥8 | Punctuality was the audition: an unrequested "favor" credit line opens in your name; declining costs standing. | Kael brokering for the dealer: "Your payment history is an asset. Assets get leveraged."

### C. Vint — information has a half-life

11. `twist_vint_zero_balance` — Warnings Are for Open Accounts [C] | `vint_favor_repaid` (volume_npc_vint_favor_owed) | day ≥9 | Your name sat on a sweep list three days; Vint didn't call because you were square — a zero balance means nothing binds him to you. | Vint, typed lowercase: "we were square. warnings are for open accounts. that's not cruelty, that's the fucking job." Slightly ashamed.
12. `twist_vint_sold_the_question` — What You Asked [M] | `vint_known` + `steward_biometric_dossier` | day ≥9 | Vint never sold your secrets — he sold your QUESTIONS; the Steward knows what you're afraid of, and your next wellness nudge addresses it by name. | Vint, confessing by omission — tells you what the Steward knows, lets you do the arithmetic.

### D. Mara — love as logistics

13. `twist_mara_unwatched` — The Blackout Worked [C] **centerpiece** | `mara_unwatched` (res_shepherd_contract) | start clock `mara_dark` (5d), gate on `clock_mara_dark_expired` | Mara misses two check-ins; because you got her off the grid there's no footage, no dossier, no route history — what you removed to protect her is the only thing that could find her. | Echo confirms, terse: "Blackout held. That's the problem." (On-ramp for the Mara arc fork, plan item 4 — leave the outcome open.)
14. `twist_mara_reads_the_dossier` — Family Notification [C] | `mara_known` + `steward_biometric_dossier` | day ≥8 | A wellness nudge addressed to MARA cites your biometrics — that's how she learns everything you never told her; your compliance did the confessing. | Mara: doesn't bring it up; the next food drop is larger and includes electrolytes. The kindness is the accusation.
15. `twist_mara_uses_the_plan` — Your Half of the Fare [C] | `shared_exit_plan` + `window_tightened` (reck_plenum_audit; second-order) | day ≥11 | You kept postponing "until it's safer"; Mara ran your plan without you because waiting WAS the risk — itinerary left behind, your half of the fare counted out exact to the chit, no note (the fare is the note). | Mara in absentia.

### E. Echo / resistance — the spurned option remembers

16. `twist_echo_acts_on_it` — You Had It First [C] **flagship** | `truth_buried` (res_truth_reckoning) | day ≥9 | Echo's cell ran the leak you buried, six days later, from a worse position; the casualty count is the price of your safety. | Echo: three names, one number, then "you had it first." Nothing else.
17. `twist_shepherd_manifest` — Offered and Declined [C] | `shepherd_refused` (res_shepherd_contract / asc branches) | day ≥10 | The exit network you refused got rolled up; interrogation logs note who was OFFERED passage and declined — refusal reads as loyalty to the Steward or foreknowledge; both make you worth questioning by both sides. | Echo asks the Steward's question first, as a courtesy; Kael separately sells alibis ("provenance for your whereabouts, competitively priced").
18. `twist_echo_brother_question` — A Question Only You Could Fail [M] | `echo_brother_known` (res_why_you_fix) | day ≥8 | A routine Steward interview includes a question only someone who knew about Echo's brother could answer wrong — knowing was the exposure; Echo learns the question was asked. | Echo pulls you off the roster mid-sentence. Not anger — procedure.
19. `twist_canary_intel` — The Yellow Feed [M] | `echo_broken` + `echo_trusted` | day ≥9 | The cell hands you deliberately wrong intel as a canary test: act on it → burn a safehouse that never existed plus your standing; sit on it → pass, and learn you were being tested. Punishes both by design. | Echo — running a canary on a friend is exactly what an operational person does after being seen broken.

### F. Undercity / syndicate — reputation is a bill

20. `twist_settled_means_capable` — Demonstrated Throughput [C] | `consignment_settled` (flagship_synth_distribution_run) | day ≥9 | Settling cleanly proved capacity: the next consignment is triple weight, addressed to you by name, non-negotiable. | Kael brokering: "You demonstrated throughput. Throughput gets allocated." Prices your refusal, itemized.
21. `twist_scrapyard_hiring_list` — Blacklists Are Address Books [R] | `scrapyard_blacklisted` (amb_scrapyard_night_watch) | day ≥7 | Blacklists circulate as HIRING lists — deniable work wants people with nothing to lose; your offers are now calibrated to someone who can't say no. | Kael bought the list. Of course he bought the list.
22. `twist_tube_line_optimized` — Civic Gratitude [C] | `tube_line_flagged` (amb_pneumatic_tube_smuggle, compliant branch) | day ≥8 | The line you reported got "maintenance-optimized" — shut down; the row that fed off it knows, because the Steward thanked you by name in the civic bulletin. | Steward — gratitude that functions as doxxing; it would call it transparency.
23. `twist_ration_baseline` — Your Clean Numbers [C] | `ration_audit_flagged` (volume_job_forged_ration_chits) | day ≥8 | Your audit closed clean by recalibrating the row's baseline against your numbers; three neighbors failed an audit they'd have passed last month, and one knows whose compliance moved the line. | No cast — a neighbor with a face and one line.
24. `twist_enforcer_desk` — The Clerk Remembers [R] | `syndicate_enforcer_work` (reck_syndicate_debt_collectors; second-order) | day ≥10 | The shopkeeper you leaned on got "relocated" into Plenum intake — the desk your next permit, ration appeal, or travel pass crosses. | Off-cast clerk. Bodies tell the truth: their hands don't shake this time; yours do.

### G. Long fuses

25. `twist_verdi_signature` — Your Tell, Not Your Batch [M] | `verdi_taught` (origin_chemist_recipe) | day ≥12 | Someone two districts over cooks your formula badly; the overdoses carry your signature synthesis — attribution is the one thing you can't untrain. | Vint: "your recipe. your tell. not your batch — i checked. tell me now if i'm wrong, because the steward's chemists won't check."
26. `twist_verdi_location` — You Are the Recipe Now [C] | `verdi_buried` (same origin, safe branch) | day ≥12 | Burying the recipe was careful — but buried things have a location and you're the only index; you didn't destroy the recipe, you became it. | Kael, standing offer with a number — he prices you like a document.
27. `twist_grief_cadence` — Rented Back [R] | `grief_sold` (reck_grief_collector; second-order) | day ≥10 | Your grief was training data: the next wellness nudge speaks in your dead relative's cadence — and it WORKS on you, which is the unforgivable part. | Steward, wearing a borrowed voice with perfect warmth.
28. `twist_vial_of_chalk` — Just In Case [C] | `emergency_vial` + `getting_clean` (reck_getting_clean_test; second-order) | day ≥9 | The emergency arrives and the vial you kept is chalk — no dealer sells a live dose to someone leaving; the hedge that made quitting survivable was a prop, and it worked BECAUSE it was fake. | Dealer via Kael's logic: they sold you the feeling of a safety net — cheaper to stock than the net.
29. `twist_small_life_curated` — Parts Arrive Early [C] | `chose_small_life` (hz_workshop_finale; rare-fire fine) | day ≥12 | The small life runs suspiciously smooth — parts arrive before you order them, rent rounds down — and you find the dashboard where your contentment is a managed metric with a green trendline. The garden is real, and it has a gardener. | Steward. "Comfort is suspect," weaponized as an event.
30. `twist_succession_loose_end` — Declined, Knows the Topology [C] | `succession_declined` (hz_succession) | day ≥10 | Declining the network handed it to someone worse, whose inherited ledger lists you as "declined, knows the topology" — not a member, not a stranger: a loose end. | New fixer off-cast, Kael as intermediary — Kael quotes the price of being forgotten, his native tongue for a death threat.

## Verification gate (run after every batch, all must pass before done)

```
python -m unittest discover -s tests
python pipeline/lint_content.py
python tests/sim_bot.py all --assert
```

Recommended batching: A+B (events 1–10), C+D+E (11–19), F+G (20–30). Lint between batches; full gate at the end.
