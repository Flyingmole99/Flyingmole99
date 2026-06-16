using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;
using ThermalBridgeTool.Common;

namespace ThermalBridgeTool.Services.Detectors
{
    /// <summary>
    /// The four edges of a rectangular opening expressed as lines (feet).
    /// </summary>
    public sealed class OpeningEdges
    {
        public Line Left;
        public Line Right;
        public Line Head;   // Sturz / top
        public Line Sill;   // Brüstung / Schwelle / bottom
        public double WidthM;
        public double HeightM;
        public bool IsReliable;   // false => geometry was estimated
        public string Note;       // warning text if not reliable
    }

    /// <summary>
    /// Derives the four reveal/head/sill edges of a window or door from its
    /// host wall direction and its width/height. Geometry placement is
    /// approximate (bounding-box centred); the edge *lengths* are taken from the
    /// type/instance dimensions, which is what the energetic calc relies on.
    /// </summary>
    public static class OpeningGeometryHelper
    {
        public static OpeningEdges Compute(FamilyInstance fi, Wall hostWall)
        {
            var edges = new OpeningEdges { IsReliable = true };

            // --- width / height -------------------------------------------------
            // Use the well-known, version-stable family dimension parameters and
            // fall back to the bounding box when they are not populated.
            double widthFeet = GetDimension(fi,
                BuiltInParameter.FAMILY_WIDTH_PARAM,
                BuiltInParameter.FAMILY_ROUGH_WIDTH_PARAM);
            double heightFeet = GetDimension(fi,
                BuiltInParameter.FAMILY_HEIGHT_PARAM,
                BuiltInParameter.FAMILY_ROUGH_HEIGHT_PARAM);

            BoundingBoxXYZ bb = fi.get_BoundingBox(null);

            if (widthFeet <= 1e-6 || heightFeet <= 1e-6)
            {
                // Fall back to bounding box extents.
                if (bb != null)
                {
                    double dx = Math.Abs(bb.Max.X - bb.Min.X);
                    double dy = Math.Abs(bb.Max.Y - bb.Min.Y);
                    if (widthFeet <= 1e-6) widthFeet = Math.Max(dx, dy);
                    if (heightFeet <= 1e-6) heightFeet = Math.Abs(bb.Max.Z - bb.Min.Z);
                    edges.IsReliable = false;
                    edges.Note = "Maße aus Bounding-Box geschätzt.";
                }
            }

            if (widthFeet <= 1e-6 || heightFeet <= 1e-6)
                return null; // cannot determine geometry at all

            edges.WidthM = UnitHelper.FeetToMeters(widthFeet);
            edges.HeightM = UnitHelper.FeetToMeters(heightFeet);

            // --- placement & orientation ---------------------------------------
            XYZ center = bb != null ? (bb.Min + bb.Max) * 0.5 : GetInsertionPoint(fi);
            if (center == null) return null;

            XYZ wallDir = GetWallDirection(hostWall);
            if (wallDir == null)
            {
                // Use the facing-perpendicular as a fallback.
                XYZ facing = fi.FacingOrientation;
                wallDir = new XYZ(-facing.Y, facing.X, 0);
                if (wallDir.GetLength() < 1e-6) wallDir = XYZ.BasisX;
                edges.IsReliable = false;
                edges.Note = (edges.Note ?? "") + " Wandrichtung aus Fenster-Ausrichtung abgeleitet.";
            }
            wallDir = wallDir.Normalize();
            XYZ up = XYZ.BasisZ;

            double hw = widthFeet * 0.5;
            double hh = heightFeet * 0.5;

            XYZ bl = center - (wallDir * hw) - (up * hh);
            XYZ br = center + (wallDir * hw) - (up * hh);
            XYZ tl = center - (wallDir * hw) + (up * hh);
            XYZ tr = center + (wallDir * hw) + (up * hh);

            edges.Left = Line.CreateBound(bl, tl);
            edges.Right = Line.CreateBound(br, tr);
            edges.Head = Line.CreateBound(tl, tr);
            edges.Sill = Line.CreateBound(bl, br);
            return edges;
        }

        private static double GetDimension(FamilyInstance fi, params BuiltInParameter[] candidates)
        {
            foreach (BuiltInParameter bip in candidates)
            {
                // instance first ...
                Parameter p = fi.get_Parameter(bip);
                if (p != null && p.HasValue && p.StorageType == StorageType.Double)
                {
                    double v = p.AsDouble();
                    if (v > 1e-6) return v;
                }
                // ... then the type
                FamilySymbol sym = fi.Symbol;
                Parameter pt = sym?.get_Parameter(bip);
                if (pt != null && pt.HasValue && pt.StorageType == StorageType.Double)
                {
                    double v = pt.AsDouble();
                    if (v > 1e-6) return v;
                }
            }
            return 0.0;
        }

        private static XYZ GetWallDirection(Wall wall)
        {
            if (wall?.Location is LocationCurve lc && lc.Curve is Line line)
                return new XYZ(line.Direction.X, line.Direction.Y, 0);
            return null;
        }

        private static XYZ GetInsertionPoint(FamilyInstance fi)
        {
            return (fi.Location as LocationPoint)?.Point;
        }
    }
}
