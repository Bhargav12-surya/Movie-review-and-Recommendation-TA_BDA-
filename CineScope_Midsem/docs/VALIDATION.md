# Validation record

This record separates executed checks from code supplied for the user's environment.

## Executed successfully in the delivery environment

- `python -m unittest discover -s tests -v`: 9/9 tests passed.
- `python -m compileall -q`: all Python files compiled.
- `node --check web/app.js`: JavaScript syntax passed.
- HTTP smoke test: catalog, review analysis and recommendation routes returned valid JSON.
- Mixed review check: positive Acting and negative Story were separated.
- Negation checks: `wasn't good` scored negatively; `not bad` scored positively under the documented rule.
- Missing evidence check: unopinionated and empty text remained unscored.
- Recommendation checks: seen films were excluded; likes/dislikes changed ranking; review theme and aspect signals changed ranking.
- MovieLens importer fixture: quoted CSV titles, rating means/counts and `(no genres listed)` were handled.
- Optional evaluator fixture: classification, exact typed entity span and ranking arithmetic were checked.
- TF-IDF JSON serving fixture: exported coefficients reproduced scikit-learn probabilities after rounding on controlled text.
- PDF checks: page render, text extraction, page numbering, table of contents and selected-page visual inspection.

## Not executed here

- Real IMDb training: the raw dataset was not redistributed or downloaded for this delivery.
- CBOW, Skip-gram, GloVe and DistilBERT training: optional packages/weights and real corpus were not installed.
- Human aspect-model training: no invented gold annotations were created.
- Real PMI/LDA outputs: these depend on the prepared review corpus.
- Scala compilation and Spark execution: Java 17 was available, but sbt and Spark were not installed.
- Full browser automation: the browser binary download was blocked by the execution environment. Static JavaScript syntax and live HTTP behavior were checked instead.
- Research-quality accuracy, F1, recommendation ranking, summary, entity or retrieval results: these require real held-out labels and are intentionally not fabricated.

## Delivery environment notes

- Python core app: standard library only.
- Java runtime observed: OpenJDK 17.
- PDF generation and rendering used ReportLab and Poppler.
- The Scala build targets Spark 3.5.7 and Scala 2.12.18; use a matching local distribution.

