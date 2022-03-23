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
import sys
import subprocess
import pkg_resources
from pathlib import Path

REQUIREMENTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "requirements.txt"
)

REQUIREMENTS = [
    req.key for req in pkg_resources.parse_requirements(Path(REQUIREMENTS_PATH).open())
]


class FBW_OT_install_requirements(bpy.types.Operator):
    bl_idname = "fbw.install_requirements"
    bl_label = "Install requirements"
    bl_description = (
        "Downloads and installs the required python packages for this add-on. You may need to restart Blender after this action. "
        "NOTE: Blender may need to be started with elevated permissions in order for packages to install properly"
    )
    bl_options = {"REGISTER", "INTERNAL"}

    @staticmethod
    def requirements_installed():
        for requirement in REQUIREMENTS:
            try:
                pkg_resources.get_distribution(requirement)
            except pkg_resources.DistributionNotFound:
                return False
        return True

    def execute(self, context):
        # First we need to ensure pip is installed
        subprocess.run(
            [
                sys.executable,
                "-m",
                "ensurepip",
            ],
            check=True,
        )
        # Then we're able to install our requirements
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                REQUIREMENTS_PATH,
            ],
            check=True,
        )
        return {"FINISHED"}
