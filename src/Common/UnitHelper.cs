using Autodesk.Revit.DB;

namespace ThermalBridgeTool.Common
{
    /// <summary>
    /// Conversion helpers between Revit internal units (feet) and SI metres.
    /// All energetic results are expressed in metres / W·K, so every length
    /// leaving the model is converted here in one single place.
    /// </summary>
    public static class UnitHelper
    {
        /// <summary>Convert an internal Revit length (feet) to metres.</summary>
        public static double FeetToMeters(double feet)
        {
            return UnitUtils.ConvertFromInternalUnits(feet, UnitTypeId.Meters);
        }

        /// <summary>Convert metres to internal Revit length (feet).</summary>
        public static double MetersToFeet(double meters)
        {
            return UnitUtils.ConvertToInternalUnits(meters, UnitTypeId.Meters);
        }

        /// <summary>Rounded metre value, used for stable duplicate signatures.</summary>
        public static double RoundM(double meters, int decimals = 3)
        {
            return System.Math.Round(meters, decimals);
        }
    }
}
