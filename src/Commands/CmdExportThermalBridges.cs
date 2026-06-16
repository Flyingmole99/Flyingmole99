using System;
using System.Collections.Generic;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Microsoft.Win32;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;
using ThermalBridgeTool.Services;

namespace ThermalBridgeTool.Commands
{
    [Transaction(TransactionMode.ReadOnly)]
    public sealed class CmdExportThermalBridges : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            Document doc = commandData.Application.ActiveUIDocument.Document;
            Logger log = App.Instance.Log;

            try
            {
                var marker = new MarkerService(log);
                var repo = new ThermalBridgeRepository(marker, log);
                List<ThermalBridge> bridges = repo.CollectAll(doc);
                if (bridges.Count == 0)
                {
                    TaskDialog.Show("Wärmebrücken", "Keine Wärmebrücken zum Export gefunden.");
                    return Result.Cancelled;
                }

                var dlg = new SaveFileDialog
                {
                    Title = "Nachweisliste exportieren",
                    FileName = "Waermebruecken_Nachweis",
                    Filter = "Excel (*.xlsx)|*.xlsx|CSV (*.csv)|*.csv"
                };
                if (dlg.ShowDialog() != true) return Result.Cancelled;

                string version = App.Instance.PsiLibrary.LoadedVersion ?? "n/a";
                var export = new ExcelExportService(log, version);

                if (dlg.FileName.EndsWith(".csv", StringComparison.OrdinalIgnoreCase))
                    export.ExportCsv(dlg.FileName, bridges);
                else
                    export.ExportXlsx(dlg.FileName, bridges);

                TaskDialog.Show("Wärmebrücken",
                    "Export abgeschlossen:\n" + dlg.FileName +
                    "\n\nNur geprüfte Wärmebrücken gehen in die Summe ein.");
                return Result.Succeeded;
            }
            catch (System.Exception ex)
            {
                log.Error("Export fehlgeschlagen", ex);
                message = ex.Message;
                return Result.Failed;
            }
        }
    }
}
