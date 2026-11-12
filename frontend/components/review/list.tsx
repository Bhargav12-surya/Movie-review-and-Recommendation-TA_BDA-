import type {Review} from "@/lib/types";

export function ReviewList({reviews}: {reviews: Review[]}) {
  return (
    <section className="section" style={{paddingTop: 6}}>
      <div className="section-heading" style={{marginTop: 8}}>
        <h2>Audience reviews</h2>
        <span className="result-count">{reviews.length}</span>
      </div>

      {reviews.length ? (
        reviews.map((review) => {
          const sentimentLabel = review.predictions.sentiment?.label;
          const statusText = (sentimentLabel ?? review.analysis_status).replaceAll("_", " ");
          const tagClass = sentimentLabel === "positive" ? "tag lime" : "tag";

          return (
            <article className="review" key={review.id}>
              <div className="review-meta">
                <span>Member</span>
                <time>{new Date(review.created_at).toLocaleDateString()}</time>
                <span className={tagClass}>{statusText}</span>
              </div>
              <p>{review.text}</p>
              {review.predictions.aspects?.aspects?.length ? (
                <div className="tags">
                  {review.predictions.aspects.aspects.map((aspect, index) => (
                    <span className="tag" key={index}>
                      {aspect.aspect.replaceAll("_", " ")} · {aspect.label}
                    </span>
                  ))}
                </div>
              ) : null}
              {review.predictions.themes?.theme_labels?.length ? (
                <div className="tags">
                  {review.predictions.themes.theme_labels.map((theme) => (
                    <span className="tag theme" key={theme}>
                      {theme.replaceAll("_", " ")}
                    </span>
                  ))}
                </div>
              ) : null}
            </article>
          );
        })
      ) : (
        <p className="empty-inline">No reviews yet. Be the first to share one.</p>
      )}
    </section>
  );
}
