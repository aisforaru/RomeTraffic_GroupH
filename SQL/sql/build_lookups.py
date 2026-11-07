import os

def generate_lookups():
    print("Generazione script SQL per le lookup ISTAT...")
    
    sql_content = """-- Tabelle di lookup per la decodifica dei codici ISTAT

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

CREATE TABLE IF NOT EXISTS road_surface_lookup (
    code SMALLINT PRIMARY KEY,
    description VARCHAR(100)
);

INSERT INTO road_surface_lookup (code, description) VALUES
(1, 'Pavimentazione asciutta'),
(2, 'Pavimentazione bagnata'),
(3, 'Viscido'),
(4, 'Innevato'),
(5, 'Ghiacciato')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS province_lookup (
    province_code CHAR(3) PRIMARY KEY,
    province_name VARCHAR(100)
);

INSERT INTO province_lookup (province_code, province_name) VALUES
('056', 'Viterbo'),
('057', 'Rieti'),
('058', 'Roma'),
('059', 'Latina'),
('060', 'Frosinone')
ON CONFLICT (province_code) DO NOTHING;
"""

    os.makedirs("sql", exist_ok=True)
    with open("sql/lookups.sql", "w", encoding="utf-8") as f:
        f.write(sql_content)
    
    print("File sql/lookups.sql generato con successo!")

if __name__ == "__main__":
    generate_lookups()