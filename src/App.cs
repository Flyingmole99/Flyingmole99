using System;
using System.Reflection;
using Autodesk.Revit.UI;
using ThermalBridgeTool.Common;
using ThermalBridgeTool.Services;

namespace ThermalBridgeTool
{
    /// <summary>
    /// Add-in entry point. Builds the ribbon and holds the per-session services
    /// (logger and loaded Psi library) that several commands share.
    /// </summary>
    public sealed class App : IExternalApplication
    {
        public static App Instance { get; private set; }

        public Logger Log { get; } = new Logger();
        public PsiLibraryService PsiLibrary { get; private set; }

        public App()
        {
            PsiLibrary = new PsiLibraryService(Log);
        }

        public Result OnStartup(UIControlledApplication application)
        {
            Instance = this;
            string asm = Assembly.GetExecutingAssembly().Location;
            const string cls = "ThermalBridgeTool.Commands.";

            RibbonPanel panel;
            try
            {
                application.CreateRibbonTab("Wärmebrücken");
                panel = application.CreateRibbonPanel("Wärmebrücken", "Wärmebrücken-Nachweis");
            }
            catch
            {
                // Tab may already exist (e.g. re-load); reuse a panel on Add-Ins tab.
                panel = application.CreateRibbonPanel("Wärmebrücken-Nachweis");
            }

            AddButton(panel, asm, cls + "CmdShowMainWindow", "Steuerung", "Hauptfenster öffnen");
            panel.AddSeparator();
            AddButton(panel, asm, cls + "CmdSetupParameters", "Parameter\nprüfen", "Shared-Parameter anlegen/prüfen");
            AddButton(panel, asm, cls + "CmdDetectThermalBridges", "Auto-\nerkennen", "Wärmebrücken automatisch erkennen");
            AddButton(panel, asm, cls + "CmdAssignPsiTypes", "Psi-Typen\nzuordnen", "Psi-Typen aus Bibliothek zuordnen");
            AddButton(panel, asm, cls + "CmdValidateThermalBridges", "Prüfen", "Plausibilitätsprüfung");
            AddButton(panel, asm, cls + "CmdExportThermalBridges", "Export\nExcel/CSV", "Nachweisliste exportieren");

            Log.Info("Thermal Bridge Tool gestartet.");
            return Result.Succeeded;
        }

        public Result OnShutdown(UIControlledApplication application)
        {
            return Result.Succeeded;
        }

        private static void AddButton(RibbonPanel panel, string asm, string className,
            string text, string tooltip)
        {
            var data = new PushButtonData(className.Replace(".", "_"), text, asm, className)
            {
                ToolTip = tooltip
            };
            panel.AddItem(data);
        }
    }
}
