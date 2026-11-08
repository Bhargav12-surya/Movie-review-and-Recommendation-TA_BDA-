# Prerequisites — Movie Review & Recommendation System

**Audit date:** 8 November 2026, Asia/Calcutta  
**Workspace:** `D:\BDA_TA`  
**Hardware:** Intel Core 7 240H · 16 GB RAM · NVIDIA RTX 5050 (8 GB VRAM, sm_120) · Windows 11

> [!IMPORTANT]
> This document lists every software prerequisite, its exact compatible version, official download link, environment configuration, and verification command. **No software has been installed, upgraded, or downloaded by this audit.** The user will manually install each item in the stated order.

---

## Table of Contents

1. [Current Environment Summary](#1-current-environment-summary)
2. [Mandatory Software — Installation Order](#2-mandatory-software--installation-order)
3. [Optional Software](#3-optional-software)
4. [Python Package Dependencies](#4-python-package-dependencies)
5. [Environment Variable Configuration](#5-environment-variable-configuration)
6. [Verification Commands](#6-verification-commands)
7. [Compatibility Notes](#7-compatibility-notes)
8. [Known Issues and Solutions](#8-known-issues-and-solutions)
9. [Disk Space Budget](#9-disk-space-budget)
10. [Installation Quick Reference](#10-installation-quick-reference)

---

## 1. Current Environment Summary

### Already Installed ✅

| Software | Version | Location |
|---|---|---|
| **Python** | 3.11.9 (64-bit) | `C:\Users\bharg\AppData\Local\Programs\Python\Python311\python.exe` |
| **pip** | 24.0 | Bundled with Python 3.11 |
| **JDK** | Temurin 21.0.12.1+1-LTS | `C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot` |
| **javac** | 21.0.12.1 | Same Adoptium installation |
| **Git** | 2.56.0.windows.4 | `C:\Program Files\Git\cmd\git.exe` |
| **NVIDIA Driver** | 621.01 (CUDA UMD 13.5) | System-managed |
| **GPU** | RTX 5050 Laptop, 8151 MiB VRAM, Compute 12.0 | Hardware |
| **VS Code** | 1.143.1 (x64) | Installed |
| **NumPy** | 2.4.6 | Global Python 3.11 |
| **pandas** | 3.1.0 | Global Python 3.11 |
| **scikit-learn** | 1.9.1 | Global Python 3.11 |
| **Pydantic** | 2.14.2 | Global Python 3.11 |
| **matplotlib** | 3.11.2 | Global Python 3.11 |
| **seaborn** | 0.13.2 | Global Python 3.11 |

### Not Installed / Not on PATH ❌

| Software | Status |
|---|---|
| **Node.js / npm** | Not found |
| **SBT** | Not found |
| **Apache Spark distribution** | Not found; `SPARK_HOME` unset |
| **PostgreSQL** | Not found; no service detected |
| **pgvector** | No PostgreSQL to host it |
| **PyTorch** | Not in Python 3.11 |
| **Transformers / Datasets / Accelerate** | Not installed |
| **Sentence Transformers** | Not installed |
| **FastAPI / Uvicorn / SQLAlchemy** | Not installed |
| **PySpark** | Not installed |
| **CUDA Toolkit (nvcc)** | Not on PATH; `CUDA_PATH` unset |
| **scalac** | Not on PATH (Scala 3 wrapper exists but not 2.13 compiler) |

### Needs Reconfiguration ⚠️

| Issue | Detail |
|---|---|
| **JAVA_HOME mismatch** | Points to Coursier-cached `jdk-21.0.12+8` with URL-encoded path chars; PATH `java` points to properly installed `jdk-21.0.12.101-hotspot`. Must be reconciled. |
| **Python `py` launcher** | Defaults to Python 3.14.6; must not be used for this project |
| **Preserved `temp/.venv`** | Uses Python 3.12.10; keep preserved, do not reuse |

---

## 2. Mandatory Software — Installation Order

Install in the following sequence. Each item lists its phase dependency.

---

### Step 1: Reconcile JAVA_HOME (Phase 0)

**No download needed** — JDK 21 is already installed. Fix the environment variable only.

**Action:** Set `JAVA_HOME` to the properly installed Adoptium JDK path:

```
JAVA_HOME = C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot
```

See [Section 5](#5-environment-variable-configuration) for how to set this.

**Verification:**
```powershell
java -version
javac -version
echo $env:JAVA_HOME
```
All three should show the **21.0.12.1** Temurin installation.

---

### Step 2: Create Python 3.11 Virtual Environment (Phase 0)

**No download needed** — Python 3.11.9 is already installed.

**Action:** Create a new isolated virtual environment at the project root:
```powershell
& "C:\Users\bharg\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv
```

**Activation:**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Verification:**
```powershell
python --version           # Should show 3.11.9
python -c "import sys; print(sys.executable)"   # Should show D:\BDA_TA\.venv\Scripts\python.exe
pip --version
```

> [!WARNING]
> Do not run `venv --clear` against the existing `temp/.venv` directory. Create `.venv` at the project root only.

---

### Step 3: SBT — Scala Build Tool (Phase 2)

| Property | Value |
|---|---|
| **Required version** | 1.10.7 (pinned in legacy `project/build.properties`) |
| **Exact download** | Windows `.msi` installer |
| **Official page** | https://www.scala-sbt.org/download.html |
| **Direct download** | https://github.com/sbt/sbt/releases/download/v1.10.7/sbt-1.10.7.msi |
| **Size** | ~130 MB installer |
| **License** | Apache 2.0 |

**Installation notes:**
- Run the `.msi` installer; it adds `sbt` to PATH automatically.
- SBT will manage the Scala 2.13 compiler internally — you do not need a separate `scalac` installation.
- SBT requires JDK; it will use the corrected `JAVA_HOME` from Step 1.

**Verification:**
```powershell
sbt --version
sbt "print scalaVersion"    # Run inside the scala project directory after build.sbt is created
```

---

### Step 4: Apache Spark 4.3.0 Distribution (Phase 2)

| Property | Value |
|---|---|
| **Required version** | 4.3.0 pre-built for Apache Hadoop |
| **Official download page** | https://spark.apache.org/downloads.html |
| **Direct download** | Select: Spark 4.3.0 → Pre-built for Apache Hadoop → Mirror link (.tgz) |
| **Approximate size** | ~400 MB compressed; ~600 MB extracted |
| **License** | Apache 2.0 |
| **Compatibility** | Java 17/21/25, Scala 2.13, Python 3.11+ (documented in official overview) |

**Installation steps:**
1. Download the `.tgz` archive from the official mirror.
2. Extract using 7-Zip or similar to a path **without spaces**, e.g., `C:\spark\spark-4.3.0-bin-hadoop3`.
3. Set `SPARK_HOME` and add to PATH (see [Section 5](#5-environment-variable-configuration)).

**Official documentation:** https://spark.apache.org/docs/4.3.0/

**Verification:**
```powershell
spark-submit --version
spark-shell       # Should launch Scala REPL with Spark context
```

---

### Step 4a: Hadoop Windows Binaries — winutils.exe (Phase 2)

| Property | Value |
|---|---|
| **Required for** | Spark on Windows (filesystem operations) |
| **Source** | Community-maintained; no official Apache Windows binary |
| **Repository** | https://github.com/cdarlint/winutils |
| **Required files** | `winutils.exe`, `hadoop.dll` matching Hadoop 3.x |

**Installation steps:**
1. Create directory `C:\hadoop\bin` (no spaces in path).
2. Download `winutils.exe` and `hadoop.dll` from the repository's `hadoop-3.3.6/bin/` folder (or the latest 3.x matching Spark's bundled Hadoop).
3. Place both files in `C:\hadoop\bin`.
4. Set `HADOOP_HOME` and add to PATH (see [Section 5](#5-environment-variable-configuration)).

> [!NOTE]
> These are community-compiled binaries. Verify the source repository's provenance. The official Hadoop project does not distribute Windows `.exe` files.

**Verification:**
```powershell
winutils.exe -version
```

---

### Step 5: PyTorch with CUDA Support (Phase 3)

| Property | Value |
|---|---|
| **Required version** | ≥ 2.7.0 with CUDA ≥ 12.8 (must include `sm_120` for RTX 5050) |
| **Recommended** | Latest stable (currently ~2.15.x) with CUDA 13.2 index |
| **Official selector** | https://pytorch.org/get-started/locally/ |
| **Previous versions** | https://pytorch.org/get-started/previous-versions/ |
| **Release/CUDA matrix** | https://github.com/pytorch/pytorch/blob/main/RELEASE.md |
| **Approximate size** | ~2.5–3.5 GB (torch + CUDA runtime libraries) |
| **License** | BSD-3-Clause |

**Installation command** (run inside activated `.venv`):
```powershell
# Visit https://pytorch.org/get-started/locally/ and select:
#   Stable → Windows → Pip → Python → CUDA 13.x
# The generated command will be similar to:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu132
```

> [!IMPORTANT]
> **Before running this command:**
> 1. Activate the `.venv` from Step 2.
> 2. Verify the exact CUDA index URL from the official selector page at installation time.
> 3. The RTX 5050 (compute capability 12.0 / Blackwell) requires `sm_120` kernel support. Older CUDA 12.4 builds will **not** work.
> 4. A full CUDA Toolkit installation (`nvcc`) is **not required** for prebuilt PyTorch wheels.
> 5. `torchvision` and `torchaudio` are not strictly needed for this text-only project but are small relative to `torch`.

**Verification:**
```python
import torch
print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA version:", torch.version.cuda)
print("GPU:", torch.cuda.get_device_name(0))
print("Arch list:", torch.cuda.get_arch_list())  # Must contain sm_120
x = torch.randn(8, 8, device="cuda")
y = torch.randn(8, 8, device="cuda")
z = x @ y
print("CUDA tensor operation:", z.shape, z.device)
torch.cuda.synchronize()
print("Peak VRAM:", torch.cuda.max_memory_allocated() / 1024**2, "MiB")
```

---

### Step 6: PostgreSQL Server (Phase 0 preparation / Phase 9 use)

| Property | Value |
|---|---|
| **Required version** | PostgreSQL 17.x stable or 18.x (if GA and stable) |
| **Official download** | https://www.postgresql.org/download/windows/ |
| **Installer** | EDB Interactive Installer (includes pgAdmin + StackBuilder) |
| **Approximate size** | ~300 MB installer; ~200 MB installed |
| **License** | PostgreSQL License (permissive) |
| **Default port** | 5432 |

**Installation notes:**
- Use the EDB installer wizard.
- Set a **superuser password** during installation — record it securely.
- Keep the default port `5432` and locale.
- The installer adds `psql` and `pg_config` to PATH via its bin directory.
- pgAdmin (included) provides a GUI management tool.

**Verification:**
```powershell
psql --version
pg_config --version
# Test connection:
psql -U postgres -c "SELECT version();"
```

---

### Step 6a: pgvector Extension for PostgreSQL (Phase 9)

| Property | Value |
|---|---|
| **Required version** | 0.8.x (matching installed PostgreSQL major) |
| **Source** | https://github.com/pgvector/pgvector |
| **Build requirement** | Visual Studio C++ Build Tools with `nmake` |
| **License** | PostgreSQL License |

**Prerequisites for building pgvector:**
1. **Visual Studio Build Tools** with "Desktop development with C++" workload.
   - Download: https://visualstudio.microsoft.com/downloads/ → "Build Tools for Visual Studio"
   - Select the **"Desktop development with C++"** workload during installation.
   - Size: ~3–6 GB.

**Build and install steps** (from x64 Native Tools Command Prompt for VS, run as Administrator):
```cmd
set "PGROOT=C:\Program Files\PostgreSQL\17"
cd %TEMP%
git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
cd pgvector
nmake /F Makefile.win
nmake /F Makefile.win install
```

**Verification (in psql):**
```sql
CREATE EXTENSION vector;
SELECT extversion FROM pg_extension WHERE extname = 'vector';
-- Test round-trip:
CREATE TABLE test_vec (id serial PRIMARY KEY, v vector(3));
INSERT INTO test_vec (v) VALUES ('[1,2,3]');
SELECT * FROM test_vec ORDER BY v <-> '[3,2,1]' LIMIT 1;
DROP TABLE test_vec;
```

> [!NOTE]
> **Alternative:** If building from source is problematic, Docker can provide a pre-built pgvector image: `pgvector/pgvector:pg17`. This requires Docker Desktop (see [Optional Software](#3-optional-software)).

---

### Step 7: Node.js (Phase 10)

| Property | Value |
|---|---|
| **Required version** | Node.js 24.x LTS (currently 24.22.2) |
| **Official download** | https://nodejs.org/en/download/ |
| **Direct installer** | https://nodejs.org/dist/v24.22.2/node-v24.22.2-x64.msi |
| **Approximate size** | ~35 MB installer; ~80 MB installed |
| **License** | MIT |
| **npm** | Bundled with Node.js |

**Installation notes:**
- Use the `.msi` installer; it adds `node` and `npm` to PATH.
- Accept defaults during installation.
- **Timing:** Not needed until Phase 10 (frontend development). Install it then to avoid premature dependency.

**Verification:**
```powershell
node --version    # Should show v24.x.x
npm --version     # Should show 10.x or higher
```

---

## 3. Optional Software

These are **not required** for the core project but may be helpful.

| Software | Purpose | When Needed | Download |
|---|---|---|---|
| **Docker Desktop** | Alternative for PostgreSQL+pgvector, possible future containerization | Only if native pgvector build fails | https://www.docker.com/products/docker-desktop/ |
| **Visual Studio Build Tools** | Required only for building pgvector from source | Phase 9, only if using native pgvector | https://visualstudio.microsoft.com/downloads/ |
| **CUDA Toolkit** | Only if a custom CUDA extension needs compilation | Not needed for prebuilt PyTorch wheels | https://developer.nvidia.com/cuda-downloads |
| **7-Zip** | Extracting `.tgz` Spark archive | Phase 2 setup | https://www.7-zip.org/download.html |
| **JupyterLab** | Interactive notebooks | Phase 1+ (installed via pip in .venv) | `pip install jupyterlab` |
| **WSL** | Linux subsystem alternative | Only if Docker/pgvector build requires it | Windows Features |
| **Postman** | API testing GUI | Phase 9+ backend testing | https://www.postman.com/downloads/ |
| **pgAdmin** | PostgreSQL GUI management | Bundled with PostgreSQL installer | N/A |
| **DBeaver** | Alternative database GUI | Optional | https://dbeaver.io/download/ |

> [!TIP]
> Visual Studio Build Tools become mandatory only if you choose the native pgvector build path. If you use Docker for PostgreSQL+pgvector instead, you can skip the Build Tools entirely.

---

## 4. Python Package Dependencies

All Python packages will be installed into the project `.venv` (Step 2). They are organized by phase/group.

### Group A — Foundation & Data (Phase 0–1)

Install first, immediately after creating the venv:

```
numpy>=2.1,<3.0
pandas>=2.1,<3.0
scikit-learn>=1.5,<2.0
pyarrow>=15.0
PyYAML>=6.0
pytest>=8.0
httpx>=0.27
matplotlib>=3.9
seaborn>=0.13
python-dotenv>=1.0
```

### Group B — PyTorch & NLP (Phase 3–6)

Install after PyTorch (Step 5) is working:

```
transformers>=4.45
datasets>=3.0
accelerate>=1.0
tokenizers>=0.20
safetensors>=0.4
evaluate>=0.4
sentence-transformers>=3.0
seqeval>=1.2
rouge-score>=0.1
```

### Group C — Backend API & Database (Phase 9)

```
fastapi>=0.115
uvicorn[standard]>=0.32
sqlalchemy>=2.0
psycopg[binary]>=3.2
pgvector>=0.3
alembic>=1.14
pydantic>=2.10
pydantic-settings>=2.6
python-jose[cryptography]>=3.3
passlib[bcrypt]>=1.7
python-multipart>=0.0.12
```

### Group D — Frontend (Phase 10, via npm)

```json
{
  "dependencies": {
    "next": "^16.0",
    "react": "^19.0",
    "react-dom": "^19.0"
  },
  "devDependencies": {
    "typescript": "^5.6",
    "tailwindcss": "^4.0",
    "@types/react": "^19.0",
    "@types/node": "^22.0"
  }
}
```

### Group E — Optional / Later Phase

```
bertopic>=0.16          # Phase 5 only, check Windows wheel
umap-learn>=0.5
hdbscan>=0.8
faster-whisper>=1.0     # Phase 11 only, separate CUDA/CTranslate2 check
pyspark==4.3.0          # Optional for notebooks; Scala is mandatory
```

> [!IMPORTANT]
> **Do not install all groups at once.** Install Group A first, verify, then Group B after PyTorch works, etc. Each group's exact pins will be resolved at installation time through `pip install` with constraints.

---

## 5. Environment Variable Configuration

### Variables to Set (User or System level)

| Variable | Value | Purpose |
|---|---|---|
| `JAVA_HOME` | `C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot` | JDK root for SBT, Spark |
| `SPARK_HOME` | `C:\spark\spark-4.3.0-bin-hadoop3` (adjust to your extraction path) | Apache Spark distribution root |
| `HADOOP_HOME` | `C:\hadoop` | Hadoop winutils location |
| `PYSPARK_PYTHON` | `D:\BDA_TA\.venv\Scripts\python.exe` | PySpark Python interpreter |
| `TMDB_API_KEY` | *(your TMDB API key)* | TMDB metadata access (set in `.env`, not system-wide) |

### PATH Additions (append to existing PATH)

Add these entries **in order** to your User or System PATH:

```
%JAVA_HOME%\bin
%SPARK_HOME%\bin
%HADOOP_HOME%\bin
```

Node.js, SBT, PostgreSQL, and Git installers add themselves to PATH automatically during installation.

### How to Set Environment Variables on Windows 11

1. Press `Win + S`, search for **"Environment Variables"**.
2. Click **"Edit the system environment variables"**.
3. Click **"Environment Variables..."** button.
4. Under **User variables** (preferred) or **System variables**:
   - Click **"New..."** to add a new variable.
   - Click on **"Path"** → **"Edit..."** → **"New"** to add PATH entries.
5. Click **OK** on all dialogs.
6. **Restart any open terminals** for changes to take effect.

### Project-level `.env` File

Application secrets go in `.env` (never committed to Git):

```env
# .env.example — copy to .env and fill values
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/cinescope
TMDB_API_KEY=your_tmdb_api_key_here
SECRET_KEY=generate_a_random_secret_key
DEBUG=false
```

---

## 6. Verification Commands

Run these after each installation step. All commands assume PowerShell.

### Full Verification Script

```powershell
# --- Step 1: Java ---
Write-Host "=== Java ===" -ForegroundColor Cyan
java -version
javac -version
Write-Host "JAVA_HOME: $env:JAVA_HOME"

# --- Step 2: Python venv ---
Write-Host "`n=== Python ===" -ForegroundColor Cyan
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import sys; print('Executable:', sys.executable)"
.\.venv\Scripts\pip.exe --version

# --- Step 3: SBT ---
Write-Host "`n=== SBT ===" -ForegroundColor Cyan
sbt --version

# --- Step 4: Spark ---
Write-Host "`n=== Spark ===" -ForegroundColor Cyan
Write-Host "SPARK_HOME: $env:SPARK_HOME"
Write-Host "HADOOP_HOME: $env:HADOOP_HOME"
spark-submit --version

# --- Step 5: PyTorch/CUDA ---
Write-Host "`n=== PyTorch ===" -ForegroundColor Cyan
.\.venv\Scripts\python.exe -c @"
import torch
print('PyTorch:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('CUDA version:', torch.version.cuda)
    print('GPU:', torch.cuda.get_device_name(0))
    arch = torch.cuda.get_arch_list()
    print('Arch list:', arch)
    has_sm120 = any('sm_120' in a or 'compute_120' in a for a in arch)
    print('sm_120 support:', has_sm120)
    x = torch.randn(4, 4, device='cuda')
    y = x @ x.T
    torch.cuda.synchronize()
    print('CUDA tensor test: PASS')
    print('Peak VRAM:', round(torch.cuda.max_memory_allocated()/1024**2, 1), 'MiB')
else:
    print('WARNING: CUDA not available')
"@

# --- Step 6: PostgreSQL ---
Write-Host "`n=== PostgreSQL ===" -ForegroundColor Cyan
psql --version
pg_config --version

# --- Step 6a: pgvector ---
Write-Host "`n=== pgvector ===" -ForegroundColor Cyan
psql -U postgres -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"

# --- Step 7: Node.js ---
Write-Host "`n=== Node.js ===" -ForegroundColor Cyan
node --version
npm --version

# --- Git (already installed) ---
Write-Host "`n=== Git ===" -ForegroundColor Cyan
git --version

# --- GPU ---
Write-Host "`n=== GPU ===" -ForegroundColor Cyan
nvidia-smi --query-gpu=name,driver_version,memory.total,compute_mode -i 0 --format=csv,noheader
```

---

## 7. Compatibility Notes

### Validated Compatible Stack

| Component | Version | Compatibility Source |
|---|---|---|
| Python | 3.11.9 | Architecture requirement; PyTorch/Spark/Transformers all support 3.11 |
| JDK | 21 (Temurin) | Spark 4.3.0 docs list Java 17/21/25 |
| Scala | 2.13.x (SBT-managed) | Spark 4.3.0 requires Scala 2.13; Scala docs confirm 2.13.11+ supports JDK 21 |
| SBT | 1.10.7 | Scala docs: SBT ≥1.9.0 required for JDK 21 |
| Spark | 4.3.0 | Official docs: Windows, Java 17/21/25, Scala 2.13, Python 3.11+ |
| PyTorch | ≥2.7.0 + CUDA ≥12.8 | RTX 5050 (sm_120/Blackwell) requires builds with sm_120 kernels |
| Transformers | ≥4.45 | Tested with Python 3.11+, PyTorch 2.6+ |
| PostgreSQL | 17.x or 18.x | Stable releases; five-year support policy |
| pgvector | 0.8.x | Must match PostgreSQL major version headers |
| Node.js | 24.x LTS | Next.js 16.x requires Node ≥20.9; 24 LTS is current |
| Next.js | 16.x | Current stable; supports Windows |
| NVIDIA Driver | 621.01 | Supports CUDA 13.5 UMD; exceeds minimum for PyTorch CUDA 12.8+ |

### Critical Compatibility Rules

1. **Do not mix Spark versions.** Legacy source uses Spark 3.5/Scala 2.12 — the new project uses Spark 4.3/Scala 2.13. They cannot share a build.
2. **Do not use Python 3.14** for this project. The `py` launcher defaults to 3.14.6, which is incompatible.
3. **PyTorch CUDA version ≠ NVIDIA driver CUDA version.** Driver 621.01 reports CUDA 13.5 capability. The PyTorch wheel bundles its own CUDA runtime (e.g., 13.2). They are independent.
4. **No full CUDA Toolkit required.** Prebuilt PyTorch wheels bundle CUDA runtime libraries. Install `nvcc`/CUDA Toolkit only if compiling custom CUDA extensions.
5. **pgvector version must match PostgreSQL major.** A pgvector built against PostgreSQL 17 headers will not work on PostgreSQL 18.

### Official Documentation Links

| Topic | URL |
|---|---|
| Spark 4.3.0 overview | https://spark.apache.org/docs/4.3.0/ |
| Spark downloads | https://spark.apache.org/downloads.html |
| PyTorch install selector | https://pytorch.org/get-started/locally/ |
| PyTorch previous versions | https://pytorch.org/get-started/previous-versions/ |
| PyTorch release/CUDA matrix | https://github.com/pytorch/pytorch/blob/main/RELEASE.md |
| NVIDIA compute capabilities | https://developer.nvidia.com/cuda/gpus |
| NVIDIA CUDA compatibility | https://docs.nvidia.com/deploy/cuda-compatibility/ |
| Transformers installation | https://huggingface.co/docs/transformers/installation |
| Scala JDK compatibility | https://docs.scala-lang.org/overviews/jdk-compatibility/overview.html |
| SBT setup | https://www.scala-sbt.org/1.x/docs/Setup.html |
| PostgreSQL downloads | https://www.postgresql.org/download/windows/ |
| PostgreSQL versioning | https://www.postgresql.org/support/versioning/ |
| pgvector installation | https://github.com/pgvector/pgvector#windows |
| Node.js downloads | https://nodejs.org/en/download/ |
| Node release schedule | https://nodejs.org/en/about/previous-releases |
| Next.js installation | https://nextjs.org/docs/app/getting-started/installation |
| winutils repository | https://github.com/cdarlint/winutils |

---

## 8. Known Issues and Solutions

### Issue 1: JAVA_HOME contains URL-encoded characters

**Problem:** Current `JAVA_HOME` points to a Coursier-cached JDK path with `%252B` URL encoding:
```
C:\Users\bharg\AppData\Local\Coursier\cache\arc\...\jdk-21.0.12+8
```
This path contains a `+` character and fails in many tools.

**Solution:** Set `JAVA_HOME` to the properly installed Adoptium JDK:
```
JAVA_HOME = C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot
```

---

### Issue 2: Python launcher (`py`) defaults to wrong version

**Problem:** `py.exe` defaults to Python 3.14.6, not 3.11.9.

**Solution:** Never use bare `py` for this project. Always either:
- Activate the `.venv` and use `python`
- Use the explicit path: `C:\Users\bharg\AppData\Local\Programs\Python\Python311\python.exe`

---

### Issue 3: Spark on Windows requires winutils.exe

**Problem:** Spark calls Hadoop filesystem utilities that don't exist natively on Windows, causing `java.io.FileNotFoundException` or `Could not locate executable null\bin\winutils.exe`.

**Solution:** Install Hadoop Windows binaries (Step 4a) and set `HADOOP_HOME`.

---

### Issue 4: Low available RAM at measurement

**Problem:** Only ~1.85 GiB was free at measurement time (of 15.71 GiB total).

**Solution:**
- Close unnecessary applications before running Spark jobs or model training.
- Do not run Spark and GPU training simultaneously.
- Re-measure available RAM with `(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB` before heavy workloads.

---

### Issue 5: Limited disk space on D: drive

**Problem:** D: drive has ~54 GiB free. With MovieLens 32M (~1.1 GiB), dependencies (~5–10 GiB), models (~2–5 GiB), and processed data (~5–10 GiB), space may be tight.

**Solution:**
- Keep a 20 GiB reserve on D:.
- Consider installing Spark and PostgreSQL on C: (129 GiB free) or E: (92 GiB free).
- Monitor with: `Get-CimInstance Win32_LogicalDisk | Select DeviceID, @{N='FreeGB';E={[math]::Round($_.FreeSpace/1GB,1)}}`.

---

### Issue 6: PyTorch sm_120 support

**Problem:** Standard PyTorch builds with CUDA ≤12.4 do not include `sm_120` kernels for the RTX 5050 Blackwell GPU, causing `RuntimeError: CUDA error: no kernel image is available`.

**Solution:** Install PyTorch with CUDA ≥12.8 index. Verify with:
```python
print(torch.cuda.get_arch_list())  # Must contain sm_120
```

---

### Issue 7: pgvector build on Windows

**Problem:** pgvector requires C++ compilation with `nmake` from Visual Studio Build Tools, which is a large (~3–6 GB) installation.

**Solutions (choose one):**
1. **Native build:** Install VS Build Tools → use x64 Native Tools prompt → `nmake /F Makefile.win`.
2. **Docker alternative:** `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=pw pgvector/pgvector:pg17` (requires Docker Desktop).

---

### Issue 8: Data loader workers on Windows

**Problem:** PyTorch `DataLoader` with `num_workers > 0` on Windows can cause `BrokenPipeError` or hangs due to `spawn` multiprocessing.

**Solution:** Start with `num_workers=0` (single-process data loading). Increase cautiously after testing.

---

## 9. Disk Space Budget

Estimated storage requirements on D: drive (current free: ~54 GiB):

| Component | Estimated Size | Drive Recommendation |
|---|---|---|
| Python `.venv` + all packages | 5–8 GiB | D: (project workspace) |
| PyTorch CUDA wheel | 2.5–3.5 GiB | D: (inside .venv) |
| Apache Spark distribution | ~0.6 GiB | C: or D: |
| PostgreSQL + pgvector | ~0.3 GiB | C: (default installer) |
| SBT + cached dependencies | ~0.5–1 GiB | User home (default) |
| Node.js + `node_modules` | ~0.3–0.5 GiB | D: |
| MovieLens 32M (already present) | ~1.1 GiB | D: (already at `data/raw/`) |
| Model checkpoints (future) | 1–3 GiB | D: |
| Processed data / Parquet (future) | 2–5 GiB | D: |
| **Reserve** | **20 GiB** | D: |
| **Total estimated** | **~33–43 GiB** | |

> [!WARNING]
> With ~54 GiB free, there is limited headroom. Consider installing Spark and PostgreSQL on C: drive. Monitor space before each major installation or data processing step.

---

## 10. Installation Quick Reference

```mermaid
flowchart TD
    A["Step 1: Fix JAVA_HOME<br/>(no download)"] --> B["Step 2: Create .venv<br/>(no download)"]
    B --> C["Step 2a: pip install Group A<br/>(foundation packages)"]
    C --> D["Step 3: Install SBT<br/>(MSI installer)"]
    D --> E["Step 4: Install Spark 4.3.0<br/>(extract .tgz + env vars)"]
    E --> F["Step 4a: Install winutils<br/>(download binaries)"]
    F --> G["Step 5: pip install PyTorch+CUDA<br/>(~3 GB download)"]
    G --> H["Step 5a: pip install Group B<br/>(NLP packages)"]
    H --> I["Step 6: Install PostgreSQL<br/>(MSI installer)"]
    I --> J["Step 6a: Build pgvector<br/>(requires VS Build Tools)"]
    J --> K["Step 6b: pip install Group C<br/>(backend packages)"]
    K --> L["Step 7: Install Node.js 24 LTS<br/>(MSI installer, Phase 10)"]
    L --> M["Step 7a: npm install Group D<br/>(frontend packages, Phase 10)"]
    
    style A fill:#90EE90
    style B fill:#90EE90
    style G fill:#FFD700
    style I fill:#FFD700
    style J fill:#FFA500
    style L fill:#87CEEB
```

**Legend:** 🟢 No download needed · 🟡 Large download · 🟠 May need VS Build Tools · 🔵 Deferred to Phase 10

### Summary Table

| Step | Software | Version | Phase | Download Link | Mandatory |
|:---:|---|---|:---:|---|:---:|
| 1 | Fix JAVA_HOME | — | 0 | N/A | ✅ |
| 2 | Python 3.11 venv | 3.11.9 | 0 | Already installed | ✅ |
| 2a | Foundation packages | See Group A | 0–1 | pip | ✅ |
| 3 | SBT | 1.10.7 | 2 | https://github.com/sbt/sbt/releases | ✅ |
| 4 | Apache Spark | 4.3.0 | 2 | https://spark.apache.org/downloads.html | ✅ |
| 4a | winutils.exe | Hadoop 3.x | 2 | https://github.com/cdarlint/winutils | ✅ |
| 5 | PyTorch + CUDA | ≥2.7 + CUDA ≥12.8 | 3 | https://pytorch.org/get-started/locally/ | ✅ |
| 5a | NLP packages | See Group B | 3–6 | pip | ✅ |
| 6 | PostgreSQL | 17.x/18.x | 9 | https://www.postgresql.org/download/windows/ | ✅ |
| 6a | pgvector | 0.8.x | 9 | https://github.com/pgvector/pgvector | ✅ |
| 6b | Backend packages | See Group C | 9 | pip | ✅ |
| 7 | Node.js | 24 LTS | 10 | https://nodejs.org/en/download/ | ✅ |
| 7a | Frontend packages | See Group D | 10 | npm | ✅ |
| — | VS Build Tools | Latest | 9 | https://visualstudio.microsoft.com/downloads/ | ⚠️* |
| — | Docker Desktop | Latest | — | https://www.docker.com/products/docker-desktop/ | ❌ |
| — | CUDA Toolkit | — | — | https://developer.nvidia.com/cuda-downloads | ❌ |

*\* Required only if building pgvector natively; not needed if using Docker for PostgreSQL.*

---

> [!NOTE]
> **After you install each prerequisite**, let me know and I will re-inspect the environment to verify correct installation, version compatibility, and readiness before proceeding to implementation.

