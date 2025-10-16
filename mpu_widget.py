# mpu_widget.py
import numpy as np
import math
import pyqtgraph.opengl as gl
from PyQt5 import QtWidgets

class MPUWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        self.view = gl.GLViewWidget()
        layout.addWidget(self.view)
        self.view.setCameraPosition(distance=10, elevation=15, azimuth=45)

        # Add grid and axes
        self.add_axes()
        g = gl.GLGridItem()
        g.scale(2, 2, 1)
        g.setDepthValue(10)
        self.view.addItem(g)

        # Create cube
        self.meshdata = self.create_cube_mesh()
        self.cube = gl.GLMeshItem(
            meshdata=self.meshdata,
            smooth=False,
            drawEdges=True,
            edgeColor=(1, 1, 1, 1),
        )
        self.cube.setGLOptions('opaque')
        self.view.addItem(self.cube)

    # ----------------------------------------------------------------
    # Update with new CAN data (MPU angles)
    # ----------------------------------------------------------------
    def update_from_can(self, msg):
        if len(msg.data) < 6:
            return

        # Extract signed 16-bit values
        phi = int.from_bytes(msg.data[0:2], byteorder='big', signed=True)
        theta = int.from_bytes(msg.data[2:4], byteorder='big', signed=True)
        psi = int.from_bytes(msg.data[4:6], byteorder='big', signed=True)
        # Convert to degrees then radians
        roll = math.radians(phi )
        pitch = math.radians(theta )
        yaw = math.radians(psi )

        self.update_cube_rotation(roll, pitch, yaw)

    # ----------------------------------------------------------------
    # Rotation math (Z-Y-X)
    # ----------------------------------------------------------------
    def update_cube_rotation(self, roll, pitch, yaw):
        Rx = np.array([
            [1, 0, 0],
            [0, math.cos(roll), -math.sin(roll)],
            [0, math.sin(roll), math.cos(roll)]
        ])
        Ry = np.array([
            [math.cos(pitch), 0, math.sin(pitch)],
            [0, 1, 0],
            [-math.sin(pitch), 0, math.cos(pitch)]
        ])
        Rz = np.array([
            [math.cos(yaw), -math.sin(yaw), 0],
            [math.sin(yaw), math.cos(yaw), 0],
            [0, 0, 1]
        ])

        R = Rz @ Ry @ Rx  # Combined rotation

        # Apply to vertices
        verts = self.original_vertices
        rotated = np.dot(verts, R.T)
        self.meshdata.setVertexes(rotated)
        self.cube.meshDataChanged()

    # ----------------------------------------------------------------
    # Cube definition (simple colors)
    # ----------------------------------------------------------------
    def create_cube_mesh(self):
        verts = np.array([
            [-1, -1, -1],
            [-1, -1,  1],
            [-1,  1, -1],
            [-1,  1,  1],
            [ 1, -1, -1],
            [ 1, -1,  1],
            [ 1,  1, -1],
            [ 1,  1,  1],
        ])
        self.original_vertices = verts.copy()

        faces = np.array([
            [0, 1, 3], [0, 3, 2],   # left
            [4, 5, 7], [4, 7, 6],   # right
            [0, 1, 5], [0, 5, 4],   # bottom
            [2, 3, 7], [2, 7, 6],   # top
            [1, 3, 7], [1, 7, 5],   # front
            [0, 2, 6], [0, 6, 4],   # back
        ])

        # Simpler, visible colors
        colors = np.array([
            [1, 0, 0, 1],  # red
            [1, 0, 0, 1],
            [0, 1, 0, 1],  # green
            [0, 1, 0, 1],
            [0, 0, 1, 1],  # blue
            [0, 0, 1, 1],
            [1, 1, 0, 1],  # yellow
            [1, 1, 0, 1],
            [1, 0, 1, 1],  # magenta
            [1, 0, 1, 1],
            [0, 1, 1, 1],  # cyan
            [0, 1, 1, 1],
        ])

        return gl.MeshData(vertexes=verts, faces=faces, faceColors=colors)

    # ----------------------------------------------------------------
    # Axis helpers
    # ----------------------------------------------------------------
    def add_axes(self):
        axis_len = 2
        for axis, color in zip(
            [[axis_len,0,0],[0,axis_len,0],[0,0,axis_len]],
            [(1,0,0,1),(0,1,0,1),(0,0,1,1)]
        ):
            line = gl.GLLinePlotItem(
                pos=np.array([[0,0,0], axis]),
                color=color, width=3
            )
            self.view.addItem(line)
