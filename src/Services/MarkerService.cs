using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.Services
{
    /// <summary>
    /// Creates and updates the physical marker objects for thermal bridges and
    /// maps between the <see cref="ThermalBridge"/> model and the element
    /// parameters.
    ///
    /// Object strategy (see README, section K): the marker is a DirectShape in
    /// the Generic Models category carrying a thin bar solid. This is the most
    /// robust option because it requires no shipped .rfa, works in every
    /// project, is visible in plan/section/3D and is filterable by the shared
    /// parameters. A line-based loadable family ("WB_Linear.rfa") can be plugged
    /// in later via the same WriteParameters/ReadBridge mapping.
    /// </summary>
    public sealed class MarkerService
    {
        private readonly Logger _log;

        public MarkerService(Logger log)
        {
            _log = log;
        }

        /// <summary>
        /// Creates a DirectShape marker for the given bridge inside an already
        /// open transaction. Returns the created element id (or null on failure).
        /// </summary>
        public ElementId CreateMarker(Document doc, ThermalBridge wb)
        {
            if (wb.GeometryLine == null)
            {
                _log.Warning($"Wärmebrücke {wb.Id} ohne Geometrie – Marker übersprungen.");
                return null;
            }

            try
            {
                Solid solid = GeometryUtil.CreateBarSolid(wb.GeometryLine, Constants.MarkerHalfThicknessFeet);
                IList<GeometryObject> geom;

                if (solid != null)
                {
                    geom = new List<GeometryObject> { solid };
                }
                else
                {
                    // Fall back to the bare line so the bridge is still recorded.
                    geom = new List<GeometryObject> { wb.GeometryLine };
                    wb.Hinweis = Append(wb.Hinweis, "Marker als Linie (Solid fehlgeschlagen).");
                }

                DirectShape ds = DirectShape.CreateElement(
                    doc, new ElementId(BuiltInCategory.OST_GenericModel));
                ds.ApplicationId = "ThermalBridgeTool";
                ds.ApplicationDataId = wb.Id;
                ds.SetShape(geom);
                ds.Name = $"WB {wb.Kategorie} {wb.Untertyp}".Trim();

                wb.MarkerElementId = ds.Id;
                WriteParameters(ds, wb);
                return ds.Id;
            }
            catch (Exception ex)
            {
                _log.Error($"Marker für {wb.Id} konnte nicht erzeugt werden.", ex);
                return null;
            }
        }

        /// <summary>Writes all WB_* parameters from the model onto the element.</summary>
        public void WriteParameters(Element e, ThermalBridge wb)
        {
            SetString(e, Constants.Wb.Id, wb.Id);
            SetString(e, Constants.Wb.Kategorie, wb.Kategorie);
            SetString(e, Constants.Wb.Untertyp, wb.Untertyp);
            SetString(e, Constants.Wb.PsiTyp, wb.PsiTyp);
            if (wb.HasPsiWert) SetDouble(e, Constants.Wb.PsiWert, wb.PsiWert);
            SetLength(e, Constants.Wb.Laenge, UnitHelper.MetersToFeet(wb.LaengeM));
            SetDouble(e, Constants.Wb.Verlustkoeffizient, wb.Verlustkoeffizient);
            SetString(e, Constants.Wb.Quelle, wb.Quelle);
            SetString(e, Constants.Wb.Status, wb.Status);
            SetString(e, Constants.Wb.Bauteil1Id, wb.Bauteil1Id);
            SetString(e, Constants.Wb.Bauteil2Id, wb.Bauteil2Id);
            SetString(e, Constants.Wb.Ebene, wb.Ebene);
            SetString(e, Constants.Wb.Aussenbezug, wb.Aussenbezug);
            SetString(e, Constants.Wb.Hinweis, wb.Hinweis);
        }

        /// <summary>Reads a <see cref="ThermalBridge"/> back from a marker element.</summary>
        public ThermalBridge ReadBridge(Element e)
        {
            string id = GetString(e, Constants.Wb.Id);
            if (string.IsNullOrEmpty(id))
                return null; // not one of our markers

            var wb = new ThermalBridge
            {
                Id = id,
                Kategorie = GetString(e, Constants.Wb.Kategorie),
                Untertyp = GetString(e, Constants.Wb.Untertyp),
                PsiTyp = GetString(e, Constants.Wb.PsiTyp),
                Quelle = GetString(e, Constants.Wb.Quelle),
                Status = GetString(e, Constants.Wb.Status),
                Bauteil1Id = GetString(e, Constants.Wb.Bauteil1Id),
                Bauteil2Id = GetString(e, Constants.Wb.Bauteil2Id),
                Ebene = GetString(e, Constants.Wb.Ebene),
                Aussenbezug = GetString(e, Constants.Wb.Aussenbezug),
                Hinweis = GetString(e, Constants.Wb.Hinweis),
                MarkerElementId = e.Id,
            };

            Parameter pPsi = e.LookupParameter(Constants.Wb.PsiWert);
            if (pPsi != null && pPsi.HasValue)
            {
                wb.PsiWert = pPsi.AsDouble();
                wb.HasPsiWert = true;
            }

            Parameter pLen = e.LookupParameter(Constants.Wb.Laenge);
            if (pLen != null && pLen.HasValue)
                wb.LaengeM = UnitHelper.FeetToMeters(pLen.AsDouble());

            wb.GeometryLine = TryGetMarkerLine(e);
            return wb;
        }

        /// <summary>Best-effort reconstruction of the bridge line from geometry.</summary>
        private static Line TryGetMarkerLine(Element e)
        {
            try
            {
                BoundingBoxXYZ bb = e.get_BoundingBox(null);
                if (bb == null) return null;
                // Use the bounding box diagonal direction is unreliable; instead
                // expose only the midpoint via a degenerate-safe line. The real
                // line is not needed after creation except for the midpoint, so
                // return a short line at the bbox centre.
                XYZ c = (bb.Min + bb.Max) * 0.5;
                return Line.CreateBound(c, c + new XYZ(0.01, 0, 0));
            }
            catch
            {
                return null;
            }
        }

        // ---------------------------------------------------------------
        // Parameter helpers
        // ---------------------------------------------------------------
        private static void SetString(Element e, string name, string value)
        {
            Parameter p = e.LookupParameter(name);
            if (p != null && !p.IsReadOnly && p.StorageType == StorageType.String)
                p.Set(value ?? string.Empty);
        }

        private static void SetDouble(Element e, string name, double value)
        {
            Parameter p = e.LookupParameter(name);
            if (p != null && !p.IsReadOnly && p.StorageType == StorageType.Double)
                p.Set(value);
        }

        private static void SetLength(Element e, string name, double feet)
        {
            Parameter p = e.LookupParameter(name);
            if (p != null && !p.IsReadOnly && p.StorageType == StorageType.Double)
                p.Set(feet);
        }

        private static string GetString(Element e, string name)
        {
            Parameter p = e.LookupParameter(name);
            return (p != null && p.StorageType == StorageType.String) ? p.AsString() : null;
        }

        private static string Append(string existing, string add)
        {
            if (string.IsNullOrEmpty(existing)) return add;
            return existing + " | " + add;
        }
    }
}
