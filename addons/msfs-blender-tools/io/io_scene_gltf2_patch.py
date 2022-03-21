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

# We need to patch some of the functions in the built in glTF importer in order to get everything to work

import numpy as np
from mathutils import Matrix
from io_scene_gltf2.blender.imp import gltf2_blender_mesh
from io_scene_gltf2.io.imp.gltf2_io_binary import BinaryData

def skin_into_bind_pose(gltf, skin_idx, vert_joints, vert_weights, locs, vert_normals):
    # Skin each position/normal using the bind pose.
    # Skinning equation: vert' = sum_(j,w) w * joint_mat[j] * vert
    # where the sum is over all (joint,weight) pairs.

    if gltf.data.asset.extensions and gltf.data.asset.extensions.get("ASOBO_asset_optimized"): # PATCH - Asobo optimized assets already apply skinning trans to verts
        return

    # Calculate joint matrices
    joint_mats = []
    pyskin = gltf.data.skins[skin_idx]
    if pyskin.inverse_bind_matrices is not None:
        inv_binds = BinaryData.get_data_from_accessor(gltf, pyskin.inverse_bind_matrices)
        inv_binds = [gltf.matrix_gltf_to_blender(m) for m in inv_binds]
    else:
        inv_binds = [Matrix.Identity(4) for i in range(len(pyskin.joints))]
    bind_mats = [gltf.vnodes[joint].bind_arma_mat for joint in pyskin.joints]
    joint_mats = [bind_mat @ inv_bind for bind_mat, inv_bind in zip(bind_mats, inv_binds)]

    # TODO: check if joint_mats are all (approximately) 1, and skip skinning

    joint_mats = np.array(joint_mats, dtype=np.float32)

    # Compute the skinning matrices for every vert
    num_verts = len(locs[0])
    skinning_mats = np.zeros((num_verts, 4, 4), dtype=np.float32)
    weight_sums = np.zeros(num_verts, dtype=np.float32)
    for js, ws in zip(vert_joints, vert_weights):
        for i in range(4):
            skinning_mats += ws[:, i].reshape(len(ws), 1, 1) * joint_mats[js[:, i]]
            weight_sums += ws[:, i]
    # Normalize weights to one; necessary for old files / quantized weights
    skinning_mats /= weight_sums.reshape(num_verts, 1, 1)

    skinning_mats_3x3 = skinning_mats[:, :3, :3]
    skinning_trans = skinning_mats[:, :3, 3]

    for vs in locs:
        vs[:] = gltf2_blender_mesh.mul_mats_vecs(skinning_mats_3x3, vs)
        vs[:] += skinning_trans

    if len(vert_normals) != 0:
        vert_normals[:] = gltf2_blender_mesh.mul_mats_vecs(skinning_mats_3x3, vert_normals)
        # Don't translate normals!
        gltf2_blender_mesh.normalize_vecs(vert_normals)

gltf2_blender_mesh.skin_into_bind_pose = skin_into_bind_pose