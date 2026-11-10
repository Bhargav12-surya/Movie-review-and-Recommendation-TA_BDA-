"""Authored only: parity,grounding and test-result failure-path regressions."""
import unittest
import io
from urllib.error import HTTPError
from unittest.mock import patch
from validation.parity import score_parity,state_parity
from validation.grounding import word_errors
from validation.reporting import comparison
from validation.testing import Results


class ValidationTests(unittest.TestCase):
    def row(self):
        return {'movie_id':'isolated-fixture','score_type':'overall','target_key':None,'model_version':'fixture-model','method_version':'fixture-method',
            'policy_sha256':'fixture-policy-hash','eligible_evidence_sha256':'fixture-evidence-hash','review_count':2,'distinct_reviewers':2,
            'effective_review_count':2.0,'score':75.0,'raw_score':75.0,'message':None}
    def test_score_parity_detects_different_frozen_evidence_despite_equal_numbers(self):
        left=self.row();right={**left,'eligible_evidence_sha256':'different-fixture-hash'}
        self.assertEqual(score_parity([left],[right],[{'movie_id':'isolated-fixture'}])['status'],'failed')
    def test_minimum_evidence_null_never_compares_equal_to_numeric_prior(self):
        left={**self.row(),'score':None,'raw_score':None,'message':'Not enough audience reviews yet.'}
        self.assertEqual(score_parity([left],[self.row()],[{'movie_id':'isolated-fixture'}])['status'],'failed')
    def test_score_scope_cannot_hide_omitted_movies(self):
        row=self.row()
        self.assertEqual(score_parity([row],[row],[{'movie_id':'isolated-fixture'},{'movie_id':'missing-fixture'}])['status'],'failed')
    def test_late_tombstone_cannot_resurrect_an_older_upsert(self):
        current={'review_id':'fixture-review','review_revision':2,'movie_id':'fixture-movie','operation':'delete','model_version':None,
            'consent_eligible':False,'moderation_eligible':True,'is_synthetic':True,'semantic_hash':'fixture-hash-v2'}
        old={**current,'review_revision':1,'operation':'upsert','semantic_hash':'fixture-hash-v1'}
        self.assertEqual(state_parity([current],[old])['status'],'failed')
        self.assertEqual(state_parity([current],[old],['fixture-review'])['status'],'incomplete')
    def test_word_error_rate_uses_reference_denominator_and_keeps_insertions(self):
        value=word_errors('a b','a x b c')
        self.assertEqual(value['edit_distance'],2);self.assertEqual(value['reference_words'],2)
        self.assertEqual(word_errors('एक फिल्म','एक फिल्म')['edit_distance'],0)
    def test_comparison_rejects_binary_vs_domain_or_different_splits(self):
        with self.assertRaises(ValueError):comparison({'studies':[{'id':'binary','task':'binary','protocol_id':'A'},{'id':'domain','task':'domain','protocol_id':'B'}]},['binary','domain'],'f1')
    def test_class_setup_error_is_reported_even_without_start_test(self):
        class ClassFailure:
            def id(self):return 'setUpClass (isolated.fixture)'
        result=Results();result.addError(ClassFailure(),(RuntimeError,RuntimeError('private message must not enter report'),None))
        self.assertEqual(result.cases[0]['status'],'error');self.assertNotIn('private',str(result.cases))
    def test_empty_or_skipped_scientific_scope_is_not_parity_pass(self):
        self.assertEqual(state_parity([],[])['status'],'incomplete')
    def test_deliberately_expected_http_unavailability_is_not_misreported(self):
        from validation.benchmark import request
        error=HTTPError('http://127.0.0.1:8000/api/v1/ready',503,'isolated fixture',{},io.BytesIO(b'fixture only'))
        with patch('validation.benchmark.build_opener') as opener:
            opener.return_value.open.side_effect=error
            result=request({'id':'isolated-readiness','url':'http://127.0.0.1:8000/api/v1/ready','expected_statuses':[503]},1)
        self.assertEqual(result['status'],'passed');self.assertEqual(result['http_status'],503)
    def test_oversized_http_body_cannot_leave_a_successful_header_verdict(self):
        from validation.benchmark import request
        response=io.BytesIO(b'x'*(2*1024**2+1));response.status=200
        with patch('validation.benchmark.build_opener') as opener:
            opener.return_value.open.return_value=response
            result=request({'id':'isolated-response-limit','url':'http://127.0.0.1:8000/api/v1/health'},1)
        self.assertEqual(result['status'],'failed')

if __name__=='__main__':unittest.main()
