"""Human-annotated grounded-answer/summary/query and permitted speech metrics."""
import re
import unicodedata
from .io import approved,digest,read,rows


def word_errors(reference,hypothesis):
    """NFC+casefold whitespace token WER; punctuation remains significant."""
    if not isinstance(reference,str) or not isinstance(hypothesis,str) or len(reference)>4096 or len(hypothesis)>4096:raise ValueError('Use bounded permitted short voice transcripts.')
    truth=unicodedata.normalize('NFC',reference).casefold().split();guess=unicodedata.normalize('NFC',hypothesis).casefold().split()
    if not truth:raise ValueError('Empty reference transcripts need a separate silence/insertions study.')
    previous=list(range(len(guess)+1))
    for i,word in enumerate(truth,1):
        current=[i]
        for j,other in enumerate(guess,1):current.append(min(previous[j]+1,current[j-1]+1,previous[j-1]+(word!=other)))
        previous=current
    return {'edit_distance':previous[-1],'reference_words':len(truth),'hypothesis_words':len(guess)}


def evaluate(config_path):
    config=read(config_path);approved(config)
    source=config['cases_path']
    if config.get('cases_sha256')!=digest(source):raise ValueError('Frozen human evaluation cases changed.')
    cases=list(rows(source,maximum_rows=10000,maximum_bytes=32*1024**2));seen=set()
    counts={'cases':len(cases),'claims':0,'supported':0,'contradicted':0,'unsupported':0,'query_cases':0,'correct_intents':0,
        'constraint_cases':0,'correct_constraints':0,'voice_cases':0,'word_errors':0,'reference_words':0,'abstentions':0}
    for case in cases:
        identifier=case['case_id']
        if identifier in seen:raise ValueError('Duplicate evaluation case.')
        seen.add(identifier)
        if (case.get('split')!='test' or case.get('is_synthetic') is not False or case.get('human_review_complete') is not True or
            not case.get('reviewed_by') or not case.get('permission_reference') or not case.get('model_version')):
            raise ValueError('Legitimate held-out cases and complete human review are required.')
        actual_path=case['actual_output_path']
        if case.get('actual_output_sha256')!=digest(actual_path):raise ValueError('An actual frozen model/service output is required.')
        actual=read(actual_path)
        if case['task']=='voice':
            if actual.get('model_revision')!=case['model_version'] or not isinstance(actual.get('text'),str):raise ValueError('Actual speech output/revision required.')
            values=word_errors(case['reference_text'],actual['text']);counts['voice_cases']+=1
            counts['word_errors']+=values['edit_distance'];counts['reference_words']+=values['reference_words'];continue
        if case['task'] not in {'query','summary'} or not case.get('evidence_snapshot_sha256'):raise ValueError('Declare the grounded query/summary evidence snapshot.')
        if actual.get('evidence_snapshot_sha256')!=case['evidence_snapshot_sha256']:raise ValueError('Output is not bound to the judged evidence snapshot.')
        if actual.get('model_version')!=case['model_version']:raise ValueError('Output model/parser version differs from the review.')
        claims=case.get('claims',[])
        if type(case.get('abstained')) is not bool:raise ValueError('Annotate abstention explicitly.')
        counts['abstentions']+=case['abstained']
        claim_ids=set()
        for claim in claims:
            verdict=claim.get('support')
            if verdict not in {'supported','contradicted','unsupported'} or not claim.get('claim_id'):raise ValueError('Complete independent sentence-level support judgments required.')
            if verdict=='supported' and not claim.get('evidence_ids'):raise ValueError('Supported claims require actual evidence references.')
            if claim['claim_id'] in claim_ids:raise ValueError('Duplicate claim judgment.')
            claim_ids.add(claim['claim_id'])
            if set(claim.get('evidence_ids',[]))-set(actual.get('evidence_ids',[])):raise ValueError('Claim cites evidence outside the frozen actual output.')
            counts['claims']+=1;counts[verdict]+=1
        if case['task']=='query':
            counts['query_cases']+=1;counts['correct_intents']+=actual.get('intent')==case['expected_intent']
            if type(case.get('constraints_correct')) is not bool:raise ValueError('Human review must assess every query constraint.')
            counts['constraint_cases']+=1;counts['correct_constraints']+=case['constraints_correct']
    def fraction(numerator,denominator):return numerator/denominator if denominator else None
    return {'kind':'human_grounding_and_speech','split':'test','status':'measured' if cases else 'incomplete','counts':counts,
        'metrics':{'supported_claim_fraction':fraction(counts['supported'],counts['claims']),
            'unsupported_claim_fraction':fraction(counts['unsupported'],counts['claims']),'contradicted_claim_fraction':fraction(counts['contradicted'],counts['claims']),
            'intent_accuracy':fraction(counts['correct_intents'],counts['query_cases']),'constraint_accuracy':fraction(counts['correct_constraints'],counts['constraint_cases']),
            'word_error_rate':fraction(counts['word_errors'],counts['reference_words'])},
        'input_sha256':{'config':digest(config_path),'cases':config['cases_sha256']},
        'limitations':'Measured is not a pass. Human coverage,inter-annotator agreement,sampling and acceptance thresholds need separate review. No transcript,private query or claim text is written to this report. WER can exceed1.'}
