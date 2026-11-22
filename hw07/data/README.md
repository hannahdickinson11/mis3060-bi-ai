# `growth_extract.csv`

Built by `scripts/00_make_extract.py` from the cleaned CSVs in `hw06/02_Data/Cleaned/` (the same files the HW6 reconciliation script reads). It is **not** exported from Power BI.

**Grain:** one row per **year × client tier × region**: 5 years (2020–2024) × 3 tiers × 5 regions = **75 rows**.

**Keys**
- `client_tier` comes from `dim_client[client_tier]`, joined on `client_id`. This is each client's *current* tier.
- `region` comes from `dim_advisor[region]`, joined on each fact row's own `advisor_id`. This matches the model's active relationships (`fact_* → dim_advisor`). The `dim_client → dim_advisor` relationship is inactive in the model, so the extract doesn't use it either.

| Column | Type | Definition | Power BI measure |
|---|---|---|---|
| `year` | key | Calendar year | `dim_date[year]` |
| `client_tier` | key | Retail, HNW, UHNW | `dim_client[client_tier]` |
| `region` | key | Advisor's region | `dim_advisor[region]` |
| `ending_aum` | **balance** | Sum of `aum` on the December snapshot of that year | `[Ending AUM]` |
| `ending_aum_ly` | **balance** | `ending_aum` for the same tier and region one year earlier. Blank for 2020, the first year in the data. | `[Ending AUM LY]` |
| `net_flows` | **flow** | Deposits − Withdrawals summed over the calendar year | `[Net Flows]` |
| `market_change` | **flow** | `ending_aum − ending_aum_ly − net_flows`. Blank for 2020. | `[Market Change]` |

**Balance vs flow**
- A **balance** is a point-in-time snapshot (AUM on one date). You can add balances across tiers or regions *within one year*. You **cannot** add them across years: adding Dec 2023 and Dec 2024 AUM counts the same money twice.
- A **flow** is an amount summed over the year. You can add flows across tiers and regions, and across years (for example, total net flows for 2021–2024).

**Blanks:** the 2020 rows are kept. `ending_aum_ly` and `market_change` are blank (not 0) for those rows. Treating them as 0 would make 2020's market change equal to its whole AUM.

**Check:** the 2024 firm totals match the HW6 reconciliation: Ending AUM $12,729,572,078.86, Ending AUM LY $10,644,971,737.00, and Organic Growth Rate 0.73%.
