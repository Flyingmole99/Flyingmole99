using System.Collections.Generic;
using Autodesk.Revit.DB;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;
using ThermalBridgeTool.Services.Detectors;

namespace ThermalBridgeTool.Services
{
    public sealed class DetectionResult
    {
        public int Created;
        public int AlreadyPresent;
        public int Skipped;
        public List<ThermalBridge> CreatedBridges = new List<ThermalBridge>();
    }

    /// <summary>
    /// Orchestrates the whole auto-detection run: runs each detector, removes
    /// duplicates, optionally clears previous auto markers and writes the new
    /// markers. All model changes happen inside a single transaction.
    /// </summary>
    public sealed class ThermalBridgeDetectionService
    {
        private readonly Logger _log;
        private readonly MarkerService _markerService;
        private readonly ThermalBridgeRepository _repository;
        private readonly DuplicateCheckService _duplicates;

        public ThermalBridgeDetectionService(
            Logger log,
            MarkerService markerService,
            ThermalBridgeRepository repository,
            DuplicateCheckService duplicates)
        {
            _log = log;
            _markerService = markerService;
            _repository = repository;
            _duplicates = duplicates;
        }

        public DetectionResult Run(Document doc, DetectionOptions options)
        {
            var result = new DetectionResult();
            var envelope = new EnvelopeService(options);

            var detected = new List<ThermalBridge>();
            if (options.DetectWindows)
                detected.AddRange(new WindowBridgeDetector(envelope, _log).Detect(doc));
            if (options.DetectDoors)
                detected.AddRange(new DoorBridgeDetector(envelope, _log).Detect(doc));
            if (options.DetectPlinth)
                detected.AddRange(new PlinthBridgeDetector(envelope, _log).Detect(doc));
            if (options.DetectFloorSlabs)
                detected.AddRange(new FloorSlabBridgeDetector(envelope, _log).Detect(doc));

            using (var tx = new Transaction(doc, "Wärmebrücken automatisch erkennen"))
            {
                tx.Start();

                if (options.DeleteExistingAutoBeforeRun)
                    _repository.DeleteAutoDetected(doc);

                List<ThermalBridge> existing = _repository.CollectAll(doc);
                DuplicateResult split = _duplicates.Split(detected, existing);
                result.AlreadyPresent = split.AlreadyPresent.Count;

                foreach (ThermalBridge wb in split.New)
                {
                    ElementId id = _markerService.CreateMarker(doc, wb);
                    if (id != null)
                    {
                        result.Created++;
                        result.CreatedBridges.Add(wb);
                    }
                    else
                    {
                        result.Skipped++;
                    }
                }

                tx.Commit();
            }

            _log.Info($"Erkennung abgeschlossen: {result.Created} erstellt, " +
                      $"{result.AlreadyPresent} bereits vorhanden, {result.Skipped} übersprungen.");
            return result;
        }
    }
}
