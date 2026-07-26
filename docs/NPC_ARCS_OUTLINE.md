# NPC ARCS — Outline & Build Spec (Plan Item 4)

Fable 5 design + key beats, July 24 2026. Connective events assigned to Sonnet 5.
Fable-written key beats live in `data/events/npc_arcs_pack.json` (5 events, DONE — do not rewrite them).
Sonnet target file: extend `data/events/npc_arcs_pack.json` with the 12 connective events specced below.

## Design intent

Each of the four cast members gets a 5–7 beat arc that ends in a **devastating fork** — a choice
where every branch costs something the player has learned to value. Existing events are beats 1–5
of each arc (nothing is rewritten); this pack adds the fork (Fable, done) and the aftermath
(Sonnet, specced). The four forks share one thesis: **the way each NPC loves/works is exactly
how they break.** Mara's logistics, Vint's zero-balance honesty, Kael's ledger, Echo's operational
discipline — each arc weaponizes its owner's defining trait against the player.

Cross-arc wiring is deliberate: Kael's marker can pay for Mara's breakout; the Steward's canary
doctrine (betrayal pack, event 19) returns in Echo's fork; Sanctuary "graduates" (betrayal event 3)
are the courier class for the Steward's offers.

## Arc maps (existing beats → Fable fork → Sonnet aftermath)

