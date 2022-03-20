# msfs-blender-tools, glTF-Blender-IO
# Copyright (C) 2022 FlyByWire Simulations, The glTF-Blender-IO authors

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
from io_scene_gltf2.io.com.gltf2_io import Accessor
from io_scene_gltf2.io.imp.gltf2_io_binary import BinaryData
from io_scene_gltf2.io.com.gltf2_io_constants import ComponentType, DataType

class MSFS_Binary:

    @staticmethod
    def to_numpy_dtype(component_type):
        return {
            ComponentType.Byte: np.int8,
            ComponentType.UnsignedByte: np.uint8,
            ComponentType.Short: np.float16,  # Asobo uses a float16 for shorts instead of int16
            ComponentType.UnsignedShort: np.uint16,
            ComponentType.UnsignedInt: np.uint32,
            ComponentType.Float: np.float32,
        }[component_type]

    @staticmethod
    def decode_accessor(gltf, accessor_idx, cache=False):
        """Decodes accessor to 2D numpy array (count x num_components)."""
        if accessor_idx in gltf.decode_accessor_cache:
            return gltf.accessor_cache[accessor_idx]

        accessor = gltf.data.accessors[accessor_idx]
        array = MSFS_Binary.decode_accessor_obj(gltf, accessor)

        if cache:
            gltf.accessor_cache[accessor_idx] = array
            # Prevent accidentally modifying cached arrays
            array.flags.writeable = False

        return array

    @staticmethod
    def decode_accessor_obj(gltf, accessor):
        # MAT2/3 have special alignment requirements that aren't handled. But it
        # doesn't matter because nothing uses them.
        assert accessor.type not in ["MAT2", "MAT3"]

        dtype = MSFS_Binary.to_numpy_dtype(accessor.component_type)
        component_nb = DataType.num_elements(accessor.type)

        if accessor.buffer_view is not None:
            bufferView = gltf.data.buffer_views[accessor.buffer_view]
            buffer_data = BinaryData.get_buffer_view(gltf, accessor.buffer_view)

            accessor_offset = accessor.byte_offset or 0
            buffer_data = buffer_data[accessor_offset:]

            bytes_per_elem = dtype(1).nbytes
            default_stride = bytes_per_elem * component_nb
            stride = bufferView.byte_stride or default_stride

            if stride == default_stride:
                array = np.frombuffer(
                    buffer_data,
                    dtype=np.dtype(dtype).newbyteorder("<"),
                    count=accessor.count * component_nb,
                )
                array = array.reshape(accessor.count, component_nb)

            else:
                # The data looks like
                #   XXXppXXXppXXXppXXX
                # where X are the components and p are padding.
                # One XXXpp group is one stride's worth of data.
                assert stride % bytes_per_elem == 0
                elems_per_stride = stride // bytes_per_elem
                num_elems = (accessor.count - 1) * elems_per_stride + component_nb

                array = np.frombuffer(
                    buffer_data,
                    dtype=np.dtype(dtype).newbyteorder("<"),
                    count=num_elems,
                )
                assert array.strides[0] == bytes_per_elem
                array = np.lib.stride_tricks.as_strided(
                    array,
                    shape=(accessor.count, component_nb),
                    strides=(stride, bytes_per_elem),
                )

        else:
            # No buffer view; initialize to zeros
            array = np.zeros((accessor.count, component_nb), dtype=dtype)

        if accessor.sparse:
            sparse_indices_obj = Accessor.from_dict(
                {
                    "count": accessor.sparse.count,
                    "bufferView": accessor.sparse.indices.buffer_view,
                    "byteOffset": accessor.sparse.indices.byte_offset or 0,
                    "componentType": accessor.sparse.indices.component_type,
                    "type": "SCALAR",
                }
            )
            sparse_indices = MSFS_Binary.decode_accessor_obj(
                gltf, sparse_indices_obj
            )
            sparse_indices = sparse_indices.reshape(len(sparse_indices))

            sparse_values_obj = Accessor.from_dict(
                {
                    "count": accessor.sparse.count,
                    "bufferView": accessor.sparse.values.buffer_view,
                    "byteOffset": accessor.sparse.values.byte_offset or 0,
                    "componentType": accessor.component_type,
                    "type": accessor.type,
                }
            )
            sparse_values = MSFS_Binary.decode_accessor_obj(
                gltf, sparse_values_obj
            )

            if not array.flags.writeable:
                array = array.copy()
            array[sparse_indices] = sparse_values

        # Normalization
        if accessor.normalized:
            if accessor.component_type == 5120:  # int8
                array = np.maximum(-1.0, array / 127.0)
            elif accessor.component_type == 5121:  # uint8
                array = array / 255.0
            elif accessor.component_type == 5122:  # int16
                array = np.maximum(-1.0, array / 32767.0)
            elif accessor.component_type == 5123:  # uint16
                array = array / 65535.0

            array = array.astype(np.float32, copy=False)

        return array