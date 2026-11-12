import Link from "next/link";
import {InfoIcon, SparkIcon} from "./icons";

export function Loading({label = "Finding your films…"}: {label?: string}) {
  return (
    <div className="empty" role="status">
      <div className="loader" />
      <p>{label}</p>
    </div>
  );
}

export function Empty({
  title,
  description,
  href,
  label = "Explore films",
}: {
  title: string;
  description: string;
  href?: string;
  label?: string;
}) {
  return (
    <section className="state empty">
      <div className="empty-icon">
        <SparkIcon size={24} />
      </div>
      <span className="eyebrow">A little space for discovery</span>
      <h2>{title}</h2>
      <p>{description}</p>
      {href && (
        <Link className="primary" href={href}>
          {label}
        </Link>
      )}
    </section>
  );
}

export function ErrorState({message, retry}: {message: string; retry?: () => void}) {
  return (
    <section className="state error" role="alert">
      <div className="empty-icon" style={{color: "var(--red)"}}>
        <InfoIcon size={24} />
      </div>
      <h2>We couldn’t load this frame.</h2>
      <p>{message}</p>
      {retry && (
        <button type="button" className="secondary" onClick={retry}>
          Try again
        </button>
      )}
    </section>
  );
}
