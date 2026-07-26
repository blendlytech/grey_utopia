---
name: balance-tester
description: Run Monte Carlo simulations, analyze ending distributions, and balance stat decay/outcome coefficients for GREY UTOPIA.
---

# Balance Tester Skill

Use this skill when auditing or tuning game balance, outcome probabilities, and statistical decay curves in GREY UTOPIA.

## Workflow

1. **Run Monte Carlo Simulation**:
   ```bash
   python tests/sim_bot.py random
   python tests/sim_bot.py cautious
   python tests/sim_bot.py reckless
   ```

2. **Analyze Key Balance Metrics**:
   - **Average Survival Days**: Target is 15–30 days for average playouts.
   - **Ending Distribution**: Ensure all 6 endings (Overdose, Institutionalization, Detachment, Off-Grid Escape, Buyout, Alienation) are reachable and no single outcome exceeds 60% across strategies.

3. **Tuning Guidance**:
   - If players die too early: Reduce `K_OD` scaling constant in `engine/decay.py` or increase `PHYS_REGEN`.
   - If Mental Decay spikes too rapidly: Adjust EMA smoothing factor `ALPHA_MOOD` (default 0.30) in `engine/decay.py`.
   - If relationships decay too fast: Increase retention strength $S$ in `data/cast.json`.
