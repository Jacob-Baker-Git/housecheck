# Zetaris USL run: GU2 7XH, SO14 5FN, BL4 0LL

Run at 2026-10-27 07:08 against the local Zetaris platform.

| Phase | Step | Status | ms | Rows |
|---|---|---|---|---|
| onboard | CREATE LIGHTNING DATABASE HOUSECHECK_LIVE DESCRIBE BY "HouseCheck live public data from po | exists | 137 | 0 |
| onboard | CREATE LIGHTNING REST TABLE crime_updated FROM HOUSECHECK_LIVE | exists | 157 | 0 |
| onboard | CREATE LIGHTNING REST TABLE pc_gu27xh FROM HOUSECHECK_LIVE | exists | 183 | 0 |
| onboard | CREATE LIGHTNING REST TABLE pc_so145fn FROM HOUSECHECK_LIVE | exists | 183 | 0 |
| onboard | CREATE LIGHTNING REST TABLE pc_bl40ll FROM HOUSECHECK_LIVE | exists | 150 | 0 |
| onboard | coordinates for GU2 7XH | ok | 357 | 1 |
| onboard | coordinates for SO14 5FN | ok | 283 | 1 |
| onboard | coordinates for BL4 0LL | ok | 367 | 1 |
| onboard | register hood_gu27xh (police.uk) | exists | 149 | 0 |
| onboard | register crime_gu27xh (police.uk) | exists | 200 | 0 |
| onboard | register fsa_gu27xh (FSA food hygiene) | exists | 149 | 0 |
| onboard | register hood_so145fn (police.uk) | exists | 149 | 0 |
| onboard | register crime_so145fn (police.uk) | exists | 158 | 0 |
| onboard | register fsa_so145fn (FSA food hygiene) | exists | 184 | 0 |
| onboard | register hood_bl40ll (police.uk) | exists | 149 | 0 |
| onboard | register crime_bl40ll (police.uk) | exists | 149 | 0 |
| onboard | register fsa_bl40ll (FSA food hygiene) | exists | 150 | 0 |
| explore | postcodes.io: where is it and who runs it? | ok | 375 | 1 |
| explore | postcodes.io: which other geographies does it sit in? | ok | 291 | 1 |
| explore | police.uk: which force and neighbourhood team? | ok | 332 | 1 |
| explore | police.uk: crimes by category, latest month | ok | 367 | 14 |
| explore | police.uk: what happened to them? (outcomes) | ok | 450 | 7 |
| explore | police.uk: busiest streets | ok | 366 | 10 |
| explore | FSA: hygiene rating distribution | ok | 499 | 7 |
| explore | FSA: what kinds of food business? | ok | 493 | 12 |
| explore | FSA: which councils inspect them, and how recently? | ok | 466 | 1 |
| probe | police.uk neighbourhood has data for GU2 7XH? | ok | 299 | 1 |
| probe | police.uk street crime has data for GU2 7XH? | ok | 375 | 1 |
| probe | FSA food hygiene has data for GU2 7XH? | ok | 432 | 1 |
| probe | police.uk neighbourhood has data for SO14 5FN? | ok | 259 | 1 |
| probe | police.uk street crime has data for SO14 5FN? | ok | 299 | 1 |
| probe | FSA food hygiene has data for SO14 5FN? | ok | 406 | 1 |
| probe | police.uk neighbourhood has data for BL4 0LL? | ok | 268 | 1 |
| probe | police.uk street crime has data for BL4 0LL? | NO DATA | 192 | 0 |
| probe | FSA food hygiene has data for BL4 0LL? | ok | 349 | 1 |
| views | CREATE SCHEMASTORE CONTAINER housecheck | exists | 166 | 0 |
| views | CREATE SCHEMASTORE VIEW area_v WITH CONTAINER housecheck | exists | 225 | 0 |
| views | CREATE SCHEMASTORE VIEW police_area_v WITH CONTAINER housecheck | exists | 150 | 0 |
| views | CREATE SCHEMASTORE VIEW street_crime_v WITH CONTAINER housecheck | exists | 284 | 0 |
| views | CREATE SCHEMASTORE VIEW fsa_establishment_v WITH CONTAINER housecheck | exists | 203 | 0 |
| usl | CREATE NAMESPACE IF NOT EXISTS lightning.metastore | created | 137 | 0 |
| usl | CREATE NAMESPACE IF NOT EXISTS lightning.metastore.housecheck | created | 141 | 0 |
| usl | COMPILE USL IF NOT EXISTS student_area DEPLOY NAMESPACE lightning.metastore.housecheck DDL | created | 182 | 0 |
| usl | UPDATE USL lightning.metastore.housecheck.student_area SET DESCRIPTION 'Student rental are | created | 141 | 0 |
| usl | UPDATE USL lightning.metastore.housecheck.student_area.area SET TABLE DESCRIPTION 'One row | created | 199 | 0 |
| usl | UPDATE USL lightning.metastore.housecheck.student_area.police_area SET TABLE DESCRIPTION ' | created | 141 | 0 |
| usl | UPDATE USL lightning.metastore.housecheck.student_area.street_crime SET TABLE DESCRIPTION  | created | 141 | 0 |
| usl | UPDATE USL lightning.metastore.housecheck.student_area.food_establishment SET TABLE DESCRI | created | 142 | 0 |
| usl | ACTIVATE USL TABLE lightning.metastore.housecheck.student_area.area AS SELECT COALESCE(pos | created | 425 | 0 |
| usl | ACTIVATE USL TABLE lightning.metastore.housecheck.student_area.police_area AS SELECT COALE | created | 383 | 0 |
| usl | ACTIVATE USL TABLE lightning.metastore.housecheck.student_area.street_crime AS SELECT COAL | created | 357 | 0 |
| usl | ACTIVATE USL TABLE lightning.metastore.housecheck.student_area.food_establishment AS SELEC | created | 425 | 0 |
| usl | REGISTER DQ dq_area_in_great_britain TABLE lightning.metastore.housecheck.student_area.are | created | 1107 | 0 |
| usl | REGISTER DQ dq_crime_month_format TABLE lightning.metastore.housecheck.student_area.street | created | 1049 | 0 |
| usl | REGISTER DQ dq_food_rating_known TABLE lightning.metastore.housecheck.student_area.food_es | created | 1600 | 0 |
| usl | REGISTER DQ dq_food_rating_dated TABLE lightning.metastore.housecheck.student_area.food_es | created | 1360 | 0 |
| usl | REGISTER DQ dq_food_rating_date_real TABLE lightning.metastore.housecheck.student_area.foo | created | 1418 | 0 |
| usl | RUN DQ TABLE lightning.metastore.housecheck.student_area.area | ok | 4096 | 2 |
| usl | RUN DQ TABLE lightning.metastore.housecheck.student_area.street_crime | ok | 5445 | 3 |
| usl | RUN DQ TABLE lightning.metastore.housecheck.student_area.food_establishment | ok | 12900 | 5 |
| usl | SHOW DQ ALL INVALID TABLE lightning.metastore.housecheck.student_area.area | ok | 6291 | 0 |
| usl | SHOW DQ ALL INVALID TABLE lightning.metastore.housecheck.student_area.street_crime | ok | 8993 | 0 |
| usl | SHOW DQ ALL INVALID TABLE lightning.metastore.housecheck.student_area.food_establishment | ok | 14586 | 70 |
| query | USL: crime profile per postcode, with council and force (3 tables joined) | ok | 2915 | 2 |
| query | USL: food hygiene per postcode | ok | 2317 | 3 |
| query | USL: do the sources agree on the council? (postcodes.io vs FSA inspector) | ok | 2252 | 3 |
| query | USL: streets with the most recorded crime near each postcode | ok | 1063 | 15 |

## onboard: coordinates for GU2 7XH

```sql
SELECT result.postcode AS postcode, result.latitude AS lat, result.longitude AS lng, result.admin_district AS admin_district, result.admin_ward AS ward, result.lsoa AS lsoa FROM housecheck_live.pc_gu27xh
```

| postcode | lat | lng | admin_district | ward | lsoa |
|---|---|---|---|---|---|
| GU2 7XH | 51.242685 | -0.587936 | Guildford | Onslow | Guildford 015C |

## onboard: coordinates for SO14 5FN

```sql
SELECT result.postcode AS postcode, result.latitude AS lat, result.longitude AS lng, result.admin_district AS admin_district, result.admin_ward AS ward, result.lsoa AS lsoa FROM housecheck_live.pc_so145fn
```

| postcode | lat | lng | admin_district | ward | lsoa |
|---|---|---|---|---|---|
| SO14 5FN | 50.902555 | -1.392459 | Southampton | Bargate | Southampton 033C |

## onboard: coordinates for BL4 0LL

```sql
SELECT result.postcode AS postcode, result.latitude AS lat, result.longitude AS lng, result.admin_district AS admin_district, result.admin_ward AS ward, result.lsoa AS lsoa FROM housecheck_live.pc_bl40ll
```

| postcode | lat | lng | admin_district | ward | lsoa |
|---|---|---|---|---|---|
| BL4 0LL | 53.553729 | -2.450055 | Bolton | Hulton | Bolton 026C |

## explore: postcodes.io: where is it and who runs it?

```sql
SELECT result.postcode, result.admin_district, result.admin_ward, result.lsoa FROM housecheck_live.pc_gu27xh
```

| postcode | admin_district | admin_ward | lsoa |
|---|---|---|---|
| GU2 7XH | Guildford | Onslow | Guildford 015C |

## explore: postcodes.io: which other geographies does it sit in?

```sql
SELECT result.region, result.parliamentary_constituency, result.codes.admin_district AS council_code FROM housecheck_live.pc_gu27xh
```

| region | parliamentary_constituency | council_code |
|---|---|---|
| South East | Guildford | E07000209 |

## explore: police.uk: which force and neighbourhood team?

```sql
SELECT force, neighbourhood FROM housecheck_live.hood_gu27xh
```

| force | neighbourhood |
|---|---|
| surrey | GDOU |

## explore: police.uk: crimes by category, latest month

```sql
SELECT category, month, COUNT(*) AS n FROM housecheck_live.crime_gu27xh GROUP BY category, month ORDER BY n DESC
```

| category | month | n |
|---|---|---|
| violent-crime | 2026-08 | 185 |
| anti-social-behaviour | 2026-08 | 79 |
| shoplifting | 2026-08 | 76 |
| public-order | 2026-08 | 64 |
| criminal-damage-arson | 2026-08 | 38 |
| other-theft | 2026-08 | 37 |
| drugs | 2026-08 | 26 |
| vehicle-crime | 2026-08 | 16 |
| other-crime | 2026-08 | 8 |
| burglary | 2026-08 | 7 |
| robbery | 2026-08 | 6 |
| possession-of-weapons | 2026-08 | 5 |
| theft-from-the-person | 2026-08 | 4 |
| bicycle-theft | 2026-08 | 3 |

## explore: police.uk: what happened to them? (outcomes)

```sql
SELECT outcome_status.category AS outcome, COUNT(*) AS n FROM housecheck_live.crime_gu27xh GROUP BY outcome_status.category ORDER BY n DESC
```

| outcome | n |
|---|---|
| Under investigation | 282 |
| Unable to prosecute suspect | 83 |
| null | 79 |
| Investigation complete; no suspect identified | 70 |
| Awaiting court outcome | 21 |
| Local resolution | 18 |
| Offender given a caution | 1 |

## explore: police.uk: busiest streets

```sql
SELECT location.street.name AS street, COUNT(*) AS n FROM housecheck_live.crime_gu27xh GROUP BY location.street.name ORDER BY n DESC LIMIT 10
```

| street | n |
|---|---|
| On or near Genyn Road | 52 |
| On or near Supermarket | 40 |
| On or near Shopping Area | 30 |
| On or near Theatre/concert Hall | 25 |
| On or near Parking Area | 24 |
| On or near Chapel Street | 21 |
| On or near Police Station | 21 |
| On or near Bridge Street | 18 |
| On or near Europa Park Road | 16 |
| On or near Petrol Station | 16 |

## explore: FSA: hygiene rating distribution

```sql
SELECT e.RatingValue AS rating, COUNT(*) AS n FROM housecheck_live.fsa_gu27xh LATERAL VIEW explode(establishments) AS e GROUP BY e.RatingValue ORDER BY rating
```

| rating | n |
|---|---|
| 1 | 3 |
| 2 | 1 |
| 3 | 14 |
| 4 | 36 |
| 5 | 167 |
| AwaitingInspection | 10 |
| Exempt | 19 |

## explore: FSA: what kinds of food business?

```sql
SELECT e.BusinessType AS business_type, COUNT(*) AS n FROM housecheck_live.fsa_gu27xh LATERAL VIEW explode(establishments) AS e GROUP BY e.BusinessType ORDER BY n DESC
```

| business_type | n |
|---|---|
| Restaurant/Cafe/Canteen | 87 |
| Retailers - other | 53 |
| Takeaway/sandwich shop | 32 |
| Pub/bar/nightclub | 27 |
| School/college/university | 14 |
| Other catering premises | 10 |
| Retailers - supermarkets/hypermarkets | 10 |
| Caring Premises | 8 |
| Mobile caterer | 3 |
| Manufacturers/packers | 3 |
| Hotel/bed & breakfast/guest house | 2 |
| Distributors/Transporters | 1 |

## explore: FSA: which councils inspect them, and how recently?

```sql
SELECT e.LocalAuthorityName AS council, COUNT(*) AS n, MIN(e.RatingDate) AS oldest, MAX(e.RatingDate) AS newest FROM housecheck_live.fsa_gu27xh LATERAL VIEW explode(establishments) AS e GROUP BY e.LocalAuthorityName
```

| council | n | oldest | newest |
|---|---|---|---|
| Guildford | 250 | 1901-01-01T00:00:00 | 2026-10-09T00:00:00 |

## probe: police.uk neighbourhood has data for GU2 7XH?

```sql
SELECT force FROM housecheck_live.hood_gu27xh LIMIT 1
```

| force |
|---|
| surrey |

## probe: police.uk street crime has data for GU2 7XH?

```sql
SELECT id FROM housecheck_live.crime_gu27xh LIMIT 1
```

| id |
|---|
| 137184857 |

## probe: FSA food hygiene has data for GU2 7XH?

```sql
SELECT size(establishments) AS n FROM housecheck_live.fsa_gu27xh
```

| n |
|---|
| 250 |

## probe: police.uk neighbourhood has data for SO14 5FN?

```sql
SELECT force FROM housecheck_live.hood_so145fn LIMIT 1
```

| force |
|---|
| hampshire |

## probe: police.uk street crime has data for SO14 5FN?

```sql
SELECT id FROM housecheck_live.crime_so145fn LIMIT 1
```

| id |
|---|
| 137312527 |

## probe: FSA food hygiene has data for SO14 5FN?

```sql
SELECT size(establishments) AS n FROM housecheck_live.fsa_so145fn
```

| n |
|---|
| 250 |

## probe: police.uk neighbourhood has data for BL4 0LL?

```sql
SELECT force FROM housecheck_live.hood_bl40ll LIMIT 1
```

| force |
|---|
| greater-manchester |

## probe: police.uk street crime has data for BL4 0LL?

```sql
SELECT id FROM housecheck_live.crime_bl40ll LIMIT 1
```

**NO DATA:** police.uk street crime returned nothing for BL4 0LL; left out of the view

## probe: FSA food hygiene has data for BL4 0LL?

```sql
SELECT size(establishments) AS n FROM housecheck_live.fsa_bl40ll
```

| n |
|---|
| 250 |

## usl: RUN DQ TABLE lightning.metastore.housecheck.student_area.area

```sql
RUN DQ TABLE lightning.metastore.housecheck.student_area.area
```

| name | table | type | total_record | valid_record | invalid_record |
|---|---|---|---|---|---|
| dq_area_in_great_britain | area | Custom Data Quality | 3 | 3 | 0 |
| postcode | area | Primary Key Constraint | 3 | 3 | 0 |

## usl: RUN DQ TABLE lightning.metastore.housecheck.student_area.street_crime

```sql
RUN DQ TABLE lightning.metastore.housecheck.student_area.street_crime
```

| name | table | type | total_record | valid_record | invalid_record |
|---|---|---|---|---|---|
| dq_crime_month_format | street_crime | Custom Data Quality | 1703 | 1703 | 0 |
| crime_key | street_crime | Primary Key Constraint | 1703 | 1703 | 0 |
| postcode | street_crime | Foreign Key Constraint | 1703 | 1703 | 0 |

## usl: RUN DQ TABLE lightning.metastore.housecheck.student_area.food_establishment

```sql
RUN DQ TABLE lightning.metastore.housecheck.student_area.food_establishment
```

| name | table | type | total_record | valid_record | invalid_record |
|---|---|---|---|---|---|
| dq_food_rating_known | food_establishment | Custom Data Quality | 750 | 750 | 0 |
| dq_food_rating_dated | food_establishment | Custom Data Quality | 750 | 750 | 0 |
| dq_food_rating_date_real | food_establishment | Custom Data Quality | 750 | 680 | 70 |
| food_key | food_establishment | Primary Key Constraint | 750 | 750 | 0 |
| postcode | food_establishment | Foreign Key Constraint | 750 | 750 | 0 |

## usl: SHOW DQ ALL INVALID TABLE lightning.metastore.housecheck.student_area.food_establishment

```sql
SHOW DQ ALL INVALID TABLE lightning.metastore.housecheck.student_area.food_establishment
```

| records |
|---|
| {\"food_key\":\"1987228-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"1699674-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"1695319-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"941756-gu27xh\",\"postcode\":\"GU2 7XH\",\"f |
| {\"food_key\":\"1699677-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"1924393-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"649480-gu27xh\",\"postcode\":\"GU2 7XH\",\"f |
| {\"food_key\":\"941757-gu27xh\",\"postcode\":\"GU2 7XH\",\"f |
| {\"food_key\":\"1822204-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"1978331-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"1621037-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"1695316-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"1846622-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"2005378-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"1853379-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"649568-gu27xh\",\"postcode\":\"GU2 7XH\",\"f |
| {\"food_key\":\"650074-gu27xh\",\"postcode\":\"GU2 7XH\",\"f |
| {\"food_key\":\"1860869-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"1929719-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"671683-gu27xh\",\"postcode\":\"GU2 7XH\",\"f |
| {\"food_key\":\"1978323-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"1053608-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"2005372-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"1965089-gu27xh\",\"postcode\":\"GU2 7XH\",\" |
| {\"food_key\":\"1453644-gu27xh\",\"postcode\":\"GU2 7XH\",\" |

_45 more rows not shown._

## query: USL: crime profile per postcode, with council and force (3 tables joined)

```sql
SELECT a.postcode, a.local_authority, p.police_force, c.crime_month, COUNT(*) AS crimes, SUM(CASE WHEN c.crime_category = 'burglary' THEN 1 ELSE 0 END) AS burglary, SUM(CASE WHEN c.crime_category = 'violent-crime' THEN 1 ELSE 0 END) AS violent, SUM(CASE WHEN c.crime_category = 'anti-social-behaviour' THEN 1 ELSE 0 END) AS antisocial FROM lightning.metastore.housecheck.student_area.area a JOIN lightning.metastore.housecheck.student_area.police_area p ON p.postcode = a.postcode JOIN lightning.metastore.housecheck.student_area.street_crime c ON c.postcode = a.postcode GROUP BY a.postcode, a.local_authority, p.police_force, c.crime_month ORDER BY crimes
```

| postcode | local_authority | police_force | crime_month | crimes | burglary | violent | antisocial |
|---|---|---|---|---|---|---|---|
| GU2 7XH | Guildford | surrey | 2026-08 | 554 | 7 | 185 | 79 |
| SO14 5FN | Southampton | hampshire | 2026-08 | 1149 | 18 | 409 | 173 |

## query: USL: food hygiene per postcode

```sql
SELECT a.postcode, COUNT(*) AS food_places, SUM(CASE WHEN f.rating_value IN ('4','5') THEN 1 ELSE 0 END) AS rated_4_or_5, SUM(CASE WHEN f.rating_value IN ('0','1','2') THEN 1 ELSE 0 END) AS rated_0_to_2, ROUND(100.0 * SUM(CASE WHEN f.rating_value IN ('4','5') THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN f.rating_value IN ('0','1','2','3','4','5') THEN 1 ELSE 0 END), 0), 1) AS pct_4_or_5 FROM lightning.metastore.housecheck.student_area.area a LEFT JOIN lightning.metastore.housecheck.student_area.food_establishment f ON f.postcode = a.postcode GROUP BY a.postcode ORDER BY pct_4_or_5 DESC
```

| postcode | food_places | rated_4_or_5 | rated_0_to_2 | pct_4_or_5 |
|---|---|---|---|---|
| GU2 7XH | 250 | 203 | 4 | 91.9 |
| SO14 5FN | 250 | 202 | 12 | 84.5 |
| BL4 0LL | 250 | 154 | 28 | 69.1 |

## query: USL: do the sources agree on the council? (postcodes.io vs FSA inspector)

```sql
SELECT a.postcode, a.local_authority AS council_postcodes_io, f.local_authority AS council_fsa, COUNT(*) AS food_places, CASE WHEN lower(a.local_authority) = lower(f.local_authority) THEN 'agree' ELSE 'CONFLICT' END AS status FROM lightning.metastore.housecheck.student_area.area a JOIN lightning.metastore.housecheck.student_area.food_establishment f ON f.postcode = a.postcode GROUP BY a.postcode, a.local_authority, f.local_authority ORDER BY a.postcode, food_places DESC
```

| postcode | council_postcodes_io | council_fsa | food_places | status |
|---|---|---|---|---|
| BL4 0LL | Bolton | Bolton | 250 | agree |
| GU2 7XH | Guildford | Guildford | 250 | agree |
| SO14 5FN | Southampton | Southampton | 250 | agree |

## query: USL: streets with the most recorded crime near each postcode

```sql
SELECT c.postcode, c.street_name, COUNT(*) AS crimes FROM lightning.metastore.housecheck.student_area.street_crime c GROUP BY c.postcode, c.street_name ORDER BY crimes DESC LIMIT 15
```

| postcode | street_name | crimes |
|---|---|---|
| SO14 5FN | On or near Parking Area | 120 |
| SO14 5FN | On or near Shopping Area | 71 |
| SO14 5FN | On or near High Street | 58 |
| GU2 7XH | On or near Genyn Road | 52 |
| SO14 5FN | On or near Supermarket | 50 |
| GU2 7XH | On or near Supermarket | 40 |
| SO14 5FN | On or near Nightclub | 38 |
| GU2 7XH | On or near Shopping Area | 30 |
| SO14 5FN | On or near Cranbury Place | 29 |
| SO14 5FN | On or near Scullards Lane | 26 |
| GU2 7XH | On or near Theatre/concert Hall | 25 |
| SO14 5FN | On or near Waterloo Terrace | 25 |
| GU2 7XH | On or near Parking Area | 24 |
| GU2 7XH | On or near Police Station | 21 |
| GU2 7XH | On or near Chapel Street | 21 |
