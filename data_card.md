# Data Card — M6 Synthetic Thermal Time-Series Benchmark
**Team SG03 | Topic M6 | Sprint 3**

---

## 1. Dataset Overview

| Property | Value |
|---|---|
| Dataset type | Fully synthetic (no real patient data) |
| Signal type | Skin temperature (°C) |
| Channels | 2 — Left breast, Right breast |
| Subjects | 20 (10 healthy, 10 pathological) |
| Sampling rate | 1 Hz |
| Duration per subject | 72 hours = 259,200 samples |
| Total samples | 5,184,000 |
| Total windows | 172,780 |
| Anomalous windows | 564 (0.33%) |
| Normal windows | 172,216 (99.67%) |
| Class imbalance ratio | 306:1 |
| Window size | 60 seconds (60 samples) |
| Overlap | 50% (step = 30 s) |
| Normal temperature range | 33–37 °C |
| Asymmetry bias (right breast) | +0 to +0.2 °C additive offset |

---

## 2. Signal Properties

### Channels — `patient_XX_windows.npy` shape: `(8639, 5, 60)`

| Channel index | Column | Description |
|:---:|---|---|
| 0 | `left_temperature` | Raw °C left breast, 4 dp |
| 1 | `right_temperature` | Raw °C right breast, 4 dp |
| 2 | `left_temperature_norm` | Z-score normalized left, 6 dp |
| 3 | `right_temperature_norm` | Z-score normalized right, 6 dp |
| 4 | `temp_asymmetry` | right − left (°C), 4 dp |

### Normalization Parameters (per patient, stored in `subjects` table)

| Patient | μ_left (°C) | σ_left | μ_right (°C) | σ_right |
|:---:|---|---|---|---|
| 00 | 33.563273 | 0.582701 | 33.663318 | 0.582203 |
| 01 | 33.672544 | 0.636325 | 33.772901 | 0.636477 |
| 02 | 33.595156 | 0.536489 | 33.695180 | 0.536445 |
| 03 | 34.520721 | 0.413283 | 34.620877 | 0.413262 |
| 04 | 33.174790 | 0.585416 | 33.274588 | 0.584945 |
| 05 | 33.100009 | 0.507008 | 33.199808 | 0.506697 |
| 06 | 34.027265 | 0.710451 | 34.126889 | 0.710031 |
| 07 | 33.500974 | 0.603697 | 33.600911 | 0.603812 |
| 08 | 32.631582 | 0.496563 | 32.731847 | 0.496983 |
| 09 | 33.098907 | 0.612392 | 33.198926 | 0.612685 |
| 10 | 32.948645 | 0.544682 | 33.049763 | 0.545065 |
| 11 | 33.517651 | 0.679020 | 33.617715 | 0.679275 |
| 12 | 33.497819 | 0.668908 | 33.597267 | 0.668363 |
| 13 | 34.413773 | 0.388289 | 34.513423 | 0.387611 |
| 14 | 33.848317 | 0.501919 | 33.948274 | 0.501919 |
| 15 | 32.784971 | 0.521961 | 32.885317 | 0.521700 |
| 16 | 33.203477 | 0.642149 | 33.303549 | 0.642496 |
| 17 | 34.051013 | 0.603289 | 34.150934 | 0.603023 |
| 18 | 33.284169 | 0.503383 | 33.384222 | 0.503533 |
| 19 | 33.315396 | 0.653417 | 33.415798 | 0.653745 |

To inverse-transform z-score back to °C:
```
x_celsius = x_norm × σ + μ
```

---

## 3. Anomaly Injection Parameters

| Anomaly type | Description | Parameters |
|---|---|---|
| `spike` | Sudden temperature spike | Amplitude: +2 to +4 °C, duration: 5–30 s |
| `drift` | Gradual temperature drift | Rate: +0.01 to +0.05 °C/s, duration: 60–300 s |

