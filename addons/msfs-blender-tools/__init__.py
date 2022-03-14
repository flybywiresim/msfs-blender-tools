# msfs-blender-tools
# Copyright (C) 2022 FlyByWire Simulations

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import bpy
import inspect
import pkgutil
import importlib
from pathlib import Path

from io_scene_gltf2.io.com.gltf2_io_extensions import Extension

bl_info = {
    "name": "Microsoft Flight Simulator Blender Tools",
    "author": "FlyByWire Simulations",
    "description": "Various Blender tools to assist in the development of assets in Microsoft Flight Simulator 2020",
    "blender": (3, 1, 0),
    "version": (0, 0, 1),
    "location": "File > Import-Export",
    "warning": "This addon is still in very early development, and is not recommended to be included in your development workflow",
    "category": "Import-Export",
    "tracker_url": "https://github.com/flybywiresim/msfs-blender-tools",
}


def get_version_string():
    return (
        str(bl_info["version"][0])
        + "."
        + str(bl_info["version"][1])
        + "."
        + str(bl_info["version"][2])
    )


class FBW_ImporterProperties(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name="MSFS Blender Tools",
        description="Enable MSFS Blender Tools import extensions",
        default=True,
    )


class GLTF_PT_FBWImporterExtensionPanel(bpy.types.Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = ""
    bl_parent_id = "GLTF_PT_import_user_extensions"
    bl_location = "File > Import > glTF 2.0"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "IMPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="MSFS Blender Tools", icon="TOOL_SETTINGS")

    def draw(self, context):
        props = bpy.context.scene.fbw_blender_tools_importer_properties

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.prop(props, "enabled", text="Enabled")


def recursive_module_search(path, root=""):
    for _, name, ispkg in pkgutil.iter_modules([str(path)]):
        if ispkg:
            yield from recursive_module_search(path / name, f"{root}.{name}")
        else:
            yield root, name


def modules():
    for root, name in recursive_module_search(Path(__file__).parent):
        if name in locals():
            yield importlib.reload(locals()[name])
        else:
            yield importlib.import_module(f".{name}", package=f"{__package__}{root}")


classes = []
extension_classes = [FBW_ImporterProperties]
extension_panels = [GLTF_PT_FBWImporterExtensionPanel]

# Refresh the list of classes
def update_class_list():
    global classes

    classes = []

    for module in modules():
        for obj in module.__dict__.values():
            if (
                inspect.isclass(obj)
                and module.__name__ in str(obj)
                and "bpy" in str(inspect.getmro(obj)[1])
            ):
                classes.append(obj)


def register():
    # Refresh the list of classes whenever the addon is reloaded so we can stay up to date with the files on disk.
    update_class_list()

    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass

    for module in modules():
        if hasattr(module, "register"):
            module.register()

    for cls in extension_classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass

    bpy.types.Scene.fbw_blender_tools_importer_properties = bpy.props.PointerProperty(
        type=FBW_ImporterProperties
    )


def register_panel():
    # Register the panel on demand, we need to be sure to only register it once
    # This is necessary because the panel is a child of the extensions panel,
    # which may not be registered when we try to register this extension
    for panel in extension_panels:
        try:
            bpy.utils.register_class(panel)
        except Exception:
            pass

    for module in modules():
        if hasattr(module, "register_panel"):
            module.register_panel()

    # If the glTF exporter is disabled, we need to unregister the extension panel
    # Just return a function to the exporter so it can unregister the panel
    return unregister_panel


def unregister():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass

    for module in modules():
        if hasattr(module, "unregister"):
            module.unregister()

    for cls in extension_classes:
        bpy.utils.unregister_class(cls)


def unregister_panel():
    for panel in extension_panels:
        try:
            bpy.utils.unregister_class(panel)
        except Exception:
            pass

    for module in modules():
        if hasattr(module, "unregister_panel"):
            module.unregister_panel()


from .io.msfs_import import Import


class glTF2ImportUserExtension(Import):
    def __init__(self):
        self.properties = bpy.context.scene.fbw_blender_tools_importer_properties
        self.extensions = [
            Extension(
                name="MSFT_texture_dds",
                extension={},
                required=True
            )
        ]
