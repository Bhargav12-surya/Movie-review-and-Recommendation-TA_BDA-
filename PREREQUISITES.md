# Prerequisites — Movie Review and Recommendation System

Updated: **9 November 2026, Asia/Calcutta**. Workspace: **D:\BDA_TA**.

This is a manual installation guide. The user downloads and installs software.
Project scripts do not install packages, resolve SBT dependencies, download models,
fetch datasets, change global Windows settings or upgrade existing installations.

The versions below are **documented installation candidates**. Published packages,
declared version requirements and official platform support were checked. They are
not a solved transitive lockfile or a claim that the complete stack has passed on
this laptop. After each manual installation, run its verification before starting
dependent implementation. Keep the historical audits intact; current execution
evidence belongs in IMPLEMENTATION_STATUS.md and generated reports.

## 1. Current environment and immediate readiness

**Latest correction, 9 November 2026:** Spark 4.3.0 with bundled Scala 2.13.18
and an SBT 1.10.7 launcher have now been found at the manually supplied paths
listed in section 11. Do not reinstall them because earlier snapshots say
"missing". A later metadata-only observation found torch2.14.1+cu132 and changed
scientific/NLP versions. The cu130 tensor results below belong to the earlier
installation. Current runtime compatibility remains to be rechecked by the user;
source generation does not supply that evidence.

The root .venv is an isolated **Python 3.11.9** environment. An earlier manual-install
recheck on9 November2026 found NumPy2.4.6,pandas2.3.3,scikit-learn1.9.1,
PyArrow26.0.1,PyYAML6.0.3,pytest9.2.0 and **torch2.14.1+cu130**. Six scientific/
test imports and pip check passed. Actual RTX5050 CUDA,FP16 and BF16 tiny tensor
operations passed. No model/backward/training check has run. This supersedes
the earlier pip-only snapshot; no installation was performed by this work.
See [the actual report](artifacts/environment/manual-install-recheck-20261109-1c28488e.json).