- Window label = `1` if **any** sample in the window is anomalous (conservative rule)
- `anomaly_ratio` column stores the fraction of anomalous samples for soft thresholding
- Ground truth: 100% known — `anomaly_label` column in `signals` / `thermal_readings`
- Asymmetry bias (+0 to +0.2 °C on right channel) is **not** an anomaly — models must not flag it

---

## 4. Database Schema

### PostgreSQL (`m6_thermal`) — port 5432

| Table | Rows | Primary Key | Description |
|---|---|---|---|
| `subjects` | 20 | `patient_id` (SMALLINT) | Patient metadata + normalization params |
| `recordings` | 20 | `id` (SERIAL) | Segment-level metadata |
| `signals` | 5,184,000 | `id` (BIGSERIAL) | Raw 1 Hz readings |
| `windows` | 172,780 | `(patient_id, window_id)` | Pre-computed 60s window metadata |
| `attention_maps` | variable | `id` (BIGSERIAL) | Sprint 3: TAAE attention weights per timestep |

#### `attention_maps` — PostgreSQL columns

| Column | Type | Description |
|---|---|---|
| `id` | BIGSERIAL | Primary key |
| `patient_id` | SMALLINT | FK → subjects(patient_id) |
| `window_id` | INTEGER | FK → windows(patient_id, window_id) |
| `timestep` | SMALLINT | 0..59 — position within the 60s window |
| `attn_weight` | FLOAT | Softmax attention weight from TAAE decoder |
| `recon_error` | FLOAT | Optional per-timestep MSE reconstruction error |
| `created_at` | TIMESTAMPTZ | Insertion timestamp |

### TimescaleDB (`m6_thermal_tsdb`) — port 5432

| Table | Rows | Type | Description |
|---|---|---|---|
| `subjects` | 20 | Regular | Same as PostgreSQL |
| `thermal_readings` | 5,184,000 | **Hypertable** | 6h chunks, segmented by patient_id |
| `windows_tsdb` | 172,780 | Regular | Window metadata |
| `attention_maps` | variable | **Hypertable** | 30-day chunks, Sprint 3 explainability |

#### `attention_maps` — TimescaleDB columns

| Column | Type | Description |
|---|---|---|
| `ts` | TIMESTAMPTZ | Partition key (hypertable) |
| `patient_id` | SMALLINT | FK → subjects(patient_id) |
| `window_id` | INTEGER | FK → windows_tsdb(patient_id, window_id) |
| `timestep` | SMALLINT | 0..59 |
| `attn_weight` | FLOAT | Softmax attention weight |
| `recon_error` | FLOAT | Optional per-timestep MSE |

---

## 5. Example Queries

### PostgreSQL

#### Fetch 1 hour of signal for patient 3
```sql
SELECT timestamp, left_temperature, right_temperature, anomaly_label
FROM signals
WHERE patient_id = 3
  AND timestamp >= (SELECT MIN(timestamp) FROM signals WHERE patient_id = 3)
  AND timestamp <  (SELECT MIN(timestamp) FROM signals WHERE patient_id = 3) + INTERVAL '1 hour'
ORDER BY timestamp;
```

#### Fetch anomalous windows for a patient
```sql
SELECT window_id, window_start, window_end, anomaly_ratio
FROM windows
WHERE patient_id = 1 AND label = 1
ORDER BY window_start;
```

#### Fetch attention maps for a window
```sql
SELECT timestep, attn_weight, recon_error
FROM attention_maps
WHERE patient_id = 1 AND window_id = 42
ORDER BY timestep;
```

#### Average temperature per minute (PostgreSQL)
```sql
SELECT DATE_TRUNC('minute', timestamp) AS bucket,
       AVG(left_temperature)  AS avg_left,
       AVG(right_temperature) AS avg_right
FROM signals
WHERE patient_id = 3
GROUP BY bucket ORDER BY bucket;
```

### TimescaleDB

