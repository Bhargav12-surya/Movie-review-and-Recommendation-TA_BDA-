# Phase12–13 source index

Updated11 November2026,Asia/Calcutta. Source generation and static verification
do not close runtime/scientific acceptance. See RUNBOOK.md and final/README.md.

- `validation/`: bounded I/O,resource sampling,HTTP benchmark,real-model reload
  check,score/Parquet exports,Python/Scala and state parity,human grounding/WER,
  evidence register,comparison reporting,fixed test runner,rehearsal and bundle.
- `configs/validation/`: selected suite and unapproved example configs for each
  scientific/operational action. Empty examples contain no fabricated data.
- `schemas/validation/`: evidence-study and private human-judgment input contracts.
- `scripts/evaluate_all.ps1`, `rehearse_demo.ps1`,
  `prepare_evaluation_bundle.ps1`, `stop_services.ps1`: explicit later actions.
- `scripts/verify_all_sources.py`: active source AST/config/notebook/import/link
  check; no application imports. Existing Scala parser accepts optional harness
  coverage and does no typing,code generation or Spark execution.
- `backend/tests/`: expanded real PostgreSQL/session/revision/queue/vector/
  unavailable-model/context/two-connection guard fixtures and contracts.
- `frontend/tests/`: real-service catalogue/journey/error/offline/voice fallback
  scenarios and a reporter omitting private text/errors/screenshots/traces.
- `tests/integration/test_validation.py`: isolated parity/report/metric guards.
- `scala/src/main/scala/com/movieintel/validation/ScoreParityJob.scala`: real
  Spark shared score arithmetic on frozen actual selected evidence.
- `notebooks/15_final_model_comparison.ipynb`: disabled actual-report comparison
  and optional measured plot export; no fitting or final-test retuning.
- `requirements/requirements-integration.txt`: manual test-only HTTPX candidate.
- `documentation/final/`: academic methods/report,actual architecture/ER,syllabus
  mapping,result/evaluation templates,reproducibility,privacy,acceptance,demo,
  limitations and Markdown presentation narrative.

Application changes are limited to the reviewed queue correctness fix and
isolated test configuration. Existing user-edited Scala work,raw datasets,
historical reports,model stores,environments,credentials and Git state remain
preserved. No new runtime outcome or scientific metric is claimed.
