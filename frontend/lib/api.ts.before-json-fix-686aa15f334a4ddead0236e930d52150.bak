export const API=(process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1").replace(/\/$/,"");
export class ApiError extends Error { constructor(public status:number,public code:string){super(code.replaceAll("_"," "));} }
export async function api<T>(path:string,options:RequestInit={},token?:string|null):Promise<T>{
 const headers=new Headers(options.headers);
 if(options.body && !(options.body instanceof FormData)) headers.set("Content-Type","application/json");
 if(token)headers.set("Authorization",`Bearer ${token}`);
 const response=await fetch(API+path,{...options,headers,cache:"no-store"});
 if(response.status===204)return undefined as T;
 const result=await response.json().catch(()=>({}));
 if(!response.ok)throw new ApiError(response.status,result?.error?.code ?? result?.detail ?? "service_unavailable");
 return result as T;
}
export function posterURL(path?:string|null){return path ? API.replace(/\/api\/v1$/,"")+path : undefined;}

