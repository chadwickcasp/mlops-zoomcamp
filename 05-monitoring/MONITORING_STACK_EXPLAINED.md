# Monitoring Stack Architecture Explained

## The Big Picture: What Problem Are We Solving?

When you deploy a machine learning model to production, you can't just "set it and forget it." Models degrade over time because:

1. **Data Drift**: The distribution of input data changes (e.g., new pickup/dropoff locations appear)
2. **Concept Drift**: The relationship between features and target changes (e.g., traffic patterns shift)
3. **Performance Degradation**: Model accuracy decreases over time

This monitoring stack provides **real-time monitoring** to detect these issues before they cause problems in production.

---

## The Architecture: A Layered Approach

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Flow Overview                           │
└─────────────────────────────────────────────────────────────────┘

   User Request
        │
        ▼
   ┌────────────────────┐
   │ Prediction Service │  ← Your ML model (makes predictions)
   │    Port: 9696      │
   └──────────┬─────────┘
              │
              ├──────────────────────┐
              │                      │
              ▼                      ▼
   ┌──────────────────┐    ┌────────────────────┐
   │     MongoDB      │    │ Evidently Service  │
   │   Port: 27018    │    │    Port: 8085      │
   │                  │    │                    │
   │ (Stores data for │    │ (Monitors data     │
   │  future analysis)│    │  quality & drift)  │
   └──────────────────┘    └──────────┬─────────┘
                                       │
                                       ▼
                              ┌────────────────────┐
                              │   Prometheus       │
                              │   Port: 9091       │
                              │                    │
                              │ (Time-series DB    │
                              │  stores metrics)   │
                              └──────────┬─────────┘
                                         │
                                         ▼
                              ┌────────────────────┐
                              │     Grafana        │
                              │   Port: 3000       │
                              │                    │
                              │ (Visualization &   │
                              │  dashboards)       │
                              └────────────────────┘
```

---

## Service-by-Service Breakdown

### 1. **Prediction Service** (Your ML Model)

**Location**: `prediction_service/app.py`

**What it does:**
- Serves your trained ML model via a REST API
- Receives POST requests with taxi trip features
- Makes predictions (trip duration)
- **Side effects**: Stores data and sends it to monitoring

**Key Code Logic:**
```python
@app.route('/predict', methods=['POST'])
def predict_endpoint():
    record = request.get_json()  # Get features like PULocationID, DOLocationID, trip_distance
    X = dv.transform([record])   # Transform features (one-hot encoding, etc.)
    y_pred = model.predict(X)    # Make prediction
    
    save_to_db(record, y_pred)           # Store in MongoDB
    send_to_evidently(record, y_pred)    # Send to monitoring
    
    return jsonify({'duration': y_pred})
```

**Why it exists:**
- This is your actual production service
- Every prediction gets logged for monitoring
- Separates business logic from monitoring logic

**Important Design Decision:**
- The prediction service sends data **asynchronously** to Evidently (via HTTP POST)
- If Evidently is down, predictions still work (failures are logged but don't break the service)

---

### 2. **MongoDB** (Data Storage)

**What it does:**
- Stores all prediction requests and results
- Acts as a historical database

**Why it exists:**
- **Audit trail**: Keep records of all predictions (regulatory compliance, debugging)
- **Future analysis**: Can query historical data for deeper analysis
- **Backup**: If monitoring service fails, data is still stored

**Data stored:**
```python
{
    "PULocationID": 100,
    "DOLocationID": 200,
    "trip_distance": 5.2,
    "prediction": 15.3  # The model's prediction
}
```

**Design Note:**
- MongoDB is **separate** from the monitoring pipeline
- It's for long-term storage, not real-time monitoring

---

### 3. **Evidently Service** (The Monitoring Engine)

**Location**: `evidently_service/app.py`

**What it does:**
- Receives batches of prediction data from the prediction service
- Compares current data to a "reference dataset" (baseline)
- Calculates statistical metrics (data drift, data quality)
- Exposes metrics in Prometheus format

**Key Concepts:**

#### A. **Reference Dataset**
- A "good" baseline dataset (e.g., `green_tripdata_2021-01.parquet`)
- Represents what the data looked like when the model was trained/validated
- Used as a comparison point

#### B. **Windowed Analysis**
```python
window_size: 5  # Process metrics every 5 predictions
calculation_period_sec: 2  # But only recalculate every 2 seconds max
```
- Collects data in a "sliding window" (last 5 predictions)
- Compares this window to the reference dataset
- Prevents over-computation

#### C. **The Monitoring Process**
```python
def iterate(self, dataset_name: str, new_rows: pd.DataFrame):
    # 1. Add new data to current window
    self.current[dataset_name] = current_data  # Last 5 rows
    
    # 2. When window is full, run Evidently monitors
    self.monitoring[dataset_name].execute(
        self.reference[dataset_name],  # Baseline (thousands of rows)
        current_data,                   # Current window (5 rows)
        self.column_mapping[dataset_name]
    )
    
    # 3. Extract metrics from Evidently
    for metric, value, labels in self.monitoring[dataset_name].metrics():
        # Convert to Prometheus Gauge metric
        found.labels(**labels).set(value)
