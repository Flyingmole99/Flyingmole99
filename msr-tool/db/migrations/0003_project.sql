-- 0003_project.sql
-- Schema `project`: projektspezifische Planungsdaten. Referenziert `catalog`
-- per UUID, materialisiert Datenpunkte aber lokal (Projektstabilität).
-- Siehe ER-Modell.md §3–§4.

BEGIN;

CREATE SCHEMA IF NOT EXISTS project;

-- Gemeinsame Trigger-Funktion: hält updated_at aktuell.
CREATE OR REPLACE FUNCTION project.set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- Projekt: Klammer über Anlagen. Bindet an ein BAS-Profil und einen
-- Bibliotheksstand (bac_version) -> Reimport verändert Altprojekte nie.
-- ---------------------------------------------------------------------------
CREATE TABLE project.projekt (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name              text NOT NULL,
    kunde             text,
    naming_profile_id bigint NOT NULL REFERENCES catalog.naming_profile(id),
    bac_version_id    bigint NOT NULL REFERENCES catalog.bac_version(id),
    status            text NOT NULL DEFAULT 'in_bearbeitung'
                        CHECK (status IN ('in_bearbeitung','freigegeben','archiviert')),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_projekt_upd BEFORE UPDATE ON project.projekt
    FOR EACH ROW EXECUTE FUNCTION project.set_updated_at();

-- ---------------------------------------------------------------------------
-- Anlage: BAS-Block 1–2 (Gewerk + Anlage, optional Teilanlage).
-- ---------------------------------------------------------------------------
CREATE TABLE project.anlage (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    projekt_id     bigint NOT NULL REFERENCES project.projekt(id) ON DELETE CASCADE,
    gewerk_kg      text NOT NULL,                        -- "420"
    anlage_kuerzel text NOT NULL,                        -- "VBA"
    nummer         integer NOT NULL DEFAULT 1,
    teilanlage     integer,
    bas            text NOT NULL,                        -- "420_VBA01"
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (projekt_id, bas)
);
CREATE INDEX ix_anlage_projekt ON project.anlage(projekt_id);
CREATE TRIGGER trg_anlage_upd BEFORE UPDATE ON project.anlage
    FOR EACH ROW EXECUTE FUNCTION project.set_updated_at();

-- ---------------------------------------------------------------------------
-- Baugruppe: instanziiertes Aggregat-Template (BAS-Block 3).
-- ---------------------------------------------------------------------------
CREATE TABLE project.baugruppe (
    id                     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    anlage_id              bigint NOT NULL REFERENCES project.anlage(id) ON DELETE CASCADE,
    aggregat_template_uuid uuid NOT NULL REFERENCES catalog.aggregat_template(uuid),
    kuerzel                text NOT NULL,                -- "KES"
    nummer                 integer NOT NULL DEFAULT 1,
    medium_pos             text,
    position               jsonb,                        -- Canvas {x,y}
    bas                    text NOT NULL,
    created_at             timestamptz NOT NULL DEFAULT now(),
    updated_at             timestamptz NOT NULL DEFAULT now(),
    UNIQUE (anlage_id, bas)
);
CREATE INDEX ix_baugruppe_anlage ON project.baugruppe(anlage_id);
CREATE INDEX ix_baugruppe_template ON project.baugruppe(aggregat_template_uuid);
CREATE TRIGGER trg_baugruppe_upd BEFORE UPDATE ON project.baugruppe
    FOR EACH ROW EXECUTE FUNCTION project.set_updated_at();

-- ---------------------------------------------------------------------------
-- Betriebsmittel / Regelorgan: Feldgerät bzw. Stellglied unter einer Baugruppe
-- (BAS-Block 4–6). kategorie trennt Sensorik (Betriebsmittel) von aktiven
-- Stellgliedern (Regelorgan).
-- ---------------------------------------------------------------------------
CREATE TABLE project.betriebsmittel (
    id                     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    baugruppe_id           bigint NOT NULL REFERENCES project.baugruppe(id) ON DELETE CASCADE,
    aggregat_template_uuid uuid REFERENCES catalog.aggregat_template(uuid),
    kategorie              text NOT NULL
                             CHECK (kategorie IN ('Regelorgan','Betriebsmittel')),
    kuerzel                text NOT NULL,                -- "T~~" / "VEN"
    nummer                 integer NOT NULL DEFAULT 1,
    bas                    text NOT NULL,
    created_at             timestamptz NOT NULL DEFAULT now(),
    updated_at             timestamptz NOT NULL DEFAULT now(),
    UNIQUE (baugruppe_id, bas)
);
CREATE INDEX ix_betriebsmittel_baugruppe ON project.betriebsmittel(baugruppe_id);
CREATE TRIGGER trg_betriebsmittel_upd BEFORE UPDATE ON project.betriebsmittel
    FOR EACH ROW EXECUTE FUNCTION project.set_updated_at();

-- ---------------------------------------------------------------------------
-- Datenpunkt: materialisierte Instanz aus aggregat_template_dp (+ Properties
-- aus dp_objekt_property). anlage_id ist denormalisiert (jeder DP gehört genau
-- einer Anlage) -> schnelle Datenpunktliste + BAS-Eindeutigkeit je Anlage.
-- Polymorphe Quelle (baugruppe|betriebsmittel) via quelle_typ/quelle_id -> kein
-- echter FK möglich (per App-Logik/Trigger konsistent gehalten).
-- ---------------------------------------------------------------------------
CREATE TABLE project.datenpunkt (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    anlage_id         bigint NOT NULL REFERENCES project.anlage(id) ON DELETE CASCADE,
    quelle_typ        text NOT NULL CHECK (quelle_typ IN ('baugruppe','betriebsmittel')),
    quelle_id         bigint NOT NULL,
    dp_objekttyp_uuid uuid NOT NULL REFERENCES catalog.dp_objekttyp(uuid),
    bas_funktion      text,                              -- "MW~01"
    bas               text NOT NULL,                     -- voll aufgelöst
    adresse           text,                              -- DDC-Kanal / BACnet-Instanz
    units             text,
    min_pres          numeric,
    max_pres          numeric,
    prio              text,
    trend             boolean NOT NULL DEFAULT false,    -- aus TL
    alarm             boolean NOT NULL DEFAULT false,    -- aus EE/NC
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (anlage_id, bas)
);
CREATE INDEX ix_datenpunkt_anlage  ON project.datenpunkt(anlage_id);
CREATE INDEX ix_datenpunkt_quelle  ON project.datenpunkt(quelle_typ, quelle_id);
CREATE INDEX ix_datenpunkt_objtyp  ON project.datenpunkt(dp_objekttyp_uuid);
CREATE TRIGGER trg_datenpunkt_upd BEFORE UPDATE ON project.datenpunkt
    FOR EACH ROW EXECUTE FUNCTION project.set_updated_at();

-- ---------------------------------------------------------------------------
-- Regelkreis: gruppiert Elemente (quer über Baugruppen) zu einem Regelkreis.
-- ---------------------------------------------------------------------------
CREATE TABLE project.regelkreis (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    anlage_id   bigint NOT NULL REFERENCES project.anlage(id) ON DELETE CASCADE,
    art         text NOT NULL,                           -- "Konstant"/"Folge"/...
    bezeichnung text,
    bas         text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_regelkreis_anlage ON project.regelkreis(anlage_id);
CREATE TRIGGER trg_regelkreis_upd BEFORE UPDATE ON project.regelkreis
    FOR EACH ROW EXECUTE FUNCTION project.set_updated_at();

-- ---------------------------------------------------------------------------
-- Regelkreis-Element: m:n Regelkreis <-> (Betriebsmittel | Datenpunkt) mit
-- Rolle. Polymorph via element_typ/element_id.
-- ---------------------------------------------------------------------------
CREATE TABLE project.regelkreis_element (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    regelkreis_id bigint NOT NULL REFERENCES project.regelkreis(id) ON DELETE CASCADE,
    element_typ   text NOT NULL CHECK (element_typ IN ('betriebsmittel','datenpunkt')),
    element_id    bigint NOT NULL,
    rolle         text NOT NULL
                    CHECK (rolle IN ('Istwert','Sollwert','Stellglied','Meldung','Fuehrung')),
    UNIQUE (regelkreis_id, element_typ, element_id, rolle)
);
CREATE INDEX ix_rk_element_rk ON project.regelkreis_element(regelkreis_id);

-- ---------------------------------------------------------------------------
-- Kabel: je Feldgerät (Betriebsmittel) eine Kabelverbindung Feld <-> Schrank.
-- ---------------------------------------------------------------------------
CREATE TABLE project.kabel (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    betriebsmittel_id bigint NOT NULL REFERENCES project.betriebsmittel(id) ON DELETE CASCADE,
    von               text,                              -- Feldgerät
    nach              text,                              -- Schaltschrank/DDC
    kabeltyp          text,
    adern             integer,
    querschnitt       text,
    laenge            numeric,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_kabel_betriebsmittel ON project.kabel(betriebsmittel_id);
CREATE TRIGGER trg_kabel_upd BEFORE UPDATE ON project.kabel
    FOR EACH ROW EXECUTE FUNCTION project.set_updated_at();

-- ---------------------------------------------------------------------------
-- Dokument: generierte Artefakte, an quelle_hash gebunden (Konsistenzprüfung).
-- ---------------------------------------------------------------------------
CREATE TABLE project.dokument (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    projekt_id  bigint NOT NULL REFERENCES project.projekt(id) ON DELETE CASCADE,
    art         text NOT NULL
                  CHECK (art IN ('datenpunktliste','kabelzugliste',
                                 'regelschema','regelbeschreibung')),
    format      text NOT NULL
                  CHECK (format IN ('xlsx','csv','docx','pdf','svg','dxf')),
    pfad        text,
    quelle_hash text,
    erzeugt_am  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_dokument_projekt ON project.dokument(projekt_id);

-- ---------------------------------------------------------------------------
-- Audit-Log: projektweite Änderungshistorie.
-- ---------------------------------------------------------------------------
CREATE TABLE project.audit_log (
    id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity    text NOT NULL,
    entity_id bigint,
    aktion    text NOT NULL,
    benutzer  text,
    zeit      timestamptz NOT NULL DEFAULT now(),
    diff      jsonb
);
CREATE INDEX ix_audit_entity ON project.audit_log(entity, entity_id);

COMMIT;
