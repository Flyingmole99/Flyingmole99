using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace ThermalBridgeTool.Common
{
    public enum LogLevel { Info, Warning, Error }

    /// <summary>
    /// Lightweight in-memory + file logger. Each command run gets a fresh
    /// session log that can also be shown to the user. Intentionally free of
    /// Revit dependencies so it stays unit-testable.
    /// </summary>
    public sealed class Logger
    {
        private readonly List<string> _lines = new List<string>();
        private readonly object _gate = new object();

        public IReadOnlyList<string> Lines
        {
            get { lock (_gate) { return _lines.ToArray(); } }
        }

        public void Info(string message) => Add(LogLevel.Info, message);
        public void Warning(string message) => Add(LogLevel.Warning, message);
        public void Error(string message) => Add(LogLevel.Error, message);

        public void Error(string message, Exception ex)
            => Add(LogLevel.Error, message + " :: " + ex.Message);

        private void Add(LogLevel level, string message)
        {
            string line = $"{DateTime.Now:HH:mm:ss} [{level}] {message}";
            lock (_gate) { _lines.Add(line); }
        }

        public string Dump()
        {
            lock (_gate) { return string.Join(Environment.NewLine, _lines); }
        }

        /// <summary>Persist the log next to a given file (best effort).</summary>
        public void WriteToFile(string path)
        {
            try
            {
                File.WriteAllText(path, Dump(), Encoding.UTF8);
            }
            catch
            {
                // Logging must never throw into the Revit transaction.
            }
        }
    }
}
