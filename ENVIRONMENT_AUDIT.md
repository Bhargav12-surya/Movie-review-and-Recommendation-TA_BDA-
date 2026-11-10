# Environment Audit — Movie Review & Recommendation System

Latest follow-up, 9 November 2026 (Asia/Calcutta): the original Phase 0 findings
below are historical. The user prepared root Python 3.11 and subsequently
installed Spark/SBT at explicit paths. A prior cu130 tensor/precision check
passed; newer cu132 package metadata needs a new runtime check. See section 14
and IMPLEMENTATION_STATUS.md. The current delivery generates files and performs
static checks only; it does not verify the changed environment by executing jobs.

Audit date: **8 November 2026, Asia/Calcutta**. Workspace: `D:\BDA_TA`. Scope: Phase 0 inspection and planning only. Status: **audit complete; implementation and installation await user approval**.

## 1. Findings that affect the execution plan

1. The requested CPU and GPU are present. NVIDIA reports an RTX 5050 Laptop GPU with **8,151 MiB VRAM**, compute capability **12.0**, and driver **621.01**. This confirms hardware detection, not working PyTorch CUDA inference.
2. **The workspace drive has 55.83 GiB free**, not the assumed 100 GB or more. The measured free space is 59.95 decimal GB. Preserve the existing files; obtain a storage decision before large installations, manual dataset extraction, or training checkpoints.
3. Physical/visible RAM is **15.71 GiB**, but only **1.10 GiB was available at the measurement**. This is current memory pressure, not evidence that the laptop cannot run the design. Do not start a heavy workload until available memory is rechecked.
4. The intended **Python 3.11.9** is installed and is the `python` on PATH. The `py` manager defaults to **3.14.6**, while the preserved `temp/.venv` uses **3.12.10**. An unqualified `py` or reuse of that environment would select the wrong project interpreter.
5. The Python 3.14 installation contains **CPU-only PyTorch 2.14.0+cpu**. A small CUDA diagnostic was attempted with that interpreter but stopped during `import torch`, with NumPy warnings and exit code 1. No tensor operation ran. There is no validated CUDA-enabled project environment.
6. JDK 21 is installed, but `JAVA_HOME` and PATH select different patch installations. Existing legacy source targets Spark 3.5.7/Scala 2.12.18; the new architecture requires Spark 4.x/Scala 2.13. Preserve the legacy project and explicitly reconcile the build before reuse.
7. Node/npm, SBT, a Spark distribution, and PostgreSQL were not detected on PATH or in the ordinary locations checked. Docker was not detected; WSL explicitly reports that it is not installed. No project listener was observed on the expected application ports.
8. Official versioned Spark 4.3.0 documentation supports the proposed JDK 21/Scala 2.13/Python 3.11 combination. The architecture's Spark 4.3.0 baseline does **not** require a speculative downgrade. Exact environment locks still need installation-time resolution and smoke tests.

No packages, drivers, models, or datasets were installed, upgraded, downloaded, trained, repaired, or removed for this audit. Only already installed executables and package metadata were examined. A read-only Windows CIM query initially failed in the sandbox and was repeated with the required escalation; that retry succeeded. No project code or serialized model was executed.

## 2. Evidence collection and interpretation

The host's diagnostic date agreed with the client date: `nvidia-smi` printed `Sun Nov 8 10:48:37 2026`. The application's future timestamps should be stored in UTC and rendered in the user's timezone. Disk and free-memory readings are snapshots and will change.

| Check | Method actually used | Result / limitation |
|---|---|---|
| Hardware/OS | `Get-CimInstance` for operating system, processor, computer system, logical disks | First attempt: access denied; escalated read-only retry succeeded |
| CPU fallback | Registry `HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0` | Confirms Core 7 240H; registry frequency is not the same as CPU base clock |
| Windows fallback | OS registry and Python `platform.platform()` | Registry retains a Windows 10 product string; CIM identifies Windows 11, so CIM is used |
| Executable discovery | `Get-Command` for relevant tools | PATH availability only, followed by known install-directory and uninstall-registry checks |
| Interpreter discovery | `python --version`, `py list -f=json`, explicit Python executable invocations | Three registered interpreter installations observed |
| Python dependencies | `importlib.metadata` and `pip check` | Installed metadata is separated from successful runtime imports |
| GPU | `nvidia-smi`, query for name/driver/memory/compute capability | Hardware/driver query passed; reports CUDA driver capability, not a Python runtime |
| PyTorch | Existing Python 3.14 interpreter, import and planned 8×8 CUDA matrix multiplication | Import failed before any tensor ran; static `torch/version.py` identifies CPU build |
| Java | `java -version`, `javac -version`, explicit `JAVA_HOME` Java version | Both JDK installations run; they differ in patch level |
| Scala | PATH wrapper and its cached distribution path inspected | Wrapper points to Scala 3.8.4; no compiler-resolution command or dependency download invoked |
| Services/ports | `Get-Service` filtered for PostgreSQL/Docker; `netstat -ano -p tcp` | No matching services/listeners observed at snapshot; not an HTTP or database health test |
| Official compatibility | Documentation pages opened through the web tool | Documentation only; no datasets or alternative dataset research |

