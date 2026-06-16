using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using ThermalBridgeTool.Models;
using ThermalBridgeTool.Services;

namespace ThermalBridgeTool.Commands
{
    [Transaction(TransactionMode.Manual)]
    public sealed class CmdDetectThermalBridges : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            Document doc = commandData.Application.ActiveUIDocument.Document;
            var log = App.Instance.Log;

            try
            {
                var options = new DetectionOptions();

                var td = new TaskDialog("Wärmebrücken automatisch erkennen")
                {
                    MainInstruction = "Erkennung starten?",
                    MainContent = "Erkannt werden: Fenster-, Tür-/Terrassentür-, Sockel- und " +
                                  "Geschossdeckenanschlüsse der thermischen Hülle.",
                    CommonButtons = TaskDialogCommonButtons.None,
                    AllowCancellation = true
                };
                td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1,
                    "Ergänzend erkennen", "Vorhandene Marker behalten, nur neue ergänzen.");
                td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2,
                    "Neu aufbauen", "Vorhandene automatisch erkannte Marker löschen und neu erzeugen.");

                TaskDialogResult r = td.Show();
                if (r == TaskDialogResult.Cancel) return Result.Cancelled;
                options.DeleteExistingAutoBeforeRun = (r == TaskDialogResult.CommandLink2);

                var service = BuildService(log);
                DetectionResult result = service.Run(doc, options);

                TaskDialog.Show("Wärmebrücken",
                    $"Erkennung abgeschlossen.\n\n" +
                    $"Neu erstellt: {result.Created}\n" +
                    $"Bereits vorhanden: {result.AlreadyPresent}\n" +
                    $"Übersprungen: {result.Skipped}\n\n" +
                    "Status der neuen Objekte: 'automatisch erkannt' bzw. 'unklar'.\n" +
                    "Bitte Psi-Typen zuordnen und Status auf 'geprüft' setzen.");
                return Result.Succeeded;
            }
            catch (System.Exception ex)
            {
                log.Error("Erkennung fehlgeschlagen", ex);
                message = ex.Message;
                return Result.Failed;
            }
        }

        internal static ThermalBridgeDetectionService BuildService(Common.Logger log)
        {
            var marker = new MarkerService(log);
            var repo = new ThermalBridgeRepository(marker, log);
            var dup = new DuplicateCheckService(log);
            return new ThermalBridgeDetectionService(log, marker, repo, dup);
        }
    }
}
