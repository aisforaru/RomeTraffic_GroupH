CREATE INDEX IF NOT EXISTS idx_accidents_prov ON accidents(province_code);
CREATE INDEX IF NOT EXISTS idx_accidents_year ON accidents(year);
CREATE INDEX IF NOT EXISTS idx_accidents_hour ON accidents(hour);
CREATE INDEX IF NOT EXISTS idx_accidents_weather ON accidents(weather);