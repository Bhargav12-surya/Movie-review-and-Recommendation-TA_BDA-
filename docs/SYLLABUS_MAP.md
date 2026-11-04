# Course-to-code mapping

| Course unit | Covered concepts | Concrete files / demonstration |
|---|---|---|
| BDA 1 | Volume/velocity/variety, Hadoop ecosystem, Mapper/Reducer | Notebook 01; `HadoopWordCount.scala`; batch vs live architecture; real 32M scale experiment instructions |
| BDA 2 | FP, immutable/mutable collections, type hierarchy, higher-order functions, closures, ConsList, tail recursion, OOP, concurrency | `FunctionalProgramming.scala` contains executable examples |
| BDA 3 | Spark driver/executors/cluster, RDD/DF/DS, transformations/actions, lazy execution, DAG, Parquet partitions | `MovieETL.scala`, notebook 05, `ReviewStream.scala`; `explain(true)` and Spark UI |
| BDA 4 | MLlib and pipelines, distributed ML case study | `SentimentPipeline.scala` and `ALSRecommender.scala`; movie-domain case study; temporal evaluation |
| TA 1 | Syntax, semantics, morphology, collocation, NLP ambiguity | Notebooks 02 and 08; negation handling and PMI; optional spaCy linguistics |
| TA 2 | One-hot, BoW, TF-IDF, n-grams, neural embeddings | Notebook 02; `training.py`; optional sentence-transformer retrieval in notebook 06 |
| TA 3 | ML/deep learning, transformer sequence models, topic modeling, HMM, graph NLP | DistilBERT/ABSA in 03, LDA in 04, optional T5 in 06, Viterbi and co-occurrence graph ranking in 08 |
| TA 4 | POS/NER/dependencies, sentiment, Q&A, summarization, evaluation and visualization | Notebooks 03/04/06/07/08; review studio; evidence summaries; charts and measured metrics |

GPT-style models, CRFs and machine translation are comparison/extension topics rather than implemented product features. The curriculum includes more algorithms than a single focused movie application needs; the project uses the relevant ones and states the boundary honestly.

## Suggested course demonstration

1. Open Discover; select Sci-Fi and Romance together and explain intersection filtering.
2. Rate **Her** highly and another title poorly; show how signed preferences alter unseen recommendations.
3. Open Review Studio; enter a mixed review praising acting and criticizing pacing. Show clause evidence and null scores for unmentioned aspects.
4. Save it; show the eligible count and aggregate change. Submit a duplicate; show the duplicate count without asserting that the author is deceptive.
5. Ask “Summarize the reviews for Arrival”, then a follow-up about its pacing. Demonstrate speech if supported.
6. Open **The Last Signal**, the fictional title with no reviews; explain metadata cold start.
7. Show the IMDb training split and actual held-out metrics. Explain why sentiment labels do not supply aspect/fake-review labels.
8. Show the Scala ETL DAG, temporal ALS split, cold-start coverage and checkpointed streaming output.
9. Present limitations, ablations and data provenance rather than inflated benchmark claims.

## Division of work

A small team can own (a) Spark/data engineering, (b) text analytics/models/evaluation, and (c) API/UI/conversation, while sharing the canonical ID and schema contracts. Keep one reproducible evaluation split across experiments.
