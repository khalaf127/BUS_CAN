# anemo_widget.py
from PyQt5 import QtWidgets, QtCore

class AnemoWidget(QtWidgets.QWidget):
    speedChanged = QtCore.pyqtSignal(int)  # emitted when slider changes

    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)

        # Title
        title = QtWidgets.QLabel("<h2>Anemometer Control</h2>")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        # Motor speed slider
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(255)
        self.slider.setValue(0)
        layout.addWidget(self.slider)

        self.value_label = QtWidgets.QLabel("Motor Speed: 0")
        self.value_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.value_label)

        # Current windmill speed display
        self.wind_speed_label = QtWidgets.QLabel("Windmill Speed: 0 RPM")
        self.wind_speed_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.wind_speed_label)

        # Connect slider to internal method
        self.slider.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self, value):
        """Called when slider value changes."""
        self.value_label.setText(f"Motor Speed: {value}")
        self.speedChanged.emit(value)  # This can be connected to motor control

    def update_wind_speed(self, rpm):
        """Call this to update the displayed windmill speed."""
        self.wind_speed_label.setText(f"Windmill Speed: {rpm} RPM")
