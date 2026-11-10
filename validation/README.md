# Local validation package

Source only. No import triggers tests,DB,models,network or services. The manual
CLI defaults to a plan; `--execute` and reviewed configs are required for data/
model/benchmark work. See [the Phase12 runbook](../documentation/phase12/RUNBOOK.md)
for complete order,input contracts,exact scope and scientific acceptance limits.

All outputs use fresh directories under artifacts and preserve earlier reports.
No package installer,model/dataset downloader,paid inference,raw-data writer or
arbitrary shell-command dispatcher is included. Unit and browser reporters omit
private text,credentials and exception messages. Empty/skipped/blocked studies
do not become passing results.

Actions: benchmark,models,score-export,state-export,parity,grounding,evidence,
rehearsal,bundle. `validation.runner` groups unit/postgres/browser/benchmark/
parity/grounding/evidence use a fixed command set. Every example config grants
no execution approval and contains no fabricated records,labels,IDs or metrics.
