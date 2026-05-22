from fpdf import FPDF
import textwrap

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'How the Ensemble Model Calculates Its Signal', border=False, align='C')
        self.ln(20)

    def chapter_title(self, title):
        self.set_font('helvetica', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, border=False, ln=True, fill=True)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('helvetica', '', 11)
        self.multi_cell(0, 6, body)
        self.ln()

    def bullet_points(self, points):
        self.set_font('helvetica', '', 11)
        for point in points:
            self.cell(5, 6, '-')
            self.multi_cell(0, 6, point)
        self.ln()

pdf = PDF()
pdf.add_page()

text1 = "The Ensemble is not a single model - it's a two-layer decision system (meta-learner). Here is exactly how it works, step by step."
pdf.chapter_body(text1)

pdf.chapter_title("Layer 0 - The 5 Worker Models")
text2 = "These all run independently and each gives a vote + confidence score:\n" \
        "- Wavelet: Filters noise from price data using wave math, detects trend (Best in: Any market)\n" \
        "- HMM: Detects which 'hidden state' (regime) the market is in (Best in: Transitions)\n" \
        "- LSTM: Deep learning; predicts next move from sequences of past prices (Best in: Trending)\n" \
        "- TFT: Forecasts multiple steps ahead simultaneously (Best in: Growth)\n" \
        "- Genetic: Evolves trading rules via natural selection (Best in: Any)\n\n" \
        "Each produces something like: {signal: 'LONG', confidence: 0.82}"
pdf.chapter_body(text2)

pdf.chapter_title("Layer 1 - The Ensemble Combines Them")
text3 = "Mode A: ML Meta-Learner (when trained on 50+ historical trades)\n" \
        "Feature vector includes:\n" \
        "- direction x confidence for each model\n" \
        "- raw confidence for each model\n" \
        "- regime code (GROWTH=+1, NORMAL=0, CRISIS=-1)\n" \
        "- model agreement score\n\n" \
        "Mode B: Dynamic Regime Weighting (the current live mode)\n" \
        "When there's not enough training data, it uses a weighted vote:\n" \
        "1. Assign regime-based weights (e.g. GROWTH: wavelet:25%, ensemble:50%...)\n" \
        "2. Performance adaptation (after 10+ trades) - Models that WON recently get heavier votes.\n" \
        "3. Agreement bonus/penalty - If 4 or more models agree, they get a 15% boost.\n" \
        "4. Weighted vote - score = weight x confidence\n" \
        "5. Disagreement penalty on final confidence\n" \
        "6. Output - If best_score < 0.25 -> HOLD, else -> best direction."
pdf.chapter_body(text3)

pdf.chapter_title("Layer 2 - Dynamic Weight Adjustments")
text4 = "After every closed trade, the DynamicWeightAdjuster updates each model's weight for next time:\n\n" \
        "new_weight = normalize(regime_base x performance_multiplier x agreement_factor)\n\n" \
        "The performance multiplier is based on rolling Sharpe ratio (last 50 trades):\n" \
        "- A model that's been winning lately -> Sharpe goes up -> gets more weight\n" \
        "- A model that's been losing -> Sharpe goes down -> weight shrinks\n\n" \
        "This is exactly how Renaissance Technologies operates - the models that have been right recently are trusted more, and the weights constantly adapt."
pdf.chapter_body(text4)

pdf.chapter_title("In Plain English")
text5 = "Every 60 seconds, Wavelet + HMM + LSTM + TFT + Genetic all look at the gold price from their own angle and vote LONG/SHORT/HOLD. The Ensemble collects all the votes, weights them by who has been winning lately and what the current market regime is, applies a penalty if models disagree, and produces one final signal with a confidence score. If confidence > 60%, the paper trading engine executes the trade."
pdf.chapter_body(text5)

pdf.output("d:/AI/Jim/docs/Ensemble_Explanation.pdf")
print("PDF created successfully at docs/Ensemble_Explanation.pdf")
