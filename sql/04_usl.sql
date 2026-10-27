-- HouseCheck USL, generated 2026-10-27 07:08 for GU2 7XH, SO14 5FN, BL4 0LL
-- One statement per Zetaris call; statements separated by '-- @@stmt'.

CREATE NAMESPACE IF NOT EXISTS lightning.metastore
-- @@stmt
CREATE NAMESPACE IF NOT EXISTS lightning.metastore.housecheck
-- @@stmt
COMPILE USL IF NOT EXISTS student_area DEPLOY NAMESPACE lightning.metastore.housecheck DDL
CREATE TABLE area (postcode varchar(8) NOT NULL PRIMARY KEY, lat decimal(9,6), lng decimal(9,6), local_authority varchar(80), ward varchar(120), lsoa varchar(80), region varchar(80));
CREATE TABLE police_area (postcode varchar(8) NOT NULL PRIMARY KEY, police_force varchar(60), neighbourhood varchar(60));
CREATE TABLE street_crime (crime_key varchar(40) NOT NULL PRIMARY KEY, postcode varchar(8) FOREIGN KEY REFERENCES area(postcode), crime_category varchar(60), crime_month varchar(7), street_name varchar(200), outcome varchar(120));
CREATE TABLE food_establishment (food_key varchar(40) NOT NULL PRIMARY KEY, postcode varchar(8) FOREIGN KEY REFERENCES area(postcode), fhrsid varchar(20), business_name varchar(200), business_type varchar(80), rating_value varchar(40), rating_date date, local_authority varchar(80))
-- @@stmt
UPDATE USL lightning.metastore.housecheck.student_area SET DESCRIPTION 'Student rental areas: where a postcode is, who polices it, recorded street crime nearby and the hygiene of food businesses nearby. Built from postcodes.io, police.uk and the FSA.'
-- @@stmt
UPDATE USL lightning.metastore.housecheck.student_area.area SET TABLE DESCRIPTION 'One row per postcode a student is considering, from postcodes.io: coordinates, council, ward and LSOA.'
-- @@stmt
UPDATE USL lightning.metastore.housecheck.student_area.police_area SET TABLE DESCRIPTION 'The police force and neighbourhood team covering the postcode, from police.uk.'
-- @@stmt
UPDATE USL lightning.metastore.housecheck.student_area.street_crime SET TABLE DESCRIPTION 'One recorded street-level crime within about a mile of the postcode in the latest month, from police.uk. Locations are snapped to anonymous points.'
-- @@stmt
UPDATE USL lightning.metastore.housecheck.student_area.food_establishment SET TABLE DESCRIPTION 'One of the nearest food businesses (up to 250, within 0.5 miles) to the postcode, with its FSA hygiene rating and the council that inspects it.'
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.housecheck.student_area.area AS SELECT COALESCE(postcode, '') AS postcode, CAST(lat AS DECIMAL(9,6)) AS lat, CAST(lng AS DECIMAL(9,6)) AS lng, local_authority, ward, lsoa, region FROM housecheck.area_v
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.housecheck.student_area.police_area AS SELECT COALESCE(postcode, '') AS postcode, police_force, neighbourhood FROM housecheck.police_area_v
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.housecheck.student_area.street_crime AS SELECT COALESCE(crime_key, '') AS crime_key, postcode, crime_category, crime_month, street_name, outcome FROM housecheck.street_crime_v
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.housecheck.student_area.food_establishment AS SELECT COALESCE(food_key, '') AS food_key, postcode, fhrsid, business_name, business_type, rating_value, CAST(rating_date AS DATE) AS rating_date, local_authority FROM housecheck.fsa_establishment_v
-- @@stmt
REGISTER DQ dq_area_in_great_britain TABLE lightning.metastore.housecheck.student_area.area AS lat BETWEEN 49.8 AND 60.9 AND lng BETWEEN -8.7 AND 1.8
-- @@stmt
REGISTER DQ dq_crime_month_format TABLE lightning.metastore.housecheck.student_area.street_crime AS crime_month IS NOT NULL AND length(crime_month) = 7
-- @@stmt
REGISTER DQ dq_food_rating_known TABLE lightning.metastore.housecheck.student_area.food_establishment AS rating_value IN ('0','1','2','3','4','5','Exempt','AwaitingInspection','AwaitingPublication','Pass','Improvement Required','Pass and Eat Safe')
-- @@stmt
REGISTER DQ dq_food_rating_dated TABLE lightning.metastore.housecheck.student_area.food_establishment AS rating_value NOT IN ('0','1','2','3','4','5') OR rating_date IS NOT NULL
-- @@stmt
REGISTER DQ dq_food_rating_date_real TABLE lightning.metastore.housecheck.student_area.food_establishment AS rating_date IS NULL OR rating_date >= DATE '2010-01-01'
-- @@stmt
RUN DQ TABLE lightning.metastore.housecheck.student_area.area
-- @@stmt
RUN DQ TABLE lightning.metastore.housecheck.student_area.street_crime
-- @@stmt
RUN DQ TABLE lightning.metastore.housecheck.student_area.food_establishment
-- @@stmt
SHOW DQ ALL INVALID TABLE lightning.metastore.housecheck.student_area.area
-- @@stmt
SHOW DQ ALL INVALID TABLE lightning.metastore.housecheck.student_area.street_crime
-- @@stmt
SHOW DQ ALL INVALID TABLE lightning.metastore.housecheck.student_area.food_establishment
