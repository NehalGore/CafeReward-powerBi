# ☕ Café Rewards — Power BI Dashboard

> End-to-end data analytics project: raw data → data cleaning → feature engineering → star schema modelling → interactive Power BI dashboard


---

## Project Overview

This project analyses a 30-day Starbucks rewards campaign using transactional and offer event data. Starting from 3 raw CSV files with 306,534 rows, the pipeline produces a fully interactive 4-page Power BI dashboard with cross-filtering, DAX measures, and a star schema data model.

**Key Results:**
- $1.78M total revenue across 138,953 transactions
- 44% offer completion rate (76,277 offers sent → 33,579 completed)
- 75.7% offer view rate
- Discount offers outperform BOGO: 58.6% vs 51.4% completion
- 45–59 age group is the largest and highest-spending customer segment
- Peak membership year: 2017 with 6,469 new members

---

## Repository Structure

```
cafe-rewards-powerbi/
│
├── data/
│   ├── raw/                        # Original source files (3 files)
│   │   ├── customers.csv
│   │   ├── offers.csv
│   │   └── events.csv
│   │
│   └── processed/                  # Clean output tables (6 files)
│       ├── dim_customers.csv
│       ├── dim_offers.csv
│       ├── dim_date.csv
│       ├── fact_transactions.csv
│       ├── fact_offer_events.csv
│       └── bridge_customer_offer.csv
│
├── notebooks/
│   └── data_pipeline.ipynb         # Full pipeline: extraction → cleaning → modelling
│
├── dashboard/
│   └── Cafe_Rewards_Dashboard.pbix # Power BI dashboard file
│
├── screenshots/
│   ├── overview_page.png
│   ├── customer_page.png
│   ├── offer_page.png
│   └── revenue_page.png
│
└── README.md
```

---

## Data Pipeline

### Source Data (3 raw files)

| File | Rows | Columns | Description |
|---|---|---|---|
| `customers.csv` | 17,000 | 5 | Customer profiles |
| `offers.csv` | 10 | 6 | Offer catalogue |
| `events.csv` | 306,534 | 4 | All campaign events mixed together |

### Data Cleaning

| Issue | Column | Fix Applied |
|---|---|---|
| Age = 118 (placeholder for unknown) | `customers.age` | Replaced with null |
| Gender null values | `customers.gender` | Filled → "Unknown" |
| Date stored as integer (20170212) | `customers.became_member_on` | Parsed → proper date |
| Value column stored as string dict | `events.value` | `ast.literal_eval()` to parse |
| Inconsistent key name ('offer id' vs 'offer_id') | `events.value` | `.get()` with fallback |
| Channels stored as string list | `offers.channels` | Parsed → 4 binary flag columns |
| All 4 event types mixed in one file | `events.event` | Split into 2 separate fact tables |

### Feature Engineering

| New Column | Table | How Derived |
|---|---|---|
| `age_group` | dim_customers | Buckets: <30 / 30-44 / 45-59 / 60-74 / 75+ |
| `income_group` | dim_customers | Buckets: <40K / 40-60K / 60-80K / 80-120K |
| `membership_year` | dim_customers | Extracted from `became_member_on` |
| `has_email/mobile/social/web` | dim_offers | Binary flags from parsed channels list |
| `roi_pct` | dim_offers | `reward / difficulty × 100` |
| `day` | fact_transactions, fact_offer_events | `hour // 24` |
| `week` | fact_transactions, fact_offer_events | `day // 7 + 1` |
| `amount` | fact_transactions | Extracted from value dict |
| `offer_id` | fact_offer_events | Extracted from value dict |
| `converted` | bridge_customer_offer | 1 if times_completed ≥ 1 |

### Output Tables (Star Schema)

| Table | Type | Rows | Columns | Source |
|---|---|---|---|---|
| `dim_customers` | Dimension | 17,000 | 9 | customers.csv (cleaned + enriched) |
| `dim_offers` | Dimension | 10 | 11 | offers.csv (parsed + enriched) |
| `dim_date` | Dimension | 30 | 5 | Built from scratch |
| `fact_transactions` | Fact | 138,953 | 5 | events.csv (filter: transaction) |
| `fact_offer_events` | Fact | 167,581 | 7 | events.csv (filter: offer events) |
| `bridge_customer_offer` | Bridge | 63,288 | 6 | Aggregated from fact_offer_events |

