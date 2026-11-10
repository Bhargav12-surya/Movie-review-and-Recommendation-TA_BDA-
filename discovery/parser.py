"""Versioned analytical intent/constraint parsing, not a claimed trained NLU model."""
import re

GENRES={'romance':'Romance','romantic':'Romance','science fiction':'Sci-Fi','sci-fi':'Sci-Fi','science-fiction':'Sci-Fi',
        'drama':'Drama','comedy':'Comedy','thriller':'Thriller','horror':'Horror','action':'Action','animation':'Animation'}
ASPECTS={'soundtrack':'music','music':'music','acting':'acting','story':'story','screenplay':'screenplay','pacing':'pacing',
         'cinematography':'cinematography','visual effects':'visual_effects'}
THEMES={'family':'love_and_family','time travel':'time_and_memory','survival':'survival','identity':'identity','sacrifice':'sacrifice'}

def parse_query(text,context=None):
    if not isinstance(text,str) or not text.strip() or len(text)>2000: raise ValueError('Bounded text query required.')
    context=context or {};normalized=text.casefold().strip()
    included,excluded=[],[]
    for alias,genre in GENRES.items():
        if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',normalized):
            target=excluded if re.search(r'\b(?:not|no|without)\s+'+re.escape(alias)+r'\b',normalized) else included
            target.append(genre)
    maximum=None
    match=re.search(r'\b(?:under|less than|shorter than)\s+(\d+)\s*(hours?|minutes?|mins?)',normalized)
    if match: maximum=int(match[1])*(60 if match[2].startswith('hour') else 1)
    if re.search(r'under\s+(?:two|2)\s+hours',normalized): maximum=120
    aspect=next((value for alias,value in ASPECTS.items() if alias in normalized),None)
    titles=[];intent='recommend'
    if normalized.startswith('compare '):
        intent='compare';titles=re.split(r'\s+and\s+',text[8:].strip(),maxsplit=1)
    else:
        similar=re.search(r'(?:similar to|movies? like)\s+(.+)',text,re.I)
        about=re.search(r'(?:how is|how was|what about)\s+(.+)',text,re.I)
        of=re.search(r'\bof\s+(.+)',text,re.I) if aspect else None
        if similar: intent='similar';titles=[similar[1]]
        elif of: intent='aspect';titles=[of[1]]
        elif about: intent='movie';titles=[about[1]]
    if aspect and not titles and context.get('last_movie_id'): intent='aspect'
    return {'intent':intent,'titles':[title.strip(' ?.!') for title in titles],
        'genres':sorted(set(included)),'excluded_genres':sorted(set(excluded)),
        'themes':sorted({value for alias,value in THEMES.items() if alias in normalized}),
        'maximum_runtime':maximum,'aspect':aspect,
        'needs_pacing_evidence':bool(re.search(r'not\s+(?:too\s+)?slow|not\s+(?:too\s+)?boring',normalized)),
        'needs_emotional_evidence':'emotional' in normalized,
        'shorter_followup':maximum is None and 'shorter' in normalized,'parser_version':'catalogue-constraints-v1'}