No broad environment-variable dump was taken. Only runtime path variables were checked. Credentials, real `.env` content, tokens, and private account configuration were not printed.

## 3. Hardware, operating system, memory, and storage

| Component | Observed value | Implication |
|---|---|---|
| Operating system | Microsoft Windows 11 Home Single Language, 64-bit, `10.0.26300` | Native PowerShell workflow is appropriate |
| CPU | Intel Core 7 240H, 10 cores, 16 logical processors | Suitable for bounded local Spark and preprocessing |
| CPU maximum clock field | 2,500 MHz from CIM | Consistent with user-reported 2.50 GHz; not a sustained performance measurement |
| Physical/visible RAM | 16,866,033,664 bytes = 15.71 GiB | Keep training, Spark, and full demonstration modes separate |
| Available RAM snapshot | 1,179,144,192 bytes = 1.10 GiB | Do not start large jobs at this pressure; remeasure after closing user-selected workloads |
| GPU | NVIDIA GeForce RTX 5050 Laptop GPU | Detected using NVIDIA's own diagnostic |
| VRAM | 8,151 MiB reported | Approximately the expected 8 GB class; Windows display use reduces available capacity |
| GPU temperature snapshot | 57°C | Idle diagnostic snapshot only, not a training thermal assessment |
| Reported power limit | 50 W in the snapshot | Actual training throughput must be measured; laptop configuration matters |
| GPU compute capability | 12.0 | Select a Windows PyTorch binary supporting this architecture |

