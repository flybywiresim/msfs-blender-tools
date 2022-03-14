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

from .msfs_primitive import MSFS_Primitive

class Import:
    def __init__(self):
        pass

    def gather_import_decode_primitive(self, gltf_mesh, gltf_primitive, import_settings):
        MSFS_Primitive.decode_primitive(import_settings, gltf_mesh, gltf_primitive)