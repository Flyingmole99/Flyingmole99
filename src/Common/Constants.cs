using System;

namespace ThermalBridgeTool.Common
{
    /// <summary>
    /// Central place for all "magic strings": shared parameter names, controlled
    /// vocabularies (categories, sub-types, status values) and other identifiers.
    /// Nothing in the codebase should hard-code these literals.
    /// </summary>
    public static class Constants
    {
        // -----------------------------------------------------------------
        // Shared parameter group used for the .txt shared parameter file.
        // -----------------------------------------------------------------
        public const string SharedParamGroupWb = "Waermebruecken";
        public const string SharedParamGroupSe = "ThermischeHuelle";

        // -----------------------------------------------------------------
        // Thermal bridge (WB) parameters. Carried by the marker objects
        // (Generic Model / DirectShape).
        // -----------------------------------------------------------------
        public static class Wb
        {
            public const string Id = "WB_ID";
            public const string Kategorie = "WB_Kategorie";
            public const string Untertyp = "WB_Untertyp";
            public const string PsiTyp = "WB_Psi_Typ";
            public const string PsiWert = "WB_Psi_Wert";                 // W/(m·K), Number
            public const string Laenge = "WB_Laenge";                    // Length (internally feet)
            public const string Verlustkoeffizient = "WB_Verlustkoeffizient"; // W/K, Number
            public const string Quelle = "WB_Quelle";
            public const string Status = "WB_Status";
            public const string Bauteil1Id = "WB_Bauteil_1_ID";
            public const string Bauteil2Id = "WB_Bauteil_2_ID";
            public const string Ebene = "WB_Ebene";
            public const string Aussenbezug = "WB_Aussenbezug";
            public const string Hinweis = "WB_Hinweis";
        }

        // -----------------------------------------------------------------
        // Thermal-envelope (SE) parameters. Carried by host components
        // (walls, floors, ...).
        // -----------------------------------------------------------------
        public static class Se
        {
            public const string ThermischeHuelle = "SE_Thermische_Huelle"; // Yes/No
            public const string BauteilGegen = "SE_Bauteil_gegen";         // Text
            public const string BauteiltypEnergie = "SE_Bauteiltyp_Energie"; // Text
        }

        // -----------------------------------------------------------------
        // Controlled vocabulary: thermal-bridge categories.
        // -----------------------------------------------------------------
        public static class Kategorie
        {
            public const string Fensteranschluss = "Fensteranschluss";
            public const string Tueranschluss = "Aussentueranschluss";
            public const string Terrassentuer = "Terrassentueranschluss";
            public const string Sockel = "Sockel/Bodenplattenrand";
            public const string Geschossdecke = "Geschossdeckenanschluss";
            // Prepared for later stages:
            public const string Dach = "Dachanschluss";
            public const string Ecke = "Gebaeudeecke";
            public const string InnenwandErdreich = "Innenwand auf Erdreich";
        }

        // -----------------------------------------------------------------
        // Controlled vocabulary: sub-types (per opening edge / connection).
        // -----------------------------------------------------------------
        public static class Untertyp
        {
            public const string Laibung = "Laibung";       // left / right reveal
            public const string Sturz = "Sturz";           // head / lintel
            public const string Bruestung = "Bruestung";   // window sill
            public const string Schwelle = "Schwelle";     // door threshold
            public const string AwAufBpl = "Außenwand auf Bodenplatte";
            public const string Deckenrand = "Deckenrand an Außenwand";
        }

        // -----------------------------------------------------------------
        // Controlled vocabulary: status values. Only "Geprueft" counts in the
        // final energetic summation.
        // -----------------------------------------------------------------
        public static class Status
        {
            public const string AutoErkannt = "automatisch erkannt";
            public const string Unklar = "unklar";
            public const string Geprueft = "geprüft";
            public const string Verworfen = "verworfen";
            public const string BereitsVorhanden = "bereits vorhanden";
        }

        // -----------------------------------------------------------------
        // Controlled vocabulary: thermal reference (against what).
        // -----------------------------------------------------------------
        public static class Aussenbezug
        {
            public const string Aussenluft = "Außenluft";
            public const string Erdreich = "Erdreich";
            public const string Unbeheizt = "unbeheizt";
            public const string Beheizt = "beheizt";
            public const string Unbekannt = "unbekannt";
        }

        // -----------------------------------------------------------------
        // Energetic component type (SE_Bauteiltyp_Energie vocabulary).
        // -----------------------------------------------------------------
        public static class Bauteiltyp
        {
            public const string Aussenwand = "Außenwand";
            public const string Dach = "Dach";
            public const string Bodenplatte = "Bodenplatte";
            public const string Geschossdecke = "Geschossdecke";
            public const string Innenwand = "Innenwand";
        }

        // Marker geometry: half thickness of the bar solid used to visualise a
        // linear bridge, in feet (~15 mm). Purely cosmetic.
        public const double MarkerHalfThicknessFeet = 0.025;

        // Tolerance (feet) for geometric duplicate / proximity checks (~1 cm).
        public const double GeometricToleranceFeet = 0.033;
    }
}
