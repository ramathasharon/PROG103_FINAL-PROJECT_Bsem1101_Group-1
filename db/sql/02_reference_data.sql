-- 02_reference_data.sql : lookup data the application needs to work
-- (districts, permit types, offices). Safe to repeat: ON CONFLICT DO NOTHING.

INSERT INTO districts (district_name, region) VALUES
    ('Bombali','Northern'), ('Falaba','Northern'), ('Koinadugu','Northern'),
    ('Tonkolili','Northern'),
    ('Kambia','North West'), ('Karene','North West'), ('Port Loko','North West'),
    ('Bo','Southern'), ('Bonthe','Southern'), ('Moyamba','Southern'),
    ('Pujehun','Southern'),
    ('Kailahun','Eastern'), ('Kenema','Eastern'), ('Kono','Eastern'),
    ('Western Area Rural','Western Area'), ('Western Area Urban','Western Area')
ON CONFLICT (district_name) DO NOTHING;

INSERT INTO permit_types (kind, type_name, details_label, base_fee, validity_years) VALUES
    ('general',  'General Permit',   'Purpose',                  100.00, 1),
    ('business', 'Business License', 'Business name',            500.00, 1),
    ('building', 'Building Permit',  'Site / plot description', 1500.00, 3)
ON CONFLICT (kind) DO NOTHING;

INSERT INTO offices (name) VALUES
    ('Business Licensing Unit'), ('Building Control Unit'), ('General Permits Desk')
ON CONFLICT (name) DO NOTHING;

INSERT INTO office_permit_types (office_name, kind) VALUES
    ('Business Licensing Unit', 'business'),
    ('Building Control Unit',   'building'),
    ('General Permits Desk',    'general')
ON CONFLICT DO NOTHING;
