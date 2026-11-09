# Phase 2 toolchain evidence

Observed on 9 November 2026, Asia/Calcutta. This supplements the original
Phase 0 audit; it does not rewrite that historical measurement.

| Component | Observed result | Meaning |
|---|---|---|
| Root Python | Existing isolated3.11.9; scientific packages appeared through manual setup; stdlib scripts execute | No further Python package installation needed for current validators/launcher |
| Selected JDK | Existing Eclipse Adoptium 21 installation, compiler processes execute | No second Java installation recommended |
| Scala compiler/library/reflect | Exact 2.13.18 jars already in local Coursier cache | Offline config compilation and Scala parsing are possible without a resolver |
| Spark 4.3.0 | Distribution not selected/found; required core/sql/mllib jars absent in inspected cache | Real compilation/runtime blocked |
| SBT 1.10.7 | No usable installation found in prior audit; matching launcher absent from inspected cache | User manual build preparation required |
| ScalaTest 3.2.19 | Requested aggregate/funsuite artifacts absent from inspected cache | Authored ScalaTest contracts have not run |
| Project JAR | Absent | Launcher refuses actual execution |
| D: free space | 52.277 GiB at the saved preflight snapshot | Above 20 GiB reserve; not an allocation guarantee |
| Available RAM | 1,869.43 MiB at that snapshot | Below 4 GiB needed by default heap+headroom policy |

Read-only cache scan examined8,567 filenames without hitting its50,000 cap.
Missing filenames in these inspected locations are not proof that no copy
exists anywhere on the laptop. Finding a few jars is not a complete classpath.
No SBT/Scala CLI/coursier resolver was executed. No package or model was fetched.

Evidence:

- [Cache filename report](../../artifacts/environment/spark-cache-20261109-18d9d1f0.json)
- [Actual launcher preflight](../../artifacts/environment/spark-preflight-20261109-18d9d1f0.json)
- [Final cached compiler execution](../../artifacts/scala-offline/20261109T033807Z-1c28488e/verification.json)

The cached compiler truly compiled PathPolicy,JobConfig,JsonCodec and the
executable PureConfigChecks; all28 checks passed. It also parsed all19 Scala
source/test files. Spark imports/API calls were not type-checked, and the22
authored ScalaTest cases were not executed. SBT build.sbt is still an unexecuted
build definition. Do not interpret these narrower checks as Phase 2 completion.

Use [PREREQUISITES.md](../../PREREQUISITES.md) and [RUNBOOK.md](RUNBOOK.md).
Prepare the manual prerequisites, remeasure resources, run actual compilation/
ScalaTest and the synthetic Parquet smoke, then batch and streaming rehearsal.
Only after that evidence gate should the queued NLP extension be integrated.

A later [manual-install recheck](../../artifacts/environment/manual-install-recheck-20261109-1c28488e.json)
also passed actual CUDA/FP16/BF16 tensors on torch2.14.1+cu130 and six scientific
imports. It measured49.269GiB disk and1,916.16MiB available RAM. These later
observations do not change the missing Spark/SBT/JAR execution gate.
