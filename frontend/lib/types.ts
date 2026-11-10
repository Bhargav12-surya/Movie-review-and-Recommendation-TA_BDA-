export type Movie = {id:string;title:string;overview:string;release_date?:string;runtime_minutes?:number;original_language?:string;genres:string[];themes?:string[];poster_url?:string|null;metadata_source?:string};
export type Score={score:number|null;review_count:number;effective_review_count?:number;message?:string|null;status?:string;model_version?:string;method_version?:string;predicted_class_distribution?:Record<string,number>;uncertainty?:{lower:number;upper:number}};
export type EvidenceSummary={status:string;summary?:Array<{quote:string;review_id:string;revision:number}>|null;selected_review_count?:number;publication_approved?:boolean;generated_candidate?:string};
export type MovieDetail=Movie & {scores:Record<string,Score>;summary:EvidenceSummary;audience_star_rating?:{mean:number|null;count:number}};
export type Review={id:string;movie_id:string;revision:number;text:string;language_code:string;created_at:string;analysis_status:string;predictions:Record<string,{status:string;label?:string;probabilities?:Record<string,number>;aspects?:Array<{aspect:string;label:string;start:number;end:number;text:string}>;model_version:string}>};
export type Catalogue={movies:Movie[];total:number;page:number;page_size:number};
export type User={id:string;display_name:string;email:string;is_admin:boolean};
export type Recommendation={movie_id:string;movie:Movie;match_score:number;contributions:Record<string,number>;evidence:Record<string,unknown>};
export type Recommendations={status:string;message?:string;recommendations:Recommendation[];cold_start?:boolean;eligible_candidate_count?:number};
export type ChatReply={status:string;text:string;movies?:MovieDetail[];evidence?:Array<{review_id:string;quote:string;label?:string}>};

