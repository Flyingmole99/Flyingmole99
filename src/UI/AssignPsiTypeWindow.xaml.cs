using System.Collections.Generic;
using System.Linq;
using System.Windows;
using ThermalBridgeTool.Models;

namespace ThermalBridgeTool.UI
{
    /// <summary>
    /// Lets the user pick a Psi_Typ_Code for the selected bridges. The window
    /// only collects the user's choices; the calling command performs all model
    /// changes inside a Revit transaction.
    /// </summary>
    public partial class AssignPsiTypeWindow : Window
    {
        private readonly List<ThermalBridge> _bridges;

        public string ChosenCode { get; private set; }
        public bool SetProven { get; private set; }
        public List<ThermalBridge> SelectedBridges { get; private set; } = new List<ThermalBridge>();
        public bool ApplyRequested { get; private set; }

        public AssignPsiTypeWindow(List<ThermalBridge> bridges, IEnumerable<PsiLibraryEntry> library)
        {
            InitializeComponent();
            _bridges = bridges;
            GridBridges.ItemsSource = _bridges;
            CmbPsi.ItemsSource = library.ToList();
            CmbPsi.DisplayMemberPath = "";
            if (CmbPsi.Items.Count > 0) CmbPsi.SelectedIndex = 0;
        }

        private void BtnApply_Click(object sender, RoutedEventArgs e)
        {
            if (!(CmbPsi.SelectedItem is PsiLibraryEntry entry))
            {
                MessageBox.Show("Bitte einen Psi-Typ wählen.");
                return;
            }
            var selected = GridBridges.SelectedItems.Cast<ThermalBridge>().ToList();
            if (selected.Count == 0)
            {
                MessageBox.Show("Bitte mindestens eine Wärmebrücke in der Liste auswählen.");
                return;
            }

            ChosenCode = entry.PsiTypCode;
            SetProven = ChkProven.IsChecked == true;
            SelectedBridges = selected;
            ApplyRequested = true;
            DialogResult = true;
            Close();
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
    }
}
