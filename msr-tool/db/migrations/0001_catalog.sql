-- 0001_catalog.sql
-- Schema `catalog`: importierte, versionierte BACtwin-Stammdaten.
-- Siehe docs/msr-tool/ER-Modell.md §2 und Import-Pipeline.md.
-- Ausführung: einmalig, in numerischer Reihenfolge (siehe db/README.md).

BEGIN;

CREATE SCHEMA IF NOT EXISTS catalog;

-- ---------------------------------------------------------------------------
-- Import-Stand: jeder Importlauf einer BACtwin-Bibliothek legt eine Version an.
-- Alle Stammdatenzeilen tragen version_id = "zuletzt in diesem Lauf berührt".
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.bac_version (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bezeichnung   text        NOT NULL UNIQUE,          -- z. B. "AMEV 1.2"
    quelle_datei  text,
    hash          text,                                  -- Datei-/Inhaltshash
    importiert_am timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Gewerke (DIN 276 / VDI 3814-4.1) — BAS-Block 1.
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.bac_gewerk (
    kg             text PRIMARY KEY,                     -- "420"
    kuerzel        text NOT NULL,                        -- "HZG"
    kuerzel_1z     text,                                 -- "H" (Variante gekürzt)
    bezeichnung_de text NOT NULL,
    bezeichnung_en text,
    status         text NOT NULL DEFAULT 'aktiv'
                     CHECK (status IN ('aktiv','veraltet')),
    version_id     bigint NOT NULL REFERENCES catalog.bac_version(id)
);

-- ---------------------------------------------------------------------------
-- BAS-Profil: definiert die BLOCKSTRUKTUR (Stellen, Trennzeichen, optional),
-- nicht die Kürzel. Aus Bibliothek 1, Blatt "2 Gliederung".
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.naming_profile (
    id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                 text NOT NULL UNIQUE,           -- "BACtwin ungekürzt"
    variante             text NOT NULL
                           CHECK (variante IN ('ungekuerzt','gekuerzt')),
    sprache              text NOT NULL DEFAULT 'de',
    trennzeichen_default text NOT NULL DEFAULT '_',
    -- [{block, name, stelle_von, stelle_bis, trennzeichen, optional}]
    segmente             jsonb NOT NULL
);

-- ---------------------------------------------------------------------------
-- BAS-Vokabular: erlaubte Kürzel je Block. BLOCK-scoped und profil-unabhängig
-- (Abweichung vom ersten ER-Entwurf: Kürzel gehören einem Block, nicht einem
-- Profil). Aus Bibliothek 1, Blatt "4 BACtwin-BAS".
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.bac_vokabular (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    block        smallint NOT NULL CHECK (block BETWEEN 1 AND 8),
    kuerzel      text NOT NULL,
    bezeichnung  text,
    beschreibung text,
    sprache      text NOT NULL DEFAULT 'de',
    status       text NOT NULL DEFAULT 'aktiv'
                   CHECK (status IN ('aktiv','veraltet')),
    version_id   bigint NOT NULL REFERENCES catalog.bac_version(id),
    UNIQUE (block, kuerzel, sprache)
);

-- ---------------------------------------------------------------------------
-- Meldeklassen (BACnet Notification Class). Bibliothek 3, Blatt "25 Meldeklasse".
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.meldeklasse (
    object_identifier text PRIMARY KEY,                  -- "NC100"
    bezeichnung_de    text NOT NULL,
    bezeichnung_en    text,
    priority          text,                              -- "{10,11,110}"
    ack_required      text,                              -- "{true,true,true}"
    version_id        bigint REFERENCES catalog.bac_version(id)
);

-- ---------------------------------------------------------------------------
-- Datenpunkt-Objekttypen (BACnet). UUID ist der stabile BACtwin-Schlüssel.
-- Bibliothek 2, Blatt "8 BACtwin_Objects_DE/EN".
-- ist_hardware  = object_type in (AI,AO,BI,BO)  -> Feldkabel nötig
-- ist_erweiterung = object_type in (EE,TL)      -> hängt an Basispunkt
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.dp_objekttyp (
    uuid            uuid PRIMARY KEY,
    obj_sort        text,                                -- "a101"
    kennung         text NOT NULL UNIQUE,                -- "AI_MW_T_AMEV1"
    object_type     text NOT NULL,                       -- AI/AO/AV/BI/BO/...
    bezeichnung_de  text,
    bezeichnung_en  text,
    ga_fl           jsonb,                               -- Funktionsbereichs-Marker
    ist_hardware    boolean NOT NULL DEFAULT false,
    ist_erweiterung boolean NOT NULL DEFAULT false,
    status          text NOT NULL DEFAULT 'aktiv'
                      CHECK (status IN ('aktiv','veraltet')),
    version_id      bigint NOT NULL REFERENCES catalog.bac_version(id)
);
CREATE INDEX ix_dp_objekttyp_object_type ON catalog.dp_objekttyp(object_type);

-- ---------------------------------------------------------------------------
-- BACnet-Property-Defaults je Objekttyp (1:1). Feste Spalten für die
-- listenrelevanten Properties, event_props(jsonb) für die optionalen Alarm-
-- Properties (Entscheidung aus Import-Pipeline.md §9.1). Bibliothek 2, "8.1–8.14".
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.dp_objekt_property (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    objekttyp_uuid     uuid NOT NULL UNIQUE
                         REFERENCES catalog.dp_objekttyp(uuid) ON DELETE CASCADE,
    object_name_muster text,
    description_muster text,
    units              text,                             -- °C / mbar / %
    min_pres           numeric,
    max_pres           numeric,
    resolution         numeric,
    notification_class text REFERENCES catalog.meldeklasse(object_identifier),
    low_limit          numeric,
    high_limit         numeric,
    deadband           numeric,
    conformance        text,
    event_props        jsonb
);

-- ---------------------------------------------------------------------------
-- Aggregat-Templates (Baugruppe / Aggregat / Anlage). UUID = BACtwin-Schlüssel.
-- Bibliothek 3, Blatt "10 AggregateTempl" (Kopfzeilen).
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.aggregat_template (
    uuid           uuid PRIMARY KEY,
    typ            text NOT NULL
                     CHECK (typ IN ('Aggregat','Baugruppe','Anlage')),
    gewerk_kg      text REFERENCES catalog.bac_gewerk(kg),
    kennung        text NOT NULL UNIQUE,                 -- "BGP_KES_nM_AMEV1"
    bezeichnung_de text,
    bezeichnung_en text,
    status         text NOT NULL DEFAULT 'aktiv'
                     CHECK (status IN ('aktiv','veraltet')),
    version_id     bigint NOT NULL REFERENCES catalog.bac_version(id)
);

-- ---------------------------------------------------------------------------
-- Template-Zeilen: je Zeile ENTWEDER ein Datenpunkt-Objekt (dp_objekttyp_uuid)
-- ODER ein Unter-Aggregat (referenz_template_uuid, Self-Reference -> Rekursion).
-- Die rohe referenz_kennung bleibt für die Import-Validierung erhalten, die FKs
-- sind auflösbar-nullable. CHECK verhindert nur, dass BEIDE FKs gesetzt sind.
-- Bibliothek 3, Blatt "10 AggregateTempl" (DP-/Referenz-Zeilen).
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.aggregat_template_dp (
    id                     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    template_uuid          uuid NOT NULL
                             REFERENCES catalog.aggregat_template(uuid) ON DELETE CASCADE,
    reihenfolge            integer NOT NULL DEFAULT 0,
    referenz_kennung       text NOT NULL,                -- roh, immer gesetzt
    ist_unteraggregat      boolean NOT NULL DEFAULT false,
    dp_objekttyp_uuid      uuid REFERENCES catalog.dp_objekttyp(uuid),
    referenz_template_uuid uuid REFERENCES catalog.aggregat_template(uuid),
    variante               text,                         -- "1.1", "2.2"
    beschreibung           text,
    bas_relativ            jsonb,                        -- nur Block 4–8
    object_name_beispiel   text,                         -- illustrativ, nicht kopieren
    CONSTRAINT chk_template_dp_ref
        CHECK (NOT (dp_objekttyp_uuid IS NOT NULL
                    AND referenz_template_uuid IS NOT NULL))
);
CREATE INDEX ix_template_dp_template ON catalog.aggregat_template_dp(template_uuid);
CREATE INDEX ix_template_dp_ref_tmpl ON catalog.aggregat_template_dp(referenz_template_uuid);
CREATE INDEX ix_template_dp_objtyp  ON catalog.aggregat_template_dp(dp_objekttyp_uuid);

-- ---------------------------------------------------------------------------
-- Ergänzende BACtwin-Referenztabellen (Bibliothek 3).
-- ---------------------------------------------------------------------------
CREATE TABLE catalog.funktionsbereich (                  -- Blatt "15"
    kennung           text PRIMARY KEY,                  -- a/b/c/d
    bezeichnung_de    text NOT NULL,
    bezeichnung_en    text,
    objekttyp_kennung text
);

CREATE TABLE catalog.zustaendigkeit (                    -- Blatt "16/17"
    kennbuchstabe text PRIMARY KEY,                      -- B/P/U
    bereich_de    text,
    bereich_en    text,
    ziffernblock  text                                   -- "11 - 39"
);

CREATE TABLE catalog.min_char_length (                   -- Blatt "23"
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property    text NOT NULL,                           -- "Object_Name"
    amev_profil text NOT NULL,                           -- MBE / AS-C / AS-D / MOU
    laenge      integer NOT NULL,
    UNIQUE (property, amev_profil)
);

CREATE TABLE catalog.priority_array (                    -- Blatt "24"
    prio         smallint PRIMARY KEY CHECK (prio BETWEEN 1 AND 16),
    verwendung   text,
    empfehlung   text,
    beschreibung text
);

CREATE TABLE catalog.event_parameter (                   -- Blatt "26"
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    objekt_template  text,
    event_algorithm  text,
    event_parameters text,
    anwendung        text
);

CREATE TABLE catalog.betreibervorgabe (                  -- Blatt "27" (optional/MVP)
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    schluessel   text,
    wert         text,
    beschreibung text
);

COMMIT;
