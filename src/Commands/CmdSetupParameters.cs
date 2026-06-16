using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using ThermalBridgeTool.Services;

namespace ThermalBridgeTool.Commands
{
    [Transaction(TransactionMode.Manual)]
    public sealed class CmdSetupParameters : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            Document doc = commandData.Application.ActiveUIDocument.Document;
            var log = App.Instance.Log;
            try
            {
                new ParameterService(log).EnsureParameters(doc);
                TaskDialog.Show("Wärmebrücken",
                    "Shared-Parameter wurden geprüft/angelegt:\n\n" +
                    "WB_* an Generische Modelle (Marker)\n" +
                    "SE_* an Wände, Decken, Fenster, Türen, Dächer.");
                return Result.Succeeded;
            }
            catch (System.Exception ex)
            {
                log.Error("Parameter-Setup fehlgeschlagen", ex);
                message = ex.Message;
                return Result.Failed;
            }
        }
    }
}
