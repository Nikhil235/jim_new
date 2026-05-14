# Phase 7: Team Culture & Operations
> *The "Simons Way" — Build a Scientific Commune, Not a Trading Floor*

**Duration**: Ongoing | **Status**: 🔴 Not Started

**Framework**: All documentation in place (`docs/PHILOSOPHY.md`)  
**Implementation**: Awaits successful completion of Phases 3-6

---

## 7.1 The Five Laws of the Commune

These are NON-NEGOTIABLE. Violating them undermines the entire system.

### Law 1: No Silos
Everyone sees ALL the code. Period. If a data engineer spots a bug in the model code, they fix it and get recognized. No "that's not my module."

### Law 2: No "Why" Rule
If data shows a 60% probability gold drops when the Yen rises on Tuesday mornings — **take the trade**. Don't waste time inventing a narrative. The pattern IS the reason.

### Law 3: Shared Destiny
Compensation tied to TOTAL system performance, not individual contributions. This kills the incentive to hide discoveries or sabotage others.

### Law 4: Weekly Research Seminar
Every week, one team member presents findings — just like a university department. Others challenge, question, improve. This is where breakthroughs happen.

### Law 5: Never Overwrite the Model
Once deployed and validated, the model trades. No one says "but I think gold will go up because of the news." The model IS the trader.

---

## 7.2 Team Structure

| Role | Count | Responsibility |
|------|-------|---------------|
| **Quant Researcher** | 2–3 | New signals, features, models |
| **Data Engineer** | 1–2 | Pipeline, data quality, feeds |
| **Infrastructure/MLOps** | 1 | GPU cluster, DBs, deployment |
| **Risk Manager** | 1 | Positions, circuit breakers, VaR |
| **Execution Engineer** | 1 | Low-latency routing, slippage |

### Hiring Principles (The Simons Way)
- ✅ Hire: Mathematicians, Physicists, CS PhDs, Astronomers
- ❌ Avoid: Traditional finance people, MBA-only candidates
- 🎯 Key trait: Intellectual curiosity > domain experience
- 🎯 Key test: Can they solve novel problems, not just apply known solutions?

---

## 7.3 Daily Operations

### Morning Routine (Before Market Open)
1. Review overnight model performance
2. Check all data feeds are live and clean
3. Verify regime detection (HMM state)
4. Review circuit breaker status
5. Confirm VaR budget for the day

### During Trading Hours
- System runs autonomously (no manual intervention)
- Monitor dashboards for anomalies
- Log any unusual market events for post-analysis

### End of Day
1. Generate daily P&L report
2. Review execution quality (slippage analysis)
3. Check model drift metrics
4. Update team Slack channel with summary

### Weekly
- Research seminar (1 hour)
- Code review session (1 hour)
- Model performance review (30 min)
- Infrastructure health check (30 min)

### Monthly
- Full strategy performance review
- Backtest refresh with latest data
- Risk parameter recalibration
- Team retrospective

---

## 7.4 Model Governance

### Change Management
```
Researcher proposes model change
        │
        ▼
Peer code review (min 2 approvals)
        │
        ▼
Backtest on full historical data
        │
        ▼
Walk-forward validation passes?
        │           │
       YES          NO → Back to research
        │
        ▼
Paper trade for 1 week minimum
        │
        ▼
Live metrics within 20% of backtest?
        │           │
       YES          NO → Investigate, iterate
        │
        ▼
Deploy to production (staged rollout)
```

### Model Retirement
- If any model underperforms for 30 consecutive days → review
- If Sharpe drops below 1.0 for 60 days → retire and replace
- Retired models stay in registry for forensic analysis

---

## 7.5 Knowledge Base

Maintain a living knowledge base:
- **Signal Zoo**: Catalog of all discovered signals (active and retired)
- **Bug Post-Mortems**: Every system failure gets a written analysis
- **Research Log**: Ideas tested, results, and conclusions
- **Market Regime Diary**: Manual notes on unusual market events

---

## 7.6 Deliverables Checklist

- [ ] Team hired and onboarded
- [ ] "Five Laws" documented and signed by all members
- [ ] Weekly seminar schedule established
- [ ] Code review process in place (GitHub/GitLab)
- [ ] Daily operations runbook written
- [ ] Model governance process documented
- [ ] Signal Zoo initialized
- [ ] Slack/Teams channels configured
- [ ] Knowledge base (Notion/Confluence) set up

---

*Back to [ROADMAP](../ROADMAP.md)*
