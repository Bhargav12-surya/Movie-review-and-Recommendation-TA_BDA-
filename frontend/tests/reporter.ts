import type {FullResult, Reporter, TestCase, TestResult} from '@playwright/test/reporter';

// Redacted machine output: never serialize errors, stdout, annotations, snippets,
// request bodies, screenshots or traces containing account/review material.
export default class EvidenceReporter implements Reporter {
  private cases:Array<{id:string;status:string;duration_ms:number}>=[];
  private errors=0;
  onError(){this.errors+=1;}
  onTestEnd(test:TestCase,result:TestResult){
    const file=test.location.file.replace(/^.*[\\/]tests[\\/]/,'tests/').replaceAll('\\','/');
    this.cases.push({id:`${file}:${test.location.line}:${test.titlePath().join(' > ')}`,
      status:result.status,duration_ms:Math.max(0,result.duration)});
  }
  onEnd(result:FullResult){
    const counts={total:this.cases.length,passed:0,failed:0,skipped:0};
    for(const item of this.cases){if(item.status==='passed')counts.passed+=1;
      else if(item.status==='skipped')counts.skipped+=1;else counts.failed+=1;}
    const status=this.errors||counts.failed||result.status!=='passed'?'failed':
      !counts.total||counts.skipped?'incomplete':'passed';
    process.stdout.write(JSON.stringify({schema_version:1,status,cases:this.cases,counts,errors_count:this.errors})+'\n');
  }
}
