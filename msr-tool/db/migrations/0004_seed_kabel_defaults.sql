-- 0004_seed_kabel_defaults.sql
-- Seed-Daten für die Kabelzugliste (Pflegedaten, nicht aus BACtwin).
-- Kabeltypen + Default-Klemmenvorlage je Signalart (dp_objekttyp_uuid = NULL).
-- Objekt-spezifische Vorlagen können später ergänzt werden und haben Vorrang.

BEGIN;

INSERT INTO catalog.kabeltyp (bezeichnung, aufbau, adern, querschnitt, schirm) VALUES
    ('J-Y(St)Y 1x2x0,8', 'paarig verseilt, gesamtgeschirmt', 2, '0,8', true),
    ('J-Y(St)Y 2x2x0,8', 'paarig verseilt, gesamtgeschirmt', 4, '0,8', true),
    ('NYM-J 3x1,5',      'Mantelleitung',                    3, '1,5', false)
ON CONFLICT (bezeichnung) DO NOTHING;

-- Default-Verdrahtung je Signalart (analoge Signale geschirmt, binär ungeschirmt-tauglich)
INSERT INTO catalog.klemmen_vorlage (dp_objekttyp_uuid, signalart, klemme, adern, kabeltyp_id, querschnitt)
SELECT NULL, v.signalart, NULL, v.adern,
       (SELECT id FROM catalog.kabeltyp WHERE bezeichnung = v.kabeltyp), v.querschnitt
FROM (VALUES
    ('AI', 2, 'J-Y(St)Y 1x2x0,8', '0,8'),
    ('AO', 2, 'J-Y(St)Y 1x2x0,8', '0,8'),
    ('BI', 2, 'J-Y(St)Y 1x2x0,8', '0,8'),
    ('BO', 2, 'J-Y(St)Y 1x2x0,8', '0,8')
) AS v(signalart, adern, kabeltyp, querschnitt);

COMMIT;
