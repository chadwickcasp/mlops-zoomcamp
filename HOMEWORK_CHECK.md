# MLOps Zoomcamp Homework Solutions Check

This document summarizes a review of homework answers across all sections of the MLOps Zoomcamp, compared against the expected answers from the course materials (2022 version).

---

## 01-intro

**Status:** No formal homework.md exists in the course structure for this section.

The `homework.ipynb` contains exploratory content (pandas/sklearn version checks, reading parquet) with some empty cells. The intro section typically uses the main course notebook rather than a separate homework form.

---

## 02-experiment-tracking

| Question | Your Answer | Expected | Status |
|----------|-------------|----------|--------|
| Q1 (MLflow version) | 1.26.1 | (no fixed option) | OK |
| Q2 (files saved to OUTPUT_FOLDER) | 4 (C) | 4 | Correct |
| Q3 (min_samples_split) | 2 (A) | 2 | Correct |
| Q4 (server config in addition to backend-store-uri) | --default-artifact-root (A) | default-artifact-root | Correct |
| Q5 (best validation RMSE) | 5.818 (C) | 5.818 | Note: Actual run may differ (e.g., 5.628) due to 2025 vs 2022 environment |
| Q6 (test RMSE of best model) | 6.061 (C) | 6.061 | Note: Actual run may differ (e.g., 5.834) due to version drift |

---

## 03-orchestration

| Question | Your Answer | Expected | Status |
|----------|-------------|----------|--------|
| Q1 (task needing .result()) | train_model | train_model | Correct |
| Q2 (validation MSE for date 2021-08-15) | 11.637 (A) | 11.637 | Correct |
| Q3 (DictVectorizer file size in bytes) | 13,191 (A) | ~13,000 | Correct |
| Q4 (Cron expression for 9 AM every 15th) | 0 9 15 * * (C) | 0 9 15 * * | Correct |
| Q5 (flow runs scheduled in advance) | 3 (B) | 3 | Correct |
| Q6 (command to view work-queues) | prefect work-queue ls (B) | prefect work-queue ls | Correct |

---

## 04-deployment

| Question | Your Answer | Expected | Status |
|----------|-------------|----------|--------|
| Q1 (mean predicted duration, Feb 2021) | 16.19 (B) | 16.19 | Correct |
| Q2 (output parquet file size) | 19M (B) | 19M | Correct |
| Q3 (convert notebook to script) | jupyter nbconvert --to script | Same | Correct |
| Q4 (first Scikit-Learn hash in Pipfile.lock) | sha256:08ef968f6b... | (value-dependent) | Plausible |
| Q5 (mean predicted duration, March 2021) | 16.29 (B) | 16.29 | Correct |
| Q6 (mean predicted duration, April 2021, Docker) | 9.96 (A) | 9.96 | Correct |

---

## 05-monitoring

| Question | Your Answer | Expected | Status |
|----------|-------------|----------|--------|
| Q1 (message at localhost:27017) | B (MongoDB HTTP message) | B | Correct |
| Q2 (command to find volume name) | docker volume ls (D) | docker volume ls | Correct |
| Q3 (last prediction by current model) | 15.74 (B) | 15.74 | Correct |
| Q4 (features drifted in Evidently report) | 2 (B) | 2 | Correct |
| Q5 (stats test for location IDs) | Jensen-Shannon distance | Jensen-Shannon | Correct |
| Q6 (last prediction with new model) | 16.64 (B) | 16.64 | Correct |
| Q7 (feature that detected drift with new ref) | trip_distance (D) | trip_distance | Correct |
| Q8 (metrics length for "report" collection) | 2 (A) | 2 | Correct |

---

## 06-best-practices

| Question | Your Answer | Expected | Status |
|----------|-------------|----------|--------|
| Q1 (if statement for main block) | — | `if __name__ == '__main__':` | Missing in notebook |
| Q2 (file besides test_batch.py for imports) | — | __init__.py | Missing in notebook |
| Q3 (rows in expected dataframe) | 2 (B) | 2 | Correct |
| Q4 (AWS CLI for Localstack) | — | aws --endpoint-url=http://localhost:4566 s3 mb s3://nyc-duration | Missing in notebook |
| Q5 (written file size in bytes) | 3512 (A) | 3512 | Correct |
| Q6 (sum of predicted durations) | 69.28 (C) | 69.28 | Correct |

---

## Overall Summary

| Section | Correct | Missing / Notes |
|---------|---------|------------------|
| 01-intro | N/A | No formal homework form |
| 02-experiment-tracking | 4/4 fixed, 2 may vary | Q5/Q6 can differ with 2025 env |
| 03-orchestration | 6/6 | All correct |
| 04-deployment | 6/6 | All correct |
| 05-monitoring | 8/8 | All correct |
| 06-best-practices | 3/6 | Q1, Q2, Q4 answers not recorded |

---

*Generated from homework review against MLOps Zoomcamp 2022 materials. If answers don't match options exactly, course instructions suggest selecting the closest one.*
