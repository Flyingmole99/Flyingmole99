using System.Windows;
using System.Windows.Controls;

namespace ThermalBridgeTool.UI
{
    public enum MainAction
    {
        None, Params, Detect, LoadLib, Assign, Validate, Export, Recreate, Close
    }

    /// <summary>
    /// Simple control panel. Each button selects an action and closes; the
    /// hosting command executes the action inside a valid Revit API context and
    /// re-opens the panel for the next step.
    /// </summary>
    public partial class MainWindow : Window
    {
        public MainAction SelectedAction { get; private set; } = MainAction.None;

        public MainWindow()
        {
            InitializeComponent();
        }

        private void Btn_Click(object sender, RoutedEventArgs e)
        {
            string tag = (sender as Button)?.Tag?.ToString() ?? "None";
            SelectedAction = System.Enum.TryParse(tag, out MainAction a) ? a : MainAction.None;
            DialogResult = SelectedAction != MainAction.Close;
            Close();
        }
    }
}
