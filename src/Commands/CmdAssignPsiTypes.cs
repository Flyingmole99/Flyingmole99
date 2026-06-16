using System.Collections.Generic;
using System.Linq;
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
    [Transaction(TransactionMode.Manual)]
    public sealed class CmdAssignPsiTypes : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            Document doc = commandData.Application.ActiveUIDocument.Document;
            Logger log = App.Instance.Log;
            PsiLibraryService library = App.Instance.PsiLibrary;

            try
            {
                if (library.Entries.Count == 0 && !TryLoadLibrary(library))
                    return Result.Cancelled;

                var marker = new MarkerService(log);
                var repo = new ThermalBridgeRepository(marker, log);
                List<ThermalBridge> bridges = repo.CollectAll(doc);
                if (bridges.Count == 0)
                {
                    TaskDialog.Show("Wärmebrücken", "Keine Wärmebrücken im Modell gefunden.");
                    return Result.Cancelled;
                }

                var window = new AssignPsiTypeWindow(bridges, library.Entries);
                bool? ok = window.ShowDialog();
                if (ok != true || !window.ApplyRequested)
                    return Result.Cancelled;

                using (var tx = new Transaction(doc, "Psi-Typen zuordnen"))
                {
                    tx.Start();
                    int applied = 0;
                    foreach (ThermalBridge wb in window.SelectedBridges)
                    {
                        if (!library.Assign(wb, window.ChosenCode)) continue;
                        if (window.SetProven) wb.Status = Constants.Status.Geprueft;

                        Element e = doc.GetElement(wb.MarkerElementId);
                        if (e != null)
                        {
                            marker.WriteParameters(e, wb);
                            applied++;
                        }
                    }
                    tx.Commit();

                    TaskDialog.Show("Wärmebrücken",
                        $"Psi-Typ '{window.ChosenCode}' auf {applied} Wärmebrücke(n) angewendet." +
                        (window.SetProven ? "\nStatus auf 'geprüft' gesetzt." : ""));
                }
                return Result.Succeeded;
            }
            catch (System.Exception ex)
            {
                log.Error("Psi-Zuordnung fehlgeschlagen", ex);
                message = ex.Message;
                return Result.Failed;
            }
        }

        private static bool TryLoadLibrary(PsiLibraryService library)
        {
            var dlg = new OpenFileDialog
            {
                Title = "Psi-Bibliothek (CSV) laden",
                Filter = "CSV-Dateien (*.csv)|*.csv|Alle Dateien (*.*)|*.*"
            };
            if (dlg.ShowDialog() != true) return false;
            library.Load(dlg.FileName);
            return library.Entries.Count > 0;
        }
    }
}
