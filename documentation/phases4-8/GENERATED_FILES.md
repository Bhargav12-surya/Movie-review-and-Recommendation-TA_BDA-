# Generated files through Phase 8

Prepared10 November2026,Asia/Calcutta. Read [the runbook](RUNBOOK.md) for exact
execution order,inputs,manual commands and acceptance checklists. No model or
runtime success is claimed from these source files.

| Group | Files |
|---|---|
|Phase4|ml/aspect_common/{config,data,metrics,engine,cli}; ml/aspect_extraction and ml/aspect_sentiment per-model bundles; ml/aspect_pipeline/{predict,evaluate}; aspect schemas; tests/aspects; notebooks07,08|
|Phase5|ml/themes/{data,task,train,evaluate,predict}; ml/topics,ml/embeddings,ml/summarization bundles; ml/common/{local_assets,evidence,records}; notebooks09,10,12|
|Phase6|ml/review_risk/{features,train,evaluate,predict}; notebook11; held-out moderation metrics and explicit unavailable ground truth|
|Phase7|scoring/{policy,eligibility,aggregate}; blank method/approval templates; Scala analytics/ReviewAnalytics.scala; audience schema; audience_scoring notebook|
|Phase8|Scala recommendation/{TemporalSplit,RankingEvaluation,RecommendationJob}; recommender/{catalogue,factors,profile,hybrid,train,evaluate,evaluation,predict}; configs/recommendation; recommendation schema; notebooks13,14|
|Manual entry points|scripts/train_aspects.ps1,prepare_aspect_baseline.py,run_offline_phase.py,run_recommendation.ps1,recommendation_readiness.py|
|Static check|scripts/verify_generated_phases.py and parse_scala_sources.py; separate PowerShell parser report; no model imports,tests,training,Spark or downloads|
|Tests|18 Python methods under tests/aspects and tests/phases4_8;4 Scala cases in AudienceAndTemporalSpec; isolated synthetic mechanism fixtures,not academic performance data|

Every new NLP component has separate train.py,evaluate.py,predict.py,config.yaml,
README.md and model_card.md. Pretrained embedding/summary components clearly
reject unsupported fine-tuning and require reviewed local assets for inference.
Null paths,thresholds and approval fields are intentional missing inputs,not
fabricated executable configuration. Weights/vectors/results are not committed.

Open work includes genuine labels/rights/canonical mapping,actual GPU/resume
checks,final-source Scala compilation/Parquet/runtime,theme/topic/retrieval and
summary factuality evaluation,risk validation,scoring parity/event integration,
actual ALS trials and hybrid selection. Later backend/frontend/chat and full
integration remain phases9-13. See IMPLEMENTATION_STATUS.md for observed checks.
