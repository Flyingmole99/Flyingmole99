-- 0002_catalog_pflegedaten.sql
-- Katalog-Stammdaten, die NICHT aus BACtwin stammen, sondern intern gepflegt
-- werden: Kabeltypen/Klemmen (Kabelzugliste), Schema-Symbole (Regelschema),
-- Textbausteine (Regelbeschreibung). Siehe ER-Modell.md §6.

BEGIN;

-- ---------------------------------------------------------------------------
-- Kabelstammdaten.
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.kabeltyp (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bezeichnung text NOT NULL UNIQUE,                    -- "J-Y(St)Y 2x2x0,8"
    aufbau      text,
    adern       integer,
    querschnitt text,
    schirm      boolean NOT NULL DEFAULT false
);

-- ---------------------------------------------------------------------------
-- Klemmen-/Verdrahtungsvorlage je Objekttyp: verbindet einen Hardware-
-- Datenpunkt (AI/AO/BI/BO) mit Klemme, Adernzahl und empfohlenem Kabeltyp.
-- Grundlage für die Kabelzugliste.
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.klemmen_vorlage (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dp_objekttyp_uuid uuid REFERENCES catalog.dp_objekttyp(uuid) ON DELETE CASCADE,
    signalart         text CHECK (signalart IN ('AI','AO','BI','BO')),
    klemme            text,
    adern             integer,
    kabeltyp_id       bigint REFERENCES catalog.kabeltyp(id),
    querschnitt       text
);
CREATE INDEX ix_klemmen_objtyp ON catalog.klemmen_vorlage(dp_objekttyp_uuid);

-- ---------------------------------------------------------------------------
-- Schema-Symbole je Aggregat ODER Objekttyp (für das Regelschema). Inline-SVG
-- + Anschlusspunkte (Medium/Position) für die automatische Verdrahtung im Graph.
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.schema_symbol (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bezug_typ       text NOT NULL CHECK (bezug_typ IN ('aggregat','objekttyp')),
    aggregat_uuid   uuid REFERENCES catalog.aggregat_template(uuid) ON DELETE CASCADE,
    objekttyp_uuid  uuid REFERENCES catalog.dp_objekttyp(uuid) ON DELETE CASCADE,
    svg             text,                                -- Inline-SVG-Symbol
    -- [{name, medium, x, y, richtung}]
    anschlusspunkte jsonb,
    CONSTRAINT chk_symbol_bezug CHECK (
        (bezug_typ = 'aggregat'  AND aggregat_uuid  IS NOT NULL AND objekttyp_uuid IS NULL) OR
        (bezug_typ = 'objekttyp' AND objekttyp_uuid IS NOT NULL AND aggregat_uuid  IS NULL)
    )
);
CREATE INDEX ix_symbol_aggregat ON catalog.schema_symbol(aggregat_uuid);
CREATE INDEX ix_symbol_objekttyp ON catalog.schema_symbol(objekttyp_uuid);

-- ---------------------------------------------------------------------------
-- Textbausteine je Regelkreis-Art (für die Regelbeschreibung). Markdown mit
-- Platzhaltern ({{vorlauf_sollwert}}, {{bas}} …), die der Generator füllt.
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.textbaustein (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    regelkreis_art text NOT NULL,                        -- "Kessel modulierend"
    sprache        text NOT NULL DEFAULT 'de',
    text_md        text NOT NULL,
    UNIQUE (regelkreis_art, sprache)
);

COMMIT;
