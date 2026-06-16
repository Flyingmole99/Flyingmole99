using Autodesk.Revit.DB;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.Services.Detectors
{
    /// <summary>
    /// Builds <see cref="ThermalBridge"/> instances with the common fields set
    /// and a deterministic WB_ID so re-runs map to the same logical bridge.
    /// </summary>
    public static class WbFactory
    {
        public static ThermalBridge Create(
            string kategorie,
            string untertyp,
            Line geometry,
            double laengeM,
            ElementId bauteil1,
            ElementId bauteil2,
            string ebene,
            string aussenbezug,
            string status,
            string hinweis,
            string edgeTag)
        {
            string b1 = IdToString(bauteil1);
            string b2 = IdToString(bauteil2);

            return new ThermalBridge
            {
                Id = BuildId(kategorie, b1, b2, edgeTag),
                Kategorie = kategorie,
                Untertyp = untertyp,
                GeometryLine = geometry,
                LaengeM = laengeM,
                Bauteil1Id = b1,
                Bauteil2Id = b2,
                Ebene = ebene,
                Aussenbezug = aussenbezug,
                Status = status,
                Hinweis = hinweis,
                PsiTyp = string.Empty,
                Quelle = string.Empty,
                HasPsiWert = false,
            };
        }

        public static string IdToString(ElementId id)
        {
            if (id == null || id == ElementId.InvalidElementId) return string.Empty;
            return id.Value.ToString();
        }

        private static string BuildId(string kategorie, string b1, string b2, string edgeTag)
        {
            string k = Short(kategorie);
            // Include both component ids so e.g. two windows in the same wall, or
            // several floors meeting one wall, produce distinct (but stable) ids.
            string host = string.IsNullOrEmpty(b2) ? b1 : $"{b1}_{b2}";
            return $"WB-{k}-{host}-{edgeTag}";
        }

        private static string Short(string kategorie)
        {
            switch (kategorie)
            {
                case Constants.Kategorie.Fensteranschluss: return "FEN";
                case Constants.Kategorie.Tueranschluss: return "TUE";
                case Constants.Kategorie.Terrassentuer: return "TER";
                case Constants.Kategorie.Sockel: return "SOC";
                case Constants.Kategorie.Geschossdecke: return "GDE";
                default: return "WB";
            }
        }
    }
}
