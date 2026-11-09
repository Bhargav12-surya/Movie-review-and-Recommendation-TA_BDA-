# Audience score methodology

Only approved calibrated three-class probabilities from eligible latest movie-linked review revisions contribute. Individual index=100*(p_positive+0.5*p_neutral). One positive-weight review per reviewer and exact text hash per movie contributes; weights are documented moderation quality, never model confidence. Effective support=(sum weights)^2/sum squared weights. Minimum review,distinct-reviewer and effective support gates precede shrinkage; thresholds and prior are deliberately null in the template until reviewed. No evidence yields a null score and exactly 'Not enough audience reviews yet.'.

Review bootstrap intervals describe sampling sensitivity,not model accuracy or selection bias. Aspect/theme/genre reception needs independent target-specific probabilities; overall sentiment,metadata keywords and personalized match cannot substitute. New absent/deleted target analysis invalidates older revisions. Source-only Scala ReviewAnalytics implements the same aggregate formula on already eligible one-row-per-reviewer inputs; actual parity and stream integration remain pending. See documentation/phases4-8/RUNBOOK.md.

