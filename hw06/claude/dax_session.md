1. The measure
dax
Top 10 Client Share =
VAR LastSnap =
    LASTNONBLANK (
        dim_date[date],
        CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) )
    )
VAR TopClients =
    CALCULATETABLE (
        TOPN (
            10,
            VALUES ( dim_client[client_id] ),
            [Ending AUM], DESC,
            dim_client[client_id], ASC          -- tie-breaker: always exactly 10
        ),
        LastSnap
    )
VAR Top10AUM =
    CALCULATE ( [Ending AUM], LastSnap, KEEPFILTERS ( TopClients ) )
VAR TotalAUM =
    CALCULATE ( [Ending AUM], LastSnap )
RETURN
    DIVIDE ( Top10AUM, TotalAUM )

I reused [Ending AUM] everywhere. The one added piece is LastSnap, which uses the same pattern your [AUM-Weighted Alpha] measure already uses. Section 2 explains why it’s needed. DAX ignores case in names, so dim_date[date] here and dim_date[Year] in the query both match the Date and Year columns in your metadata.

2. How the filter context works

Step 1: lock the snapshot date. LastSnap runs in the visual’s filter context. It returns the single latest dim_date[date] that has snapshot rows for whatever is filtered (a year, a tier, or both). For 2024 that’s 2024-12-01.

Why lock it first: [Ending AUM] works out its own last date wherever it’s evaluated. Inside TOPN, it’s evaluated once per client. Without a locked date, a client who left in June 2024 would be ranked by their June balance. That client could then make the top 10 even though they aren’t in the December total, so the top 10 and the total would come from different dates. Wrapping everything in LastSnap makes the ranking, the top-10 sum and the total all use the same date. Within that one date, [Ending AUM] sums across clients only, so it never adds balances across months.

Step 2: what TOPN sees. VALUES ( dim_client[client_id] ) returns the clients still visible after the current filters on dim_client. If the visual is filtered to one client_tier, that’s only that tier’s clients. For each client, TOPN steps into that client’s row (context transition) and evaluates [Ending AUM] with that client and LastSnap as filters. Clients with no snapshot on that date get BLANK, and blanks sort to the bottom.

Why VALUES and not ALL: ALL ( dim_client ) would rank every client in the firm, ignoring the tier filter. The top 10 would be the firm’s top 10. In a single tier, most of them wouldn’t be visible, so the top-10 sum would only include whichever happened to be in that tier. VALUES keeps the ranking inside the current filter.

Step 3: top-10 sum and total. Top10AUM adds the top-10 client list as a filter alongside the existing ones. KEEPFILTERS intersects the list with the current filter instead of replacing it. Since the list is already a subset of the visible clients this changes nothing today, but it protects you if someone later filters on client_id directly. TotalAUM uses the same date and the same filters minus the top-10 list. Dividing the two gives a ratio between 0 and 1.

3. Test query (DAX query view)

The measure is defined inside the query, so this runs before you add it to the model. Once it’s in the model, the definition here temporarily replaces it while the query runs. The QA measures exist only in this query.

dax
DEFINE
    MEASURE _Measures_[Top 10 Client Share] =
        VAR LastSnap = LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
        VAR TopClients =
            CALCULATETABLE (
                TOPN ( 10, VALUES ( dim_client[client_id] ), [Ending AUM], DESC, dim_client[client_id], ASC ),
                LastSnap
            )
        VAR Top10AUM = CALCULATE ( [Ending AUM], LastSnap, KEEPFILTERS ( TopClients ) )
        VAR TotalAUM = CALCULATE ( [Ending AUM], LastSnap )
        RETURN DIVIDE ( Top10AUM, TotalAUM )

    MEASURE _Measures_[QA Snapshot Date] =
        MAXX ( LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) ), dim_date[date] )

    MEASURE _Measures_[QA Top 10 AUM] =
        [Top 10 Client Share] * [Ending AUM]