#### Average temperature per minute (time_bucket)
```sql
SELECT time_bucket('1 minute', timestamp) AS bucket,
       AVG(left_temperature_norm)  AS avg_left,
       AVG(right_temperature_norm) AS avg_right
FROM thermal_readings
WHERE patient_id = 3
GROUP BY bucket ORDER BY bucket;
```

#### Anomaly rate per hour across all patients
```sql
SELECT time_bucket('1 hour', timestamp) AS hour_bucket,
       patient_id,
       COUNT(*) AS total_samples,
       SUM(anomaly_label) AS anomaly_count,
       ROUND(100.0 * SUM(anomaly_label) / COUNT(*), 4) AS anomaly_rate_pct
FROM thermal_readings
GROUP BY hour_bucket, patient_id
ORDER BY hour_bucket, patient_id;
```

#### Fetch attention maps (TimescaleDB)
```sql
SELECT timestep, attn_weight, recon_error
FROM attention_maps
WHERE patient_id = 1 AND window_id = 42
ORDER BY timestep;
```

---

## 6. ETL Pipeline Summary

| Stage | Operation | Result |
|---|---|---|
| 1 | CSV parsing & schema validation | 20/20 files accepted, 0 rejected |
| 2 | Gap detection & imputation | 0 gaps detected (synthetic data is regular) |
| 3 | Derived fields | `temp_asymmetry`, `session_second` computed |
| 4 | Z-score normalization | Per-patient, per-channel |
| 5 | Windowing | 60s windows, 50% overlap, conservative labeling |
| 6 | Export | cleaned CSV + NPY + metadata CSV |

| ETL Metric | Value |
|---|---|
| Patients processed | 20 |
| Rows per patient | 259,200 |
| Windows per patient | 8,639 |
| Interpolated rows | 0 |
| Segments per patient | 1 (no gaps) |

---

## 7. Sprint 2 Benchmark Results

### Ingestion Rate

| Metric | PostgreSQL | TimescaleDB |
|---|---|---|
| Ingestion speed (rows/s) | 24,883 | 32,572 |
| Total ingestion time | 208.3 s | 159.2 s |
| Pipeline time | 273.4 s | 217.0 s |

### Storage

| Metric | PostgreSQL | TimescaleDB |
|---|---|---|
| signals table size | 735 MB | 119 MB (compressed) |
| Compression ratio | 1.0× | **6.3×** |
| Space saved | — | 84.2% |

### Query Benchmark (8 queries × 5 runs)

| ID | Category | PG Median | TSDB Median | Winner |
|---|---|---|---|---|
| BMW1 | Write 10k rows | 1241 ms | 212 ms | **TSDB 5.9×** |
| BMW2 | Write 50k rows | 1286 ms | 372 ms | **TSDB 3.5×** |
| BMR1 | Read 1h scan | 20 ms | 24 ms | PG 1.2× |
| BMR2 | Read 72h scan | 1565 ms | 1676 ms | PG 1.1× |
| BMA1 | Avg temp/min | 570 ms | 188 ms | **TSDB 3.0×** |
| BMA2 | Anomaly rate/h | 1766 ms | 711 ms | **TSDB 2.5×** |
| BMS1 | Disk size query | 3 ms | 43 ms | PG 16.9× |
| BMS2 | Compression stats | 2 ms | 4 ms | PG 2.0× |

---

## 8. Sprint 3 Results

### DB-to-Model Pipeline Benchmark

| Batch size | TSDB ms/batch | NPY ms/batch | NPY speedup |
|:---:|---:|---:|---:|
| 16 | 492.19 | 366.20 | 1.3× |
| 32 | 1252.20 | 41.44 | 30× |
| 64 | 3539.40 | 58.34 | 60× |
| 128 | 2177.00 | 122.65 | 18× |

Recommended pattern: pre-export windows to NPY from TimescaleDB once, then train from NPY.

### Robustness Under Double-σ Noise

