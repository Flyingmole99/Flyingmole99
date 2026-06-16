namespace ThermalBridgeTool.Models
{
    /// <summary>
    /// Options controlling the auto-detection run. Defaults are conservative.
    /// </summary>
    public sealed class DetectionOptions
    {
        public bool DetectWindows { get; set; } = true;
        public bool DetectDoors { get; set; } = true;
        public bool DetectPlinth { get; set; } = true;
        public bool DetectFloorSlabs { get; set; } = true;

        /// <summary>
        /// If true, all existing auto-detected markers (status "automatisch
        /// erkannt" / "unklar") are deleted before a fresh detection run.
        /// Proven ("geprüft") markers are never touched automatically.
        /// </summary>
        public bool DeleteExistingAutoBeforeRun { get; set; } = false;

        /// <summary>
        /// If true, a wall is treated as part of the thermal envelope only when
        /// SE_Thermische_Huelle is explicitly set. If false, the wall "Function =
        /// Exterior" is accepted as a fallback heuristic.
        /// </summary>
        public bool RequireExplicitEnvelopeFlag { get; set; } = false;
    }
}
