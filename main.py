import sys
import numpy as np
import can

from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout,
    QStackedLayout, QHBoxLayout
)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QVector3D
import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtGui

class SensorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sensor Dashboard")
        self.setGeometry(100, 100, 800, 600)

        # === CAN Setup ===
        try:
            self.bus = can.interface.Bus('can0', bustype='socketcan')
        except Exception as e:
            print(f"CAN init error: {e}")
            self.bus = None

        self.active_sensor_id = None

        # === Main Layout ===
        main_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        # Buttons
        self.btn_mpu = QPushButton("MPU9250")
        self.btn_vl = QPushButton("VL6180X")
        self.btn_anemo = QPushButton("Anemometer")

        self.btn_mpu.clicked.connect(lambda: self.activate_sensor(0x02))
        self.btn_vl.clicked.connect(lambda: self.activate_sensor(0x01))
        self.btn_anemo.clicked.connect(lambda: self.activate_sensor(0x03))

        button_layout.addWidget(self.btn_mpu)
        button_layout.addWidget(self.btn_vl)
        button_layout.addWidget(self.btn_anemo)

        main_layout.addLayout(button_layout)

        # === View Stack (for sensor views) ===
        self.view_stack = QStackedLayout()

        # 1. MPU View with 3D Cube
        self.mpu_widget = gl.GLViewWidget()
        self.mpu_widget.opts['distance'] = 5
        self.mpu_widget.setCameraPosition(distance=10, elevation=10, azimuth=30)

        # Coordinate axes for orientation reference
        self.add_axes(self.mpu_widget)

        # Custom cube with colored faces
        self.mpu_cube = self.create_colored_cube(size=1.0)
        self.mpu_widget.addItem(self.mpu_cube)

        # 2. VL6180X View
        self.vl_widget = QLabel("VL6180X Data")
        self.vl_widget.setStyleSheet("font-size: 24px;")

        # 3. Anemometer View
        self.anemo_widget = QLabel("Anemometer Data")
        self.anemo_widget.setStyleSheet("font-size: 24px;")

        self.view_stack.addWidget(self.mpu_widget)
        self.view_stack.addWidget(self.vl_widget)
        self.view_stack.addWidget(self.anemo_widget)

        main_layout.addLayout(self.view_stack)
        self.setLayout(main_layout)

        # === Timer for CAN polling ===
        self.timer = QTimer()
        self.timer.timeout.connect(self.send_can_request)

    def activate_sensor(self, sensor_id):
        self.active_sensor_id = sensor_id
        self.timer.start(10)  # Poll every 10 ms

        if sensor_id == 0x02:
            self.view_stack.setCurrentWidget(self.mpu_widget)
        elif sensor_id == 0x01:
            self.view_stack.setCurrentWidget(self.vl_widget)
        elif sensor_id == 0x03:
            self.view_stack.setCurrentWidget(self.anemo_widget)

    def send_can_request(self):
        if self.bus is None or self.active_sensor_id is None:
            return

        try:
            msg = can.Message(arbitration_id=self.active_sensor_id, data=[], is_extended_id=False)
            self.bus.send(msg)

            response = self.bus.recv(timeout=0.01)
            if response:
                self.handle_response(response)
        except can.CanError as e:
            print(f"CAN error: {e}")
        except Exception as e:
            print(f"General error: {e}")

    def handle_response(self, msg):
        if msg.arbitration_id == 0x08 and len(msg.data) >= 6:  # MPU9250 response
            phi = int.from_bytes(msg.data[0:2], byteorder='big', signed=True)
            theta = int.from_bytes(msg.data[2:4], byteorder='big', signed=True)
            psi = int.from_bytes(msg.data[4:6], byteorder='big', signed=True)

            print(f"MPU9250 -> Roll: {phi/100:.2f}°, Pitch: {theta/100:.2f}°, Yaw: {psi/100:.2f}°")

            # Convert degrees * 100 to radians
            roll = np.radians(phi )
            pitch = np.radians(theta )
            yaw = np.radians(psi )

            self.update_cube_rotation(roll, pitch, yaw)

        elif msg.arbitration_id == 0x01:
            self.vl_widget.setText(f"VL6180X Data: {msg.data.hex()}")
        elif msg.arbitration_id == 0x03:
            self.anemo_widget.setText(f"Anemometer Data: {msg.data.hex()}")

    def update_cube_rotation(self, roll, pitch, yaw):
        # Rotation matrices
        R_x = np.array([
            [1, 0, 0],
            [0, np.cos(roll), -np.sin(roll)],
            [0, np.sin(roll), np.cos(roll)]
        ])
        R_y = np.array([
            [np.cos(pitch), 0, np.sin(pitch)],
            [0, 1, 0],
            [-np.sin(pitch), 0, np.cos(pitch)]
        ])
        R_z = np.array([
            [np.cos(yaw), -np.sin(yaw), 0],
            [np.sin(yaw), np.cos(yaw), 0],
            [0, 0, 1]
        ])

        R = R_z @ R_y @ R_x
        m = np.eye(4)
        m[:3, :3] = R

        mat = QtGui.QMatrix4x4(*m.flatten())
        self.mpu_cube.setTransform(mat)

    def add_axes(self, view_widget):
        # Add coordinate axes (RGB)
        axis_length = 2.0
        x_axis = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [axis_length, 0, 0]]), color=(1, 0, 0, 1), width=3)
        y_axis = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [0, axis_length, 0]]), color=(0, 1, 0, 1), width=3)
        z_axis = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [0, 0, axis_length]]), color=(0, 0, 1, 1), width=3)
        view_widget.addItem(x_axis)
        view_widget.addItem(y_axis)
        view_widget.addItem(z_axis)

    def create_colored_cube(self, size=1.0):
        # Cube with colored faces
        verts = np.array([
            [-1, -1, -1],
            [ 1, -1, -1],
            [ 1,  1, -1],
            [-1,  1, -1],
            [-1, -1,  1],
            [ 1, -1,  1],
            [ 1,  1,  1],
            [-1,  1,  1]
        ]) * (size / 2.0)

        faces = np.array([
            [0, 1, 2], [0, 2, 3],  # Bottom
            [4, 5, 6], [4, 6, 7],  # Top
            [0, 1, 5], [0, 5, 4],  # Front (red)
            [2, 3, 7], [2, 7, 6],  # Back (green)
            [1, 2, 6], [1, 6, 5],  # Right (blue)
            [3, 0, 4], [3, 4, 7],  # Left (yellow)
        ])

        colors = np.array([
            [1, 0, 0, 1],  # red
            [1, 0, 0, 1],  # red
            [0, 1, 0, 1],  # green
            [0, 1, 0, 1],  # green
            [0, 0, 1, 1],  # blue
            [0, 0, 1, 1],  # blue
            [1, 1, 0, 1],  # yellow
            [1, 1, 0, 1],  # yellow
            [1, 0, 1, 1],  # magenta
            [1, 0, 1, 1],  # magenta
            [0, 1, 1, 1],  # cyan
            [0, 1, 1, 1],  # cyan
        ])

        mesh = gl.GLMeshItem(vertexes=verts, faces=faces, faceColors=colors, smooth=False, drawEdges=True)
        return mesh

    def closeEvent(self, event):
        if self.bus:
            self.bus.shutdown()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = SensorGUI()
    gui.show()
    sys.exit(app.exec_())
