To: Mingfei Chen <mingfeichen@lbl.gov>
Cc: Hasan Yasini <HasanYasini@lbl.gov>
Subject: Questions before loading the RecycNec / cell-wall enrichment 16S data into CORAL

Hi Mingfei,

We're getting ready to load the 16S amplicon data from Enrichments/RecycNec on the ENIGMA team
drive (sequencing set Bri_1-2: 192 libraries, 1,466 ASVs) into CORAL and the ENIGMA Lakehouse. It
covers the fresh/recycled necromass enrichments and Hasan's cell-wall and phosphate enrichments. I
understand Bri has moved on, so I'm sending these to you; please forward anything Hasan or someone
else can answer more easily. Questions 1-3 block the load; the rest we can work around.

Inoculum (blocking)

1. Every row of Bri_1-2_meta.tsv gives the inoculum as 20251210_L7-SZ2_Isolations (one row says
   L7-SZ). CORAL has no L7 sample from 2025-12-10; the closest are the Hazen-lab bottles
   20251208-L7-SZ1-UF and 20251208-L7-SZ2-UF from 2025-12-08. Which date was the groundwater
   collected?
2. Which zone(s) did each experiment start from? The lab's 2026 progress report says the necromass
   enrichments used SSO-L7-SZ1 and SZ2, and the cell-wall/phosphate enrichments used SSO-L7-SZ1,
   but the metadata lists L7-SZ2 for all of them. Were SZ1 and SZ2 water kept separate or pooled
   (the three "L7-SZ1-SZ2-inocula" libraries suggest pooling for some)?
3. What are the six filter libraries? "L7-SZ1-SZ2-inocula-1/2/3" and "sz1 a/b/c": is each the
   starting groundwater filtered at time zero, and from which zone and what volume?

Sample labels

4. "cntrl-pyruva-7Ana-2-T4" appears twice: 926R_inline22 IT061 (plate well F1) and IT065 (F5). No
   library is labelled "cntrl-pyruva-7Aer-2-T4", and the F-row layout suggests F5 is that sample.
   Is that right?
5. "cntrl-pyruva-7Aer-1-T3" (IT055) is filed under the Ground-Water-Cell-Wall-Enrichments
   campaign, but all its sibling pyruvate controls are RecycNec. Should it be RecycNec?
6. "Recyc-Arthro-7Ana-1-T4" (926R_inline21 IT094) has no reads in the count table. We'll leave it
   out as a failed library unless you know otherwise.

Experimental details (helpful, not blocking)

7. Timepoints T1-T5 are days 2, 6, 11, 13 and 27 for the necromass bottles. Do the pyruvate controls
   (no day recorded) follow the same days? For the cell-wall set, w1/w2/w4 are 7/14/28 days, but
   "nag/nam-cell-wall-w1-2" is recorded as day 14, and "nag/nam-cell-wall-w1-1" has no day. Which
   is correct?
8. Which strains produced the necromass ("Pseudo" and "Arthro"; the Pseudomonas and Arthrobacter
   cell walls), and which strains make up the syncom in "syncom t0-1/2/3"? If they are ENIGMA
   isolates, we would link them to their strain records.
9. The metadata gives a sequencing date of 2026-02-13; the Readme says 3/25/2026. Which is right?
10. Do you want any hold on the Lakehouse release until the manuscripts are out? CORAL/Lakehouse
    access is limited to ENIGMA, and we can record a citation once one exists.

Also two older questions from the 2024 SSO pilot time series that were waiting on Bri
(20241220_IC_results_SSO_timeseries.xlsx,
https://drive.google.com/file/d/1QcKS8yYId740wf3LHO7J0fsEnyty_0Yh/view):

11. The pilot time-series metadata registers 19 "-ICTOC" bottles for each of 2024-09-09, 09-18 and
    10-14, but the IC workbook has only the first two dates and no TOC/TN. Were the 2024-10-14 IC
    samples and the time-series TOC/TN run, and if so, where are the results?
12. For L8-SZ1 and L8-SZ2 the sampling_period label and Date Sampled disagree (T1 rows dated 09-18,
    T2 rows dated 09-09). We loaded them by the T1/T2 label. Is that right for L8?

Thanks!
John-Marc
