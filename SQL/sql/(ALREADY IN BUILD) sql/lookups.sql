CREATE TABLE IF NOT EXISTS weather_lookup (
    code SMALLINT PRIMARY KEY,
    description VARCHAR(100)
);

INSERT INTO weather_lookup (code, description) VALUES
(1, 'Sereno'),
(2, 'Nebbia'),
(3, 'Pioggia'),
(4, 'Nevischio / Neve'),
(5, 'Grandine'),
(9, 'Altro / Non noto')
ON CONFLICT (code) DO NOTHING;