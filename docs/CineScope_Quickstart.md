# CineScope — Quickstart

Movie Review and Recommendation System for Big Data Analysis + Text Analytics.

## Run the complete local application

1. Extract `CineScope_Project.zip` and open a terminal in the `CineScope` folder.
2. Install Python 3.11 (Python 3.10–3.12 is supported).
3. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

On macOS/Linux, use `source .venv/bin/activate` instead of the second command.

4. Install and start:

```bash
python -m pip install -e ".[notebooks,dev]"
python -m uvicorn cinescope.api:app --host 127.0.0.1 --port 8000
```

5. Open **http://127.0.0.1:8000**. Interactive API documentation is at **http://127.0.0.1:8000/docs**.

No API key or GPU is needed for this default application. A trained TF-IDF sentiment model is included and loads automatically. Ratings and submitted reviews persist locally.

## What is included

- **9 Jupyter notebooks**: quickstart, data preparation, text representations, sentiment/ABSA training, trust/topics/summaries, Spark/ALS, conversation/speech, evaluation, linguistics/sequences/graphs.
- **6 Scala programs**: FP concepts, Spark ETL, Spark sentiment pipeline, ALS, streaming reviews and Hadoop Mapper/Reducer.
- A FastAPI/SQLite backend, responsive movie UI, ingestion/export scripts and tests.
- A trained IMDb CPU sentiment model and MovieLens-small ALS factors, with measured reports and a model card.

## Try the app

- Combine **Sci-Fi + Romance** in Discover.
- Rate **Her** and compare your recommendations; inspect My taste.
- Write “The acting is excellent, but the pacing is terrible” in Review Studio.
- Save a review and inspect the updated summary and evidence.
- Ask “Summarize the reviews for Arrival”.
- Open **The Last Signal**, a fictional sample title with no reviews, to demonstrate cold start.

The sample catalog includes **synthetic reviews**, clearly labeled. Genre/theme coverage and aspect sentiment indices are not objective film-quality ratings. Review screening identifies suspicious patterns; it does not prove that a review is fake.

## Open the notebooks

```bash
python -m jupyterlab notebooks
```

The notebooks run in a lightweight demonstration mode by default. Enable their explicit training/download switches to reproduce real-data experiments. Follow the full README inside the ZIP for real MovieLens/IMDb/TMDB ingestion, Scala/Spark execution, model settings and API routes.

Optional transformer, aspect and Whisper paths need their documented model downloads. TMDB ingestion needs your API token; aspect fine-tuning needs human annotations. The hosted frontend preview uses its browser demo engine, while the local application uses the supplied backend and trained sentiment model.

## Measured results and checks

- IMDb baseline: **90.05% accuracy**, macro-F1 **0.90052**, on **24,799 deduplicated held-out reviews**. This is not the untouched 25,000-review official benchmark.
- ALS: test RMSE **0.95287**, scorable coverage **90.72%**. Its top-10 ranking trailed the popularity baseline in this run; that finding is preserved in the reports.
- **11 backend tests passed**; all nine notebooks passed default cell execution in-process; all six Scala sources compiled; the real Scala ALS training job ran successfully.
- Transformer/GPU, microphone and multi-node cluster paths were not executed here. Details are in `docs/VALIDATION.md` within the project.

This is a local academic application. Keep the supplied localhost binding; authentication and deployment controls are separate work if you later expose the backend to other users.
