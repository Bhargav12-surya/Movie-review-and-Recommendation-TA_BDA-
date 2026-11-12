export const API=(process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1").replace(/\/$/,"");
export class ApiError extends Error { constructor(public status:number,public code:string){super(code.replaceAll("_"," "));} }
export async function api<T>(path:string,options:RequestInit={},token?:string|null):Promise<T>{
 const headers=new Headers(options.headers);
 if(options.body && !(options.body instanceof FormData)) headers.set("Content-Type","application/json");
 if(token)headers.set("Authorization",`Bearer ${token}`);
 const response=await fetch(API+path,{...options,headers,cache:"no-store"});
 if(response.status===204)return undefined as T;
 // Reject cancelled or invalid JSON instead of returning an empty object.
 let result;
 try {
   result = await response.json();
 } catch (error) {
   if (options.signal?.aborted ||
       (error instanceof DOMException && error.name === 'AbortError')) {
     throw error;
   }
   throw new ApiError(response.ok ? 502 : response.status, 'invalid_api_response');
 }
 if (options.signal?.aborted) {
   throw new DOMException('Request cancelled', 'AbortError');
 }
 if(!response.ok)throw new ApiError(response.status,result?.error?.code ?? result?.detail ?? "service_unavailable");
 return result as T;
}
export function posterURL(path?:string|null){return path ? API.replace(/\/api\/v1$/,"")+path : undefined;}

