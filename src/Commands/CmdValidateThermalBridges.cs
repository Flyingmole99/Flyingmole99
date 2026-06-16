using System.Collections.Generic;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;
using ThermalBridgeTool.Services;
using ThermalBridgeTool.UI;

namespace ThermalBridgeTool.Commands
{
    [Transaction(TransactionMode.ReadOnly)]
    public sealed class CmdValidateThermalBridges : IExternalCommand
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
                    TaskDialog.Show("Wärmebrücken", "Keine Wärmebrücken im Modell gefunden.");
                    return Result.Cancelled;
                }

                List<ValidationIssue> issues = new ValidationService().Validate(bridges);
                new ValidationResultWindow(issues).ShowDialog();
                return Result.Succeeded;
            }
            catch (System.Exception ex)
            {
                log.Error("Plausibilitätsprüfung fehlgeschlagen", ex);
                message = ex.Message;
                return Result.Failed;
            }
        }
    }
}
