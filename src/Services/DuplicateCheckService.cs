using System.Collections.Generic;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.Services
{
    public sealed class DuplicateResult
    {
        public List<ThermalBridge> New = new List<ThermalBridge>();
        public List<ThermalBridge> AlreadyPresent = new List<ThermalBridge>();
    }

    /// <summary>
    /// (E) Prevents duplicate bridge objects. Compares newly detected bridges
    /// against the ones already in the model using the duplicate signature
    /// (category, sub-type, component pair, rounded length, rounded midpoint).
    /// Existing bridges are never silently overwritten – they are reported as
    /// "bereits vorhanden".
    /// </summary>
    public sealed class DuplicateCheckService
    {
        private readonly Logger _log;

        public DuplicateCheckService(Logger log)
        {
            _log = log;
        }

        public DuplicateResult Split(
            IEnumerable<ThermalBridge> detected,
            IEnumerable<ThermalBridge> existing)
        {
            var result = new DuplicateResult();

            var existingKeys = new HashSet<string>();
            foreach (ThermalBridge e in existing)
            {
                existingKeys.Add(e.DuplicateSignature());
                existingKeys.Add(e.Id); // also dedupe by deterministic id
            }

            var seenThisRun = new HashSet<string>();

            foreach (ThermalBridge d in detected)
            {
                string sig = d.DuplicateSignature();
                if (existingKeys.Contains(sig) || existingKeys.Contains(d.Id) ||
                    seenThisRun.Contains(sig))
                {
                    d.Status = Constants.Status.BereitsVorhanden;
                    result.AlreadyPresent.Add(d);
                }
                else
                {
                    seenThisRun.Add(sig);
                    result.New.Add(d);
                }
            }

            _log.Info($"Dublettenprüfung: {result.New.Count} neu, " +
                      $"{result.AlreadyPresent.Count} bereits vorhanden.");
            return result;
        }
    }
}
