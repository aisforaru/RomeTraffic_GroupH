CREATE TABLE IF NOT EXISTS accidents (
    accident_id SERIAL PRIMARY KEY,
    year SMALLINT,
    province_code CHAR(3),
    municipality_code CHAR(3),
    weekday SMALLINT,
    quarter SMALLINT,
    hour SMALLINT,
    location_type SMALLINT,
    carriageway_type SMALLINT,
    road_feature SMALLINT,
    road_surface SMALLINT,
    weather SMALLINT,
    accident_type SMALLINT,
    vehicle_a_type SMALLINT,
    deaths_24h SMALLINT,
    deaths_30d SMALLINT,
    injured SMALLINT
);