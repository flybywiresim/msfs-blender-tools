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

import os
import bpy
import json
import base64
import numpy as np
import configparser
from io import BytesIO

from io_scene_gltf2.io.com import gltf2_io_debug

# TODO: maybe convert before material import runs in order to get texture values to set properly, normals issue, other material import issues, list indices must be integers or slices, not NoneType

class MSFS_Texture:

    SerializedName = "MSFT_texture_dds"

    @staticmethod
    def rename_image(gltf, gltf_img, blender_image):
        if hasattr(gltf, "packed_image_names") and gltf_img in gltf.packed_image_names:
            blender_image.name = gltf.packed_image_names[gltf_img]
            gltf_img.blender_image_name = blender_image.name

    @staticmethod
    def convert_normal_map(gltf, gltf_img, blender_image):
        if (
            hasattr(gltf, "normals_needing_conversion")
            and gltf_img in gltf.normals_needing_conversion
        ):
            # Asobo normal maps have no z (blue) channel, so we have to calculate one, as well as flip the y (green) channel
            width = blender_image.size[0]
            height = blender_image.size[1]
            pixels = np.empty(width * height * 4, dtype=np.float32)
            blender_image.pixels.foreach_get(pixels)
            pixels = pixels.reshape((-1, 4))
            rgb_pixels = pixels[:, 0:3]
            rgb_pixels[:, 1] = 1.0 - rgb_pixels[:, 1]
            rgb_pixels[:, 2] = np.sqrt(
                1 - (rgb_pixels[:, 0] - 0.5) ** 2 - (rgb_pixels[:, 1] - 0.5) ** 2
            )
            pixel_data = pixels.reshape((-1, 1)).transpose()[0]
            blender_image.pixels.foreach_set(pixel_data)
            blender_image.update()

    @staticmethod
    def convert_textures(gltf):
        """
        Convert all textures from DDS to PNG before scene creation.
        Use PIL to open the DDS image, and embed the image data into the glTF file. That way we don't need to write anything to disk (slow)
        """
        from PIL import Image

        for gltf_texture in gltf.data.textures:
            if (
                gltf_texture.extensions is not None
                and MSFS_Texture.SerializedName in gltf_texture.extensions
            ):
                addon_settings = bpy.context.preferences.addons[
                    os.path.splitext(__package__)[0]
                ].preferences

                source = gltf.data.images[
                    gltf_texture.extensions[MSFS_Texture.SerializedName].get("source") # TODO: cases where referencing image already converted
                ]

                if source.uri.startswith("data:application/octet-stream;base64,"):
                    gltf2_io_debug.print_console("INFO", f"Texture already converted, skipping")
                    gltf_texture.extensions = None
                    gltf_texture.source = gltf.data.images.index(source)
                    continue

                gltf2_io_debug.print_console("INFO", f"Converting texture {source.uri}")

                # Assume we are in a proper structured project
                textures_folder = os.path.join(
                    os.path.dirname(os.path.dirname(gltf.import_settings["filepath"])),
                    "TEXTURE",
                )

                texture_path = os.path.join(textures_folder, source.uri)
                if os.path.exists(texture_path):
                    pass
                else:
                    # Use fallbacks in the texture.cfg
                    texture_config_path = os.path.join(textures_folder, "texture.cfg")
                    if not os.path.exists(texture_config_path):
                        gltf2_io_debug.print_console("WARNING", f"Texture {source.uri} failed to convert")
                        continue

                    parser = configparser.ConfigParser()
                    parser.read(texture_config_path)

                    if "fltsim" not in parser:
                        gltf2_io_debug.print_console("WARNING", f"Texture {source.uri} failed to convert")
                        continue

                    fltsim = parser["fltsim"]
                    for fallback in list(fltsim):
                        fallback_path = os.path.join(
                            addon_settings.fs_base_dir or "",
                            fltsim[fallback].split(".")[-1],
                        )

                        if not os.path.exists(fallback_path):
                            gltf2_io_debug.print_console("WARNING", f"Texture {source.uri} failed to convert")
                            continue

                        fallback_texture_path = os.path.join(fallback_path, source.uri)
                        if os.path.exists(fallback_texture_path):
                            texture_path = fallback_texture_path
                            break

                    if not os.path.exists(texture_path):
                        gltf2_io_debug.print_console("WARNING", f"Texture {source.uri} failed to convert")
                        continue

                # Now we read the texture
                image = Image.open(texture_path)

                # Check JSON
                image_json = texture_path + ".json"
                if os.path.exists(image_json):
                    with open(image_json, "r") as f:
                        data = json.loads(f.read())

                    if "FL_BITMAP_TANGENT_DXT5N" in data.get("Flags", []):
                        # During the build process, many changes are applied to the normal maps. We want to undo that
                        if not hasattr(gltf, "normals_needing_conversion"):
                            gltf.normals_needing_conversion = []
                        gltf.normals_needing_conversion.append(source)

                # Create buffer view
                buffer = BytesIO()
                image.save(buffer, format="PNG") # TODO: this performance is so awful

                data = "data:application/octet-stream;base64," + base64.b64encode(
                    buffer.getvalue()
                ).decode("ascii")

                # The Khronos importer sets packed image names with placeholder values. We want to make sure we respect the original names
                if not hasattr(gltf, "packed_image_names"):
                    gltf.packed_image_names = {}
                gltf.packed_image_names[source] = source.uri.split('.')[0] # Remove extensions from filename

                source.uri = data
                gltf_texture.extensions = None
                gltf_texture.source = gltf.data.images.index(source)
