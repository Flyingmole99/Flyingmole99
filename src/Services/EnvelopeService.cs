using Autodesk.Revit.DB;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.Services
{
    /// <summary>
    /// Decides whether a host component (wall/floor) belongs to the thermal
    /// envelope and against what it faces. Prefers the explicit SE_* parameters;
    /// falls back to the Revit "Function = Exterior" heuristic when allowed.
    /// </summary>
    public sealed class EnvelopeService
    {
        private readonly DetectionOptions _options;

        public EnvelopeService(DetectionOptions options)
        {
            _options = options;
        }

        public bool IsEnvelope(Element host)
        {
            if (host == null) return false;

            Parameter flag = host.LookupParameter(Constants.Se.ThermischeHuelle);
            if (flag != null && flag.HasValue && flag.StorageType == StorageType.Integer)
            {
                if (flag.AsInteger() == 1) return true;
                // Explicitly set to "No" => never envelope.
                if (flag.AsInteger() == 0 && _options.RequireExplicitEnvelopeFlag) return false;
            }

            if (_options.RequireExplicitEnvelopeFlag)
                return false; // only the explicit flag counts

            // Fallback heuristic for walls: Function = Exterior.
            if (host is Wall wall)
                return IsExteriorWall(wall);

            return false;
        }

        public static bool IsExteriorWall(Wall wall)
        {
            if (wall == null) return false;
            WallType wt = wall.WallType;
            if (wt == null) return false;
            Parameter f = wt.get_Parameter(BuiltInParameter.FUNCTION_PARAM);
            if (f != null && f.HasValue)
                return f.AsInteger() == (int)WallFunction.Exterior;
            return false;
        }

        /// <summary>
        /// Reads SE_Bauteil_gegen if present, otherwise returns "Außenluft" as a
        /// conservative default for an envelope wall.
        /// </summary>
        public string ThermalReference(Element host)
        {
            Parameter p = host?.LookupParameter(Constants.Se.BauteilGegen);
            if (p != null && p.StorageType == StorageType.String)
            {
                string v = p.AsString();
                if (!string.IsNullOrWhiteSpace(v)) return v;
            }
            return Constants.Aussenbezug.Aussenluft;
        }
    }
}
