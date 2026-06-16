using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.Services.Detectors
{
    /// <summary>
    /// (A) Detects window connections: for every window hosted in an envelope
    /// wall, four linear bridges (left/right reveal, head, sill) are created.
    /// </summary>
    public sealed class WindowBridgeDetector
    {
        private readonly EnvelopeService _envelope;
        private readonly Logger _log;

        public WindowBridgeDetector(EnvelopeService envelope, Logger log)
        {
            _envelope = envelope;
            _log = log;
        }

        public List<ThermalBridge> Detect(Document doc)
        {
            var bridges = new List<ThermalBridge>();

            var windows = new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Windows)
                .OfClass(typeof(FamilyInstance))
                .Cast<FamilyInstance>();

            foreach (FamilyInstance win in windows)
            {
                Wall host = win.Host as Wall;
                if (host == null)
                {
                    _log.Warning($"Fenster {win.Id.Value}: keine gültige Host-Wand – übersprungen.");
                    continue;
                }
                if (!_envelope.IsEnvelope(host))
                    continue; // not part of the thermal envelope

                OpeningEdges edges = OpeningGeometryHelper.Compute(win, host);
                if (edges == null)
                {
                    _log.Warning($"Fenster {win.Id.Value}: Geometrie nicht bestimmbar – übersprungen.");
                    continue;
                }

                string status = edges.IsReliable ? Constants.Status.AutoErkannt : Constants.Status.Unklar;
                string ebene = LevelName(doc, host);
                string bezug = _envelope.ThermalReference(host);

                bridges.Add(WbFactory.Create(Constants.Kategorie.Fensteranschluss, Constants.Untertyp.Laibung,
                    edges.Left, edges.HeightM, host.Id, win.Id, ebene, bezug, status, edges.Note, "L"));
                bridges.Add(WbFactory.Create(Constants.Kategorie.Fensteranschluss, Constants.Untertyp.Laibung,
                    edges.Right, edges.HeightM, host.Id, win.Id, ebene, bezug, status, edges.Note, "R"));
                bridges.Add(WbFactory.Create(Constants.Kategorie.Fensteranschluss, Constants.Untertyp.Sturz,
                    edges.Head, edges.WidthM, host.Id, win.Id, ebene, bezug, status, edges.Note, "O"));
                bridges.Add(WbFactory.Create(Constants.Kategorie.Fensteranschluss, Constants.Untertyp.Bruestung,
                    edges.Sill, edges.WidthM, host.Id, win.Id, ebene, bezug, status, edges.Note, "U"));
            }

            _log.Info($"Fensteranschlüsse erkannt: {bridges.Count} (aus {CountVisited(doc)} Fenstern).");
            return bridges;
        }

        private static int CountVisited(Document doc)
        {
            return new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Windows)
                .OfClass(typeof(FamilyInstance)).GetElementCount();
        }

        internal static string LevelName(Document doc, Element host)
        {
            ElementId lvlId = host.LevelId;
            if (lvlId != null && lvlId != ElementId.InvalidElementId)
            {
                if (doc.GetElement(lvlId) is Level lvl) return lvl.Name;
            }
            return string.Empty;
        }
    }
}
