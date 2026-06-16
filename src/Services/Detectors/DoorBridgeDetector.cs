using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.Services.Detectors
{
    /// <summary>
    /// (B) Detects exterior / terrace door connections. The threshold (Schwelle)
    /// is marked as a separate sub-type because it usually receives a different
    /// Psi value. Terrace/French doors are classified separately when type name,
    /// height or parameters indicate it.
    /// </summary>
    public sealed class DoorBridgeDetector
    {
        private readonly EnvelopeService _envelope;
        private readonly Logger _log;

        // Heuristic markers in type/family names that indicate a terrace door.
        private static readonly string[] TerraceHints =
            { "terrasse", "terrassen", "fenstertür", "fenstertuer", "balkon", "hebeschiebe", "french" };

        // Doors taller than this are treated as terrace/French doors when no
        // explicit hint is present (full-height glazing).
        private const double TerraceHeightThresholdM = 2.0;

        public DoorBridgeDetector(EnvelopeService envelope, Logger log)
        {
            _envelope = envelope;
            _log = log;
        }

        public List<ThermalBridge> Detect(Document doc)
        {
            var bridges = new List<ThermalBridge>();

            var doors = new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Doors)
                .OfClass(typeof(FamilyInstance))
                .Cast<FamilyInstance>();

            foreach (FamilyInstance door in doors)
            {
                Wall host = door.Host as Wall;
                if (host == null)
                {
                    _log.Warning($"Tür {door.Id.Value}: keine gültige Host-Wand – übersprungen.");
                    continue;
                }
                if (!_envelope.IsEnvelope(host))
                    continue;

                OpeningEdges edges = OpeningGeometryHelper.Compute(door, host);
                if (edges == null)
                {
                    _log.Warning($"Tür {door.Id.Value}: Geometrie nicht bestimmbar – übersprungen.");
                    continue;
                }

                bool isTerrace = IsTerraceDoor(door, edges.HeightM);
                string kategorie = isTerrace ? Constants.Kategorie.Terrassentuer : Constants.Kategorie.Tueranschluss;
                string status = edges.IsReliable ? Constants.Status.AutoErkannt : Constants.Status.Unklar;
                string ebene = WindowBridgeDetector.LevelName(doc, host);
                string bezug = _envelope.ThermalReference(host);

                bridges.Add(WbFactory.Create(kategorie, Constants.Untertyp.Laibung,
                    edges.Left, edges.HeightM, host.Id, door.Id, ebene, bezug, status, edges.Note, "L"));
                bridges.Add(WbFactory.Create(kategorie, Constants.Untertyp.Laibung,
                    edges.Right, edges.HeightM, host.Id, door.Id, ebene, bezug, status, edges.Note, "R"));
                bridges.Add(WbFactory.Create(kategorie, Constants.Untertyp.Sturz,
                    edges.Head, edges.WidthM, host.Id, door.Id, ebene, bezug, status, edges.Note, "O"));
                // Threshold is its own sub-type.
                bridges.Add(WbFactory.Create(kategorie, Constants.Untertyp.Schwelle,
                    edges.Sill, edges.WidthM, host.Id, door.Id, ebene, bezug, status,
                    Append(edges.Note, "Schwelle ggf. eigener Psi-Wert."), "S"));
            }

            _log.Info($"Türanschlüsse erkannt: {bridges.Count}.");
            return bridges;
        }

        private bool IsTerraceDoor(FamilyInstance door, double heightM)
        {
            string name = (door.Symbol?.FamilyName + " " + door.Name + " " +
                           door.Symbol?.Name).ToLowerInvariant();
            foreach (string hint in TerraceHints)
                if (name.Contains(hint)) return true;

            return heightM >= TerraceHeightThresholdM;
        }

        private static string Append(string a, string b)
        {
            if (string.IsNullOrEmpty(a)) return b;
            return a + " | " + b;
        }
    }
}
