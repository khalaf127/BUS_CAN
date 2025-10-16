# main_ihm.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedLayout, QLabel
)
from PyQt5.QtCore import QTimer
from can_interface import CANInterface
from mpu_widget import MPUWidget
from anemo_widget import AnemoWidget


class MainIHM(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sensor Dashboard")
        self.setGeometry(100, 100, 900, 700)

        # === CAN Interface ===
        self.can = CANInterface('can0')
        self.can.add_callback(self.handle_response)

        # === Layouts ===
        main_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        # Sensor buttons
        self.btn_mpu = QPushButton("MPU9250")
        self.btn_vl = QPushButton("VL6180X")
        self.btn_anemo = QPushButton("Anemometer")

        self.btn_mpu.clicked.connect(lambda: self.activate_sensor(0x02))
        self.btn_vl.clicked.connect(lambda: self.activate_sensor(0x01))
        self.btn_anemo.clicked.connect(lambda: self.activate_sensor(0x03))

        for b in (self.btn_mpu, self.btn_vl, self.btn_anemo):
            button_layout.addWidget(b)

        main_layout.addLayout(button_layout)

        # === Sensor Views ===
        self.view_stack = QStackedLayout()

        self.mpu_widget = MPUWidget()
        self.vl_widget = QLabel("VL6180X — (ignored for now)")
        self.anemo_widget = AnemoWidget()

        # Connect slider to CAN command
        self.anemo_widget.speedChanged.connect(self.send_motor_command)

        self.view_stack.addWidget(self.mpu_widget)
        self.view_stack.addWidget(self.vl_widget)
        self.view_stack.addWidget(self.anemo_widget)

        main_layout.addLayout(self.view_stack)
        self.setLayout(main_layout)

        # === CAN Polling Timer ===
        self.active_sensor_id = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.request_data)

    # ---------------------------------------------------------------
    # Sensor activation
    # ---------------------------------------------------------------
    def activate_sensor(self, sensor_id):
        print(f"🔵 activate_sensor called with ID=0x{sensor_id:X}")
        self.active_sensor_id = sensor_id
        self.timer.start(10)  # send every 10 ms
        print(f"✅ Timer started ({self.timer.interval()} ms)")

        if sensor_id == 0x02:
            self.view_stack.setCurrentWidget(self.mpu_widget)
        elif sensor_id == 0x01:
            self.view_stack.setCurrentWidget(self.vl_widget)
        elif sensor_id == 0x03:
            self.view_stack.setCurrentWidget(self.anemo_widget)

    # ---------------------------------------------------------------
    # Periodic CAN request
    # ---------------------------------------------------------------
    def request_data(self):
        if self.active_sensor_id:
            try:
                # If it's the VL6180X, send current motor speed
                if self.active_sensor_id == 0x01:
                    speed = self.anemo_widget.slider.value()
                    self.can.send_message(0x01, [speed])
                    print(f"⚡ Sent speed {speed} to sensor ID 0x01")
                
                elif self.active_sensor_id == 0x03:  # Anemometer
                    speed = self.anemo_widget.slider.value()
                    self.can.send_message(0x03, [speed])
                    print(f"⚡ Sent speed {speed} to sensor ID 0x03")
                else:
                    self.can.send_message(self.active_sensor_id, [1])
            except Exception as e:
                print(f"❌ Error sending CAN frame: {e}")

    # ---------------------------------------------------------------
    # Send slider value manually (optional, also used in request_data)
    # ---------------------------------------------------------------
    def send_motor_command(self, value):
        if self.active_sensor_id == 0x01:  # only send if sensor 0x01 is active
            try:
                self.can.send_message(0x01, [value])
                print(f"⚡ Slider moved: sent {value} to CAN ID 0x01")
            except Exception as e:
                print(f"❌ Failed to send motor command: {e}")

    # ---------------------------------------------------------------
    # Handle responses from STM
    # ---------------------------------------------------------------
    def handle_response(self, msg):
        print(f"📨 Received CAN frame: ID=0x{msg.arbitration_id:X}, Data={list(msg.data)}")

        if msg.arbitration_id == 0x08:  # MPU9250 reply
            self.mpu_widget.update_from_can(msg)
        
        elif msg.arbitration_id == 0x09:
            if len(msg.data) >= 1:
                rpm = msg.data[0]
                self.anemo_widget.update_wind_speed(rpm)
                print(f"🌬️ Windmill speed updated: {rpm} RPM")
            else:
                print("⚠️ Invalid data for wind speed frame")
    # ---------------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------------
    def closeEvent(self, e):
        self.can.close()
        e.accept()


# ================================================================
# Entry point
# ================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainIHM()
    win.show()
    sys.exit(app.exec_())
