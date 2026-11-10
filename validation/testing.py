"""Run opted-in test modules with structured results and no captured private text."""
import argparse
from contextlib import redirect_stdout,redirect_stderr
import io
import json
import os
import re
import sys
import time
import unittest

PREFIXES=('tests.foundation.','tests.data_quality.','tests.ml.','tests.aspects.','tests.phases4_8.','tests.integration.','backend.tests.','discovery.tests.')


class Results(unittest.TestResult):
    def __init__(self):super().__init__();self.cases=[];self.current={};self.started={}
    def startTest(self,test):
        super().startTest(test);self.started[test]=time.perf_counter()
        identifier=test.id();self.current[test]={'id':identifier if re.fullmatch(r'[\w.:-]{1,300}',identifier) else 'redacted_test_id','status':'passed'}
    def stopTest(self,test):
        self.current[test]['duration_ms']=1000*(time.perf_counter()-self.started.pop(test));self.cases.append(self.current.pop(test));super().stopTest(test)
    def record(self,test,status,**details):
        if test in self.current:self.current[test].update(status=status,**details)
        else:
            identifier=test.id();self.cases.append({'id':identifier if re.fullmatch(r'[\w.(): -]{1,300}',identifier) else 'redacted_suite_id','status':status,'duration_ms':0,**details})
    def addError(self,test,error):self.record(test,'error',error_type=error[0].__name__);self.errors.append((test,'redacted'))
    def addFailure(self,test,error):self.record(test,'failed',error_type=error[0].__name__);self.failures.append((test,'redacted'))
    def addSkip(self,test,reason):self.record(test,'skipped');self.skipped.append((test,'reason_redacted'))
    def addExpectedFailure(self,test,error):self.current[test]['status']='expected_failure';self.expectedFailures.append((test,'redacted'))
    def addUnexpectedSuccess(self,test):self.current[test]['status']='unexpected_success';self.unexpectedSuccesses.append(test)
    def addSubTest(self,test,subtest,error):
        if error is not None:self.current[test].update(status='failed',error_type=error[0].__name__);self.failures.append((test,'redacted_subtest'))


def run(modules):
    if not modules or any(not name.startswith(PREFIXES) or not re.fullmatch(r'[A-Za-z0-9_.]+',name) for name in modules):raise ValueError('Choose explicit project test modules only.')
    result=Results();started=time.perf_counter()
    with open(os.devnull,'w',encoding='utf-8') as sink,redirect_stdout(sink),redirect_stderr(sink):
        suite=unittest.defaultTestLoader.loadTestsFromNames(modules);suite.run(result)
    statuses=[item['status'] for item in result.cases]
    status='failed' if any(value in {'failed','error','unexpected_success'} for value in statuses) else 'incomplete' if not statuses or any(value!='passed' for value in statuses) else 'passed'
    return {'kind':'unit_or_postgres_tests','status':status,'tests_run':result.testsRun,'duration_seconds':time.perf_counter()-started,
        'counts':{name:statuses.count(name) for name in set(statuses)},'cases':result.cases,
        'privacy':'Only static case identifiers,status,duration and error types; no tracebacks,exception messages,request bodies or credentials.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');parser.add_argument('--modules',nargs='+',required=True);args=parser.parse_args()
    if not args.execute:print(json.dumps({'status':'planned','executed':False}));return 0
    try:report=run(args.modules)
    except Exception as error:report={'status':'failed','error_type':type(error).__name__}
    print(json.dumps(report));return 0 if report['status']=='passed' else 2

if __name__=='__main__':raise SystemExit(main())
