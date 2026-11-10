"use client";
import Link from "next/link";import {useState} from "react";import {posterURL} from "@/lib/api";import type {Movie} from "@/lib/types";
export function Poster({movie,large=false}:{movie:Movie;large?:boolean}){
 const [failed,setFailed]=useState(false);const url=posterURL(movie.poster_url);
 return <div className={`poster ${large?"large":""}`}>{url&&!failed?<img src={url} alt={`Poster for ${movie.title}`} loading="lazy" onError={()=>setFailed(true)}/>:<div className="poster-empty"><span>{movie.title.split(" ").slice(0,2).map(word=>word[0]).join("")}</span><small>Poster unavailable</small></div>}</div>;
}
export function MovieCard({movie}:{movie:Movie}){return <article className="movie-card"><Link href={`/movies/${movie.id}`}><Poster movie={movie}/><div className="card-line"><h3>{movie.title}</h3><span>{movie.release_date?.slice(0,4)??"—"}</span></div><p>{movie.genres.slice(0,2).join(" / ")||"Genres unavailable"}</p></Link></article>;}
export function MovieGrid({movies}:{movies:Movie[]}){return <div className="movie-grid">{movies.map(movie=><MovieCard key={movie.id} movie={movie}/>)}</div>;}

