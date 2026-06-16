using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.Services.Detectors
{
    /// <summary>
    /// (D) Detects floor-slab edges at envelope walls ("Deckenrand an
    /// Außenwand"). A contact line is created along the wall at the floor
    /// elevation when the floor footprint overlaps the wall and the floor sits
    /// within the wall's vertical span (above the base, to avoid double-counting
    /// the plinth).
    ///
    /// NOTE: A precise wall/floor contact length needs solid-solid intersection,
    /// which is fragile across models. This stage uses a conservative bounding-
    /// box overlap test and uses the wall length as contact length, flagging the
    /// result as an approximation. When no reliable overlap is found, nothing is
    /// created (validation rule "Geschossdeckenanschluss ohne gültige
    /// Kontaktlinie" then never produces a false positive).
    /// </summary>
    public sealed class FloorSlabBridgeDetector
    {
        private readonly EnvelopeService _envelope;
        private readonly Logger _log;

        public FloorSlabBridgeDetector(EnvelopeService envelope, Logger log)
        {
            _envelope = envelope;
            _log = log;
        }

        public List<ThermalBridge> Detect(Document doc)
        {
            var bridges = new List<ThermalBridge>();

            var walls = new FilteredElementCollector(doc)
                .OfClass(typeof(Wall))
                .Cast<Wall>()
                .Where(w => _envelope.IsEnvelope(w))
                .ToList();

            var floors = new FilteredElementCollector(doc)
                .OfClass(typeof(Floor))
                .Cast<Floor>()
                .ToList();

            foreach (Floor floor in floors)
            {
                BoundingBoxXYZ fbb = floor.get_BoundingBox(null);
                if (fbb == null) continue;
                double floorZ = FloorElevation(doc, floor, fbb);

                foreach (Wall wall in walls)
                {
                    if (!(wall.Location is LocationCurve lc) || !(lc.Curve is Line wallLine))
                        continue;

                    BoundingBoxXYZ wbb = wall.get_BoundingBox(null);
                    if (wbb == null) continue;

                    // Floor must sit within the wall height, but not at its very base
                    // (that is the plinth, handled separately).
                    double tol = Constants.GeometricToleranceFeet;
                    if (floorZ <= wbb.Min.Z + tol) continue;          // plinth / below
                    if (floorZ >= wbb.Max.Z - tol) continue;          // at/above top

                    if (!OverlapXY(wbb, fbb)) continue;

                    Line contact = GeometryUtil.FlattenToZ(wallLine, floorZ);
                    if (contact == null) continue;

                    double lengthM = UnitHelper.FeetToMeters(contact.Length);
                    string ebene = WindowBridgeDetector.LevelName(doc, floor);
                    string bezug = _envelope.ThermalReference(wall);

                    bridges.Add(WbFactory.Create(
                        Constants.Kategorie.Geschossdecke,
                        Constants.Untertyp.Deckenrand,
                        contact,
                        lengthM,
                        wall.Id,
                        floor.Id,
                        ebene,
                        bezug,
                        // Approximate contact length => mark "unklar" so the user
                        // verifies the length before it counts.
                        Constants.Status.Unklar,
                        "Kontaktlänge = Wandachsenlänge (Näherung) – Länge prüfen.",
                        "DECK-" + floor.Id.Value));
                }
            }

            _log.Info($"Geschossdeckenanschlüsse erkannt: {bridges.Count}.");
            return bridges;
        }

        private static bool OverlapXY(BoundingBoxXYZ a, BoundingBoxXYZ b)
        {
            bool xOverlap = a.Min.X <= b.Max.X && a.Max.X >= b.Min.X;
            bool yOverlap = a.Min.Y <= b.Max.Y && a.Max.Y >= b.Min.Y;
            return xOverlap && yOverlap;
        }

        private static double FloorElevation(Document doc, Floor floor, BoundingBoxXYZ fbb)
        {
            if (floor.LevelId != null && floor.LevelId != ElementId.InvalidElementId &&
                doc.GetElement(floor.LevelId) is Level lvl)
                return lvl.Elevation;
            return (fbb.Min.Z + fbb.Max.Z) * 0.5;
        }
    }
}
