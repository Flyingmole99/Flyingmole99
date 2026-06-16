using Autodesk.Revit.DB;
using ThermalBridgeTool.Common;

namespace ThermalBridgeTool.Models
{
    /// <summary>
    /// In-memory representation of a single linear thermal bridge. This is the
    /// data object that is written to / read from the marker element and that
    /// the export and validation services operate on.
    ///
    /// Length is held in metres (the auditable unit). Conversion to/from Revit
    /// feet happens only at the model boundary (MarkerService / repository).
    /// </summary>
    public sealed class ThermalBridge
    {
        public string Id { get; set; }                 // WB_ID, stable string id
        public string Kategorie { get; set; }          // WB_Kategorie
        public string Untertyp { get; set; }           // WB_Untertyp
        public string PsiTyp { get; set; }             // WB_Psi_Typ (library code)
        public double PsiWert { get; set; }            // WB_Psi_Wert [W/(m·K)]
        public bool HasPsiWert { get; set; }           // distinguishes 0 from "empty"
        public double LaengeM { get; set; }            // WB_Laenge [m]
        public string Quelle { get; set; }             // WB_Quelle
        public string Status { get; set; }             // WB_Status
        public string Bauteil1Id { get; set; }         // WB_Bauteil_1_ID
        public string Bauteil2Id { get; set; }         // WB_Bauteil_2_ID
        public string Ebene { get; set; }              // WB_Ebene
        public string Aussenbezug { get; set; }        // WB_Aussenbezug
        public string Hinweis { get; set; }            // WB_Hinweis

        /// <summary>Geometry of the bridge as a line in internal units (feet).</summary>
        public Line GeometryLine { get; set; }

        /// <summary>Element id of the marker once it exists in the model.</summary>
        public ElementId MarkerElementId { get; set; }

        /// <summary>Loss coefficient [W/K] = Psi * Length. Always derived.</summary>
        public double Verlustkoeffizient => PsiWert * LaengeM;

        /// <summary>Only proven ("geprüft") bridges count in the final sum.</summary>
        public bool IsProven => Status == Constants.Status.Geprueft;

        /// <summary>
        /// Stable geometric/semantic key used for duplicate detection. Built
        /// from category, sub-type, the two host components, rounded length and
        /// rounded midpoint so re-runs do not create duplicates.
        /// </summary>
        public string DuplicateSignature()
        {
            string b1 = Bauteil1Id ?? "";
            string b2 = Bauteil2Id ?? "";
            // Order-independent component pair.
            string pair = string.CompareOrdinal(b1, b2) <= 0 ? b1 + "|" + b2 : b2 + "|" + b1;

            string mid = "";
            if (GeometryLine != null)
            {
                XYZ m = GeometryLine.Evaluate(0.5, true);
                mid = $"{UnitHelper.RoundM(UnitHelper.FeetToMeters(m.X), 2)}:" +
                      $"{UnitHelper.RoundM(UnitHelper.FeetToMeters(m.Y), 2)}:" +
                      $"{UnitHelper.RoundM(UnitHelper.FeetToMeters(m.Z), 2)}";
            }

            return string.Join("#",
                Kategorie ?? "",
                Untertyp ?? "",
                pair,
                UnitHelper.RoundM(LaengeM, 2).ToString("0.00"),
                mid);
        }
    }
}
