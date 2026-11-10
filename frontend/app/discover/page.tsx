import {Suspense} from 'react';import {Discover} from '@/components/movie/discover';import {Loading} from '@/components/ui/states';
export default function Page(){return <Suspense fallback={<Loading/>}><Discover/></Suspense>;}
