using System;
using System.Collections.Generic;
using System.IO;
using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using ThermalBridgeTool.Common;

namespace ThermalBridgeTool.Services
{
    /// <summary>
    /// Creates the shared parameters and binds them to the relevant categories.
    ///
    /// Strategy:
    ///  * WB_* parameters bind to the Generic Models category (the marker host).
    ///  * SE_* parameters bind to Walls, Floors, Windows, Doors, Roofs.
    ///
    /// The shared parameter definition file is created on the fly in a temp
    /// location so the tool works even if the office has no central .txt file.
    /// If a central file is desired, point Application.SharedParametersFilename
    /// at it before calling EnsureParameters.
    /// </summary>
    public sealed class ParameterService
    {
        private readonly Logger _log;

        public ParameterService(Logger log)
        {
            _log = log;
        }

        private sealed class ParamDef
        {
            public string Name;
            public ForgeTypeId Spec;
            public string Group;
        }

        public void EnsureParameters(Document doc)
        {
            Application app = doc.Application;

            // Make sure a shared parameter file is available.
            DefinitionFile defFile = GetOrCreateSharedParameterFile(app);

            var wbParams = new List<ParamDef>
            {
                new ParamDef { Name = Constants.Wb.Id, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.Kategorie, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.Untertyp, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.PsiTyp, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.PsiWert, Spec = SpecTypeId.Number, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.Laenge, Spec = SpecTypeId.Length, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.Verlustkoeffizient, Spec = SpecTypeId.Number, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.Quelle, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.Status, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.Bauteil1Id, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.Bauteil2Id, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.Ebene, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.Aussenbezug, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupWb },
                new ParamDef { Name = Constants.Wb.Hinweis, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupWb },
            };

            var seParams = new List<ParamDef>
            {
                new ParamDef { Name = Constants.Se.ThermischeHuelle, Spec = SpecTypeId.Boolean.YesNo, Group = Constants.SharedParamGroupSe },
                new ParamDef { Name = Constants.Se.BauteilGegen, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupSe },
                new ParamDef { Name = Constants.Se.BauteiltypEnergie, Spec = SpecTypeId.String.Text, Group = Constants.SharedParamGroupSe },
            };

            var wbCats = new CategorySet();
            wbCats.Insert(GetCategory(doc, BuiltInCategory.OST_GenericModel));

            var seCats = new CategorySet();
            foreach (BuiltInCategory bic in new[]
            {
                BuiltInCategory.OST_Walls,
                BuiltInCategory.OST_Floors,
                BuiltInCategory.OST_Windows,
                BuiltInCategory.OST_Doors,
                BuiltInCategory.OST_Roofs
            })
            {
                Category c = GetCategory(doc, bic);
                if (c != null) seCats.Insert(c);
            }

            using (var tx = new Transaction(doc, "Wärmebrücken-Parameter anlegen"))
            {
                tx.Start();
                foreach (var p in wbParams)
                    BindParameter(doc, defFile, p, wbCats);
                foreach (var p in seParams)
                    BindParameter(doc, defFile, p, seCats);
                tx.Commit();
            }

            _log.Info("Parameter geprüft/angelegt: "
                      + (wbParams.Count + seParams.Count) + " Definitionen.");
        }

        private void BindParameter(Document doc, DefinitionFile defFile, ParamDef p, CategorySet cats)
        {
            // Already bound? Then nothing to do.
            if (IsBound(doc, p.Name))
                return;

            DefinitionGroup group = defFile.Groups.get_Item(p.Group)
                                    ?? defFile.Groups.Create(p.Group);

            Definition definition = group.Definitions.get_Item(p.Name);
            if (definition == null)
            {
                var opt = new ExternalDefinitionCreationOptions(p.Name, p.Spec);
                definition = group.Definitions.Create(opt);
            }

            // Instance binding: every marker / component carries its own value.
            InstanceBinding binding = doc.Application.Create.NewInstanceBinding(cats);

            // GroupTypeId.Data => parameter shows up under "Daten" in properties.
            bool ok = doc.ParameterBindings.Insert(definition, binding, GroupTypeId.Data);
            if (!ok)
            {
                // Insert returns false if it already exists for the category; try ReInsert.
                doc.ParameterBindings.ReInsert(definition, binding, GroupTypeId.Data);
            }
            _log.Info($"Parameter gebunden: {p.Name}");
        }

        private static bool IsBound(Document doc, string paramName)
        {
            BindingMap map = doc.ParameterBindings;
            DefinitionBindingMapIterator it = map.ForwardIterator();
            it.Reset();
            while (it.MoveNext())
            {
                if (it.Key != null && it.Key.Name == paramName)
                    return true;
            }
            return false;
        }

        private static Category GetCategory(Document doc, BuiltInCategory bic)
        {
            try { return Category.GetCategory(doc, bic); }
            catch { return null; }
        }

        private DefinitionFile GetOrCreateSharedParameterFile(Application app)
        {
            string current = app.SharedParametersFilename;
            if (!string.IsNullOrWhiteSpace(current) && File.Exists(current))
            {
                DefinitionFile f = app.OpenSharedParameterFile();
                if (f != null) return f;
            }

            // Create a private shared parameter file so we never depend on the
            // user having one configured.
            string path = Path.Combine(Path.GetTempPath(), "ThermalBridgeTool_SharedParams.txt");
            if (!File.Exists(path))
            {
                using (File.Create(path)) { }
            }
            app.SharedParametersFilename = path;
            DefinitionFile file = app.OpenSharedParameterFile();
            if (file == null)
                throw new InvalidOperationException(
                    "Shared-Parameter-Datei konnte nicht geöffnet werden: " + path);

            _log.Info("Shared-Parameter-Datei: " + path);
            return file;
        }
    }
}
