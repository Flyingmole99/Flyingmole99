using System.Collections.Generic;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.Services
{
    /// <summary>
    /// (G) Plausibility check. Produces a list of issues per bridge. A bridge may
    /// only be treated as proven ("nachweiswirksam") when it has no Error-level
    /// issues and its status is "geprüft".
    /// </summary>
    public sealed class ValidationService
    {
        public List<ValidationIssue> Validate(IEnumerable<ThermalBridge> bridges)
        {
            var issues = new List<ValidationIssue>();

            // Duplicate detection across the whole set.
            var seenSignatures = new Dictionary<string, string>();

            foreach (ThermalBridge wb in bridges)
            {
                string id = wb.Id;
                string marker = wb.MarkerElementId?.Value.ToString();

                // Length empty / zero.
                if (wb.LaengeM <= 1e-6)
                    Add(issues, id, marker, IssueSeverity.Error, "LEN_EMPTY",
                        "WB_Laenge ist leer oder 0.");

                // Psi type empty.
                bool psiTypMissing = string.IsNullOrWhiteSpace(wb.PsiTyp);
                if (psiTypMissing)
                    Add(issues, id, marker, IssueSeverity.Warning, "PSITYP_EMPTY",
                        "WB_Psi_Typ ist leer.");

                // Psi value empty.
                if (!wb.HasPsiWert || wb.PsiWert == 0.0)
                    Add(issues, id, marker, IssueSeverity.Warning, "PSIVAL_EMPTY",
                        "WB_Psi_Wert ist leer oder 0.");

                // Source empty.
                if (string.IsNullOrWhiteSpace(wb.Quelle))
                    Add(issues, id, marker, IssueSeverity.Warning, "SRC_EMPTY",
                        "WB_Quelle ist leer.");

                // Still auto-detected / unclear.
                if (wb.Status == Constants.Status.AutoErkannt)
                    Add(issues, id, marker, IssueSeverity.Info, "STATUS_AUTO",
                        "WB_Status noch 'automatisch erkannt' – nicht nachweiswirksam.");
                if (wb.Status == Constants.Status.Unklar)
                    Add(issues, id, marker, IssueSeverity.Warning, "STATUS_UNCLEAR",
                        "WB_Status 'unklar' – Geometrie/Länge prüfen.");

                // Proven but mandatory values missing.
                if (wb.IsProven)
                {
                    if (psiTypMissing || !wb.HasPsiWert || wb.PsiWert == 0.0 ||
                        string.IsNullOrWhiteSpace(wb.Quelle) || wb.LaengeM <= 1e-6)
                    {
                        Add(issues, id, marker, IssueSeverity.Error, "PROVEN_INCOMPLETE",
                            "Status 'geprüft', aber Pflichtwerte (Psi-Typ/Wert/Quelle/Länge) fehlen.");
                    }
                }

                // Floor-slab connection without a valid contact line.
                if (wb.Kategorie == Constants.Kategorie.Geschossdecke && wb.GeometryLine == null)
                    Add(issues, id, marker, IssueSeverity.Error, "DECK_NO_CONTACT",
                        "Geschossdeckenanschluss ohne gültige Kontaktlinie.");

                // Window/door without valid host wall.
                if ((wb.Kategorie == Constants.Kategorie.Fensteranschluss ||
                     wb.Kategorie == Constants.Kategorie.Tueranschluss ||
                     wb.Kategorie == Constants.Kategorie.Terrassentuer) &&
                    string.IsNullOrWhiteSpace(wb.Bauteil1Id))
                    Add(issues, id, marker, IssueSeverity.Error, "NO_HOST",
                        "Fenster/Tür ohne gültige Host-Wand.");

                // Possible duplicate.
                string sig = wb.DuplicateSignature();
                if (seenSignatures.TryGetValue(sig, out string firstId))
                    Add(issues, id, marker, IssueSeverity.Warning, "DUPLICATE",
                        $"Mögliche Dublette zu {firstId}.");
                else
                    seenSignatures[sig] = id;
            }

            return issues;
        }

        private static void Add(List<ValidationIssue> list, string id, string marker,
            IssueSeverity sev, string code, string message)
        {
            list.Add(new ValidationIssue(id, marker, sev, code, message));
        }
    }
}
