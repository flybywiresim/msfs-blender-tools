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

from .msfs_primitive import MSFS_Primitive
from .msfs_texture import MSFS_Texture

def on_built_asset(func):
    def inner(*args, **kwargs):
        gltf = args[-1] # The Khronos importer always passes the glTF as the last argument
        if gltf.data.asset.extensions and "ASOBO_asset_optimized" in gltf.data.asset.extensions:
            return func(*args, **kwargs)
        else:
            pass

    return inner

class Import:
    def __init__(self):
        pass

    @on_built_asset
    def gather_import_scene_before_hook(self, gltf_scene, blender_scene, gltf):
        # Overwrite certain import settings
        gltf.import_settings['merge_vertices'] = True # Having this set to False gives us some shading issues
        gltf.import_settings['guess_original_bind_pose'] = False # Having this set to True causes lots of skinning issues
        gltf.import_settings['bone_heuristic'] = 'BLENDER' # Setting this to BLENDER yields the best results for reimporting back into the sim. From limited testing, this resolves wingflex and winglets being flipped
        MSFS_Texture.convert_textures(gltf)

    @on_built_asset
    def gather_import_decode_primitive(self, gltf_mesh, gltf_primitive, skin_idx, import_settings):
        MSFS_Primitive.decode_primitive(import_settings, gltf_mesh, gltf_primitive)

    @on_built_asset
    def gather_import_mesh_options(self, mesh_options, gltf_mesh, skin_idx, import_settings):
        mesh_options.skin_into_bind_pose = False # The MSFS build process already calculates bind pose on the vertex locations, so if we do it again it will cause many visual errors
        mesh_options.use_auto_smooth = False # For some reason using auto smooth on built files causes shading issues, so we disable it

    @on_built_asset
    def gather_import_image_after_hook(self, gltf_img, blender_image, import_settings):
        MSFS_Texture.rename_image(import_settings, gltf_img, blender_image)
        MSFS_Texture.convert_normal_map(import_settings, gltf_img, blender_image)

    @on_built_asset
    def gather_import_animations(self, gltf_animations, animation_options, import_settings):
        animation_options.restore_first_anim = False # We don't want to restore the first animation as it causes issues at export
