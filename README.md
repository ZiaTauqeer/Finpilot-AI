# FinPilot

<div align="center">

### Intelligent Personal Finance Management Powered by AI

Automatically transform transaction SMS messages into structured financial insights, spending analytics, and predictive budgeting recommendations.

</div>

---

## Overview

FinPilot is an AI-powered personal finance platform that automatically captures and analyzes financial transaction SMS messages to provide users with a comprehensive view of their spending behavior.

By leveraging Large Language Models (LLMs), machine learning, and forecasting techniques, FinPilot converts unstructured transaction notifications into categorized financial records, actionable insights, and forward-looking budget forecasts. The platform enables users to monitor expenses, understand spending patterns, and make informed financial decisions without manual data entry.

---

## Key Capabilities

### Automated Transaction Monitoring

FinPilot continuously monitors transaction-related SMS notifications and extracts relevant financial information, including:

- Transaction amount
- Merchant or payee information
- Transaction type (debit, credit, transfer, etc.)
- Date and time
- Account references (where applicable)

The extraction pipeline is designed to handle transaction formats from multiple banks, payment providers, and financial institutions.

### AI-Driven Expense Categorization

Using LLM-powered classification models, FinPilot automatically categorizes transactions into meaningful spending groups such as:

- Food & Dining
- Groceries
- Transportation
- Shopping
- Entertainment
- Utilities
- Healthcare
- Education
- Travel
- Investments
- Subscriptions
- Miscellaneous

The categorization engine continuously improves accuracy through contextual understanding and merchant intelligence.

### Budget Management

FinPilot helps users establish and maintain financial discipline through:

- Monthly and custom budget creation
- Category-level spending limits
- Real-time budget utilization tracking
- Budget performance reporting
- Variance analysis against spending targets

### Predictive Financial Forecasting

Advanced forecasting models analyze historical spending behavior to provide:

- End-of-month expenditure projections
- Category-level spending forecasts
- Budget overrun predictions
- Cash flow trend analysis
- Financial planning recommendations

### Intelligent Financial Insights

FinPilot generates personalized insights that help users better understand their finances, including:

- Spending trend analysis
- Unusual transaction detection
- Recurring subscription identification
- Merchant-level expenditure summaries
- Savings opportunities
- Personalized budgeting recommendations

### Proactive Alerts

Users can receive timely notifications for:

- Budget threshold breaches
- Projected overspending risks
- Unusual spending activity
- Significant spending changes
- Upcoming recurring expenses

---

## How It Works

```text
SMS Transaction Notification
            │
            ▼
    Transaction Extraction
            │
            ▼
      Data Normalization
            │
            ▼
    AI Categorization Engine
            │
            ▼
      Financial Analytics
            │
     ┌──────┼──────┐
     ▼      ▼      ▼
 Budgets  Insights Forecasts
```

---

## Example Workflow

### Incoming SMS

```text
Your account XX1234 has been debited INR 450.00 at Starbucks Mumbai on 15-Jan-2026.
Available balance: INR 12,540.00.
```

### Structured Transaction

```json
{
  "amount": 450.00,
  "currency": "INR",
  "merchant": "Starbucks",
  "transaction_type": "debit",
  "timestamp": "2026-01-15T10:32:00"
}
```

### AI Classification

```json
{
  "category": "Food & Dining",
  "confidence_score": 0.98
}
```

---

## Artificial Intelligence Architecture

### Large Language Models (LLMs)

LLMs are utilized for:

- Merchant normalization
- Transaction understanding
- Expense categorization
- Financial insight generation
- Natural language financial analysis

### Machine Learning

Machine learning models support:

- Behavioral spending analysis
- Anomaly detection
- Subscription identification
- User-specific categorization refinement
- Spending pattern recognition

### Forecasting Engine

Forecasting models enable:

- Monthly spending projections
- Budget forecasting
- Trend analysis
- Cash flow prediction
- Financial planning support

---

## Privacy & Security

FinPilot is designed with a privacy-first architecture.

Key principles include:

- Explicit user consent for SMS access
- Secure storage of financial data
- Encryption of sensitive information
- Minimal data collection practices
- Transparent data processing policies

FinPilot does not require access to banking credentials and operates solely on transaction notifications provided through authorized SMS permissions.

---

## Benefits

- Fully automated expense tracking
- Elimination of manual transaction entry
- Accurate AI-powered categorization
- Data-driven budgeting assistance
- Predictive spending intelligence
- Improved financial awareness
- Personalized recommendations for better money management

---

## Technology Stack

### Frontend

- Vue 3
- TypeScript
- Vite
- Tailwind CSS

### Backend

- Python
- FastAPI

### Artificial Intelligence & Analytics

- Large Language Models (LLMs)
- Machine Learning Models
- Time-Series Forecasting Models

### Data Storage

- PostgreSQL

### Deployment & Infrastructure

- Docker
- Nginx
- Cloud Infrastructure (AWS, Azure, or GCP)

---

## Future Roadmap

- Multi-bank transaction aggregation
- Investment and portfolio tracking
- Savings goal planning
- Bill and subscription management
- Family and shared budgeting
- OCR-based receipt processing
- AI financial assistant
- Advanced wealth analytics
- Personalized financial health scoring

---

## Mission

FinPilot's mission is to simplify personal finance management through intelligent automation. By combining SMS-based transaction monitoring with artificial intelligence and predictive analytics, FinPilot empowers individuals to gain greater visibility into their finances, improve budgeting habits, and make more informed financial decisions.

---

## License

This project is licensed under the MIT License.

---

**FinPilot** — Intelligent Finance. Simplified.