---

## Data Model Relationships

```
dim_customers ←── fact_transactions        (customer_id, Many:1)
dim_customers ←── fact_offer_events        (customer_id, Many:1)
dim_offers    ←── fact_offer_events        (offer_id,    Many:1)
dim_date      ←── fact_transactions        (day,         Many:1)
dim_date      ←── fact_offer_events        (day,         Many:1)
dim_customers ⟷── bridge_customer_offer   (customer_id, Both directions)
dim_offers    ⟷── bridge_customer_offer   (offer_id,    Both directions)
```

---

## DAX Measures

```dax
Total_Revenue         = SUM(fact_transactions[amount])
Total_Transaction     = COUNTROWS(fact_transactions)
Active_Customers      = DISTINCTCOUNT(fact_transactions[customer_id])
Avg_Transaction_Value = AVERAGE(fact_transactions[amount])
Revenue_per_Customer  = DIVIDE([Total_Revenue], [Active_Customers], 0)
Revenue_Female        = CALCULATE([Total_Revenue], dim_customers[gender]="F")
Revenue_Male          = CALCULATE([Total_Revenue], dim_customers[gender]="M")

Offers_Received    = CALCULATE(COUNTROWS(fact_offer_events), fact_offer_events[event_type]="offer received")
Offers_Viewed      = CALCULATE(COUNTROWS(fact_offer_events), fact_offer_events[event_type]="offer viewed")
Offers_Completed   = CALCULATE(COUNTROWS(fact_offer_events), fact_offer_events[event_type]="offer completed")
View_Rate_Pct      = DIVIDE([Offers_Viewed], [Offers_Received], 0) * 100
Completion_Rate_Pct = DIVIDE([Offers_Completed], [Offers_Received], 0) * 100

Total_Members         = COUNTROWS(dim_customers)
Converted_Customers   = CALCULATE(DISTINCTCOUNT(bridge_customer_offer[customer_id]), bridge_customer_offer[converted]=1)
```

---

## Dashboard Pages

### Page 1 — Overview
KPI cards (Revenue, Transactions, Customers, Completion Rate) · Daily revenue & transaction trend · Revenue by gender donut · Offer funnel bar · Age group stacked bar

### Page 2 — Customer
KPI cards (Members, Female, Male) · Income group treemap · Gender donut · Age × gender stacked bar · Membership growth line chart · Slicers: gender, age_group, income_group

### Page 3 — Offer
KPI cards (Offers Received, Completion Rate, View Rate) · Completion rate gauge · BOGO vs Discount clustered bar · Offer detail table with ROI % · Slicers: offer_type, has_email, duration

### Page 4 — Revenue
KPI cards (Total Revenue, Female Revenue, Male Revenue) · Daily dual-axis trend (revenue + transactions) · Age × income matrix heatmap · Revenue by membership year · Slicers: gender, week_label, membership_year

---

## How to Run

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/cafe-rewards-powerbi.git
cd cafe-rewards-powerbi
```

### 2. Install Python dependencies
```bash
pip install pandas
```

### 3. Run the data pipeline
```bash
jupyter notebook notebooks/data_pipeline.ipynb
```
This generates all 6 processed CSV files in `data/processed/`.

### 4. Open in Power BI
- Open `dashboard/Cafe_Rewards_Dashboard.pbix` in Power BI Desktop
- Or import the 6 CSVs from `data/processed/` manually and follow the data model setup

---

## Tools & Technologies

- Python 3.x · Pandas · ast (standard library)
- Power BI Desktop
- DAX (Data Analysis Expressions)
- Star Schema data modelling

---

## Key Insights

1. Discount offers (58.6% completion) convert better than BOGO (51.4%) — price savings matter more than free items
2. The 45–59 age group is the largest segment and generates the highest revenue
3. Female and male customers contribute nearly equal revenue ($863K vs $844K)
4. Revenue peaked in Week 4 of the campaign, suggesting delayed offer response
5. Customers who joined in 2017 (peak acquisition year) are now the highest-spending cohort

---

## Author

**Nehal Gore**
MCA (AI & ML) · Ramdeobaba University, Nagpur


---

*Dataset: Starbucks Rewards Offers (public dataset)*
