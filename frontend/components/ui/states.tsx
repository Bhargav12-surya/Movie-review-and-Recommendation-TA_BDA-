import Link from "next/link";
export function Loading({label="Loading your next frame…"}:{label?:string}){return <div className="state" role="status"><span className="loading-dot"/>{label}</div>;}
export function Empty({title,description,href,label="Explore films"}:{title:string;description:string;href?:string;label?:string}){return <section className="state empty"><span className="eyebrow">A little space for discovery</span><h2>{title}</h2><p>{description}</p>{href&&<Link className="button" href={href}>{label}</Link>}</section>;}
export function ErrorState({message,retry}:{message:string;retry?:()=>void}){return <section className="state error" role="alert"><h2>We couldn’t load this frame.</h2><p>{message}</p>{retry&&<button className="button secondary" onClick={retry}>Try again</button>}</section>;}

