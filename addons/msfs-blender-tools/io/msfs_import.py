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

class Import:
    def __init__(self):
        pass

    # TODO: add check if optimized mesh

    def gather_import_scene_before_hook(self, gltf_scene, blender_scene, gltf):
        # Overwrite certain import settings
        gltf.import_settings['merge_vertices'] = True # Having this set to False gives us some shading issues
        gltf.import_settings['guess_original_bind_pose'] = False # Having this set to True causes lots of skinning issues
        MSFS_Texture.convert_textures(gltf)

    def gather_import_scene_after_animation_hook(self, gltf_scene, blender_scene, import_settings):
        # Undo some things done during the standard Khronos import process
        for obj in bpy.data.objects:
            # Unmute all tracks
            if obj.animation_data and obj.animation_data.nla_tracks:
                for track in obj.animation_data.nla_tracks:
                    track.mute = False
        
            # Remove auto smooth
            if obj.type == "MESH":
                obj.data.use_auto_smooth = False

    def gather_import_decode_primitive(self, gltf_mesh, gltf_primitive, skin_idx, import_settings):
        MSFS_Primitive.decode_primitive(import_settings, gltf_mesh, gltf_primitive)

    def gather_import_mesh_options(self, mesh_options, gltf_mesh, skin_idx, import_settings):
        mesh_options.skin_into_bind_pose = False # The MSFS build process already calculates bind pose on the vertex locations, so if we do it again it will cause many visual errors

    def gather_import_image_after_hook(self, gltf_img, blender_image, import_settings):
        MSFS_Texture.rename_image(import_settings, gltf_img, blender_image)
        MSFS_Texture.convert_normal_map(import_settings, gltf_img, blender_image)
