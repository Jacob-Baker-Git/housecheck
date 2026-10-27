-- HouseCheck USL, generated 2026-10-27 07:08 for GU2 7XH, SO14 5FN, BL4 0LL
-- One statement per Zetaris call; statements separated by '-- @@stmt'.

-- USL: crime profile per postcode, with council and force (3 tables joined)
SELECT a.postcode, a.local_authority, p.police_force, c.crime_month, COUNT(*) AS crimes, SUM(CASE WHEN c.crime_category = 'burglary' THEN 1 ELSE 0 END) AS burglary, SUM(CASE WHEN c.crime_category = 'violent-crime' THEN 1 ELSE 0 END) AS violent, SUM(CASE WHEN c.crime_category = 'anti-social-behaviour' THEN 1 ELSE 0 END) AS antisocial FROM lightning.metastore.housecheck.student_area.area a JOIN lightning.metastore.housecheck.student_area.police_area p ON p.postcode = a.postcode JOIN lightning.metastore.housecheck.student_area.street_crime c ON c.postcode = a.postcode GROUP BY a.postcode, a.local_authority, p.police_force, c.crime_month ORDER BY crimes
-- @@stmt
-- USL: food hygiene per postcode
SELECT a.postcode, COUNT(*) AS food_places, SUM(CASE WHEN f.rating_value IN ('4','5') THEN 1 ELSE 0 END) AS rated_4_or_5, SUM(CASE WHEN f.rating_value IN ('0','1','2') THEN 1 ELSE 0 END) AS rated_0_to_2, ROUND(100.0 * SUM(CASE WHEN f.rating_value IN ('4','5') THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN f.rating_value IN ('0','1','2','3','4','5') THEN 1 ELSE 0 END), 0), 1) AS pct_4_or_5 FROM lightning.metastore.housecheck.student_area.area a LEFT JOIN lightning.metastore.housecheck.student_area.food_establishment f ON f.postcode = a.postcode GROUP BY a.postcode ORDER BY pct_4_or_5 DESC
-- @@stmt
-- USL: do the sources agree on the council? (postcodes.io vs FSA inspector)
SELECT a.postcode, a.local_authority AS council_postcodes_io, f.local_authority AS council_fsa, COUNT(*) AS food_places, CASE WHEN lower(a.local_authority) = lower(f.local_authority) THEN 'agree' ELSE 'CONFLICT' END AS status FROM lightning.metastore.housecheck.student_area.area a JOIN lightning.metastore.housecheck.student_area.food_establishment f ON f.postcode = a.postcode GROUP BY a.postcode, a.local_authority, f.local_authority ORDER BY a.postcode, food_places DESC
-- @@stmt
-- USL: streets with the most recorded crime near each postcode
SELECT c.postcode, c.street_name, COUNT(*) AS crimes FROM lightning.metastore.housecheck.student_area.street_crime c GROUP BY c.postcode, c.street_name ORDER BY crimes DESC LIMIT 15
