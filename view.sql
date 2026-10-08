-- 1) Indexes (run once). The covering index lets MySQL read UB/UH
-- straight from the index without touching process_raw rows.
CREATE INDEX ix_pr_hid_cover
    ON process_raw (ProcessR_ProcessHID, ProcessR_RokokKe, ProcessR_UB, ProcessR_UH);
CREATE INDEX ix_ph_leader ON process_header (ProcessH_LeaderID);
CREATE INDEX ix_ph_staff ON process_header (ProcessH_StaffID);

-- 2) Same columns, same values, same grouping — no derived table,
-- no second join to process_header.
-- Slot rule is unchanged: scale 1 -> RokokKe, scale 2 -> RokokKe + 3,
-- any other scale_no -> NULL (row still counts toward Avg CW).
CREATE OR REPLACE VIEW daily_report AS
SELECT
    l.Emp_ID AS `ID GL`,
    l.Emp_Name AS `Nama GL`,
    s.Emp_ID AS `ID PPSKT`,
    s.Emp_Name AS `Nama PPSKT`,

    -- UB
    ROUND(AVG(CASE WHEN (CASE ph.scale_no WHEN 1 THEN pr.ProcessR_RokokKe WHEN 2 THEN pr.ProcessR_RokokKe + 3 END) = 1 THEN pr.ProcessR_UB END),2) AS `UB [1]`,
    ROUND(AVG(CASE WHEN (CASE ph.scale_no WHEN 1 THEN pr.ProcessR_RokokKe WHEN 2 THEN pr.ProcessR_RokokKe + 3 END) = 2 THEN pr.ProcessR_UB END),2) AS `UB [2]`,
    ROUND(AVG(CASE WHEN (CASE ph.scale_no WHEN 1 THEN pr.ProcessR_RokokKe WHEN 2 THEN pr.ProcessR_RokokKe + 3 END) = 3 THEN pr.ProcessR_UB END),2) AS `UB [3]`,
    ROUND(AVG(CASE WHEN (CASE ph.scale_no WHEN 1 THEN pr.ProcessR_RokokKe WHEN 2 THEN pr.ProcessR_RokokKe + 3 END) = 4 THEN pr.ProcessR_UB END),2) AS `UB [4]`,
    ROUND(AVG(CASE WHEN (CASE ph.scale_no WHEN 1 THEN pr.ProcessR_RokokKe WHEN 2 THEN pr.ProcessR_RokokKe + 3 END) = 5 THEN pr.ProcessR_UB END),2) AS `UB [5]`,
    ROUND(AVG(CASE WHEN (CASE ph.scale_no WHEN 1 THEN pr.ProcessR_RokokKe WHEN 2 THEN pr.ProcessR_RokokKe + 3 END) = 6 THEN pr.ProcessR_UB END),2) AS `UB [6]`,

    -- UH
    ROUND(AVG(CASE WHEN (CASE ph.scale_no WHEN 1 THEN pr.ProcessR_RokokKe WHEN 2 THEN pr.ProcessR_RokokKe + 3 END) = 1 THEN pr.ProcessR_UH END),2) AS `UH [1]`,
    ROUND(AVG(CASE WHEN (CASE ph.scale_no WHEN 1 THEN pr.ProcessR_RokokKe WHEN 2 THEN pr.ProcessR_RokokKe + 3 END) = 2 THEN pr.ProcessR_UH END),2) AS `UH [2]`,
    ROUND(AVG(CASE WHEN (CASE ph.scale_no WHEN 1 THEN pr.ProcessR_RokokKe WHEN 2 THEN pr.ProcessR_RokokKe + 3 END) = 3 THEN pr.ProcessR_UH END),2) AS `UH [3]`,
    ROUND(AVG(CASE WHEN (CASE ph.scale_no WHEN 1 THEN pr.ProcessR_RokokKe WHEN 2 THEN pr.ProcessR_RokokKe + 3 END) = 4 THEN pr.ProcessR_UH END),2) AS `UH [4]`,
    ROUND(AVG(CASE WHEN (CASE ph.scale_no WHEN 1 THEN pr.ProcessR_RokokKe WHEN 2 THEN pr.ProcessR_RokokKe + 3 END) = 5 THEN pr.ProcessR_UH END),2) AS `UH [5]`,
    ROUND(AVG(CASE WHEN (CASE ph.scale_no WHEN 1 THEN pr.ProcessR_RokokKe WHEN 2 THEN pr.ProcessR_RokokKe + 3 END) = 6 THEN pr.ProcessR_UH END),2) AS `UH [6]`,

    -- Average gabungan
    ROUND(AVG(pr.ProcessR_UB),2) AS `Avg CW [1]`,
    ROUND(AVG(pr.ProcessR_UH),2) AS `Avg CW [2]`,

    MIN(ph.start_at) AS `Start`,
    MAX(ph.end_at) AS `End`,
    DATE(MIN(ph.created_at)) AS `Tanggal`

FROM process_header ph
JOIN member l ON l.Member_ID = ph.ProcessH_LeaderID
JOIN member s ON s.Member_ID = ph.ProcessH_StaffID
JOIN process_raw pr ON pr.ProcessR_ProcessHID = ph.ProcessH_ID

GROUP BY
    l.Emp_ID,
    l.Emp_Name,
    s.Emp_ID,
    s.Emp_Name,
    ph.start_at;
