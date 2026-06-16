using System.Collections.Generic;
using Autodesk.Revit.DB;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.Services
{
    /// <summary>
    /// Reads existing thermal-bridge markers from the model and deletes
    /// auto-detected ones on request. The repository is the only place that
    /// knows markers are DirectShapes in the Generic Models category.
    /// </summary>
    public sealed class ThermalBridgeRepository
    {
        private readonly MarkerService _markerService;
        private readonly Logger _log;

        public ThermalBridgeRepository(MarkerService markerService, Logger log)
        {
            _markerService = markerService;
            _log = log;
        }

        public List<ThermalBridge> CollectAll(Document doc)
        {
            var result = new List<ThermalBridge>();
            var collector = new FilteredElementCollector(doc)
                .OfClass(typeof(DirectShape))
                .OfCategory(BuiltInCategory.OST_GenericModel);

            foreach (Element e in collector)
            {
                ThermalBridge wb = _markerService.ReadBridge(e);
                if (wb != null)
                    result.Add(wb);
            }
            return result;
        }

        /// <summary>
        /// Deletes markers that are still auto-detected / unclear. Proven and
        /// rejected markers are preserved (they carry user decisions).
        /// Must be called inside an open transaction.
        /// </summary>
        public int DeleteAutoDetected(Document doc)
        {
            var toDelete = new List<ElementId>();
            foreach (ThermalBridge wb in CollectAll(doc))
            {
                if (wb.Status == Constants.Status.AutoErkannt ||
                    wb.Status == Constants.Status.Unklar)
                {
                    if (wb.MarkerElementId != null)
                        toDelete.Add(wb.MarkerElementId);
                }
            }

            foreach (ElementId id in toDelete)
                doc.Delete(id);

            _log.Info($"Automatisch erkannte Wärmebrücken gelöscht: {toDelete.Count}");
            return toDelete.Count;
        }
    }
}