The NVIDIA compute capability table lists the RTX 5050 under 12.0. This agrees with the local driver query. [NVIDIA compute capabilities](https://developer.nvidia.com/cuda/gpus)

| Drive | Total bytes | Free bytes | Free GiB | Free decimal GB |
|---|---:|---:|---:|---:|
| `C:` | 346,855,305,216 | 138,557,231,104 | 129.04 | 138.56 |
| `D:` — current workspace | 322,279,829,504 | 59,949,912,064 | **55.83** | **59.95** |
| `E:` | 322,278,780,928 | 98,499,907,584 | 91.74 | 98.50 |

The 100 GB assumption fails for `D:`. With a proposed 20 GiB workspace-drive reserve, approximately 35.83 GiB remains before new downloads and processing. That arithmetic is a planning limit, not an assurance that it covers all dependencies, raw and curated data, caches, and checkpoints. Other drives are observations only; no files were moved and no cross-drive cache was configured. Obtain approval for an explicit location or for user-managed space recovery. Never recover space by deleting original datasets or the preserved prototype.

MovieLens files appeared locally after this disk measurement, adding 1,194,583,199 bytes of archive/extracted inputs as recorded in DATASET_AUDIT.md. The values above remain timestamped audit snapshots; available space must be measured again before setup rather than assumed unchanged.

## 4. Installed tools and runtime paths

| Tool | Actual observation | Readiness |
|---|---|---|
| Python on PATH | `3.11.9`, 64-bit; `C:\Users\bharg\AppData\Local\Programs\Python\Python311\python.exe` | Meets requested interpreter line; use its explicit path for environment creation |
| `pip` for PATH Python | `24.0` | Present; no upgrade performed |
| Python manager | `py.exe` WindowsApps alias, manager `26.4` | `py list` works; default runtime is 3.14.6 |
| Managed Python 3.12 | `3.12.10`; `C:\Users\bharg\AppData\Local\Python\pythoncore-3.12-64\python.exe` | Preserved legacy runtime |
| Managed Python 3.14 | `3.14.6`; `C:\Users\bharg\AppData\Local\Python\pythoncore-3.14-64\python.exe` | Default for manager; do not select for the new Python 3.11 project |
| Root project `.venv` | Not present at audit start | Create a distinct environment only after approval |
| `temp/.venv` | Python 3.12.10; `include-system-site-packages = false` | Existing environment preserved; not the target 3.11 environment |
| NVIDIA diagnostic | `C:\WINDOWS\system32\nvidia-smi.exe`, version 621.01 | Runs successfully |
| CUDA Toolkit compiler | `nvcc` not on PATH; default CUDA Toolkit directory not found; `CUDA_PATH` unset | Full Toolkit not detected; do not install just because it is absent |
| Java on PATH | Temurin JDK `21.0.12.1+1-LTS`, `C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot` | `java` and `javac` run |
| `JAVA_HOME` Java | Temurin `21.0.12+8-LTS`, cached Coursier installation | Existing path is valid but differs from PATH |
| Scala command | Coursier `scala.bat` wrapper points to cached `scala3-3.8.4` distribution | Does not establish a Scala 2.13 project compiler |
| `scalac` | Not on PATH | SBT-managed compiler can supply it later; do not confuse with Scala 3 wrapper |
| SBT | Not on PATH; legacy source pins `1.10.7` | Installed SBT not detected |
| Spark distribution | `spark-submit` / `spark-shell` not on PATH; `SPARK_HOME` unset | Runtime not detected; source declarations are not installation evidence |
| Node.js / npm | Not on PATH; common Program Files/user install directories not found; no matching registry entry observed | Required frontend runtime not detected |
| Git | `2.56.0.windows.4`, `C:\Program Files\Git\cmd\git.exe` | Present; repository state is audited separately |
| VS Code | `1.143.1`, x64 | Version returned despite a crashpad access-denied diagnostic |
| PostgreSQL tools/server | `psql`/`pg_config` not on PATH; common install locations/registry/services not found | Local database not detected; custom unexamined locations remain possible |
| pgvector server extension | No PostgreSQL instance available to query | Not verified; a Python `pgvector` package would not prove server-extension availability |
| JupyterLab | 4.6.4 metadata and executable in `temp/.venv` | Present in legacy env; server was not launched |
| Docker | Command/common install location/registry/service not detected | Optional deployment path unavailable in observed environment |
| WSL | `wsl --status` explicitly reports not installed | No Linux environment prepared; no installation attempted |

Only `JAVA_HOME` was set among checked runtime-path variables; `SPARK_HOME`, `SCALA_HOME`, `CUDA_PATH`, `VIRTUAL_ENV`, and `CONDA_PREFIX` were empty. Do not edit global PATH or JAVA_HOME silently. Prefer a project-scoped launcher that selects one approved JDK and records its identity.

The preserved venv's `pyvenv.cfg` records an original creation command targeting `D:\BDA_TA\.venv`, while it is now located under `temp/`. Running its Python succeeded, but console-script launchers may retain old absolute paths. Treat it as historical, preserve it, and create the approved environment separately rather than repairing it in place.

## 5. Python dependency metadata

The table reports metadata, not a guarantee that native extensions import. `pip check` returned **No broken requirements found** for Python 3.11 and `temp/.venv`; this does not test binary compatibility, GPU execution, or project completeness.

| Package | PATH Python 3.11.9 | Preserved `temp/.venv` Python 3.12.10 |
|---|---|---|
| pip | 24.0 | 25.0.1 |
| NumPy | 2.4.6 | 2.5.3 |
| pandas | 3.1.0 | 2.3.3 |
| scikit-learn | 1.9.1 | 1.7.2 |
| Pydantic | 2.14.2 | 2.13.5 |
| FastAPI | Not installed in this interpreter | 0.141.1 |
| Uvicorn | Not installed | 0.54.0 |
| JupyterLab | Not installed | 4.6.4 |
| pytest | Not installed | 9.1.1 |
| PyArrow | Not installed | 22.0.0 |
| torch | Not installed | Not installed |
| Transformers / Datasets / Accelerate | Not installed | Not installed |
| Sentence Transformers / BERTopic | Not installed | Not installed |
| SQLAlchemy / psycopg / psycopg2 / pgvector | Not installed | Not installed |
| PySpark | Not installed | Not installed |
| Hugging Face Hub / tokenizers / safetensors | Not queried for this interpreter | Not installed |

The third Python 3.14.6 installation has torch metadata **2.14.0**, static build version **2.14.0+cpu**, `cuda = None`, and NumPy metadata **1.26.4**. Both wheel tags report `cp314-cp314-win_amd64`. Transformers, Datasets, PySpark, Sentence Transformers, BERTopic, JupyterLab, SQLAlchemy, and pgvector were not installed in that interpreter. No attempt was made to uninstall or change them.

Existing package versions must not be copied into the new lockfile merely because they are installed. The legacy project's manifest and the actual environments disagree; the future Python 3.11 lock should be resolved and tested as one coherent package set, without upgrading shared interpreters.

## 6. GPU and PyTorch validation result

`nvidia-smi` produced:

```text
GPU: NVIDIA GeForce RTX 5050 Laptop GPU
Driver: 621.01
Driver model: WDDM
CUDA UMD Version: 13.5
VRAM: 8151 MiB
Compute capability: 12.0
```

The initial query returned 7,910 MiB free. A later full table reported zero MiB allocated and no listed processes. These are separate snapshots; they are not a precision memory benchmark.

The attempted smoke script imported `torch`, planned to print the build/runtime, query CUDA support, then multiply two 8×8 CUDA tensors. It **exited with code 1 during import**, before its first diagnostic print. Output included an experimental MINGW-W64 NumPy warning and floating-point runtime warnings in NumPy's `getlimits.py`. This establishes a failed import in that interpreter; the exact underlying import failure was not diagnosed or repaired. Static inspection independently establishes that its torch build is CPU-only.

| Acceptance check | Status |
|---|---|
| GPU detected by NVIDIA driver | PASS |
| Expected GPU name, compute capability, and approximate VRAM reported | PASS |
| Correct project Python 3.11 virtual environment | NOT CREATED — approval pending |
| PyTorch imports in project environment | NOT RUN — PyTorch absent there |
| PyTorch imports in existing 3.14 installation | FAIL — process exited during import |
| CUDA-enabled PyTorch build in project environment | NOT INSTALLED |
| `torch.cuda.is_available()` | NOT VERIFIED |
| Small CUDA tensor operation | NOT RUN — import did not complete |
| FP16/BF16 forward/backward compatibility | NOT RUN |
| GPU memory monitoring through PyTorch | NOT RUN |
| DistilBERT forward pass / checkpoint resume | DEFERRED — no model download or training authorized |

The driver-reported CUDA version is not `torch.version.cuda`, not evidence of an installed Toolkit, and not proof that a selected binary supports `sm_120`. Driver 621.01 exceeds NVIDIA's documented CUDA 13.x minor-compatibility baseline of 580, but actual library and architecture compatibility must still pass a runtime test. [NVIDIA CUDA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)

## 7. Official compatibility review and proposed version decisions

### Spark, Scala, Java, and Python

The versioned Spark 4.3.0 overview explicitly lists Windows, Java 17/21/25, Scala 2.13, and Python 3.11+. It also requires Scala applications to match Spark's compiled Scala version. Therefore **Spark 4.3.0 + JDK 21 + Scala 2.13 + Python 3.11** is a documented target. Pin the Scala patch to the selected Spark artifact/build metadata and keep Spark versions identical across Scala dependencies, distribution, and any optional PySpark environment. [Spark 4.3.0 overview](https://spark.apache.org/docs/4.3.0/)

The legacy `temp/scala/build.sbt` instead sets Scala **2.12.18** and Spark **3.5.7**. Spark 3.5.7 documents Java 8/11/17; JDK 21 is outside that stated set. The source must be reviewed for Spark 4 behavior changes before reuse; do not simply change version strings and claim compatibility. [Spark 3.5.7 overview](https://spark.apache.org/docs/3.5.7/)

Scala's JDK table gives Scala 2.13.11 and SBT 1.9.0 as minimums for JDK 21. The old SBT pin 1.10.7 clears that tooling floor but is not an installed executable. Retain it as a candidate only after dependency/build validation; no blanket tooling upgrade is justified. [Scala JDK compatibility](https://docs.scala-lang.org/overviews/jdk-compatibility/overview.html), [SBT setup](https://www.scala-sbt.org/1.x/docs/Setup.html)

### PyTorch, CUDA, and Transformers

The official PyTorch sources are not fully aligned in their rendered content: the installation page says the latest stable requires Python 3.11+, while its static selector shows 2.7.0; the repository's release matrix has a 2.15 row and Windows Blackwell 12.0 support for CUDA 13.2.2/13.4 builds. The previous-versions page explicitly lists a Windows CUDA 13.2 build for torch 2.14.1. These establish candidates, not a tested project pin. At approved installation time, resolve the actual Windows/Python 3.11 wheel, reconcile selector/release data, record its exact version/hash/index, and validate CUDA. No nightly or CPU wheel should become the training default. [PyTorch installation](https://pytorch.org/get-started/locally/), [release/CUDA matrix](https://github.com/pytorch/pytorch/blob/main/RELEASE.md), [published previous-version commands](https://pytorch.org/get-started/previous-versions/)

A full standalone CUDA Toolkit is not a prerequisite for ordinary prebuilt PyTorch wheel training; add it only if an approved extension needs compilation. The local NVIDIA driver still has to support the chosen runtime. Do not install a driver merely to match an arbitrary tutorial version.

Transformers' current installation guide reports testing on Python 3.11+ and PyTorch 2.6+. This is a minimum compatibility statement, not confirmation that every newest combination is suitable. Resolve Transformers, Datasets, Accelerate, tokenizers, safetensors, and Sentence Transformers together and run offline-loading/inference checks before pinning the final lock. [Transformers installation and offline mode](https://huggingface.co/docs/transformers/installation)

### Node.js, Next.js, and frontend

The current Next.js installation guide identifies version 16.4.5, supports Windows, and requires Node 20.9 or newer. Use the architecture's **Node 24 LTS** candidate, which remains a supported LTS line; do not choose the lowest Next.js-compatible Node if it is already end of life. Pin the actual Node patch, Next.js, React, TypeScript, Tailwind, chart library, and lockfile together during frontend setup. No Node installer or scaffolding command was run. [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [Node release status](https://nodejs.org/en/about/previous-releases)

### PostgreSQL and pgvector on Windows

Use a supported stable PostgreSQL major with an explicitly compatible pgvector build; PostgreSQL 18 with pgvector 0.8.7 is a candidate supported by the extension's current installation examples. Resolve its current patch and server-extension ABI before installation. Native Windows pgvector instructions require Visual Studio C++ tools and `nmake` from an elevated x64 build prompt. Python's `pgvector` adapter does not install the server extension. Native installation is the initial proposal; Docker/WSL is an approval-dependent alternative with extra storage/RAM overhead, not a mandatory assumption. [pgvector installation](https://github.com/pgvector/pgvector), [PostgreSQL Windows installers](https://www.postgresql.org/download/windows/)

PostgreSQL supports majors for five years and recommends current minor fixes. Avoid a release candidate as the academic baseline. Verify the local extension with `SELECT extversion FROM pg_extension WHERE extname = 'vector'`, then round-trip a real dimensioned vector. [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)

## 8. Recommended dependency installation order — proposal only

The following sequence is for approval and subsequent implementation. None has been executed.

1. **Approve storage and runtime boundaries.** Recheck free RAM/disk, keep raw data read-only, and choose an approved cache/model location. Preserve `temp/` and all existing deleted/untracked Git states. Do not automatically relocate data to another drive.
2. **Create an isolated root Python 3.11 environment** using the explicit existing 3.11 executable. Never run `venv --clear` against an existing directory. Record interpreter and pip identity. Add ignore rules before dependencies/artifacts can be staged.
3. **Install the minimal audit/test group**: configured versions of pytest, PyArrow, small-table pandas/NumPy, scikit-learn, YAML/configuration tools, and plotting/notebook dependencies needed for the first phase. Inspect resolver output and binary wheels; lock the tested set. Keep Jupyter on localhost and launch it only on demand.
4. **Configure one JDK 21 and the Scala/Spark toolchain**: project-scoped Java selection, SBT, compatible Scala 2.13 patch, Spark 4.3.0 distribution/dependencies. The Spark download/dependency cache may be large; explain its size before installation. Run a tiny Scala job before MovieLens processing. PySpark is optional for notebooks and must not replace the mandatory Scala implementation.
5. **Install CUDA-enabled PyTorch** in that 3.11 environment from the verified official wheel index. This can consume multiple GB with runtime libraries; explain the resolved package sizes. Install only required libraries rather than automatically adding vision/audio packages for a text project. Validate import, architecture list, device capability, matrix operation, synchronization, finite results, and memory before model downloads.
6. **Install NLP packages as one compatible group**: Transformers, Datasets, Accelerate, Sentence Transformers, evaluation libraries, and safe model serialization dependencies. Add BERTopic/topic dependencies when Phase 5 needs them. Pretrained models require a separate explicit artifact/license/storage review; datasets remain manually supplied by the user.
7. **Install PostgreSQL + verified pgvector** through the approved native route. Explain any C++ build-tool dependency before installing it. Add SQLAlchemy, Pydantic, psycopg, migrations, FastAPI, Uvicorn, settings, secure authentication, and test tools in the Python lock. Create the real schema in Phase 9; checking extension viability earlier avoids a late blocker.
8. **Install Node 24 LTS/npm** and pin the frontend stack when Phase 10 begins. Commit a package lock, never `node_modules`. No hosted website or paid inference service is required.
9. **Add offline speech recognition only for Phase 11** after choosing a licensed compact checkpoint and verifying Windows decoding dependencies, CPU/GPU memory behavior, and local-only audio handling. Text remains the fallback. Do not pull a large optional generative chat model into the core dependency set.

Exact patches for unresolved packages are deliberately not fabricated. The implementation phase should first produce reviewable constraints/lockfiles and an estimated footprint, then obtain any installation approval required by the user's constraints. Python package groups may share the new environment if tested together; isolate only proven conflicts.

## 9. Resource policy to validate before heavy work

These are conservative proposed starting settings, not measured capacity or performance claims.

| Mode | Starting limits | Readiness condition |
|---|---|---|
| Spark batch | `local[4]`, approximately 3–4 GiB driver heap, 8–16 shuffle partitions, selective persistence | Recheck available RAM; no concurrent model training; observe Spark UI/shuffle/spill |
| Sentiment training | DistilBERT, micro-batch 4, sequence length 128, accumulation configurable, workers 0 initially | Approved training, validated labels/splits, working CUDA, monitor RAM/VRAM |
| Aspect extraction | Micro-batch 2–4, sequence length 128, checkpointing only if needed | One training model at a time; exact span alignment validated |
| Other NLP training | Compact theme/aspect heads; no large-model-from-scratch training | Approval and preflight for each substantial job |
| Embeddings | Small batches, persisted outputs | No all-movies/all-reviews pairwise dense similarity matrix |
| Summarization | Compact model, chunked evidence, batch 1 initially | Background job, source review IDs, human factuality evaluation |
| Local demonstration | Database + backend + Next.js, one inference worker/model-loading manager | Training stopped; Spark only when demonstrating it; CPU fallback tested |

Mixed precision must be selected after checking actual BF16 support; otherwise evaluate FP16 with appropriate scaling. Gradient accumulation, resumable checkpoints, dynamic padding, early stopping, and configurable batch/sequence lengths belong in the training interface. `empty_cache()` does not release live tensors. No fixed batch size is guaranteed to fit 8 GB VRAM.

One Uvicorn inference worker should be the initial GPU-serving policy: multiple worker processes can duplicate model memory. Use bounded inference concurrency and serialized GPU access across sentiment/aspect/summary/voice tasks. Do not keep every optional model resident. Retain a CPU route for small tests and graceful queued/pending analysis when the model is unavailable.

## 10. Localhost readiness and future validation

| Component | Required address | Audit status |
|---|---|---|
| Frontend | `http://localhost:3000` | No listener observed; Next.js runtime not detected |
| Backend | `http://localhost:8000` | No listener observed; new backend not implemented |
| API docs | `http://localhost:8000/docs` | Not requested because backend unavailable |
| PostgreSQL | `localhost:5432` | No listener/server detected; no DB credentials queried |
| JupyterLab | `http://localhost:8888` | No listener; package exists only in preserved env |
| Spark UI | `http://localhost:4040` while a job runs | No active job/listener; no Spark launch attempted |

Before training, require a passing GPU tensor smoke test in the **new Python 3.11 environment**. Then, after model-download and training approval, run a tiny forward/backward/checkpoint/resume test on permitted data. Keep this distinct from a statistically valid model experiment.

Before a full dataset job, compile/run a tiny independent Scala DataFrame/RDD example, write/read a tiny Parquet output, show `explain` and Spark UI, and verify a checkpointed file-stream restart. These are future tests, not audit accomplishments.

Before integration acceptance, require real PostgreSQL migrations, pgvector dimension checks, authenticated review submission, actual model persistence, no-evidence behavior, recommendations, and grounded chat. Test an offline rehearsal with local models/metadata/artwork and no retraining. Record actual model load time, latency distributions, memory, and failures; no performance targets or metrics are claimed by this audit.

## 11. Audit input fingerprints

SHA-256 records identify the small configuration files actually inspected; they are not dataset or model provenance validation.

| File | SHA-256 |
|---|---|
| `ARCHITECTURE.md` | `52E0E9ED68F743C3B44913D6C079F177787DA3814A0BD38C88AAE24BE37621E3` |
| `temp/pyproject.toml` | `B33D6ED9BE7A9C22FDA14FE4F99A1DD08ED8D4F3BA13F7EA83F0A2AE2C9B2B82` |
| `temp/scala/build.sbt` | `43873E5E96469318D3689CAB472071EE898A3F22D834034E2231B4E8B54FB5E9` |
| `temp/scala/project/build.properties` | `84D1A08240C782D6691E9829EC54530A45D10809B0E5200DB4035723D852928C` |
| `temp/.venv/pyvenv.cfg` | `26BE4D27D90DEE50111F6C2076582AB9D0568D14E081572F43D1219C42110477` |

## 12. Completion checklist and approval boundary

- [x] Hardware, memory, GPU, disk, Windows, and runtime paths inspected.
- [x] Intended Python and preserved environments distinguished.
- [x] Installed package metadata and limited consistency checks recorded.
- [x] NVIDIA diagnostics run; existing torch build identified honestly.
- [x] Official Spark/JDK/Scala/Python and frontend/database compatibility consulted.
- [x] Installation order, missing components, and unresolved pins documented.
- [x] No installation, dataset/model download, training, original-file deletion, or legacy-file replacement performed. The dataset audit records the separate creation and cleanup of temporary SQLite sidecars.
- [ ] User approves the detailed implementation plan and material architecture decisions.
- [ ] User approves the concrete dependency footprint/install actions and storage arrangement.
- [ ] New environment passes CUDA, Scala/Spark, database, and later localhost smoke tests.

**Stop here. This audit authorizes no implementation or installations by itself.** Continue only after the user approves the next phase described in `IMPLEMENTATION_PLAN.md`.

## 13. Executed follow-up after manual setup — 9 November 2026

The Phase0 stop above is historical. The user subsequently authorized source
implementation and dependency-based Phase2 progress; manual acquisition and
training restrictions remain. New packages appeared outside this agent's
installation workflow. No installation, upgrade or global configuration edit
was performed by this audit or the Phase2 implementation.

The actual selected interpreter remains D:\BDA_TA\.venv\Scripts\python.exe,
Python3.11.9. The diagnostic process now sees JAVA_HOME matching the existing
Adoptium21.0.12.1 JDK. Current metadata/import evidence:

| Package | Actual version | Executed verification |
|---|---|---|
| NumPy | 2.4.6 | Import passed |
| pandas | 2.3.3 | Import passed |
| scikit-learn | 1.9.1 | Import passed; no model fit |
| PyArrow | 26.0.1 | Import passed; no Scala Parquet proof |
| PyYAML | 6.0.3 | Import passed |
| pytest | 9.2.0 | Import passed; project suite ran through unittest |
| torch | 2.14.1+cu130 | Actual CUDA tensor operation passed |
| httpx | 0.28.1 | Metadata observed |
| matplotlib | 3.11.2 | Metadata observed |
| seaborn | 0.13.2 | Metadata observed |
| python-dotenv | 1.2.4 | Metadata observed |

pip check reported no broken requirements. This checks installed declared
constraints; it is not a solved future NLP/backend environment or a benchmark.
Transformers,Datasets,Accelerate,Sentence Transformers,JupyterLab and backend
packages were still absent in this selected environment at the recheck.

The actual torch build reports CUDA runtime13.0,RTX5050,compute capability12.0
and sm_120 in its architecture list. A tiny float32 CUDA multiplication completed
with finite results. Float16 and BF16 multiplications also completed with finite
results. Peak tensor allocation was33,558,528bytes and reserved memory35,651,584bytes
for this check. No model,backward pass,training,throughput benchmark or resume
test ran. AMP in a chosen Transformer training loop still requires its own test.
NVIDIA driver621.01 and8,151MiB VRAM were detected without modifying them.

Both CUDA13.0 and13.2 Windows builds are published for PyTorch2.14.1 in the
[official installation guide](https://pytorch.org/get-started/previous-versions/).
The installed cu130 build is working for this bounded test. The user-edited NLP
manifest still requests cu132 and earlier analysis constraints differ from the
new installed versions. Preserve both the installation and user's edits;
reconcile the later manual dependency plan rather than silently upgrading or
downgrading. No CUDA Toolkit or driver replacement is justified by this result.

The recheck measured49.269GiB free on D: and1,916.16MiB available RAM. These
snapshots do not certify headroom for Spark/training. Spark/SBT,Node/npm and
PostgreSQL tools remain unavailable in the checked locations. Phase2 still
requires real Spark compilation,ScalaTest and Windows Parquet/streaming runs.

Evidence: [full manual-install recheck](artifacts/environment/manual-install-recheck-20261109-1c28488e.json),
[Phase2 toolchain audit](documentation/bda/LOCAL_TOOLCHAIN_AUDIT.md),
[current implementation status](IMPLEMENTATION_STATUS.md).

## 14. Subsequent manual installations and source-only handoff

Observed 9 November 2026, Asia/Calcutta. This supersedes the earlier claims that
Spark/SBT were absent in checked locations. The user installed these tools; no
installer, resolver, upgrade or PATH/global-variable mutation was run here.

| Tool | Newly observed location/version | Evidence and limit |
|---|---|---|
| JDK | C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot; 21.0.12.1+1 | Used by the earlier offline compiler |
| Spark | C:\spark\spark-4.3.0-bin-hadoop3; 4.3.0 | RELEASE says Hadoop3.5.0; 279 bundled JARs inspected |
| Scala | 2.13.18 bundled compiler/library/reflect | Matches the configured Spark/Scala source target |
| SBT | C:\Program Files (x86)\sbt; launcher default1.10.7 | Launcher files found; SBT was not bootstrapped or executed |

Spark and SBT were not on the checked process PATH. configs/environment.json
now records their homes, and source discovery accepts explicit arguments, named
environment variables or those configured paths. A global PATH edit or duplicate
installation is unnecessary. Discovery code and its new tests are generated;
only their syntax has been checked in the file-only scope.

Before the file-only instruction, all15 main Scala files compiled against the
installed distribution and were packaged without SBT resolution. The report is
[the successful offline build](artifacts/scala-build/20261109T082431Z-6ca44eba/build_report.json).
Later CSV quoting/deletion-flag source edits have not been recompiled. ScalaTest,
Spark runtime, Parquet, full32M processing and streaming remain unexecuted.

A later package-metadata observation found torch2.14.1+cu132,NumPy2.2.6,
scikit-learn1.7.2,PyArrow22.0.0,Transformers4.57.3,Accelerate1.11.0,
tokenizers0.22.1,safetensors0.6.2 and huggingface-hub0.36.0. Datasets,
Sentence Transformers and JupyterLab were absent in that snapshot. This was
metadata evidence, not fresh native imports or GPU operations. It supersedes
the package listing in section13 as current metadata; the successful cu130 CUDA
report remains historical evidence for its exact earlier installation.

Recheck the current cu132 build and changed scientific stack before training.
No manually supplied model weights were found in the scoped model/cache paths;
no weights were downloaded. The last resource snapshot was about49.147GiB free
disk and less than2GiB available RAM, below the default Spark headroom guard.
These values are not current readiness guarantees. The user's current scope is
file generation with static validation; new runtime probes are deferred.

## 15. Through-Phase11 source-delivery observation

10 November2026,Asia/Calcutta. Metadata only: selected root Python3.11.9;
Node24.22.2 at `C:\Program Files\nodejs\node.exe`; user-installed frontend
package-lock/node_modules with TypeScript5.9.3 and Next16.4.5 were observed.
Direct frontend pins match installed metadata and the root lock entries.
Static TypeScript checking passed; build/browser/service execution did not run.

Root Python metadata still lacks fastapi,starlette,uvicorn,SQLAlchemy,psycopg,
pgvector,alembic,pydantic,pydantic-settings,pwdlib and python-multipart.
Sentence Transformers5.1.2 is now present; faster-whisper remains absent. No
backend/NLP imports,database connection,CUDA operation,installation or model
inference was performed for this snapshot. Previous available RAM/disk and
cu130 tensor checks are historical, not a readiness guarantee for this stack.

Follow PREREQUISITES.md section12 for the manual-install/verification order and
documentation/phases9-11/RUNBOOK.md for source contracts. The user deferred
Phases12–13. Current-source static reports are recorded in
IMPLEMENTATION_STATUS.md; they do not establish runtime acceptance.
