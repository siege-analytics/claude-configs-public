# #976 Tier C pre-mortem — develop only

Base `f115158b58db3690d2ea63999699284dc79db1bb`. This risk inventory was prepared before implementation with a review-only Execute-mode spoke. No merge, deploy, install, release or main promotion is authorized.

### Tiger: catalog safety and cross-repository leakage

**Severity:** HIGH. **Likelihood:** Medium. Mitigation and falsification are recorded per row below.

| Class | Severity | Likelihood | Failure mode | Falsification / mitigation |
|---|---|---|---|---|
| Tiger | HIGH | Medium | Catalog raw-path writes bypass UC procedures | Operational Delta/Parquet/Iceberg/ORC/SparkApplication/INSERT route positives, Postgres/SQLite/CSV/CPU/read-only negatives, actual selected paths and bytes in all packages. |
| Tiger | HIGH | Medium | A bare technology mention or visualization loads an unrelated engine | Action/context gates and read-only/negation/docs/pure-map negatives; unknown and ambiguous remain kernel-only. |
| Tiger | HIGH | Low | SU-only requirements leak into unrelated repository | Exact GitHub host/repo versus foreign-host and bare owner/repo fixtures; all global data source+package content scanned for ungated SU prescriptions. |
| Tiger | HIGH | Medium | New routes overflow without a visible diagnostic or implicitly load shelves | 12/80,000/20,000 kernel-only overflow, reference-shelf explicit rejection and multi-route fixtures. |
| Elephant | MEDIUM | High | Cost figures misreported as runtime savings | Exact-base archive package reconstruction, UTF-8 selected bytes and char/token estimates separate; no ambient/runtime savings or transitive-reference claim. |
| Elephant | MEDIUM | Medium | Unknown project consumer inferred from references | Ledger uses UNKNOWN except exact declared Siege Utilities overlay; no retirement or lifecycle completion. |

Rollback: revert this one develop-only PR if a tested selector contract is falsified. Existing main/install/release protections and legacy references remain untouched.
