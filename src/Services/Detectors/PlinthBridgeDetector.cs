using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.Services.Detectors
{
    /// <summary>
    /// (C) Detects the plinth / base-slab edge: along the bottom edge of the
    /// envelope exterior walls of the lowest relevant storey a linear bridge
    /// "Außenwand auf Bodenplatte" is created.
    /// </summary>
    public sealed class PlinthBridgeDetector
    {
        private readonly EnvelopeService _envelope;
        private readonly Logger _log;

        public PlinthBridgeDetector(EnvelopeService envelope, Logger log)
        {
            _envelope = envelope;
            _log = log;
        }

        public List<ThermalBridge> Detect(Document doc)
        {
            var bridges = new List<ThermalBridge>();

            // Envelope exterior walls.
            var walls = new FilteredElementCollector(doc)
                .OfClass(typeof(Wall))
                .Cast<Wall>()
                .Where(w => _envelope.IsEnvelope(w))
                .ToList();

            if (walls.Count == 0)
            {
                _log.Warning("Sockel: keine Außenwände der thermischen Hülle gefunden.");
                return bridges;
            }

            // Lowest level among these walls (by level elevation).
            double lowestElev = double.MaxValue;
            foreach (Wall w in walls)
            {
                double e = LevelElevation(doc, w);
                if (e < lowestElev) lowestElev = e;
            }

            bool hasGroundSlab = HasFloorAgainstGround(doc);
            if (!hasGroundSlab)
                _log.Warning("Sockel: keine Bodenplatte/Decke gegen Erdreich gefunden – Markierung als 'unklar'.");

            foreach (Wall w in walls)
            {
                if (LevelElevation(doc, w) > lowestElev + Constants.GeometricToleranceFeet)
                    continue; // only the lowest storey

                if (!(w.Location is LocationCurve lc) || !(lc.Curve is Line wallLine))
                {
                    _log.Warning($"Sockel: Wand {w.Id.Value} hat keine gerade Achse – übersprungen.");
                    continue;
                }

                BoundingBoxXYZ bb = w.get_BoundingBox(null);
                double baseZ = bb != null ? bb.Min.Z : wallLine.GetEndPoint(0).Z;

                Line baseLine = GeometryUtil.FlattenToZ(wallLine, baseZ);
                if (baseLine == null) continue;

                double lengthM = UnitHelper.FeetToMeters(baseLine.Length);
                string status = hasGroundSlab ? Constants.Status.AutoErkannt : Constants.Status.Unklar;
                string note = hasGroundSlab ? null : "Keine Bodenplatte gegen Erdreich erkannt.";

                bridges.Add(WbFactory.Create(
                    Constants.Kategorie.Sockel,
                    Constants.Untertyp.AwAufBpl,
                    baseLine,
                    lengthM,
                    w.Id,
                    ElementId.InvalidElementId,
                    WindowBridgeDetector.LevelName(doc, w),
                    Constants.Aussenbezug.Erdreich,
                    status,
                    note,
                    "BASE"));
            }

            _log.Info($"Sockel/Bodenplattenrand erkannt: {bridges.Count}.");
            return bridges;
        }

        private static double LevelElevation(Document doc, Wall w)
        {
            if (w.LevelId != null && w.LevelId != ElementId.InvalidElementId &&
                doc.GetElement(w.LevelId) is Level lvl)
                return lvl.Elevation;

            BoundingBoxXYZ bb = w.get_BoundingBox(null);
            return bb != null ? bb.Min.Z : 0.0;
        }

        private bool HasFloorAgainstGround(Document doc)
        {
            var floors = new FilteredElementCollector(doc)
                .OfClass(typeof(Floor))
                .Cast<Floor>();

            foreach (Floor f in floors)
            {
                Parameter gegen = f.LookupParameter(Constants.Se.BauteilGegen);
                if (gegen != null && gegen.StorageType == StorageType.String)
                {
                    string v = gegen.AsString();
                    if (!string.IsNullOrWhiteSpace(v) &&
                        v.IndexOf("erdreich", System.StringComparison.OrdinalIgnoreCase) >= 0)
                        return true;
                }
                Parameter typ = f.LookupParameter(Constants.Se.BauteiltypEnergie);
                if (typ != null && typ.StorageType == StorageType.String)
                {
                    string v = typ.AsString();
                    if (!string.IsNullOrWhiteSpace(v) &&
                        v.IndexOf("bodenplatte", System.StringComparison.OrdinalIgnoreCase) >= 0)
                        return true;
                }
            }
            return false;
        }
    }
}
