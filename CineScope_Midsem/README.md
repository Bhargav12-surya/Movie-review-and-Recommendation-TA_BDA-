# CineScope Mid-sem: the small version

A local English movie-review demo with a frontend, immediate sentiment/aspect analysis, browser history and explainable recommendations. **Start with the core app only.** Optional labs are a separate final-project learning track.

## Run (Windows, macOS or Linux)

Install Python 3.10+ (3.11 or 3.12 recommended). Extract the ZIP and open a terminal inside `CineScope_Midsem`:

```bash
python app.py
```

Open http://127.0.0.1:8000. Windows users can use `py app.py` if `python` is unavailable. No pip install, API key, GPU, Node, Spark or internet is needed for this demo. Keep the terminal open; stop with Ctrl+C. Do not double-click the HTML file.

Try the example button, change the text, choose a rating, save it, and inspect recommendations. Refresh to check persistence. History is in browser localStorage, limited to 200 movies, with one entry per movie. The local server does not store review history. Clearing browser data clears it.

## What is actually included

| Feature | Mid-sem implementation |
|---|---|
| Live sentiment | Small English lexicon with a short negation window; 300 ms input debounce |
| Story, Acting, Visuals, Music, Pacing, Ending | Nearest-keyword opinion assignment, clause evidence, missing scores remain null |
| Themes / genres | Explicit mentions, clause sentiment and clause coverage; genre metadata shown separately |
| Recommendations | Signed rating/genre profile + review theme and aspect signals + a small rating prior |
| Dataset | 12 fictional titles with explicitly synthetic reviews; optional MovieLens import |
| Big-data component | One Scala Spark batch file: clean, aggregate, join, Parquet, bounded JSON export |
| Optional trained overall sentiment | Train BoW/TF-IDF on IMDb; JSON TF-IDF export loads in the app after restart |
| Optional research | True n-gram LM, Word2Vec, GloVe comparison, DistilBERT, aspect training, PMI and LDA |

The source core is `app.py`, `engine.py`, `web/` and `data/catalog.json`. You can ignore `optional/` and `scala/` for the first run. The app is Python + plain HTML/CSS/JS; **Scala is specifically the offline big-data layer**, not the web backend.

No trained models from the original ZIP have been copied. Original model results are not results of this smaller version. A 100/100 rule score means all detected opinion hits were positive, not 100% accuracy or confidence. “No evidence” is not neutral. Theme/genre clause scores can accidentally include opinions about another subject in that clause.

## MovieLens (recommended second step)

Download and extract https://files.grouplens.org/datasets/movielens/ml-latest-small.zip yourself. Read its README and retain its attribution/usage conditions. MovieLens supplies ratings, movie metadata and tags; it is **not a labeled full-review sentiment dataset**. This project does not redistribute it.

```bash
python import_movielens.py /path/to/ml-latest-small
```

Windows PowerShell:

```powershell
$env:CINESCOPE_CATALOG = "data/movielens.json"
python app.py
```

macOS/Linux:

```bash
CINESCOPE_CATALOG=data/movielens.json python app.py
```

Run from the project root. Dataset ratings supply a prior, while your browser history supplies personal tastes. The importer does not impersonate a MovieLens user. To add legitimately obtained movie-linked review text, provide CSV columns `movieId,review`:

```bash
python import_movielens.py /path/to/ml-latest-small --reviews linked_reviews.csv
```

Use real movie IDs. IMDb review filenames are not MovieLens IDs. Up to 20 unique reviews per film are retained for the small app; the complete original corpus should remain separate. Without linked reviews, recommendation theme/aspect components are zero. The basic genre-history recommender still works.

## Optional: train overall sentiment

Use an isolated virtual environment. Download/extract Stanford aclImdb from https://ai.stanford.edu/~amaas/data/sentiment/ and retain the source README.

```bash
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r optional/requirements.txt
python optional/prepare_imdb.py /path/to/aclImdb
python optional/train_baselines.py
python app.py
```

Training writes `data/sentiment.json` and real measurement reports. The app automatically loads that JSON at startup. Only overall sentiment changes; aspects remain rules. The binary model cannot establish a learned neutral class. Its 0-100 output is positive-class model probability multiplied by 100, not an independently calibrated confidence measure. Remove/rename the JSON and restart to return to rules.

BoW and TF-IDF use identical rows, tokenization, n-gram range, feature budget and validation C candidates. Validation chooses C separately for each method; test is used only for final reporting. TF-IDF is exported as the preselected serving baseline, regardless of which test score is higher. No accuracy is promised.

## Optional NLP experiments

```bash
python optional/ngram_lab.py
python optional/corpus_lab.py
python -m pip install gensim
python optional/word_vectors.py
# Optional 100-dimensional local GloVe text:
python optional/word_vectors.py --glove /path/to/glove.6B.100d.txt
python -m pip install torch transformers
python optional/train_distilbert.py --epochs 2
python optional/train_aspects.py data/my_human_annotations.csv
```

`optional/Ngram_Lab.ipynb` is the notebook entry point for the language-model experiment; Jupyter is optional. Set `PYTHONHASHSEED=42` before Word2Vec training if you require stronger repeatability. Save the complete `pip freeze` with each experiment. Heavy dependencies, weights and real-corpus training were not run as part of this delivery. DistilBERT truncates at 256 tokens; report that limitation against full-text TF-IDF. It is an offline comparison, not automatically served. Aspect models also remain offline. Human annotations must use the template columns; collect all five classes where appropriate, preserve held-out data and report per-class support.

## Scala / Spark big-data demo

Target combination: Java 17, Spark 3.5.7 distribution built for Scala 2.12, Scala 2.12.18 via sbt. Keep binary versions aligned; do not mix a Spark 4.x / Scala 2.13 installation with this build.

```bash
cd scala
sbt package
cd ..
spark-submit --master "local[2]" --class MovieStats scala/target/scala-2.12/cinescope-midsem_2.12-1.0.0.jar /path/to/ml-latest-small output/run1
python scala/import_spark_catalog.py output/run1/ui_catalog
```

Then set `CINESCOPE_CATALOG` as above. `output/run1` must be new: writes deliberately fail if outputs already exist. Windows commands should be run in a configured Spark terminal or WSL. The pure Python importer is sufficient for MovieLens-small; Spark is included for explaining and scaling batch operations. On a cluster, provide shared HDFS/object-storage paths and an appropriate master. Only the top 2,000 movies by rating count are exported for the local UI; full results remain in Parquet. This cap favors popular movies and is not a full-catalog recommendation benchmark.

## Tests and limitations

```bash
python -m unittest discover -s tests -v
```

See `docs/VALIDATION.md` for performed checks and unexecuted paths. See `docs/Handbook.md` or the companion PDF for explanations, formulas, walkthroughs, syllabus coverage, advanced evaluation protocols and viva answers.

For mid-sem, present a working prototype and explain the rules honestly. For final submission, collect real data, annotate aspects, train models, evaluate held-out performance and benchmark Spark separately. Spark source code alone is not evidence of big-data speedup. This is a localhost teaching server, not a multi-user deployment.
