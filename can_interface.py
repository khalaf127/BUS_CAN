# can_interface.py
import can
import threading
import time

class CANInterface:
    def __init__(self, channel='can0'):
        """Initialize and open the CAN interface"""
        self.channel = channel
        self.bus = None
        self.callbacks = []
        self.running = False

        try:
            print(f"🔧 Opening CAN bus '{channel}' using socketcan …")
            # socketcan: the bitrate is configured in Linux, no need to pass it
            self.bus = can.interface.Bus(channel=channel, bustype='socketcan')
            print("✅ CAN interface opened successfully!")
        except Exception as e:
            print(f"❌ CAN init error: {e}")
            return

        # Start background receive thread
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def _read_loop(self):
        """Continuously read messages from CAN bus"""
        while self.running and self.bus:
            try:
                msg = self.bus.recv(timeout=0.1)
                if msg:
                    print(f"📩 Received frame: ID=0x{msg.arbitration_id:X}, Data={list(msg.data)}")
                    for cb in self.callbacks:
                        cb(msg)
            except can.CanError as e:
                print(f"⚠️ CAN read error: {e}")
                time.sleep(0.1)

    def send_message(self, can_id, data):
        """Send a CAN message with the given ID and data"""
        if not self.bus:
            print("❌ CAN bus not initialized!")
            return
        try:
            msg = can.Message(arbitration_id=can_id, data=bytearray(data), is_extended_id=False)
            self.bus.send(msg)
            print(f"✅ Sent CAN frame ID=0x{can_id:X}, Data={list(data)}")
        except can.CanError as e:
            print(f"❌ CAN send error: {e}")
        except Exception as e:
            print(f"❌ General CAN send error: {e}")

    def add_callback(self, callback):
        """Register a callback for received messages"""
        if callable(callback):
            self.callbacks.append(callback)

    def close(self):
        """Close CAN interface cleanly"""
        self.running = False
        if self.bus:
            try:
                self.bus.shutdown()
                print("🛑 CAN bus closed cleanly.")
            except Exception as e:
                print(f"⚠️ Error while closing CAN bus: {e}")
            self.bus = None