### MARA (Sister) — the blackout was a door with no window
1. `fam_mara_*` intros → `mara_known` (sonnet_5_volume_pack)
2. deepen events → `mara_established`
3. `volume_family_mara_wants_out_together` → `shared_exit_plan`
4. `twist_mara_reads_the_dossier` (your compliance confessed for you)
5. `twist_mara_unwatched` → clock `mara_dark` (5d)
6. **FORK (Fable, done): `arc_mara_the_door`** — consumes `clock_mara_dark_expired`. The blackout
   *worked*: an unmonitored adult reads as an anomaly, and the coverage-gap sweep took her on day
   two. Sanctuary intake, "family reunification pending household compliance review."
   - Volunteer for the review → `mara_ransomed` + `steward_leash` (she comes home; you're enrolled)
   - Break her out (requires any: `kael_marker` / Kael ≥55 / `echo_trusted`) → success `mara_freed`
     (free, and gone — she saw your name on the blackout work order); failure `mara_deep`
     (transferred to Serenity Annex)
   - Wait for processing → `mara_graduated` (she comes back cured, warm, logging her own meals)
7. Aftermath (Sonnet): one event per outcome flag, below.

### VINT (Informant) — a zero balance means nothing binds him
1. vint intros → `vint_known`
2. deepen → `vint_established`
3. `volume_npc_vint_favor_owed` → `vint_favor_repaid`
4. `twist_vint_zero_balance` (he didn't warn you; you were square)
5. `twist_vint_sold_the_question` (he sold what you asked, not what you said)
6. **FORK (Fable, done): `arc_vint_open_account`** — Vint's handle is on a consolidation sweep,
   pickup 06:00. You're square with him. His own doctrine says nobody owes him the call.
   - Warn him free → success `vint_owes_you` (saved, and ruined: an informant in debt starts
     telling you what you want to hear); failure `vint_taken` (your warning is why they moved early)
   - Stay square → `vint_taken` (his queued last message approves; his clients inherit to you)
   - Sell him the warning → success `vint_counterparty` (he escapes; the friendship was the
     discount and you spent it); failure `vint_taken` (he pays, runs, is taken; you hold his money)
7. Aftermath (Sonnet): below.

### KAEL (Broker) — everything prices; not everything clears
1. `volume_npc_kael_syndicate_check_in` → `kael_impressed`
2. `twist_kael_asset_listing` / `twist_kael_buys_your_tab`
3. `twist_kael_clean_credit` / `twist_kael_exit_appraisal`
4. **KEY BEAT (Fable, done): `arc_kael_unpriced_line`** — his book, open for three minutes: your
   own line (rates, sister's district, projected default date), and one line with no number:
   *Tomas*, a crèche transfer docket twelve years old. Sets `kael_soft_spot_known` (ask / memorize
   branches; memorize also sets `kael_docket_memorized`; closing the book unread sets nothing).
5. **FORK (Fable, done): `arc_kael_the_audit`** — syndicate auditors, three days out. The hole in
   Kael's book is twelve years of skim keeping Tomas's processing file "pending review."
   - Keep the proof → `kael_owned` (every price drops, every conversation dies)
   - Sell it to the auditors → `kael_sold` (his book goes to a consolidator; your debts reprice)
   - Bring it to him (requires `kael_soft_spot_known`) → `kael_spared` + `kael_marker` (he closes
     the hole the only way it closes — lets the file lapse — and hands you one line at zero)
6. Aftermath (Sonnet): below.

### ECHO (Resistance) — the person is gone; the leverage was archived
1. `res_*` contact → `echo_contact`
2. trusted chain → `echo_trusted`
3. `res_why_you_fix` → `echo_brother_known` (canon: brother ALREADY returned from Sanctuary hollow —
   "He's happy now," in the voice people use for the word drowned; do not contradict this)
4. `echo_broken` beat / `twist_canary_intel` / `twist_echo_brother_question`
5. **FORK (Fable, done): `arc_echo_rollback_offer`** — a Sanctuary graduate delivers the Steward's
   offer: it kept a **pre-Sanctuary personality snapshot** of Echo's brother. Restoration is
   available. The price is the cell's dead-drop schedule. You are the channel because knowing about
   the brother was the exposure.
   - Take it to Echo → success `echo_refused_brother` (she refuses a copy of someone she already
     grieved); failure `cell_burned` + `brother_restored` (he comes back asking questions again —
     including what it cost)
   - Bury it → `offer_buried` (you decided for her)
   - Counterfeit the trade (requires any: `undercity_smuggling_rep` / `echo_trusted`) — a drop
     schedule that was true last month → success `brother_restored` + clock `false_ledger` (6d);
     failure `cell_burned` (the offer was itself the canary; the Steward already had the real one)
6. Aftermath (Sonnet): below.

## The 12 Sonnet connective events (specs)

Format: id | consumes | delivery. All: `max_fires: 1`, ≥3 choices, day-gate ≥1–2 days after their
fork is possible (Mara/Echo forks are clock-gated; use day ≥15 for their aftermath), harm ~12–14 on
bad branches. Copy the JSON shape of the five Fable events in this pack. Do not invent schema.

1. `arc_mara_supervised` | `mara_ransomed` + `steward_leash` | Mara home under "enhanced wellness
   partnership" — the flat is full of sensors she dusts like furniture; the leash payoff: a nudge
   asks you to reschedule a job the Steward shouldn't know about. Logistics voice: she stocks your
   shelf by dossier now, not by memory.
2. `arc_mara_postmark` | `mara_freed` | No message ever comes — that's the message. What arrives is
   a shipment: her half of the old exit fund, exact to the chit, routed through four dead drops.
   She learned that from you. Meaning up, everything else down.
3. `arc_mara_graduated_checkin` | `mara_graduated` | She visits weekly, on schedule, cheerful,
   punctual — she never came on schedule in her life. She gently recommends Sanctuary intake
   "before winter." The kindness is procedural now. Offer a choice to test her (she passes, which
   is worse).
4. `arc_mara_annex` | `mara_deep` | Serenity Annex has visiting hours. She's fine. She's fine in
   a way that has a version number. One last long-odds extraction hook allowed (gamble; failure
   is final — no further Mara events; do NOT kill her — absence, not corpse).
5. `arc_vint_soft_intel` | `vint_owes_you` | His first repayment tip is accurate, early, and free.
   The second is what you wanted to hear and wrong by one digit that matters. He knows it as he
   sends it. "i warned you about me. that was the last good tip. invoice enclosed" — the invoice
   is him going dark for your protection.
6. `arc_vint_inherited_book` | `vint_taken` | His clients arrive with open questions and standing
   payment. Take the book (become a Vint; Heat and Wealth up, Meaning down) or burn it (his
   accounts close unpaid; somewhere a sweep list gets shorter by nobody).
7. `arc_vint_exact_change` | `vint_counterparty` | He resurfaces once, sells you something vital at
   precisely market rate, counts the chits twice in front of you, and leaves the tip you once
   would have gotten free as a "sample" — proving he still has it, and that you can't afford him.
8. `arc_kael_owned_discount` | `kael_owned` | The discounts arrive unasked, itemized as "goodwill."
   Using them works and feels like spending teeth. Final line: he asks you, flat, what your price
   would have been — and logs the answer.
9. `arc_kael_new_owner` | `kael_sold` | The consolidator calls every debt Kael held on you within
   one week, bundled, at default rates. Kael's last act was accurate bookkeeping: your file
   includes a note in his hand — "pays late, pays whole. do not sell to the Steward." He priced
   you fairly. That's the eulogy.
10. `arc_kael_marker_holds` | `kael_spared` (+ `kael_marker` if unspent) | The audit closes. Kael
    quotes you a price that's wrong — low — for the first time ever, catches it himself, corrects
    it, and pauses one beat too long. That beat is the whole event. If `kael_marker` still unspent:
    he reminds you it doesn't expire, and that carrying it costs him nothing and you everything.
11. `arc_echo_recall_notice` | `clock_false_ledger_expired` | The counterfeit surfaces: a polite
    "ledger reconciliation" names the discrepancy but not the author — the Steward would rather
    hold the debt than collect it. Echo works out the shape of what you did and says only: "you
    gambled us. it paid. don't ever tell me the odds you took." Sets nothing; costs sleep.
12. `arc_echo_the_courier` | `clock_custody_release_expired` (+ `echo_brother_known`) | Optional
    prequel texture, fires before the fork when available: the custody graduate from betrayal
    event 3 reappears — as the Steward's courier trainee. The kindness pipeline has a career
    track. Foreshadows the rollback offer's courier; sets nothing.

## Hard mechanical rules (unchanged from betrayal pack — verified against engine)

- Copy the JSON shape of the Fable events in `npc_arcs_pack.json`. Same field names, same grammar.
- Every event: `max_fires: 1`, ≥3 choices (engine assert), `prob` on every choice, symbol ops only.
- Preconditions: `"op"`/`"value"` — NEVER `"min"`/`"max"` (engine silently passes the gate).
- `clocks_start` inside success/failure branches: `{"name": days}`, positive int. Expiry mints
  `clock_<name>_expired`.
- Harm severity ~12–14 on bad branches, cap 25/stat. Wealth is raw credits (~50k bankroll).
- Relationship keys, exact: `Mara (Sister)`, `Vint (Informant)`, `Kael (Broker)`, `Echo (Resistance)`.
- Do not modify `engine/*.py` or `ui/*.py` (CLAUDE.md Checkpoint 3).
- Voice: docs/VOICE_BIBLE.md is law. Vint types lowercase, he/him, may swear. Kael never swears —
  he prices. Echo is terse. The Steward is warm oil and NEVER profane. Mara's love is logistics.
- Profanity budget: the 5 Fable events already contain 2 strong uses (Vint fork, Mara fork). Keep
  the 12 Sonnet events to ≤1 strong use total across all twelve.

## New wiring introduced by this pack (complete list — add nothing else)

- Flags: `mara_ransomed`, `steward_leash`, `mara_freed`, `mara_deep`, `mara_graduated`,
  `vint_owes_you`, `vint_taken`, `vint_counterparty`, `kael_soft_spot_known`,
  `kael_docket_memorized`, `kael_owned`, `kael_sold`, `kael_spared`, `kael_marker`,
  `echo_refused_brother`, `cell_burned`, `brother_restored`, `offer_buried`.
- Clock: `false_ledger` (6d, started by Echo fork counterfeit-success).
- Consumed pre-existing hooks: `clock_mara_dark_expired` (Mara fork), `clock_custody_release_expired`
  (Sonnet event 12), `echo_brother_known`, `kael_impressed`, `vint_known`/`vint_favor_repaid`,
  `echo_trusted`, `undercity_smuggling_rep`.
- Chekhov status after Sonnet pass: every flag above is consumed except `kael_docket_memorized`
  (reserved: plan item 5 legacy hook — a run-2 event where you still know the docket number) and
  `offer_buried` (consumed by a betrayal-style delayed reveal — Sonnet may add a 13th event
  `arc_echo_learns_the_offer`, day ≥16, if budget allows; otherwise it feeds ending epilogues).
- Ending epilogue suggestions (plan item 6, do NOT edit endings.json in this pass): react to
  `mara_graduated`, `vint_taken`, `kael_owned`, `echo_refused_brother`, `brother_restored`.

## Verification gate (after every batch; all must pass)

```
python -m unittest discover -s tests
python pipeline/lint_content.py
python tests/sim_bot.py all --assert
```

Recommended Sonnet batching: Mara 1–4, Vint+Kael 5–10, Echo 11–12 (+optional 13). Lint between
batches; full gate at the end.
