using System.Collections.Generic;
using System.Linq;
using System.Windows;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.UI
{
    public partial class ValidationResultWindow : Window
    {
        public ValidationResultWindow(IReadOnlyList<ValidationIssue> issues)
        {
            InitializeComponent();
            GridIssues.ItemsSource = issues
                .OrderByDescending(i => i.Severity)
                .ToList();

            int errors = issues.Count(i => i.Severity == IssueSeverity.Error);
            int warnings = issues.Count(i => i.Severity == IssueSeverity.Warning);
            int infos = issues.Count(i => i.Severity == IssueSeverity.Info);
            TxtSummary.Text = $"{errors} Fehler, {warnings} Warnungen, {infos} Hinweise.";
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
