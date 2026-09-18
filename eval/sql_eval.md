# Part 1 eval -- BI questions over the extracted ticket table

Ground truth computed directly from `data/tickets_ground_truth.csv` by
`scripts/generate_tickets.py`. Use these to check that the table you built with
`ML.GENERATE_TEXT` actually agrees with what is in the prose.

Extraction will not be perfect, and that is the point -- the gap between these
numbers and the ones your extracted table produces is the most honest thing you
can put on screen in Part 1.

## Q1. Which fulfillment center is slowest to resolve tickets?

**Answer: Rotterdam NL (8.7 days average, against 5.3 for Reno NV).** This is the planted operational finding.

| Fulfillment center | Tickets | Avg resolution days |
|---|---|---|
| Rotterdam NL | 45 | 8.7 |
| Harrisburg PA | 50 | 5.9 |
| Reno NV | 85 | 5.3 |

## Q2. Which payment methods take longest to close out?

**Answer: Klarna Pay-in-4 (9.7 days), Shop Pay (8.1 days).** Instalment providers reschedule on their own cycle
rather than ours, so a ticket that touches one stays open longer. Note that
Klarna is EU-only in this dataset, so its tickets also carry the Rotterdam drag
from Q1 -- worth pointing out on camera as a confounder rather than pretending
the two effects are independent.

| Payment method | Tickets | Avg resolution days |
|---|---|---|
| Klarna Pay-in-4 | 12 | 9.7 |
| Shop Pay | 17 | 8.1 |
| Apple Pay | 20 | 6.4 |
| Mastercard | 26 | 6.1 |
| Visa | 43 | 5.9 |

## Q3. Ticket volume and refund exposure by issue category

| Issue category | Tickets | Total refunded |
|---|---|---|
| shipping_delay | 32 | $1,158.85 |
| warranty_claim | 29 | $0.00 |
| return_request | 27 | $4,661.50 |
| exchange_sizing | 23 | $0.00 |
| refund_status | 21 | $3,644.00 |
| damaged_in_transit | 10 | $313.00 |
| lost_parcel | 10 | $502.00 |
| payment_declined | 7 | $0.00 |
| product_question | 7 | $0.00 |
| duties_customs | 6 | $936.50 |
| address_change | 5 | $0.00 |
| order_cancellation | 3 | $129.00 |

## Q4. Which product drives the most warranty claims?

**Answer: Summit GTX Hiking Boot -- 11 of 29 warranty claims in the corpus**, and the failure mode is consistently sole
separation. This is the product-quality finding worth building the segment
around.

| Product | Warranty claims |
|---|---|
| Summit GTX Hiking Boot | 11 |
| Basecamp Unisex Tee | 3 |
| Cache 10K Power Bank | 3 |
| Switchback Trail-Stretch Pant | 2 |
| Belay Glove | 2 |

## Q5. When do EU/UK shipping delays cluster?

**Answer: December and January.** Filter `issue_category = 'shipping_delay'`
and `region IN ('EU','UK')`, then group by month of `opened_date`. Busiest
months in this corpus: 2025-12 (4), 2026-01 (3). The peak-season DHL Express backlog is visible
in the data and ties directly back to the holiday cut-off dates in
`data/kb/holiday-shipping-and-peak-season.md`.

## Suggested extraction schema

```
ticket_id, opened_date, channel, agent, issue_category, priority, order_id,
sku, product_name, product_category, region, fulfillment_center, carrier,
payment_method, resolution_days, refund_amount_usd, outcome, csat
```

`refund_amount_usd` and `csat` are deliberately NULL on a good share of tickets.
Null handling is worth one minute of screen time; it is where naive extraction
prompts hallucinate zeros.
