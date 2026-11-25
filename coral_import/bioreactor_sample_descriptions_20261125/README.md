# Bioreactor sample descriptions, 2026-11-25 (in place)

`Sample0002965` (Bioreactor Coupon, 2014-12-24) and `Sample0002966` (Matthew Fields Bioreactor, 2014-06-10) at FW-305 are not
sediment from the well: they stand for material from Fields Lab laboratory biofilm reactors (CDC reactors, glass-bead coupons)
fed FW-305 groundwater (Kothari et al. 2021, mSystems, PMID 34184913: methods and Table S2). Only the description was changed
(`01_update_descriptions.py`, guarded AQL); name, location, date, depth, material and package are as recorded.

Why nothing else (user, 2026-11-25): the depth (5.61975 m) equals that of every FW-305 groundwater sample and presumably refers
to the groundwater that fed or inoculated the reactors; the 2014-12-24 date has no evidence for or against; 43 of the 52 isolates
are described as from bulk groundwater and 9 as from coupons (all 27 of "Bioreactor Coupon" from bulk groundwater), so no single
material fits and splitting the samples would need records of how the reactors were sampled, which are not expected to exist.
Candidate terms noted but not used: `biofilm material` ENVO:01000156, `anthropogenic environmental material` ENVO:0010001,
package `microbial mat|biofilm` MIxS:0000011.

Lakehouse: sync-20261125-134831, `sdt_sample` reloaded; the download differs from the previous one in these two descriptions only.
