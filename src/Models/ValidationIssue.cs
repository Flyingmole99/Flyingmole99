namespace ThermalBridgeTool.Models
{
    public enum IssueSeverity { Info, Warning, Error }

    /// <summary>
    /// One finding of the plausibility check. Severity drives whether a bridge
    /// may be promoted to "geprüft" / exported as proven.
    /// </summary>
    public sealed class ValidationIssue
    {
        public string WbId { get; set; }
        public string MarkerElementId { get; set; }
        public IssueSeverity Severity { get; set; }
        public string Code { get; set; }      // short machine code, e.g. "LEN_EMPTY"
        public string Message { get; set; }   // human readable (German)

        public ValidationIssue() { }

        public ValidationIssue(string wbId, string markerId, IssueSeverity severity, string code, string message)
        {
            WbId = wbId;
            MarkerElementId = markerId;
            Severity = severity;
            Code = code;
            Message = message;
        }
    }
}
