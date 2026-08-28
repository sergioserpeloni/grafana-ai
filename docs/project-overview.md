# Grafana AI Observability — Project Overview

## 1. Problem

Traditional observability platforms are very effective at collecting and visualizing infrastructure metrics, but interpreting those metrics still frequently requires human analysis.

A dashboard can show that CPU utilization increased, oscillated, or reached a critical threshold. However, understanding the behavior of the time series and turning it into contextual operational information requires additional analysis.

This project explores how a local Large Language Model (LLM) can be integrated with an observability platform to assist with this interpretation.

---

## 2. Solution

Grafana AI Observability is a proof of concept that connects traditional observability components with modern AI technologies.

The platform retrieves real time-series data from a Grafana dashboard through the Model Context Protocol (MCP), sends the contextualized data to a locally running LLM, and generates an operational analysis report.

The fundamental idea is:

> **Give the AI access to real observability context and let it explain what is happening.**

---

## 3. Architecture

The current architecture is composed of:

```text
Metrics Exporter
       │
       ▼
  Prometheus
       │
       ▼
    Grafana
       │
       ▼
  MCP Server
       │
       ▼
    AI API
       │
       ▼
Ollama + Gemma 3 4B
       │
       ▼
Observability Report
```

Each component has a specific responsibility:

- **Python Exporter** — generates the monitored metric.
- **Prometheus** — collects and stores the time series.
- **Grafana** — visualizes the metric and provides dashboard context.
- **MCP Server** — exposes controlled access to Grafana data.
- **AI API** — orchestrates MCP data retrieval and LLM analysis.
- **Ollama + Gemma 3 4B** — performs local inference.
- **SQLite** — provides local persistence for historical analysis and anomaly events.

---

## 4. Data Flow

The analysis follows these steps:

1. The exporter publishes the infrastructure utilization metric.
2. Prometheus collects the metric.
3. Grafana queries Prometheus and displays the time series.
4. The AI service starts an MCP client.
5. The MCP server retrieves the configured Grafana dashboard and panel.
6. Grafana executes the panel query and returns the real time-series data.
7. The AI service extracts the relevant timestamp/value pairs.
8. The data is provided to the local Gemma 3 4B model.
9. The model analyzes the chronological behavior of the series.
10. An operational observability report is generated.

The model is therefore working with **real dashboard data**, rather than a manually constructed example.

---

## 5. AI Analysis

The current proof of concept asks the model to identify and describe observable characteristics of the time series, including:

- trends;
- peaks;
- drops;
- oscillations;
- stability;
- changes in behavior;
- potential anomalies;
- periods that may require investigation.

The system intentionally distinguishes between:

**Observed behavior**

What can be directly supported by the time-series data.

**Operational hypothesis**

A possible explanation that requires additional evidence.

This distinction is important because an LLM should not present an unsupported assumption as an established infrastructure event.

---

## 6. Model Context Protocol

MCP provides the integration layer between the AI application and the observability environment.

Instead of embedding Grafana data directly into the application, the AI service requests the required context through an MCP tool.

The current MCP server exposes:

```text
get_panel_data(dashboard_uid, panel_id)
```

This tool retrieves the configured dashboard panel and returns the relevant Grafana data to the AI application.

The MCP server currently operates through `stdio`, so no dedicated MCP network port is exposed.

---

## 7. Local AI

The project uses:

```text
Ollama
└── Gemma 3 4B
```

The model runs locally, which allows the proof of concept to perform inference without depending on an external AI API.

This architecture also provides an environment for experimenting with:

- local LLM deployment;
- private observability data;
- AI-assisted infrastructure analysis;
- MCP-based context retrieval.

---

## 8. Anomaly Detection

In addition to LLM-based interpretation, the project includes deterministic anomaly detection logic.

The current implementation uses configurable threshold and variation rules to identify potentially abnormal events.

These rules are intentionally simple because the current objective is architectural experimentation rather than production-grade anomaly detection.

Future versions can incorporate statistical baselines, seasonality, machine learning models, and historical context.

---

## 9. Security Considerations

The project is designed around several basic security principles:

- credentials are provided through environment variables;
- `.env` files are excluded from version control;
- Grafana service tokens should use minimum required permissions;
- generated databases and reports are excluded from the repository;
- observability data should be reviewed before being provided to an AI model;
- local inference reduces the need to send monitoring data to external AI services.

The current implementation is a proof of concept and should be hardened before production deployment.

---

## 10. Current Limitations

The current version is intentionally experimental.

Some limitations include:

- the infrastructure metric is simulated;
- anomaly detection uses deterministic thresholds;
- the AI analysis depends on the quality and context of the Grafana panel;
- there is no persistent incident-management workflow;
- there is no authentication layer protecting the AI API;
- the system has not yet been evaluated against a large production dataset.

These limitations define the next stage of development rather than being considered final design decisions.

---

## 11. Future Evolution

Potential future improvements include:

- real infrastructure metrics;
- statistical anomaly detection;
- seasonal baselines;
- correlation between multiple metrics;
- historical incident context;
- machine-learning-based anomaly detection;
- automated alert correlation;
- richer MCP tools;
- operator feedback;
- AI-assisted root-cause analysis;
- automated incident summaries;
- integration with alerting systems.

The long-term goal is to explore how observability platforms can evolve from systems that **show what happened** into systems that can help explain **why it may have happened and what deserves attention**.

---

## 12. Project Status

**Status:** Proof of Concept

**Version:** `v0.1.0`

The project is an experimental AI Engineering and AIOps initiative focused on integrating observability, time-series analysis, MCP and local LLM inference.
