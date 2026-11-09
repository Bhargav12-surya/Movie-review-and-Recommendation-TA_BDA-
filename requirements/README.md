# Dependency manifests

All installations are performed manually by the user. No script installs,
upgrades or removes software.

Phase 0 diagnostics and Phase 1 validation use Python 3.11's standard library.
Run them with the existing root virtual environment; requirements/phase1.txt
documents that no additional package is required.

requirements/analysis.txt contains exact direct dependency candidates for EDA
and later classical baselines. requirements-dev.txt selects an optional pytest
runner; the current unittest suites do not require it. These are documented,
published compatible candidates, not a claim that a transitive resolver or
runtime test has succeeded. After manual installation, run pip check and the
relevant import/functional verification before generating a final lock.

The later requirements-nlp.txt and requirements-backend.txt files contain
candidate direct pins for their named phases. The requirements-dev.txt file
inside this directory delegates to the single root pytest pin. They are
instructions for manual installation, not evidence that anything is installed.

PyTorch's CUDA wheel is installed separately from the official CUDA index.
Its GPU build must pass a tensor operation in this project's Python 3.11
environment. NLP, backend, frontend and speech dependency groups are added
in their respective phases; do not bulk-install unrelated groups.

Consult PREREQUISITES.md for official sources, exact selected candidates,
installation order, environment configuration and verification commands.

Late9 November recheck: scientific packages and torch2.14.1+cu130 appeared through
manual setup. Imports,pip check and tiny CUDA/FP16/BF16 checks passed. Older
analysis/root pytest candidates differ from the actual versions, and the NLP
manifest still targets cu132. Those manifests were preserved. Reconcile future
manual resolution with the working environment; do not force incidental
downgrades or replace the verified GPU runtime merely to apply an earlier list.
