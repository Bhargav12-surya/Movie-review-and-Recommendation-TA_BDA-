"use client";
import Link from "next/link";import {useRouter,usePathname} from "next/navigation";import {useAuth} from "@/lib/auth";import {api} from "@/lib/api";
export function Shell({children}:{children:React.ReactNode}){
 const auth=useAuth();const router=useRouter();const path=usePathname();
 async function logout(){try{await api("/auth/logout",{method:"POST"},auth.token);}finally{auth.clear();router.push("/");}}
 return <><a className="skip" href="#content">Skip to content</a><header className="site-header"><Link className="brand" href="/" aria-label="Framewise home"><span className="brand-mark">f.</span>framewise<span className="brand-dot">/</span></Link><nav aria-label="Main navigation">{[["/discover","Discover"],["/recommendations","For you"],["/watchlist","Watchlist"],["/assistant","Film companion"]].map(([href,label])=><Link key={href} href={href} aria-current={path===href?"page":undefined}>{label}</Link>)}</nav><div className="header-account">{auth.user?<><Link href="/profile">{auth.user.display_name}</Link><button onClick={logout} className="text-button">Sign out</button></>:<Link className="button small secondary" href="/auth">Sign in</Link>}</div></header><main id="content">{children}</main><footer><Link className="brand" href="/">framewise/</Link><p>Find a film. Form an opinion. Keep the evidence.</p><Link href="/about">How our intelligence works</Link><span>Local research edition · BDA + Text Analytics</span></footer></>;
}

