import type {EvidenceSummary} from "@/lib/types";
import {ChatIcon} from "@/components/ui/icons";

export function ReviewSummary({summary}: {summary: EvidenceSummary}) {
  return (
    <section className="summary-panel summary" id="read-the-room">
      <div className="summary-heading">
        <div className="cine-avatar">
          <ChatIcon size={18} />
        </div>
        <div style={{flex: 1}}>
          <span className="eyebrow" style={{marginBottom: 4}}>
            READ THE ROOM
          </span>
          <h2>The review consensus</h2>
        </div>
        <span className="tag lime">Grounded</span>
      </div>

      {summary.publication_approved && summary.generated_candidate && (
        <p className="summary-text">{summary.generated_candidate}</p>
      )}

      {summary.summary?.length ? (
        <div className="evidence-grid">
          {summary.summary.slice(0, 6).map((item, index) => (
            <blockquote key={item.review_id + index}>
              <p>“{item.quote}”</p>
              <cite>
                Review {item.review_id.slice(0, 8)} · r{item.revision}
              </cite>
            </blockquote>
          ))}
        </div>
      ) : (
        <p className="summary-text muted">
          Not enough audience reviews yet.
        </p>
      )}
    </section>
  );
}
