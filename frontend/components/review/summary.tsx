import type {EvidenceSummary} from "@/lib/types";
export function ReviewSummary({summary}:{summary:EvidenceSummary}){
 return <section className="panel summary"><div className="section-heading"><div><span className="eyebrow">Audience edit</span><h2>What the reviews are saying</h2></div><span className="subtle-tag">Grounded in reviews</span></div>{summary.summary?.length?<><p className="muted">Selected audience evidence · each excerpt keeps its source.</p><div className="evidence-grid">{summary.summary.slice(0,6).map((item,index)=><blockquote key={item.review_id+index}><p>“{item.quote}”</p><cite>Review {item.review_id.slice(0,8)} · revision {item.revision}</cite></blockquote>)}</div></>:<p className="muted">Not enough audience reviews yet. A grounded summary will appear here when eligible evidence is available.</p>}{summary.publication_approved&&summary.generated_candidate&&<p>{summary.generated_candidate}</p>}</section>;
}

