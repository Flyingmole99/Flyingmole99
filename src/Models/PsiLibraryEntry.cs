namespace ThermalBridgeTool.Models
{
    /// <summary>
    /// One row of the external Psi-value library (CSV/Excel). The library is the
    /// single source of truth for proven Psi values; the model only stores the
    /// code (Psi_Typ_Code) plus a snapshot of value and source for auditability.
    /// </summary>
    public sealed class PsiLibraryEntry
    {
        public string PsiTypCode { get; set; }   // Psi_Typ_Code
        public string Kategorie { get; set; }     // Kategorie
        public string Untertyp { get; set; }      // Untertyp
        public string Beschreibung { get; set; }  // Beschreibung
        public double PsiWert { get; set; }       // Psi_Wert [W/(m·K)]
        public string Quelle { get; set; }        // Quelle
        public string GueltigFuer { get; set; }   // Gueltig_fuer
        public string Status { get; set; }        // Status (freigegeben / entwurf ...)
        public string Version { get; set; }       // Version

        public override string ToString()
        {
            return $"{PsiTypCode}  ({PsiWert:0.000} W/mK)  {Beschreibung}";
        }
    }
}
