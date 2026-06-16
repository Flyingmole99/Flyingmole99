using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using ClosedXML.Excel;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.Services
{
    /// <summary>
    /// (H) Exports the proof list. Two formats are supported:
    ///   * CSV  – dependency-free, always available.
    ///   * XLSX – via ClosedXML, with a formatted summary row.
    ///
    /// Loss coefficient = Psi * Length [W/K]. Only proven ("geprüft") bridges go
    /// into the final sum; all others are exported but flagged "nicht
    /// nachweiswirksam".
    /// </summary>
    public sealed class ExcelExportService
    {
        private readonly Logger _log;
        private readonly string _libraryVersion;

        public ExcelExportService(Logger log, string libraryVersion)
        {
            _log = log;
            _libraryVersion = libraryVersion ?? "n/a";
        }

        private static readonly string[] Headers =
        {
            "WB_ID", "WB_Kategorie", "WB_Untertyp", "WB_Psi_Typ", "WB_Psi_Wert",
            "WB_Laenge_m", "WB_Verlustkoeffizient_W_K", "WB_Quelle", "WB_Status",
            "WB_Ebene", "WB_Bauteil_1_ID", "WB_Bauteil_2_ID", "WB_Nachweiswirksam",
            "WB_Hinweis"
        };

        public void ExportCsv(string path, IReadOnlyList<ThermalBridge> bridges)
        {
            var ci = CultureInfo.InvariantCulture;
            var sb = new StringBuilder();
            sb.AppendLine(string.Join(";", Headers));

            double sum = 0.0;
            foreach (ThermalBridge wb in bridges)
            {
                bool proven = wb.IsProven;
                if (proven) sum += wb.Verlustkoeffizient;

                sb.AppendLine(string.Join(";", new[]
                {
                    Csv(wb.Id),
                    Csv(wb.Kategorie),
                    Csv(wb.Untertyp),
                    Csv(wb.PsiTyp),
                    wb.HasPsiWert ? wb.PsiWert.ToString("0.###", ci) : "",
                    wb.LaengeM.ToString("0.###", ci),
                    wb.Verlustkoeffizient.ToString("0.####", ci),
                    Csv(wb.Quelle),
                    Csv(wb.Status),
                    Csv(wb.Ebene),
                    Csv(wb.Bauteil1Id),
                    Csv(wb.Bauteil2Id),
                    proven ? "ja" : "nein (nicht nachweiswirksam)",
                    Csv(wb.Hinweis),
                }));
            }

            sb.AppendLine();
            sb.AppendLine(string.Join(";", new[]
            {
                Csv("Summe_Waermebrueckenverlustkoeffizient_W_K (nur geprüft)"),
                "", "", "", "", "", sum.ToString("0.####", ci), "", "", "", "", "", "", ""
            }));
            sb.AppendLine(string.Join(";", new[] { Csv("Psi-Bibliothek Version"), Csv(_libraryVersion) }));
            sb.AppendLine(string.Join(";", new[] { Csv("Export"), Csv(DateTime.Now.ToString("yyyy-MM-dd HH:mm")) }));

            File.WriteAllText(path, sb.ToString(), new UTF8Encoding(true));
            _log.Info($"CSV-Export geschrieben: {path} ({bridges.Count} Zeilen, Summe {sum:0.###} W/K).");
        }

        public void ExportXlsx(string path, IReadOnlyList<ThermalBridge> bridges)
        {
            using (var wbDoc = new XLWorkbook())
            {
                IXLWorksheet ws = wbDoc.Worksheets.Add("Wärmebrücken");

                for (int c = 0; c < Headers.Length; c++)
                {
                    IXLCell cell = ws.Cell(1, c + 1);
                    cell.Value = Headers[c];
                    cell.Style.Font.Bold = true;
                    cell.Style.Fill.BackgroundColor = XLColor.LightGray;
                }

                int row = 2;
                double sum = 0.0;
                foreach (ThermalBridge wb in bridges)
                {
                    bool proven = wb.IsProven;
                    if (proven) sum += wb.Verlustkoeffizient;

                    ws.Cell(row, 1).Value = wb.Id;
                    ws.Cell(row, 2).Value = wb.Kategorie;
                    ws.Cell(row, 3).Value = wb.Untertyp;
                    ws.Cell(row, 4).Value = wb.PsiTyp;
                    if (wb.HasPsiWert) ws.Cell(row, 5).Value = wb.PsiWert;
                    ws.Cell(row, 6).Value = wb.LaengeM;
                    ws.Cell(row, 7).Value = wb.Verlustkoeffizient;
                    ws.Cell(row, 8).Value = wb.Quelle;
                    ws.Cell(row, 9).Value = wb.Status;
                    ws.Cell(row, 10).Value = wb.Ebene;
                    ws.Cell(row, 11).Value = wb.Bauteil1Id;
                    ws.Cell(row, 12).Value = wb.Bauteil2Id;
                    ws.Cell(row, 13).Value = proven ? "ja" : "nein (nicht nachweiswirksam)";
                    ws.Cell(row, 14).Value = wb.Hinweis;

                    if (!proven)
                        ws.Range(row, 1, row, Headers.Length).Style.Font.FontColor = XLColor.Gray;
                    row++;
                }

                int sumRow = row + 1;
                ws.Cell(sumRow, 1).Value = "Summe_Waermebrueckenverlustkoeffizient_W_K (nur geprüft)";
                ws.Cell(sumRow, 1).Style.Font.Bold = true;
                ws.Cell(sumRow, 7).Value = sum;
                ws.Cell(sumRow, 7).Style.Font.Bold = true;
                ws.Cell(sumRow, 7).Style.Fill.BackgroundColor = XLColor.LightYellow;

                ws.Cell(sumRow + 1, 1).Value = "Psi-Bibliothek Version";
                ws.Cell(sumRow + 1, 2).Value = _libraryVersion;
                ws.Cell(sumRow + 2, 1).Value = "Export";
                ws.Cell(sumRow + 2, 2).Value = DateTime.Now.ToString("yyyy-MM-dd HH:mm");

                ws.Columns().AdjustToContents();
                wbDoc.SaveAs(path);
            }

            double total = bridges.Where(b => b.IsProven).Sum(b => b.Verlustkoeffizient);
            _log.Info($"XLSX-Export geschrieben: {path} ({bridges.Count} Zeilen, Summe {total:0.###} W/K).");
        }

        private static string Csv(string value)
        {
            if (string.IsNullOrEmpty(value)) return "";
            if (value.Contains(';') || value.Contains('"') || value.Contains('\n'))
                return "\"" + value.Replace("\"", "\"\"") + "\"";
            return value;
        }
    }
}