| Condition | F1 | Precision | Recall |
|---|:---:|:---:|:---:|
| Clean test set | 0.0210 | 0.0107 | 0.5000 |
| Noisy (2σ) | 0.0057 | 0.0028 | 1.0000 |
| F1 degradation | **72.86%** | | |

Threshold τ = 0.4279 (85th percentile of healthy training losses).

---
## 9. MedAttnAID (TAAE) — Anomaly Detection Metrics

| Metric | Value |
|---|---|
| F1 (%) | 2.25 |
| Precision (%) | 1.14 |
| Recall (%) | 59.55 |
| Individual Accuracy (%) | **100.0** |
| Window loss threshold τ | 0.4274 (85th percentile, MSE) |
| Optimal subject threshold | 5.0% |
| TP / FP / FN / TN | 53 / 4579 / 36 / 21249 |

### Asymmetry Confound Test — False Positive Rate per Channel (Healthy subjects)

| Channel | FPR Healthy (%) |
|---|:---:|
| Left breast | 17.86% |
| Right breast | 18.07% |

**Note:** Right channel FPR (18.07%) is marginally higher than left (17.86%), consistent with the expected +0 to +0.2 °C asymmetry bias. The difference is small (0.21%) and does not indicate the model is confounded by the asymmetry offset. Both channels operate near the same false positive rate under the 85th-percentile threshold.

---

## 10. Known Limitations

- **Synthetic data only** — not validated on real clinical thermal recordings.
- **Fixed 1 Hz sampling** — no variable-rate or missing-timestamp scenarios tested.
- **Small cohort** — 20 subjects. Statistical conclusions are limited.
- **Asymmetry confound** — right breast has a persistent +0 to +0.2 °C bias. Must not be flagged as anomalous.
- **Severe class imbalance** — 0.33% anomaly rate. Raw accuracy is misleading; use F1 and AUC-ROC.
- **No gap imputation exercised** — gap-handling code is implemented but not triggered (synthetic data has no gaps).
- **Single-machine benchmark** — both databases ran on the same host. Production results may differ.
- **n=5 benchmark runs** — p95 latency is statistically indicative only.

---

## 11. Ethical Considerations

This dataset is **100% synthetic** — no real patient data was used at any stage. There are:
- No privacy concerns
- No consent requirements
- No IRB restrictions
- No anonymization needed

The dataset is immediately publishable and reusable by external researchers. The asymmetry bias (+0 to +0.2 °C on the right breast) models a known physiological phenomenon and must not be misinterpreted as a pathological finding.

---

## 12. Published Files

| File | Location | Description |
|---|---|---|
| `schema_postgres.sql` | `sprint3_output/team3/` | DDL PostgreSQL (Sprint 3 update) |
| `schema_timescaledb.sql` | `sprint3_output/team3/` | DDL TimescaleDB (Sprint 3 update) |
| `schema_postgres.sql` (Sprint 2) | `dual_db_ingestion/sql/` | Original Sprint 2 DDL |
| `schema_timescaledb.sql` (Sprint 2) | `dual_db_ingestion/sql/` | Original Sprint 2 DDL |
| Sample dump (50 windows, 2 patients) | `schema_postgres.sql` Section 3 | Ready for external replication |

---

## 13. Reproduction

```bash
# Sprint 2 — Regenerate data
git clone https://github.com/malik630/Data-Wrangling
cd Data-Wrangling
pip install -r requirements.txt
python etl_pipeline.py --data-dir data/raw --out-dir data/processed
python dual_db_ingestion/scripts/ingest_postgres.py
python dual_db_ingestion/scripts/ingest_tsdb.py

# Sprint 3 — Train model & run benchmarks
git clone https://github.com/malik630/Data-Loader
cd Data-Loader
pip install -r requirements.txt
python train.py
python sprint3_output/team3/db_pipeline_benchmark.py
python sprint3_output/team3/robustness_test.py
```

