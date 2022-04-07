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

import numpy as np
from io_scene_gltf2.io.com.gltf2_io import Accessor, BufferView
from io_scene_gltf2.io.com.gltf2_io_constants import ComponentType
from io_scene_gltf2.io.imp.gltf2_io_binary import BinaryData

from .msfs_binary import MSFS_Binary


# TODO: RuntimeWarning: invalid value encountered in true_divide RuntimeWarning: invalid value encountered in multiply large_result = 1.055 * np.power(color, 1.0 / 2.4, where=not_small) - 0.055


class MSFS_Primitive:

    SerializedName = "ASOBO_primitive"

    @staticmethod
    def copy_accessor(accessor):
        return Accessor(
            buffer_view=accessor.buffer_view,
            byte_offset=accessor.byte_offset,
            component_type=accessor.component_type,
            count=accessor.count,
            extensions=accessor.extensions,
            extras=accessor.extras,
            max=accessor.max,
            min=accessor.min,
            name=accessor.name,
            normalized=accessor.normalized,
            sparse=accessor.sparse,
            type=accessor.type,
        )

    @staticmethod
    def decode_primitive(gltf, gltf_mesh, gltf_prim):
        if (
            gltf_prim.extras is not None
            and MSFS_Primitive.SerializedName in gltf_prim.extras
        ):
            if gltf_prim.indices is None:
                return

            print(
                f"INFO | MSFS Decoder: Decoding primitive {gltf_mesh.primitives.index(gltf_prim)} for mesh {gltf_mesh.name}"
            )

            extension = gltf_prim.extras[MSFS_Primitive.SerializedName]

            indices = MSFS_Binary.decode_accessor(gltf, gltf_prim.indices)
            indices = indices.reshape(len(indices))

            base_vertex_index = 0
            primitive_count = 0
            start_index = 0

            # While it would be more efficient to do `extension.get(PROPERTY, 0)`, unfortunately there are cases where the key is present but with a null value
            if extension.get("BaseVertexIndex"):
                base_vertex_index = extension.get("BaseVertexIndex")
            if extension.get("PrimitiveCount"):
                primitive_count = extension.get("PrimitiveCount")
            if extension.get("StartIndex"):
                start_index = extension.get("StartIndex")

            new_indices = np.array(
                [
                    x + base_vertex_index
                    for x in indices[
                        start_index : (start_index + (primitive_count * 3))
                    ]
                ]
            )

            # We have to flip face vertex order. For example: a face with indices [1, 2, 3] will become [3, 2, 1]. We need to do this to ensure the normals are facing the correct way
            # First, Group indices into faces (groups of 3)
            new_indices = new_indices.reshape(-1, 3)
            # Flip faces
            new_indices = new_indices[:, ::-1]
            # Flatten
            new_indices = new_indices.flatten()

            # Set correct data type
            max_index = new_indices.max()
            if max_index < 65535:
                component_type = ComponentType.UnsignedShort
                new_indices = new_indices.astype(np.uint16, copy=False)
            elif max_index < 4294967295:
                component_type = ComponentType.UnsignedInt
                new_indices = new_indices.astype(np.uint32, copy=False)
            else:
                raise RuntimeError(
                    f"Mesh {gltf_mesh.name} contains too many vertices"
                )  # Not sure if this will ever happen, but check just in case

            # Choose a buffer index which does not yet exist, skipping over existing glTF buffers yet to be loaded
            # and buffers which were generated and did not exist in the initial glTF file.
            base_buffer_idx = len(gltf.data.buffers)
            for existing_buffer_idx in gltf.buffers:
                if base_buffer_idx <= existing_buffer_idx:
                    base_buffer_idx = existing_buffer_idx + 1

            # Generate new buffer holding the new indices
            gltf.buffers[base_buffer_idx] = new_indices.tobytes()

            # Create a buffer view referencing the new buffer
            gltf.data.buffer_views.append(
                BufferView.from_dict(
                    {
                        "buffer": base_buffer_idx,
                        "byteLength": len(new_indices.tobytes()),
                    }
                )
            )

            # Create new accessor with the decoded data
            new_accessor = MSFS_Primitive.copy_accessor(
                gltf.data.accessors[gltf_prim.indices]
            )
            new_accessor.buffer_view = len(gltf.data.buffer_views) - 1
            new_accessor.component_type = component_type
            new_accessor.count = len(new_indices)
            new_accessor.byte_offset = 0

            # Set the new accessor
            gltf.data.accessors.append(new_accessor)
            gltf_prim.indices = len(gltf.data.accessors) - 1

            # Read each attribute
            for attr_idx, (attr, accessor_idx) in enumerate(
                gltf_prim.attributes.items()
            ):
                accessor = gltf.data.accessors[accessor_idx]

                # Create a new accessor with the decoded data
                new_accessor = MSFS_Primitive.copy_accessor(accessor)

                data = MSFS_Binary.decode_accessor(gltf, gltf_prim.attributes[attr])

                # Handle certain attributes
                # TODO: color, tangent, texcoord, normal?
                if attr == "NORMAL":
                    # For some reason the normal attribute has a 4th value - we only need three. TODO: figure out what to do with last normal value
                    data = data[:, :-1]
                    # Since we flipped indices order, flip normals
                    data = np.negative(data)
                    new_accessor.type = "VEC3"
                elif attr.startswith("COLOR_"):
                    data = np.zeros(data.shape) # Disregard all previous values - MSFS always sets these values to 15360
                    data.fill(15360)
                    new_accessor.component_type = ComponentType.UnsignedShort
                elif attr.startswith("TEXCOORD_"):
                    new_accessor.component_type = ComponentType.Float
                elif attr.startswith("JOINTS_"):
                    # Joint data needs to have 4 values - BLEND1 primitives only have 1
                    if extension.get("VertexType") == "BLEND1":
                        data = np.pad(data, (0, 4 - data.shape[1]))
                    new_accessor.type = "VEC4"
                elif attr.startswith("WEIGHTS_"):
                    # Weight data needs to have 4 values - BLEND1 primitives only have 1
                    if extension.get("VertexType") == "BLEND1":
                        data = np.pad(data, (0, 4 - data.shape[1]))
                    new_accessor.type = "VEC4"
                    new_accessor.normalized = None
                    new_accessor.component_type = ComponentType.Float

                data = data.astype(ComponentType.to_numpy_dtype(new_accessor.component_type)).tobytes()

                # Generate new buffer holding the new attribute
                buffer_idx = base_buffer_idx + 1 + attr_idx
                gltf.buffers[buffer_idx] = data

                # Create a buffer view referencing the new buffer
                gltf.data.buffer_views.append(
                    BufferView.from_dict(
                        {"buffer": buffer_idx, "byteLength": len(data)}
                    )
                )

                new_accessor.buffer_view = len(gltf.data.buffer_views) - 1
                new_accessor.byte_offset = 0

                # Set the new accessor
                gltf.data.accessors.append(new_accessor)
                gltf_prim.attributes[attr] = len(gltf.data.accessors) - 1