```

**What Metrics Does It Calculate?**
- **Data Drift**: Are the input distributions changing? (using statistical tests like KS test)
- **Data Quality**: Are there missing values, outliers, unexpected values?
- **Target Drift**: Is the target variable distribution changing?

**Why It Exists:**
- Evidently is a specialized library for ML monitoring
- Does the heavy statistical lifting (drift detection, quality checks)
- Converts ML-specific metrics to Prometheus format

**API Endpoints:**
- `POST /iterate/taxi`: Receives new prediction data
- `GET /metrics`: Exposes metrics in Prometheus format (used by Prometheus scraper)

---

### 4. **Prometheus** (Time-Series Database)

**Location**: `evidently_service/config/prometheus.yml`

**What it does:**
- Periodically scrapes metrics from Evidently Service (`GET /metrics`)
- Stores metrics as time-series data
- Provides a query language (PromQL) for accessing metrics

**Configuration:**
```yaml
scrape_configs:
  - job_name: 'service'
    scrape_interval: 10s  # Every 10 seconds
    static_configs:
      - targets: ['evidently_service.:8085']  # Scrape from Evidently
```

**What Metrics Are Stored?**
Prometheus scrapes metrics like:
```
evidently:evidently_data_drift_dataset_drift_score{dataset_name="taxi"} 0.85
evidently:evidently_data_quality_missing_values{dataset_name="taxi",column="PULocationID"} 0.0
```

**Why Prometheus?**
- **Standard**: Industry standard for metrics collection
- **Scalable**: Handles millions of time-series
- **Query Language**: PromQL allows complex queries and alerting
- **Integration**: Works seamlessly with Grafana

**Design Decision:**
- **Pull model**: Prometheus pulls metrics (scrapes), rather than services pushing
- Benefits: If Prometheus is down, services don't break
- Prometheus controls when to collect metrics

---

### 5. **Grafana** (Visualization)

**What it does:**
- Connects to Prometheus as a data source
- Displays metrics as graphs, dashboards, and alerts
- Provides a user-friendly interface for monitoring

**Configuration Files:**

#### `grafana_datasources.yaml`
- Tells Grafana: "Use Prometheus as a data source"
- Configures connection: `http://prometheus:9090`

#### `grafana_dashboards.yaml`
- Tells Grafana: "Load dashboards from `/opt/grafana/dashboards`"
- Dashboard JSON files define what graphs to show

**Why Grafana?**
- **Visualization**: Makes metrics human-readable
- **Dashboards**: Pre-built visualizations for common metrics
- **Alerts**: Can trigger alerts when metrics exceed thresholds
- **Collaboration**: Teams can share dashboards

**Typical Dashboard Shows:**
- Data drift score over time
- Distribution of predictions
- Data quality metrics (missing values, outliers)
- Alert status (is drift detected?)

---

## Data Flow: Step-by-Step

