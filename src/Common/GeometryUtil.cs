using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;

namespace ThermalBridgeTool.Common
{
    /// <summary>
    /// Geometry helpers shared by the detectors and the marker service.
    /// All inputs/outputs are in Revit internal units (feet).
    /// </summary>
    public static class GeometryUtil
    {
        /// <summary>
        /// Returns a stable unit vector perpendicular to <paramref name="dir"/>.
        /// </summary>
        public static XYZ AnyPerpendicular(XYZ dir)
        {
            XYZ n = dir.Normalize();
            XYZ reference = Math.Abs(n.Z) < 0.9 ? XYZ.BasisZ : XYZ.BasisX;
            XYZ perp = n.CrossProduct(reference);
            if (perp.GetLength() < 1e-9)
                perp = n.CrossProduct(XYZ.BasisY);
            return perp.Normalize();
        }

        /// <summary>
        /// Builds a thin rectangular bar solid centred on <paramref name="line"/>
        /// so a linear bridge is visible (with thickness) in plan, section and 3D.
        /// Returns null if the geometry could not be created.
        /// </summary>
        public static Solid CreateBarSolid(Line line, double halfThickness)
        {
            try
            {
                XYZ start = line.GetEndPoint(0);
                XYZ dir = (line.GetEndPoint(1) - start).Normalize();
                double length = line.Length;
                if (length < 1e-6) return null;

                XYZ u = AnyPerpendicular(dir);
                XYZ v = dir.CrossProduct(u).Normalize();

                XYZ p0 = start + (u * halfThickness) + (v * halfThickness);
                XYZ p1 = start + (u * halfThickness) - (v * halfThickness);
                XYZ p2 = start - (u * halfThickness) - (v * halfThickness);
                XYZ p3 = start - (u * halfThickness) + (v * halfThickness);

                var profile = new List<Curve>
                {
                    Line.CreateBound(p0, p1),
                    Line.CreateBound(p1, p2),
                    Line.CreateBound(p2, p3),
                    Line.CreateBound(p3, p0),
                };
                var loop = CurveLoop.Create(profile);

                return GeometryCreationUtilities.CreateExtrusionGeometry(
                    new List<CurveLoop> { loop }, dir, length);
            }
            catch
            {
                return null;
            }
        }

        /// <summary>
        /// Horizontal projection of a curve onto a plane at a given Z.
        /// Returns null if the curve is not a (near) straight line.
        /// </summary>
        public static Line FlattenToZ(Curve curve, double z)
        {
            if (curve is Line ln)
            {
                XYZ a = ln.GetEndPoint(0);
                XYZ b = ln.GetEndPoint(1);
                XYZ a2 = new XYZ(a.X, a.Y, z);
                XYZ b2 = new XYZ(b.X, b.Y, z);
                if (a2.DistanceTo(b2) < 1e-6) return null;
                return Line.CreateBound(a2, b2);
            }
            return null;
        }

        /// <summary>Whether two points are within tolerance (feet).</summary>
        public static bool AlmostEqual(XYZ a, XYZ b, double tol)
        {
            return a.DistanceTo(b) <= tol;
        }
    }
}
