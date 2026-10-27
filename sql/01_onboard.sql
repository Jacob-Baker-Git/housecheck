-- HouseCheck USL, generated 2026-10-27 07:08 for GU2 7XH, SO14 5FN, BL4 0LL
-- One statement per Zetaris call; statements separated by '-- @@stmt'.

CREATE LIGHTNING DATABASE HOUSECHECK_LIVE DESCRIBE BY "HouseCheck live public data from postcodes.io, police.uk and the FSA"
-- @@stmt
CREATE LIGHTNING REST TABLE crime_updated FROM HOUSECHECK_LIVE REQUEST(endpoint "https://data.police.uk/api/crime-last-updated", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json") BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE pc_gu27xh FROM HOUSECHECK_LIVE REQUEST(endpoint "https://api.postcodes.io/postcodes/GU27XH", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json") BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE hood_gu27xh FROM HOUSECHECK_LIVE REQUEST(endpoint "https://data.police.uk/api/locate-neighbourhood?q=51.242685,-0.587936", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json") BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE crime_gu27xh FROM HOUSECHECK_LIVE REQUEST(endpoint "https://data.police.uk/api/crimes-street/all-crime?lat=51.242685&lng=-0.587936", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json") BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE fsa_gu27xh FROM HOUSECHECK_LIVE REQUEST(endpoint "https://api.ratings.food.gov.uk/Establishments?latitude=51.242685&longitude=-0.587936&maxDistanceLimit=0.5&sortOptionKey=distance&pageSize=250", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json", x-api-version "2") BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE pc_so145fn FROM HOUSECHECK_LIVE REQUEST(endpoint "https://api.postcodes.io/postcodes/SO145FN", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json") BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE hood_so145fn FROM HOUSECHECK_LIVE REQUEST(endpoint "https://data.police.uk/api/locate-neighbourhood?q=50.902555,-1.392459", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json") BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE crime_so145fn FROM HOUSECHECK_LIVE REQUEST(endpoint "https://data.police.uk/api/crimes-street/all-crime?lat=50.902555&lng=-1.392459", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json") BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE fsa_so145fn FROM HOUSECHECK_LIVE REQUEST(endpoint "https://api.ratings.food.gov.uk/Establishments?latitude=50.902555&longitude=-1.392459&maxDistanceLimit=0.5&sortOptionKey=distance&pageSize=250", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json", x-api-version "2") BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE pc_bl40ll FROM HOUSECHECK_LIVE REQUEST(endpoint "https://api.postcodes.io/postcodes/BL40LL", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json") BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE hood_bl40ll FROM HOUSECHECK_LIVE REQUEST(endpoint "https://data.police.uk/api/locate-neighbourhood?q=53.553729,-2.450055", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json") BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE crime_bl40ll FROM HOUSECHECK_LIVE REQUEST(endpoint "https://data.police.uk/api/crimes-street/all-crime?lat=53.553729&lng=-2.450055", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json") BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE fsa_bl40ll FROM HOUSECHECK_LIVE REQUEST(endpoint "https://api.ratings.food.gov.uk/Establishments?latitude=53.553729&longitude=-2.450055&maxDistanceLimit=0.5&sortOptionKey=distance&pageSize=250", method "get", response_type "json", http_encoding "URLENCODED") HEADER (user-agent "HouseCheck/0.1 (Open Agent Hackathon 2026)", accept "application/json", x-api-version "2") BODY ()
