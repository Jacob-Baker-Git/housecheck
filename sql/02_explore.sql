-- HouseCheck USL, generated 2026-10-27 07:08 for GU2 7XH, SO14 5FN, BL4 0LL
-- One statement per Zetaris call; statements separated by '-- @@stmt'.

-- postcodes.io: where is it and who runs it?
SELECT result.postcode, result.admin_district, result.admin_ward, result.lsoa FROM housecheck_live.pc_gu27xh
-- @@stmt
-- postcodes.io: which other geographies does it sit in?
SELECT result.region, result.parliamentary_constituency, result.codes.admin_district AS council_code FROM housecheck_live.pc_gu27xh
-- @@stmt
-- police.uk: which force and neighbourhood team?
SELECT force, neighbourhood FROM housecheck_live.hood_gu27xh
-- @@stmt
-- police.uk: crimes by category, latest month
SELECT category, month, COUNT(*) AS n FROM housecheck_live.crime_gu27xh GROUP BY category, month ORDER BY n DESC
-- @@stmt
-- police.uk: what happened to them? (outcomes)
SELECT outcome_status.category AS outcome, COUNT(*) AS n FROM housecheck_live.crime_gu27xh GROUP BY outcome_status.category ORDER BY n DESC
-- @@stmt
-- police.uk: busiest streets
SELECT location.street.name AS street, COUNT(*) AS n FROM housecheck_live.crime_gu27xh GROUP BY location.street.name ORDER BY n DESC LIMIT 10
-- @@stmt
-- FSA: hygiene rating distribution
SELECT e.RatingValue AS rating, COUNT(*) AS n FROM housecheck_live.fsa_gu27xh LATERAL VIEW explode(establishments) AS e GROUP BY e.RatingValue ORDER BY rating
-- @@stmt
-- FSA: what kinds of food business?
SELECT e.BusinessType AS business_type, COUNT(*) AS n FROM housecheck_live.fsa_gu27xh LATERAL VIEW explode(establishments) AS e GROUP BY e.BusinessType ORDER BY n DESC
-- @@stmt
-- FSA: which councils inspect them, and how recently?
SELECT e.LocalAuthorityName AS council, COUNT(*) AS n, MIN(e.RatingDate) AS oldest, MAX(e.RatingDate) AS newest FROM housecheck_live.fsa_gu27xh LATERAL VIEW explode(establishments) AS e GROUP BY e.LocalAuthorityName