### 1. **User Makes Prediction Request**
```
User → POST /predict → Prediction Service
{
  "PULocationID": 100,
  "DOLocationID": 200,
  "trip_distance": 5.2
}
```

### 2. **Prediction Service Processes**
```python
# Makes prediction
prediction = model.predict(transform(features))

# Stores in MongoDB (for audit/history)
save_to_db(features, prediction)

# Sends to Evidently (for monitoring)
POST http://evidently_service:8085/iterate/taxi
Body: [{"PULocationID": 100, "DOLocationID": 200, "trip_distance": 5.2, "prediction": 15.3}]
```

### 3. **Evidently Service Accumulates Data**
```python
# Evidently receives data and adds to window
current_window = [row1, row2, row3, row4, row5]  # Last 5 predictions

# When window is full and time period elapsed:
#   - Runs statistical tests (compare window to reference)
#   - Calculates metrics (drift score, quality metrics)
#   - Exposes as Prometheus metrics
```

### 4. **Prometheus Scrapes Metrics**
```
Every 10 seconds:
  Prometheus → GET http://evidently_service:8085/metrics
  Receives: Prometheus-formatted metrics
  Stores: Time-series data in TSDB
```

### 5. **Grafana Queries Prometheus**
```
User opens Grafana dashboard:
  Grafana → Query Prometheus (via PromQL)
  Example: "Show me data drift score over last 24 hours"
  Prometheus → Returns time-series data
  Grafana → Renders as graph
```

---

## Design Philosophy: Why This Architecture?

### 1. **Separation of Concerns**
- **Prediction Service**: Business logic (making predictions)
- **Evidently Service**: Monitoring logic (statistical analysis)
- **Prometheus**: Metrics storage
- **Grafana**: Visualization

Each service does ONE thing well.

### 2. **Fault Tolerance**
- If Grafana is down → Monitoring still happens (Prometheus stores data)
- If Prometheus is down → Evidently still collects data (just not stored)
- If Evidently is down → Predictions still work (service degrades gracefully)

### 3. **Scalability**
- Prometheus can scrape multiple services
- Grafana can query multiple data sources
- Each service can scale independently

### 4. **Industry Standards**
- Prometheus + Grafana = Standard observability stack
- Evidently = Specialized ML monitoring
- Together = Production-ready monitoring

---

## Key Configuration Parameters

### Evidently Service (`config.yaml`)
```yaml
window_size: 5  # How many predictions to accumulate before calculating metrics
calculation_period_sec: 2  # Minimum time between metric calculations
```
- **Trade-off**: Smaller window = faster detection, more computation
- **Trade-off**: Larger window = less computation, slower detection

### Prometheus (`prometheus.yml`)
```yaml
scrape_interval: 10s  # How often to collect metrics
```
- **Trade-off**: More frequent = more data, more load
- **Trade-off**: Less frequent = less data, lower load

---

## Common Questions

### Q: Why not just monitor the model's accuracy directly?
**A:** In production, you often don't have ground truth immediately. You have to detect problems before they impact users. Data drift detection catches issues early.

### Q: Why use a "reference dataset" instead of the training data?
**A:** The reference dataset represents a "known good" period. It's more flexible than training data (can use validation data, or a specific production period that was good).

### Q: What happens if the reference dataset is old?
**A:** That's a problem! The reference should be updated periodically. The course mentions "moving reference" option for this.

### Q: Why MongoDB AND Prometheus?
**A:** 
- **MongoDB**: Long-term storage, full records, queryable
- **Prometheus**: Time-series optimized, metrics only, fast queries

They serve different purposes.

---

## Summary

This stack implements a **production monitoring system** for ML models:

1. **Prediction Service** makes predictions and sends data downstream
2. **MongoDB** stores everything for audit/history
3. **Evidently Service** does statistical analysis to detect drift/quality issues
4. **Prometheus** collects and stores metrics over time
5. **Grafana** visualizes metrics for humans

The architecture is:
- **Modular**: Each service has a clear responsibility
- **Fault-tolerant**: Services can fail independently
- **Standard**: Uses industry-standard tools
- **Scalable**: Can grow with your needs