Some earlier analysis/test candidate pins below differ from these new installs.
At that earlier check the NLP manifest targeted cu132 while the detected build was cu130.
Both CUDA options are published for Windows PyTorch2.14.1 in the
[official version guide](https://pytorch.org/get-started/previous-versions/).
Do not replace working packages or force downgrades just to apply an older
candidate list. Reconcile the future manual install with the observed working
environment first. The complete future dependency set is not a tested lock.

| Component | Observed state | Action |
|---|---|---|
| Python | 3.11.9 x64 at C:\Users\bharg\AppData\Local\Programs\Python\Python311\python.exe | Keep; use the root .venv explicitly |
| Root project .venv | Python3.11.9; scientific/test packages now installed; Transformers/Datasets/backend still missing | Keep; six scientific/test imports verified |
| Python launcher | Bare py selects 3.14.6 | Do not use it to select this project's interpreter |
| Preserved temp/.venv | Python 3.12.10 | Preserve; do not reuse, clear or upgrade it |
| Java on PATH | Adoptium Temurin 21.0.12.1+1-LTS | Keep this installed JDK |
| JAVA_HOME | Latest diagnostic process matches the selected Adoptium JDK21 | Keep; earlier Coursier mismatch was a historical snapshot |
| NVIDIA | RTX 5050 Laptop,8151 MiB,capability 12.0; driver 621.01 | Keep driver; no automatic driver/CUDA change |
| Git / VS Code | Previously observed 2.56.0.windows.4 / 1.143.1 | Keep; no duplicate installation |
| SBT / Spark | Not found in checked PATH/install locations | Manual Phase 2 prerequisite |
| PyTorch CUDA | 2.14.1+cu130; sm_120 and tiny CUDA/FP16/BF16 checks pass | Reuse validated build; reconcile the cu132 candidate before any manual replacement |
| PostgreSQL / pgvector | Server/extension not verified | Manual Phase 9 prerequisite |
| Node / npm | Not found in checked locations | Deferred to Phase 10 |
| Docker / WSL | Not prepared in the audit | Optional alternative deployment, not a prerequisite |

The separate Python 3.14 installation's CPU-only torch import failed in the earlier
audit. That does not establish that Python 3.14 is universally incompatible; it
establishes that the inspected installation is unsuitable for this project's
selected Python 3.11/CUDA environment.

The available Foundation checks and standard-library Phase 1 validators do not
require pandas, Spark, CUDA, PostgreSQL or Node. Missing later tools remain explicit
phase blockers. A passing Foundation profile does not certify the full application.

## 2. Mandatory software, exact versions and official sources

Keep already installed working tools. Install each missing component only when its
phase needs it. Choose storage locations explicitly; none are moved automatically.

| Software | Selected version | Needed by | Official download/source |
|---|---|---|---|
| Windows x64 | Existing Windows11 installation | All phases | Existing OS; [Microsoft Windows](https://www.microsoft.com/software-download/windows11) |
| Windows PowerShell | Existing Windows PowerShell 5.1 | Foundation/scripts | Built into Windows; [Microsoft documentation](https://learn.microsoft.com/powershell/scripting/windows-powershell/overview) |
| Python x64 | **3.11.9**, existing | Phase 0 onward | [Python 3.11.9 release](https://www.python.org/downloads/release/python-3119/) |
| JDK x64 | **Temurin 21.0.12.1+1**, existing | JVM checks/Phase 2 | [Adoptium JDK 21 releases](https://adoptium.net/temurin/releases/?version=21&os=windows&arch=x64&package=jdk) |
| Git | Existing **2.56.0.windows.4** | Source control | [Git for Windows](https://git-scm.com/download/win) |
| VS Code | Existing **1.143.1** | Development | [VS Code Windows](https://code.visualstudio.com/download) |
| SBT | **1.10.7** | Phase 2 builds | [Official release/MSI](https://github.com/sbt/sbt/releases/tag/v1.10.7), [installation guide](https://www.scala-sbt.org/1.x/docs/Installing-sbt-on-Windows.html) |
| Apache Spark | **4.3.0**, Scala 2.13 build | Phase 2 | [Apache downloads](https://spark.apache.org/downloads.html), [versioned documentation](https://spark.apache.org/docs/4.3.0/) |
| Scala compiler | **2.13.18**, managed by the approved SBT/Spark build | Phase 2 | [Scala 2.13.18 release](https://github.com/scala/scala/releases/tag/v2.13.18); no separate compiler installation needed |
| Hadoop client libraries | **3.5.0** in the inspected Spark 4.3.0 source baseline | Phase 2 | Supplied by Spark distribution/dependencies; [tagged Spark POM](https://raw.githubusercontent.com/apache/spark/v4.3.0/pom.xml) |
| PyTorch CUDA | **2.14.1+cu132**, CPython3.11 Windows x64 | Phase 3 | [Official wheel index](https://download.pytorch.org/whl/cu132/torch/), [published installation commands](https://pytorch.org/get-started/previous-versions/) |
| PostgreSQL x64 | **18.6** candidate | Phase 9 | [Official Windows installers](https://www.postgresql.org/download/windows/), [supported version table](https://www.postgresql.org/support/versioning/) |
| pgvector server extension | **0.8.7**, built for PostgreSQL 18 x64 | Phase 9 | [Official tagged source](https://github.com/pgvector/pgvector/tree/v0.8.7), [Windows instructions](https://raw.githubusercontent.com/pgvector/pgvector/v0.8.7/README.md) |
| Node.js x64 | **24.22.2 LTS** | Phase 10 | [Official release/MSI and checksums](https://nodejs.org/download/release/v24.22.2/) |
| npm | Version bundled with the selected Node 24.22.2 installer | Phase 10 | Same Node installer; record npm --version after installation; no separate npm upgrade |

Spark 4.3.0's tagged POM specifies Scala 2.13.18 and Hadoop 3.5.0. Inspect the actual
downloaded distribution's RELEASE/jars before pinning its final build metadata.
Match Spark versions across distribution and Scala dependencies. Do not mix the
legacy Spark 3.5.7/Scala 2.12.18 project with this build. [Spark build metadata](https://raw.githubusercontent.com/apache/spark/v4.3.0/pom.xml)

The exact Windows torch wheel listing includes
torch-2.14.1+cu132-cp311-cp311-win_amd64.whl. The tagged release matrix lists
CUDA 13.2.1 Windows Blackwell12.0 support. This establishes an available candidate;
a real local CUDA tensor operation remains mandatory. Install only torch for this
text project. [Tagged PyTorch compatibility matrix](https://raw.githubusercontent.com/pytorch/pytorch/v2.14.1/RELEASE.md)

## 3. Optional and conditional software

| Item | Status and version policy | Official source |
|---|---|---|
| Visual Studio C++ Build Tools | Conditional requirement if native pgvector compilation is selected; x64 MSVC/nmake plus matching PostgreSQL 18 headers. Select and record the exact supported toolset/build before installation | [Microsoft C++ command-line tools](https://learn.microsoft.com/cpp/build/building-on-the-command-line?view=msvc-170), [Build Tools downloads](https://visualstudio.microsoft.com/downloads/) |
| Docker Desktop / WSL | Optional alternative for PostgreSQL+pgvector; no version selected or installation required now. Exact image/version and resource cost need approval before adopting this route | [Docker Windows](https://docs.docker.com/desktop/setup/install/windows-install/), [Microsoft WSL](https://learn.microsoft.com/windows/wsl/install) |
| PowerShell 7 | Optional; scripts are compatible with the built-in PowerShell 5.1. Avoid duplicate installation unless needed | [Microsoft PowerShell releases](https://github.com/PowerShell/PowerShell/releases) |
| Full CUDA Toolkit | Not required for ordinary prebuilt torch wheels. Select an exact Toolkit only if an approved extension actually needs compilation | [NVIDIA Toolkit](https://developer.nvidia.com/cuda-downloads) |
| Hadoop Windows native binaries | Conditional on a reproduced local Spark filesystem/Parquet failure; no binary version or download is approved now | [Apache Hadoop 3.5.0 source/build instructions](https://github.com/apache/hadoop/blob/rel/release-3.5.0/BUILDING.txt) |
| BERTopic | Candidate **0.17.3**, Phase 5 exploration; inspect transitive Windows wheels and memory before installation | [Official PyPI release](https://pypi.org/project/bertopic/0.17.3/) |
| Offline speech | faster-whisper candidate **1.2.1**, Phase 11; CPU-first. Its CTranslate2/CUDA/cuDNN compatibility is separate from torch | [Official PyPI release](https://pypi.org/project/faster-whisper/1.2.1/), [project runtime requirements](https://github.com/SYSTRAN/faster-whisper) |
| PySpark | Optional **4.3.0** for a justified notebook exercise; Scala remains the actual BDA implementation | [Official PyPI release](https://pypi.org/project/pyspark/4.3.0/) |

No mandatory Postman, second database GUI, Conda, standalone Scala compiler,
cloud GPU, paid AI API or archive utility is introduced. Windows tar can extract
the Spark .tgz after manual download; a preferred archive GUI is the user's choice.

### Windows Hadoop decision

Do not automatically fetch community winutils.exe or hadoop.dll. A generic
"Hadoop 3.x" match is insufficient, and the old suggestion of Hadoop 3.3.6 does not
match the inspected Hadoop 3.5.0 baseline.

First install the approved Spark distribution manually, then run a tiny local
Scala filesystem/Parquet read/write test in Phase 2 after build dependencies are
authorized. Record the exact error if it fails. Only then decide whether a trusted
matching native build is needed, verify its provenance/checksum/architecture,
and obtain approval for that dependency. Missing Hadoop native warnings alone
do not prove that every required local operation is broken.

## 4. Python and frontend dependency candidates

Every listed version is a direct candidate. Transitive constraints, Windows
wheels, imports and representative operations must pass after manual installation
before recording a tested lock. Do not bulk-install every phase.

### Phase 0/1: no third-party dependency for current validators

The current inventory/CSV/JSON/mapping validation and unittest suites use Python's
standard library. requirements/phase1.txt records this. Run the root interpreter
directly. requirements-dev.txt offers pytest 8.4.2 as an optional runner.

Earlier EDA/classical-baseline candidates in requirements/analysis.txt follow.
They differ from the current manual installs in section1; preserve the working
environment and reconcile constraints before using these older pins.

| Package | Pin | Official release |
|---|---|---|
| numpy | 2.2.6 | [PyPI](https://pypi.org/project/numpy/2.2.6/) |
| pandas | 2.3.3 | [PyPI](https://pypi.org/project/pandas/2.3.3/) |
| scikit-learn | 1.7.2 | [PyPI](https://pypi.org/project/scikit-learn/1.7.2/) |
| pyarrow | 22.0.0 | [PyPI](https://pypi.org/project/pyarrow/22.0.0/) |
| PyYAML | 6.0.3 | [PyPI](https://pypi.org/project/PyYAML/6.0.3/) |
| matplotlib | 3.10.7 | [PyPI](https://pypi.org/project/matplotlib/3.10.7/) |
| seaborn | 0.13.2 | [PyPI](https://pypi.org/project/seaborn/0.13.2/) |
| python-dotenv | 1.2.1 | [PyPI](https://pypi.org/project/python-dotenv/1.2.1/) |
| pytest | 8.4.2 | [PyPI](https://pypi.org/project/pytest/8.4.2/) |
| httpx | 0.28.1, later HTTP tests | [PyPI](https://pypi.org/project/httpx/0.28.1/) |
| JupyterLab | 4.6.4, notebooks on demand | [PyPI](https://pypi.org/project/jupyterlab/4.6.4/) |

These earlier candidate commands are retained for a separately reviewed fresh
environment. They are not the next step for this already prepared environment:

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements\analysis.txt
.\.venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
~~~

Do not run these automatically. Current standard-library tests need neither command.

### Phase 3–6: NLP candidates

Install torch separately using its official CUDA index before this group.

| Package | Pin | Official release |
|---|---|---|
| transformers | 4.57.3 | [PyPI](https://pypi.org/project/transformers/4.57.3/) |
| datasets | 4.4.1 | [PyPI](https://pypi.org/project/datasets/4.4.1/) |
| accelerate | 1.11.0 | [PyPI](https://pypi.org/project/accelerate/1.11.0/) |
| sentence-transformers | 5.1.2 | [PyPI](https://pypi.org/project/sentence-transformers/5.1.2/) |
| tokenizers | 0.22.1 | [PyPI](https://pypi.org/project/tokenizers/0.22.1/) |
| safetensors | 0.6.2 | [PyPI](https://pypi.org/project/safetensors/0.6.2/) |
| huggingface-hub | 0.36.0 | [PyPI](https://pypi.org/project/huggingface-hub/0.36.0/) |
| sentencepiece | 0.2.1 | [PyPI](https://pypi.org/project/sentencepiece/0.2.1/) |
| evaluate | 0.4.6 | [PyPI](https://pypi.org/project/evaluate/0.4.6/) |
| seqeval | 1.2.2, Phase 4 span evaluation | [PyPI](https://pypi.org/project/seqeval/1.2.2/) |
| rouge-score | 0.1.2, Phase 5 summaries | [PyPI](https://pypi.org/project/rouge-score/0.1.2/) |
| bert-score | 0.3.13, Phase 5 reference evaluation | [PyPI](https://pypi.org/project/bert-score/0.3.13/) |

Sentence Transformers 5.1.2 declares Transformers>=4.41,<5. Transformers 4.57.3
declares Hub>=0.34,<1 and tokenizers>=0.22,<=0.23. Datasets 4.4.1 requires
PyArrow>=21 and fsspec<=2025.10.0; retain that fsspec constraint during resolution.
These declared ranges support the proposed direct pins; they do not replace an
installed resolver/import test. [Sentence Transformers metadata](https://raw.githubusercontent.com/UKPLab/sentence-transformers/v5.1.2/pyproject.toml), [Transformers metadata](https://raw.githubusercontent.com/huggingface/transformers/v4.57.3/setup.py), [Datasets metadata](https://raw.githubusercontent.com/huggingface/datasets/4.4.1/setup.py)

The precise manual torch command for the selected candidate is:

~~~powershell
.\.venv\Scripts\python.exe -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu132
~~~

The installed version should identify the CUDA build, such as 2.14.1+cu132.
The existing2.14.1+cu130 build now passes local tensor/precision checks. The
command above is a fresh-install candidate, not a request to replace that build.
No torchvision or torchaudio is needed. No model checkpoint is downloaded by
this guide or by an environment verification command.

The candidate manifests requirements/requirements-nlp.txt and
requirements/requirements-backend.txt now record these direct pins. Their
presence is not installation approval or a runtime-tested lockfile. Use the
NLP/backend groups only at their respective approved phase after manual
prerequisite verification and data/model decisions.

### Phase 9: backend and database adapters

| Package | Pin | Official release |
|---|---|---|
| fastapi | 0.141.1 | [PyPI](https://pypi.org/project/fastapi/0.141.1/) |
| starlette | 1.3.1 | [PyPI](https://pypi.org/project/starlette/1.3.1/) |
| uvicorn | 0.35.0 | [PyPI](https://pypi.org/project/uvicorn/0.35.0/) |
| SQLAlchemy | 2.0.44 | [PyPI](https://pypi.org/project/SQLAlchemy/2.0.44/) |
| psycopg[binary] | 3.2.12 | [PyPI](https://pypi.org/project/psycopg/3.2.12/) |
| pgvector, Python adapter | 0.4.1 | [PyPI](https://pypi.org/project/pgvector/0.4.1/) |
| alembic | 1.17.1 | [PyPI](https://pypi.org/project/alembic/1.17.1/) |
| pydantic | 2.12.4 | [PyPI](https://pypi.org/project/pydantic/2.12.4/) |
| pydantic-settings | 2.12.0 | [PyPI](https://pypi.org/project/pydantic-settings/2.12.0/) |
| PyJWT | 2.10.1 | [PyPI](https://pypi.org/project/PyJWT/2.10.1/) |
| pwdlib[argon2] | 0.3.0 | [PyPI](https://pypi.org/project/pwdlib/0.3.0/) |
| python-multipart | 0.0.20 | [PyPI](https://pypi.org/project/python-multipart/0.0.20/) |

The old FastAPI 0.115.14 restriction excluded later Starlette multipart fixes.
The proposed newer FastAPI/Starlette pair needs complete resolution and endpoint
tests in Phase 9. Starlette 1.3.1 addresses the documented form-parsing issue;
httpx 0.28.1 TestClient support has a deprecation path. Reassess test dependencies
before implementation instead of silently upgrading shared packages.
[FastAPI dependency metadata](https://raw.githubusercontent.com/fastapi/fastapi/0.141.1/pyproject.toml),
[Starlette advisory](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq),
[TestClient implementation](https://raw.githubusercontent.com/Kludex/starlette/1.3.1/starlette/testclient.py)

The Python pgvector package does not install the PostgreSQL server extension.
Both components are needed in Phase 9.

### Phase 10: frontend candidates

| Package | Exact candidate | Official source |
|---|---|---|
| next | 16.4.5 | [Versioned package](https://www.npmjs.com/package/next/v/16.4.5) |
| react / react-dom | 19.3.0 each | [React versions](https://react.dev/versions), [React package](https://www.npmjs.com/package/react/v/19.3.0), [React DOM package](https://www.npmjs.com/package/react-dom/v/19.3.0) |
| typescript | 5.9.3 | [Versioned package](https://www.npmjs.com/package/typescript/v/5.9.3) |
| tailwindcss / @tailwindcss/postcss | 4.1.17 each | [Tailwind](https://www.npmjs.com/package/tailwindcss/v/4.1.17), [PostCSS plugin](https://www.npmjs.com/package/@tailwindcss/postcss/v/4.1.17) |
| postcss | 8.5.23 | [Versioned package](https://www.npmjs.com/package/postcss/v/8.5.23) |
| recharts | 3.3.0 | [Versioned package](https://www.npmjs.com/package/recharts/v/3.3.0) |
| react-is | 19.3.0, aligned with React | [Versioned package](https://www.npmjs.com/package/react-is/v/19.3.0) |

Next16.4.5 declares Node>=20.9 and accepts React19; the selected Node 24 LTS
candidate meets that declaration. Exact @types packages and test tools are
resolved with the actual Phase 10 application and lockfile. Install Node/npm and
generate package.json/package-lock only at that phase. No frontend dependency
installation or scaffolding command is part of the current foundation.
[Next manifest](https://raw.githubusercontent.com/vercel/next.js/v16.4.5/packages/next/package.json)

## 5. Installation order and manual instructions

1. **Verify the existing Python/JDK and resources.** Run the Foundation profile
   below. Root .venv is already present; do not recreate it. Confirm free space
   and available memory before any substantial installation/job.
2. **Run standard-library Phase 1 validators/tests.** No package installation is
   needed. Human labels, consent, source provenance and mapping decisions remain
   separate gates even when raw MovieLens/IMDb files exist.
3. **Add analysis/test/notebook packages only when needed.** The user chooses
   and runs the selected manual commands. Verify pip check, imports and a small
   representative operation; record final resolved versions.
4. **Prepare SBT/Spark before Phase 2.** Install the SBT 1.10.7 Windows MSI and
   manually download the Spark 4.3.0 distribution from Apache. Verify its
   published archive checksum/signature. Extract to a user-approved location
   without spaces, such as C:\spark\spark-4.3.0-bin-hadoop3. Do not move existing
   data or change storage automatically. SBT manages Scala; no duplicate
   standalone compiler is required.
5. **Authorize dependency resolution separately.** Merely invoking SBT/Scala
   can download launcher/compiler/dependency files. First verify local installer
   metadata and launcher location. Once the user approves those downloads,
   resolve the pinned Phase 2 build and run a tiny Scala/Parquet test. Save
   execution evidence and decide whether Windows native Hadoop support is needed.
6. **Verify the existing CUDA torch wheel before Phase 3.** Root Python3.11 now
   has2.14.1+cu130; the cu132 candidate remains a separate manual choice. Run the tiny CUDA test
   before any permitted checkpoint download or training. Keep the working
   NVIDIA driver unless actual evidence requires an approved change.
7. **Add NLP groups by task.** Review licenses and local artifact locations
   separately before the user supplies/downloads pretrained weights. Do not
   download datasets or weights as a side effect of verification.
8. **Prepare PostgreSQL 18.6+pgvector0.8.7 for Phase 9.** Use the official Windows
   installer, a securely stored administrator password and an explicit data
   location/port 5432. Do not assume the installer modifies PATH. The application
   later uses a dedicated limited role, not the postgres superuser.
9. **Select native pgvector or an approved alternative.** For native Windows,
   install the necessary x64 C++ tools manually; download the tagged pgvector
   source and follow its Windows instructions using PostgreSQL 18 headers.
   Run nmake only from the approved x64 tools prompt after source/toolchain review.
   Enabling vector in the selected application database is a Phase 9 setup action,
   not a read-only health check. Docker/WSL remains an alternative requiring a
   separate deployment/resource decision.
10. **Install Node 24.22.2 in Phase 10.** Use the official Windows x64 MSI and its
    checksums. Record bundled npm version. Pin package.json and commit a reviewed
    lockfile after authorized installation; never commit node_modules.
11. **Add optional speech in Phase 11.** Start CPU-only with approved cached
    weights; validate decoding/runtime dependencies and keep text input.

If a missing installation blocks a required phase, stop at that gate and report
the exact item. Do not fill the gap by changing stacks or fabricating outputs.

## 6. Environment variables and PATH

Current project selection is recorded in configs/environment.json. Verification
uses the chosen JDK directly; it does not modify global JAVA_HOME, PATH or drivers.

Selected JDK:

~~~text
C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot
~~~

Verify it directly:

~~~powershell
& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\java.exe' -version
& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\javac.exe' -version
~~~

For a manually approved SBT/Spark command, select the JDK in that terminal only:

~~~powershell
$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'
$projectJavaBin = Join-Path $env:JAVA_HOME 'bin'
if (($env:Path -split ';') -notcontains $projectJavaBin) {
    $env:Path = $projectJavaBin + ';' + $env:Path
}
~~~

This affects that terminal and its children. It does not call setx or edit
Windows User/System environment settings. A plus sign in an existing JDK path
is not itself proof of failure; the observed problem is inconsistent selection.

After manually extracting Spark to the chosen location, the user can set
SPARK_HOME in the approved terminal and invoke its absolute .cmd path:

~~~powershell
$env:SPARK_HOME = 'C:\spark\spark-4.3.0-bin-hadoop3'
& (Join-Path $env:SPARK_HOME 'bin\spark-submit.cmd') --version
~~~

No HADOOP_HOME is required by this guide unless the conditional native-dependency
decision establishes a need. PYSPARK_PYTHON is relevant only for optional PySpark;
Scala jobs do not require a Python interpreter environment variable.

PostgreSQL and Node can be invoked through their installed absolute paths if
PATH discovery fails. Check actual paths instead of installing a second copy.

.env.example contains blank secret fields and local configuration. Copy it
manually only when needed. Keep .env private. Do not use a superuser connection
URL in the frontend, print credentials or dump the full environment. No TMDB
request or key is required for current validation work.

## 7. Verification commands and expected evidence

These commands inspect local software. No command below installs a package,
resolves an SBT build, downloads a model or starts the application.

### Python, configuration and resources

~~~powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.prefix != sys.base_prefix)"
.\.venv\Scripts\python.exe -m pip --version
.\.venv\Scripts\python.exe -m pip check
.\scripts\verify_environment.ps1 -Profile Foundation -Json
.\scripts\verify_environment.ps1 -Profile Data -Json
~~~

Expected: selected Python 3.11.9/root .venv, resource snapshots and truthful
pass/missing/deferred checks. An empty environment can pass pip check; that
does not mean the project packages or native/GPU libraries work.

After manually installing analysis packages:

~~~powershell
.\scripts\verify_environment.ps1 -Profile Data -CheckImports -Json
.\.venv\Scripts\python.exe -c "import numpy,pandas,sklearn,pyarrow,yaml; print(numpy.__version__,pandas.__version__,sklearn.__version__,pyarrow.__version__)"
~~~

### Java, Git, SBT and Spark

~~~powershell
Get-Command java,javac,git -ErrorAction SilentlyContinue
git --version
& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\java.exe' -version
& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\javac.exe' -version
Get-Command sbt -ErrorAction SilentlyContinue
.\scripts\verify_environment.ps1 -Profile Spark -Json
~~~

SBT launcher discovery or an MSI version is installation evidence only. Do not
run sbt --version, scala, sbt compile or a dependency command merely as an
unapproved inspection: the launcher may resolve/download software. Compilation
and a real Spark job are deferred until manual dependency preparation is
complete. Spark --version uses an already supplied distribution; no fallback
download/resolution is permitted.

### NVIDIA and CUDA torch

~~~powershell
nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv,noheader
.\scripts\verify_environment.ps1 -Profile Nlp -CheckCuda -Json
~~~

Run the second command after manual CUDA torch installation. It must show the
actual torch/runtime build, device/capability, architectures, a finite CUDA
matrix operation and memory. Precision checks establish local FP16/BF16
support; metadata alone does not. If torch is missing or import fails, the
result must remain missing/failed.

nvidia-smi's CUDA UMD13.5 is a driver capability, not torch.version.cuda and
not evidence of an installed full Toolkit. Never infer that torch must use
exactly 13.5. Verify capability 12.0 and an executed kernel for this GPU.
[NVIDIA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/)

### PostgreSQL and pgvector

After manual installation, substitute the actual installation path and
the dedicated application role/database created in the approved Phase 9 setup:

~~~powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' --version
& 'C:\Program Files\PostgreSQL\18\bin\pg_config.exe' --version
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -X -h 127.0.0.1 -U movie_app -d movie_intelligence -c "SELECT version();"
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -X -h 127.0.0.1 -U movie_app -d movie_intelligence -c "SELECT extversion FROM pg_extension WHERE extname='vector';"
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -X -h 127.0.0.1 -U movie_app -d movie_intelligence -c "SELECT '[1,2,3]'::vector <-> '[3,2,1]'::vector;"
~~~

The final query tests a vector expression without creating/dropping a table.
A TCP listener alone does not prove server identity, credentials or extension
availability. Current health scripts do not create databases or migrations.

### Node/npm and services

Only after Phase 10 manual installation:

~~~powershell
node --version
npm --version
.\scripts\verify_environment.ps1 -Profile Frontend -Json
~~~

Expected Node v24.22.2; record the bundled npm version. Frontend package imports,
TypeScript checks and browser tests remain Phase 10 work.

For already running services:

~~~powershell
.\scripts\check_health.ps1 -Json
.\scripts\check_health.ps1 -CheckDatabase -DatabaseName movie_intelligence -DatabaseUser movie_app -Json
~~~

The database option uses noninteractive read-only SQL and needs an already
configured credential mechanism. Do not put a password in a command argument.
No services are started. An unavailable/unverified report is expected before
backend/frontend/database implementation.

Optional reports use -OutputPath with a **new file** in an existing workspace
directory. Protected paths, existing files and raw datasets are rejected.
Keep actual JSON reports as evidence; do not claim that listing a verification
command means it passed.

## 8. Compatibility notes and known issues

| Symptom / constraint | Required response |
|---|---|
| Wrong interpreter or root packages absent | Invoke .venv\Scripts\python.exe explicitly; inspect sys.executable. Never clear/reuse temp/.venv or repair global Python automatically |
| Global JAVA_HOME differs from selected JDK | Use project-scoped configuration/child-process selection; report mismatch and verify the chosen java/javac |
| Spark/Scala versions differ | Use Spark 4.3.0 with Scala 2.13.18 and the inspected matching distribution; do not mix legacy2.12 artifacts |
| winutils/Hadoop native warning | Reproduce the failing required filesystem operation first; review matching Hadoop 3.5.0 provenance before approving native binaries |
| CPU torch or no sm_120 kernel | Verify selected interpreter/build and actual CUDA kernel. Use the official candidate wheel; do not update drivers blindly |
| torch imports but CUDA is false | Record torch.version.cuda, device architecture, driver and the actual error; no training until a real tensor test passes |
| NumPy/native-extension import failure | Check wheel/interpreter/ABI in the isolated environment; pip check alone is insufficient. Do not repair unrelated shared runtimes |
| pgvector Python package exists but SQL type fails | Install/enable the matching server extension through approved Phase 9 setup; adapter and extension are separate |
| pgvector native build fails | Verify x64 MSVC/nmake, PG18 headers/import libraries and the tagged source; agree an alternative before adding Docker/WSL |
| DataLoader worker spawn/hang | Start num_workers=0 and use a proper main guard before increasing workers |
| Memory/VRAM pressure | Recheck current available resources; separate Spark, training and demonstration modes; reduce approved micro-batches |
| No permitted data/labels/model artifacts | Run validators/report blockers; do not fabricate labels, predictions or checkpoints |

The installed driver should remain unless a reproduced incompatibility requires
an approved update. A full Toolkit, cloud GPU and simultaneous large models are
not part of the core setup.

## 9. Storage, memory and offline operation

The latest parent-session sample was approximately **53.18 GiB free on D:** and
**1.89 GiB available RAM**. These are changing point-in-time observations. Obtain
new measurements from verify_environment.ps1 before every substantial operation.

Keep a practical **20 GiB D: reserve**. Budget the archive plus extracted data,
processed copies, one isolated environment, torch runtime, limited approved
checkpoints, dependency caches and Spark scratch space. Torch is part of the
venv footprint; do not count it twice as a separate full environment. Native
C++ Build Tools and optional Docker images can add substantial disk usage.

Exact installation footprints are determined from the chosen packages/installers
before manual installation. The existing resource snapshots do not guarantee
that every workload fits. Do not move data/caches to C: or E: or delete historical
environments to recover space automatically.

Run one substantial GPU model at a time. Separate large Spark jobs, Transformer
training and full application demonstration. Cache approved weights, tokenizers,
metadata and permitted artwork before the offline rehearsal; verification must
not trigger downloads. Core inference requires no paid API.

## 10. Installation completion checklist and hand-off

- [ ] Confirm explicit root Python 3.11.9 and preserve legacy runtimes.
- [ ] Confirm selected project JDK 21 and document global JAVA_HOME mismatch.
- [ ] Run Foundation/Data reports; record current free RAM/disk.
- [ ] Manually add only packages needed for the next authorized phase.
- [ ] Verify pip check plus required native imports/functional operations.
- [ ] Manually prepare SBT 1.10.7/Spark 4.3.0 and approve dependency resolution.
- [ ] Prove Scala 2.13.18/Parquet operation and decide native Windows needs.
- [x] Root torch2.14.1+cu130 detected; actual CUDA/FP16/BF16 tensor checks pass. Model/backward/resume checks remain separate.
- [ ] Review approved model licenses/cache budget before any weight download.
- [ ] Manually prepare PostgreSQL 18.6 and matching pgvector0.8.7 for Phase 9.
- [ ] Prepare Node 24.22.2/npm and the actual frontend lockfile in Phase 10.
- [ ] Reinspect after each installation and update IMPLEMENTATION_STATUS.md.
- [ ] Start dependent execution only after its relevant gate passes.

The user performs all installations. Ordinary authorized source edits/tests
continue within the current phase; missing later prerequisites do not justify
skipping phase gates or claiming the complete application works.

## 11. Manual-install follow-up and next verification

Observed9 November2026,Asia/Calcutta. Do not install duplicate Spark/SBT tools:

| Existing tool | Project setting | Required later check |
|---|---|---|
| JDK21.0.12.1+1 | C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot | Explicit java/javac version and selected child JAVA_HOME |
| Spark4.3.0/Hadoop3.5.0/Scala2.13.18 | spark.home=C:/spark/spark-4.3.0-bin-hadoop3 | Final-source offline build, real Parquet/runtime smoke and full batch reconciliation |
| SBT1.10.7 launcher | sbt.home=C:/Program Files (x86)/sbt | Boot/build dependency resolution is a separate manual acquisition/approval step |

Those homes are recorded in configs/environment.json. Discovery order is an
explicit command argument, then its named environment variable, then project
configuration. PATH need not be changed to use the project scripts. A standalone
Scala installation is unnecessary when the matching bundled compiler suffices.
SBT presence is not proof of cached ScalaTest dependencies or an executed build.

The latest metadata observation shows torch2.14.1+cu132 rather than the earlier
tested cu130 build, plus changed scientific package versions and newly present
Transformers4.57.3. See ENVIRONMENT_AUDIT.md section14 for the full scoped list.
Keep the user's requirements/requirements-nlp.txt unchanged; do not force older
candidate versions over the manual installation. Requirements remain a declared
plan, not a tested lock. Datasets,Sentence Transformers and JupyterLab were still
missing in that snapshot. Install only the approved next-phase subset manually
after reviewing its resolution; no install command is executed by this handoff.

Later verification, from the repository root:

~~~powershell
.\scripts\verify_environment.ps1 -Profile Foundation -Json
.\scripts\verify_environment.ps1 -Profile Spark -Json
.\scripts\run_spark_jobs.ps1 -Job preflight -Json
.\.venv\Scripts\python.exe -m pip check
~~~

Use the explicit interpreter and actual CUDA/AMP verification documented above
for the changed cu132 build. These commands are future actions, not checks run
in the current file-generation scope. Source-only syntax validation does not
certify native package ABI, CUDA kernels, checkpoint resume or model quality.