-- 1) Grand total
EVALUATE
ROW (
    "Snapshot Date", [QA Snapshot Date],
    "Ending Clients", [Ending Clients],
    "Ending AUM", [Ending AUM],
    "Top 10 AUM", [QA Top 10 AUM],
    "Top 10 Client Share", [Top 10 Client Share]
)

-- 2) By year
EVALUATE
SUMMARIZECOLUMNS (
    dim_date[Year],
    "Snapshot Date", [QA Snapshot Date],
    "Ending Clients", [Ending Clients],
    "Ending AUM", [Ending AUM],
    "Top 10 Client Share", [Top 10 Client Share]
)
ORDER BY dim_date[Year]

-- 3) By client tier, 2024 only
EVALUATE
SUMMARIZECOLUMNS (
    dim_client[client_tier],
    TREATAS ( { 2024 }, dim_date[Year] ),
    "Snapshot Date", [QA Snapshot Date],
    "Ending Clients", [Ending Clients],
    "Ending AUM", [Ending AUM],
    "Top 10 Client Share", [Top 10 Client Share]
)
ORDER BY dim_client[client_tier]

-- 4) Eyeball check: the actual 2024 top 10 (should be exactly 10 rows)
EVALUATE
CALCULATETABLE (
    VAR LastSnap = LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
    RETURN
        TOPN (
            10,
            ADDCOLUMNS (
                VALUES ( dim_client[client_id] ),
                "@Tier", CALCULATE ( SELECTEDVALUE ( dim_client[client_tier] ) ),
                "@Ending AUM", CALCULATE ( [Ending AUM], LastSnap )
            ),
            [@Ending AUM], DESC, dim_client[client_id], ASC
        ),
    dim_date[Year] = 2024
)
ORDER BY [@Ending AUM] DESC

What to check:

Result 1 should match the 2024 row of result 2, because both use the 2024-12-01 snapshot.
The @Ending AUM values in result 4 should add up to Top 10 AUM in result 1.
4. Edge cases
Ties at rank 10. On its own, TOPN returns every client tied at the cutoff, so you could get 11 or more clients and an overstated share. The client_id ASC tie-breaker forces exactly 10. Ties are unlikely with decimal AUM, but when one happens, the lower client_id wins, which is an arbitrary choice.
Fewer than 10 clients in the filter. The result is 100%. That’s technically right but misleading, for example on a small tier or a single advisor. To blank it out instead, change the RETURN to IF ( [Ending Clients] < 10, BLANK (), DIVIDE ( Top10AUM, TotalAUM ) ). This reuses your existing [Ending Clients], which works out to the same date.
client_id on rows. Every row shows 100%. Don’t put this measure in a client-level table.
Advisor, benchmark or account_type filters. These filter fact_portfolio_snapshot but don’t flow to dim_client, because relationships are single-direction. VALUES still returns every client, but clients outside the filter get BLANK and the tie-breaker sorts them last, so the result stays correct. It just ranks more rows than it needs to. If an advisor has fewer than 10 clients, blank-AUM clients fill the remaining slots and the share shows 100% (see #2).
Churned clients. A client who left during the year isn’t in that year’s top 10, because they have no December snapshot. That’s correct for a point-in-time measure, but say so if anyone asks “who were our biggest clients in 2024?”
Zero or negative AUM. Negative balances shrink the total and can push the ratio above 1. Run MIN ( fact_portfolio_snapshot[aum] ) to confirm there aren’t any.
Date filters that skip the 1st. Snapshots are dated the 1st, so a slicer range like Dec 15–31 has no snapshot and returns BLANK. December’s balance only appears when Dec 1 is inside the filter.
Tier is today’s tier. dim_client holds one row per client, so 2020 by client_tier groups clients by their current tier, not the tier they had in 2020.
Shares don’t add up. Each tier’s share is that tier’s own top 10 against that tier’s total. The grand-total row is the firm-wide top 10, not a combination of the tier rows. Each year’s row also ranks its own top 10, so the clients can change from year to year.