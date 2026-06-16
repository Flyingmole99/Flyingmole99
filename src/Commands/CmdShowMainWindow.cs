using System.Collections.Generic;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Microsoft.Win32;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;
using ThermalBridgeTool.Services;
using ThermalBridgeTool.UI;

namespace ThermalBridgeTool.Commands
{
    /// <summary>
    /// Control panel command. Shows the main window and dispatches each chosen
    /// step. Every step runs in this command's valid API context; after a step
    /// the panel reopens so the user can continue the workflow.
    /// </summary>
    [Transaction(TransactionMode.Manual)]
    public sealed class CmdShowMainWindow : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;
            Logger log = App.Instance.Log;

            while (true)
            {
                var window = new MainWindow();
                window.ShowDialog();
                MainAction action = window.SelectedAction;
                if (action == MainAction.Close || action == MainAction.None)
                    break;

                try
                {
                    Dispatch(action, doc, log);
                }
                catch (System.Exception ex)
                {
                    log.Error("Aktion fehlgeschlagen: " + action, ex);
                    TaskDialog.Show("Wärmebrücken", "Fehler: " + ex.Message);
                }
            }
            return Result.Succeeded;
        }

        private void Dispatch(MainAction action, Document doc, Logger log)
        {
            var marker = new MarkerService(log);
            var repo = new ThermalBridgeRepository(marker, log);

            switch (action)
            {
                case MainAction.Params:
                    new ParameterService(log).EnsureParameters(doc);
                    TaskDialog.Show("Wärmebrücken", "Parameter geprüft/angelegt.");
                    break;

                case MainAction.Detect:
                    RunDetection(doc, log, deleteFirst: false);
                    break;

                case MainAction.Recreate:
                    RunDetection(doc, log, deleteFirst: true);
                    break;

                case MainAction.LoadLib:
                    LoadLibrary();
                    break;

                case MainAction.Assign:
                    Assign(doc, log, marker, repo);
                    break;

                case MainAction.Validate:
                    Validate(doc, repo);
                    break;

                case MainAction.Export:
                    Export(doc, log, repo);
                    break;
            }
        }

        private static void RunDetection(Document doc, Logger log, bool deleteFirst)
        {
            var options = new DetectionOptions { DeleteExistingAutoBeforeRun = deleteFirst };
            DetectionResult result = CmdDetectThermalBridges.BuildService(log).Run(doc, options);
            TaskDialog.Show("Wärmebrücken",
                $"Neu: {result.Created}, bereits vorhanden: {result.AlreadyPresent}, " +
                $"übersprungen: {result.Skipped}.");
        }

        private static void LoadLibrary()
        {
            var dlg = new OpenFileDialog
            {
                Title = "Psi-Bibliothek (CSV) laden",
                Filter = "CSV-Dateien (*.csv)|*.csv|Alle Dateien (*.*)|*.*"
            };
            if (dlg.ShowDialog() != true) return;
            int n = App.Instance.PsiLibrary.Load(dlg.FileName);
            TaskDialog.Show("Wärmebrücken", $"{n} Psi-Einträge geladen " +
                $"(Version {App.Instance.PsiLibrary.LoadedVersion}).");
        }

        private static void Assign(Document doc, Logger log, MarkerService marker, ThermalBridgeRepository repo)
        {
            PsiLibraryService library = App.Instance.PsiLibrary;
            if (library.Entries.Count == 0)
            {
                TaskDialog.Show("Wärmebrücken", "Bitte zuerst die Psi-Bibliothek laden (Schritt 3).");
                return;
            }
            List<ThermalBridge> bridges = repo.CollectAll(doc);
            if (bridges.Count == 0)
            {
                TaskDialog.Show("Wärmebrücken", "Keine Wärmebrücken gefunden.");
                return;
            }

            var win = new AssignPsiTypeWindow(bridges, library.Entries);
            if (win.ShowDialog() != true || !win.ApplyRequested) return;

            using (var tx = new Transaction(doc, "Psi-Typen zuordnen"))
            {
                tx.Start();
                int applied = 0;
                foreach (ThermalBridge wb in win.SelectedBridges)
                {
                    if (!library.Assign(wb, win.ChosenCode)) continue;
                    if (win.SetProven) wb.Status = Constants.Status.Geprueft;
                    Element e = doc.GetElement(wb.MarkerElementId);
                    if (e != null) { marker.WriteParameters(e, wb); applied++; }
                }
                tx.Commit();
                TaskDialog.Show("Wärmebrücken", $"Auf {applied} Wärmebrücke(n) angewendet.");
            }
        }

        private static void Validate(Document doc, ThermalBridgeRepository repo)
        {
            List<ThermalBridge> bridges = repo.CollectAll(doc);
            if (bridges.Count == 0)
            {
                TaskDialog.Show("Wärmebrücken", "Keine Wärmebrücken gefunden.");
                return;
            }
            List<ValidationIssue> issues = new ValidationService().Validate(bridges);
            new ValidationResultWindow(issues).ShowDialog();
        }

        private static void Export(Document doc, Logger log, ThermalBridgeRepository repo)
        {
            List<ThermalBridge> bridges = repo.CollectAll(doc);
            if (bridges.Count == 0)
            {
                TaskDialog.Show("Wärmebrücken", "Keine Wärmebrücken gefunden.");
                return;
            }
            var dlg = new SaveFileDialog
            {
                Title = "Nachweisliste exportieren",
                FileName = "Waermebruecken_Nachweis",
                Filter = "Excel (*.xlsx)|*.xlsx|CSV (*.csv)|*.csv"
            };
            if (dlg.ShowDialog() != true) return;

            var export = new ExcelExportService(log, App.Instance.PsiLibrary.LoadedVersion);
            if (dlg.FileName.EndsWith(".csv", System.StringComparison.OrdinalIgnoreCase))
                export.ExportCsv(dlg.FileName, bridges);
            else
                export.ExportXlsx(dlg.FileName, bridges);
            TaskDialog.Show("Wärmebrücken", "Export abgeschlossen:\n" + dlg.FileName);
        }
    }
}
