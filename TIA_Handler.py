import sys
import os
import clr

# ⚠️ UPDATE THIS PATH to match your installed TIA Portal version
TIA_DLL_PATH = r"C:\Program Files\Siemens\Automation\Portal V17\PublicAPI\V17\Siemens.Engineering.dll"
clr.AddReference(TIA_DLL_PATH)

from System.IO import DirectoryInfo, FileInfo
import Siemens.Engineering as tia
import Siemens.Engineering.HW.Features as hwf
import Siemens.Engineering.Compiler as comp

class TiaHandler:
    """
    Handles TIA Portal lifecycle & direct import of AI-generated OB XML files.
    """
    def __init__(self):
        self._tia = None
        self._project = None

    # ── Project Management ─────────────────────────────────────────────
    def open_project(self, project_path: str):
        if self._tia is None:
            self._tia = tia.TiaPortal(tia.TiaPortalMode.WithUserInterface)
        self._project = self._tia.Projects.Open(FileInfo(project_path))
        print(f"Project opened: {project_path}")

    def save_project(self):
        self._require_project()
        self._project.Save()
        print("Project saved.")

    def close_project(self):
        if self._project:
            self._project.Close()
            self._project = None
            print("Project closed.")

    def dispose(self):
        if self._tia:
            self._tia.Dispose()
            self._tia = None
            print("TIA Portal instance disposed.")

    # ── AI Workflow: Direct OB Import ──────────────────────────────────
    def import_generated_ob(self, xml_path: str, project_path: str, with_ui: bool = True):
        """
        Opens a TIA project, imports a single generated OB XML, saves, and closes.
        Safe for one-shot AI generation workflows.
        """
        mode = tia.TiaPortalMode.WithUserInterface if with_ui else tia.TiaPortalMode.WithoutUserInterface
        local_tia = tia.TiaPortal(mode)
        try:
            print(f"Opening TIA project: {project_path}")
            project = local_tia.Projects.Open(FileInfo(project_path))
            plc = self._find_plc_software_in_project(project)

            print(f"Importing OB XML: {xml_path}")
            plc.BlockGroup.Import(FileInfo(xml_path), tia.ImportOptions.Override)

            print("Saving project...")
            project.Save()
            print("Import & Save complete.")
        finally:
            if project:
                project.Close()
            local_tia.Dispose()

    # ── Legacy Export/Import (Folder-based) ────────────────────────────
    def export_all(self, export_folder: str):
        self._require_project()
        plc = self._find_plc_software()
        os.makedirs(export_folder, exist_ok=True)
        self._export_block_group_recursive(plc.BlockGroup, os.path.join(export_folder, "Blocks"))
        self._export_tag_tables_recursive(plc.TagTableGroup, os.path.join(export_folder, "Tags"))
        print(f"Export complete → {export_folder}")

    def import_all(self, import_folder: str):
        self._require_project()
        plc = self._find_plc_software()
        tags_folder = os.path.join(import_folder, "Tags")
        if os.path.isdir(tags_folder):
            self._import_tag_tables_recursive(plc.TagTableGroup, tags_folder)
        blocks_folder = os.path.join(import_folder, "Blocks")
        if os.path.isdir(blocks_folder):
            self._import_block_group_recursive(plc.BlockGroup, blocks_folder)
        print(f"Import complete ← {import_folder}")

    # ── Helpers ────────────────────────────────────────────────────────
    def _find_plc_software(self):
        return self._find_plc_software_in_project(self._project)

    def _find_plc_software_in_project(self, project):
        for device in project.Devices:
            for device_item in device.DeviceItems:
                result = self._get_plc_from_device_item(device_item)
                if result is not None:
                    return result
        raise RuntimeError("No PLC software found in the project.")

    def _get_plc_from_device_item(self, device_item):
        sc = tia.IEngineeringServiceProvider(device_item).GetService[hwf.SoftwareContainer]()
        if sc is not None:
            from Siemens.Engineering.SW import PlcSoftware
            if isinstance(sc.Software, PlcSoftware):
                return sc.Software
        for child in device_item.DeviceItems:
            result = self._get_plc_from_device_item(child)
            if result is not None:
                return result
        return None

    def _export_block_group_recursive(self, group, folder: str):
        os.makedirs(folder, exist_ok=True)
        for block in group.Blocks:
            out = os.path.join(folder, block.Name + ".xml")
            block.Export(FileInfo(out), tia.ExportOptions.WithDefaults)
        for sub in group.Groups:
            self._export_block_group_recursive(sub, os.path.join(folder, sub.Name))

    def _export_tag_tables_recursive(self, group, folder: str):
        os.makedirs(folder, exist_ok=True)
        for table in group.TagTables:
            out = os.path.join(folder, table.Name + ".xml")
            table.Export(FileInfo(out), tia.ExportOptions.WithDefaults)
        for sub in group.Groups:
            self._export_tag_tables_recursive(sub, os.path.join(folder, sub.Name))

    def _import_block_group_recursive(self, group, folder: str):
        if not os.path.isdir(folder): return
        for filename in (f for f in os.listdir(folder) if f.endswith(".xml")):
            group.Blocks.Import(FileInfo(os.path.join(folder, filename)), tia.ImportOptions.Override)
        for dir_name in (d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d))):
            sub_group = self._find_or_create_block_group(group, dir_name)
            self._import_block_group_recursive(sub_group, os.path.join(folder, dir_name))

    def _import_tag_tables_recursive(self, group, folder: str):
        if not os.path.isdir(folder): return
        for filename in (f for f in os.listdir(folder) if f.endswith(".xml")):
            group.TagTables.Import(FileInfo(os.path.join(folder, filename)), tia.ImportOptions.Override)
        for dir_name in (d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d))):
            sub_group = self._find_or_create_tag_group(group, dir_name)
            self._import_tag_tables_recursive(sub_group, os.path.join(folder, dir_name))

    @staticmethod
    def _find_or_create_block_group(parent_group, name: str):
        for g in parent_group.Groups:
            if g.Name == name: return g
        return parent_group.Groups.Create(name)

    @staticmethod
    def _find_or_create_tag_group(parent_group, name: str):
        for g in parent_group.Groups:
            if g.Name == name: return g
        return parent_group.Groups.Create(name)

    def _require_project(self):
        if self._project is None:
            raise RuntimeError("No project is open. Call open_project() first.")

# ── Context manager support ─────────────────────────────────────────────
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_project()
        self.dispose()
        return False

# ── Example usage ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Quick test of direct import workflow
    handler = TiaHandler()
    handler.import_generated_ob(
        xml_path=r"C:\Path\To\OB1_generated.xml",
        project_path=r"C:\Path\To\Project.ap17",
        with_ui=True
    )