"use client";
import {BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid} from "recharts";
import type {Score} from "@/lib/types";

export function AudienceScore({score}: {score?: Score}) {
  const available = score?.score !== null && score?.score !== undefined;
  return (
    <div className="audience-score">
      <div className={`score-number ${available ? "" : "muted"}`}>
        {available ? Math.round(score!.score!) : "—"}
        <span>/100</span>
      </div>
      <div>
        <span className="eyebrow" style={{marginBottom: 4}}>
          Audience sentiment
        </span>
        <p>
          {available
            ? `${score!.review_count} eligible review${score!.review_count === 1 ? "" : "s"}`
            : score?.message ?? "Not enough audience reviews yet."}
        </p>
        {available && score?.uncertainty && (
          <small>
            Interval: {score.uncertainty.lower.toFixed(1)} – {score.uncertainty.upper.toFixed(1)}
          </small>
        )}
      </div>
    </div>
  );
}

export function ScoreProfile({scores}: {scores: Record<string, Score>}) {
  const distribution = scores.overall?.predicted_class_distribution;
  const aspects = Object.entries(scores).filter(([key]) => key.startsWith("aspect:"));

  if (!distribution && !aspects.length) {
    return null;
  }

  return (
    <section className="panel">
      <h2>Aspect breakdown</h2>

      {distribution && (
        <div className="chart" aria-label="Sentiment distribution">
          <ResponsiveContainer width="100%" height={170}>
            <BarChart data={Object.entries(distribution).map(([name, count]) => ({name, count}))}>
              <CartesianGrid stroke="#2a3035" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" stroke="#9aa5ab" fontSize={12} tickLine={false} />
              <YAxis allowDecimals={false} stroke="#9aa5ab" fontSize={12} tickLine={false} />
              <Tooltip
                contentStyle={{
                  background: "#15191d",
                  border: "1px solid #2a3035",
                  borderRadius: 8,
                  color: "#f2f4f3",
                  fontSize: 12,
                }}
              />
              <Bar dataKey="count" fill="#c5f277" radius={[5, 5, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {aspects.length > 0 && (
        <div className="aspect-grid" style={{gridTemplateColumns: "1fr 1fr", gap: "16px 14px"}}>
          {aspects.map(([key, score]) => {
            const val = score.score;
            const low = val !== null && val < 45;
            return (
              <div className="aspect" key={key}>
                <div>
                  <span>{key.slice(7).replaceAll("_", " ")}</span>
                  <strong className={low ? "low" : ""}>{val === null ? "—" : Math.round(val)}</strong>
                </div>
                <div className="bar">
                  <i
                    style={{
                      width: `${val ?? 0}%`,
                      background: low ? "var(--amber)" : "var(--lime)",
                    }}
                  />
                </div>
                <small>
                  {score.review_count} review{score.review_count === 1 ? "" : "s"}
                </small>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
