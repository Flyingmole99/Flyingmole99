using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.Services
{
    /// <summary>
    /// (F) Loads the external Psi-value library (CSV) and assigns a Psi_Typ_Code
    /// to a thermal bridge. On assignment the Psi value and source are copied
    /// from the library so the model carries an auditable snapshot, while the
    /// code preserves the link back to the library version.
    /// </summary>
    public sealed class PsiLibraryService
    {
        private readonly Logger _log;
        private readonly List<PsiLibraryEntry> _entries = new List<PsiLibraryEntry>();

        public PsiLibraryService(Logger log)
        {
            _log = log;
        }

        public IReadOnlyList<PsiLibraryEntry> Entries => _entries;
        public string LoadedVersion { get; private set; }
        public string LoadedPath { get; private set; }

        /// <summary>
        /// Reads the library from a CSV file. Auto-detects ';' vs ',' separators
        /// and accepts both '.' and ',' decimal separators for the Psi value.
        /// </summary>
        public int Load(string path)
        {
            _entries.Clear();
            if (!File.Exists(path))
                throw new FileNotFoundException("Psi-Bibliothek nicht gefunden.", path);

            string[] lines = File.ReadAllLines(path, Encoding.UTF8);
            if (lines.Length < 2)
            {
                _log.Warning("Psi-Bibliothek enthält keine Datenzeilen.");
                return 0;
            }

            char sep = DetectSeparator(lines[0]);
            string[] header = SplitLine(lines[0], sep);
            var idx = MapHeader(header);

            for (int i = 1; i < lines.Length; i++)
            {
                if (string.IsNullOrWhiteSpace(lines[i])) continue;
                string[] cols = SplitLine(lines[i], sep);

                var entry = new PsiLibraryEntry
                {
                    PsiTypCode = Get(cols, idx, "psi_typ_code"),
                    Kategorie = Get(cols, idx, "kategorie"),
                    Untertyp = Get(cols, idx, "untertyp"),
                    Beschreibung = Get(cols, idx, "beschreibung"),
                    PsiWert = ParseDouble(Get(cols, idx, "psi_wert")),
                    Quelle = Get(cols, idx, "quelle"),
                    GueltigFuer = Get(cols, idx, "gueltig_fuer"),
                    Status = Get(cols, idx, "status"),
                    Version = Get(cols, idx, "version"),
                };

                if (string.IsNullOrWhiteSpace(entry.PsiTypCode))
                    continue;
                _entries.Add(entry);
            }

            LoadedPath = path;
            LoadedVersion = _entries.Select(e => e.Version)
                                    .FirstOrDefault(v => !string.IsNullOrWhiteSpace(v)) ?? "n/a";
            _log.Info($"Psi-Bibliothek geladen: {_entries.Count} Einträge (Version {LoadedVersion}).");
            return _entries.Count;
        }

        public PsiLibraryEntry Find(string code)
        {
            if (string.IsNullOrWhiteSpace(code)) return null;
            return _entries.FirstOrDefault(e =>
                string.Equals(e.PsiTypCode, code, StringComparison.OrdinalIgnoreCase));
        }

        /// <summary>
        /// Applies a library entry to a bridge: sets Psi type, value and source.
        /// Does NOT change the status – promoting to "geprüft" stays a manual,
        /// explicit user decision.
        /// </summary>
        public bool Assign(ThermalBridge wb, string psiTypCode)
        {
            PsiLibraryEntry entry = Find(psiTypCode);
            if (entry == null)
            {
                _log.Warning($"Psi-Code '{psiTypCode}' nicht in Bibliothek gefunden.");
                return false;
            }

            wb.PsiTyp = entry.PsiTypCode;
            wb.PsiWert = entry.PsiWert;
            wb.HasPsiWert = true;
            wb.Quelle = string.IsNullOrWhiteSpace(entry.Version)
                ? entry.Quelle
                : $"{entry.Quelle} (v{entry.Version})";
            return true;
        }

        // ---------------------------------------------------------------
        private static char DetectSeparator(string headerLine)
        {
            int semic = headerLine.Count(c => c == ';');
            int comma = headerLine.Count(c => c == ',');
            return semic >= comma ? ';' : ',';
        }

        private static string[] SplitLine(string line, char sep)
        {
            // Minimal CSV: supports quoted fields containing the separator.
            var result = new List<string>();
            var sb = new StringBuilder();
            bool inQuotes = false;
            foreach (char c in line)
            {
                if (c == '"') { inQuotes = !inQuotes; continue; }
                if (c == sep && !inQuotes) { result.Add(sb.ToString().Trim()); sb.Clear(); }
                else sb.Append(c);
            }
            result.Add(sb.ToString().Trim());
            return result.ToArray();
        }

        private static Dictionary<string, int> MapHeader(string[] header)
        {
            var map = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            for (int i = 0; i < header.Length; i++)
            {
                string key = header[i].Trim().ToLowerInvariant();
                if (!map.ContainsKey(key)) map[key] = i;
            }
            return map;
        }

        private static string Get(string[] cols, Dictionary<string, int> idx, string name)
        {
            if (idx.TryGetValue(name, out int i) && i < cols.Length)
                return cols[i];
            return string.Empty;
        }

        private static double ParseDouble(string raw)
        {
            if (string.IsNullOrWhiteSpace(raw)) return 0.0;
            raw = raw.Trim().Replace(',', '.');
            return double.TryParse(raw, NumberStyles.Any, CultureInfo.InvariantCulture, out double v)
                ? v : 0.0;
        }
    }
}
