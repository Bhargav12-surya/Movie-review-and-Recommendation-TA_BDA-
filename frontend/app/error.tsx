"use client";import {ErrorState} from "@/components/ui/states";export default function Boundary({reset}:{error:Error;reset:()=>void}){return <ErrorState message="The local service could not complete this request." retry={reset}/>;}

