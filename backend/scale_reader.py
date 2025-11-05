"""USB Scale reader module for reading weight data from connected scales.

Supports various USB scale protocols and provides a unified interface.
"""
from __future__ import annotations

import re
import time
from typing import Optional, List, Dict
import serial
import serial.tools.list_ports


class ScaleReader:
    """USB Scale reader class for communicating with digital scales."""
    
    def __init__(self, port: Optional[str] = None, baudrate: int = 9600, timeout: float = 2.0):
        """Initialize scale reader.
        
        Args:
            port: Serial port name (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
                 If None, will attempt to auto-detect
            baudrate: Communication speed (common values: 9600, 19200, 115200)
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection: Optional[serial.Serial] = None
        self._last_weight = 0.0
        
    @staticmethod
    def list_available_ports() -> List[Dict[str, str]]:
        """List all available serial ports.
        
        Returns:
            List of dictionaries containing port information
        """
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid
            })
        return ports
    
    def connect(self, port: Optional[str] = None) -> bool:
        """Connect to the scale.
        
        Args:
            port: Serial port to connect to. If None, uses self.port or auto-detects
            
        Returns:
            True if connection successful, False otherwise
        """
        if port:
            self.port = port
            
        if not self.port:
            # Try to auto-detect scale
            available_ports = self.list_available_ports()
            if not available_ports:
                return False
            self.port = available_ports[0]['device']
        
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            time.sleep(0.5)  # Allow connection to stabilize
            return True
        except (serial.SerialException, OSError) as e:
            print(f"Failed to connect to scale on {self.port}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the scale."""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            self.serial_connection = None
    
    def read_weight(self) -> Optional[float]:
        """Read current weight from the scale.
        
        Returns:
            Weight in grams, or None if read failed
        """
        if not self.serial_connection or not self.serial_connection.is_open:
            return None
        
        try:
            # Clear input buffer
            self.serial_connection.reset_input_buffer()
            
            # Read data from scale
            raw_data = self.serial_connection.readline()
            
            if not raw_data:
                return self._last_weight
            
            # Decode the data
            data_str = raw_data.decode('ascii', errors='ignore').strip()
            
            # Parse weight from various common scale formats
            weight = self._parse_weight(data_str)
            
            if weight is not None:
                self._last_weight = weight
                
            return weight
            
        except (serial.SerialException, UnicodeDecodeError, ValueError) as e:
            print(f"Error reading from scale: {e}")
            return None
    
    def _parse_weight(self, data: str) -> Optional[float]:
        """Parse weight value from scale data string.
        
        Common formats:
        - "ST,GS,+00123.4g"
        - "123.4 g"
        - "0.1234 kg"
        - "+00123g"
        
        Args:
            data: Raw data string from scale
            
        Returns:
            Weight in grams, or None if parsing failed
        """
        if not data:
            return None
        
        # Pattern 1: Standard format with unit (e.g., "123.4 g", "0.123 kg")
        match = re.search(r'([+-]?\d+\.?\d*)\s*(g|kg|lb|oz)', data, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            
            # Convert to grams
            if unit == 'kg':
                value *= 1000
            elif unit == 'lb':
                value *= 453.592
            elif unit == 'oz':
                value *= 28.3495
            
            return value
        
        # Pattern 2: Format with status and unit (e.g., "ST,GS,+00123.4g")
        match = re.search(r'([+-]?\d+\.?\d*)\s*g', data, re.IGNORECASE)
        if match:
            return float(match.group(1))
        
        # Pattern 3: Just numbers (assume grams)
        match = re.search(r'([+-]?\d+\.?\d+)', data)
        if match:
            return float(match.group(1))
        
        return None
    
    def tare(self) -> bool:
        """Send tare command to the scale (zero the scale).
        
        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.serial_connection or not self.serial_connection.is_open:
            return False
        
        try:
            # Common tare commands - try multiple variations
            for cmd in [b'T\r\n', b'Z\r\n', b'TARE\r\n']:
                self.serial_connection.write(cmd)
                time.sleep(0.2)
            return True
        except serial.SerialException as e:
            print(f"Error sending tare command: {e}")
            return False
    
    def is_stable(self, tolerance: float = 0.1, samples: int = 3) -> bool:
        """Check if scale reading is stable.
        
        Args:
            tolerance: Maximum allowed deviation between readings (grams)
            samples: Number of samples to take
            
        Returns:
            True if readings are stable, False otherwise
        """
        readings = []
        for _ in range(samples):
            weight = self.read_weight()
            if weight is None:
                return False
            readings.append(weight)
            time.sleep(0.1)
        
        if not readings:
            return False
        
        max_diff = max(readings) - min(readings)
        return max_diff <= tolerance
    
    def get_stable_weight(self, max_attempts: int = 10, tolerance: float = 0.1, stable_duration: float = 3.0) -> Optional[float]:
        """Wait for and return a stable weight reading.
        
        Args:
            max_attempts: Maximum number of attempts to get stable reading
            tolerance: Maximum allowed deviation between readings (grams)
            stable_duration: Duration in seconds that weight must remain stable (default: 3.0)
            
        Returns:
            Stable weight in grams, or None if could not get stable reading
        """
        stable_start_time = None
        stable_value = None
        check_interval = 0.1  # Check every 100ms
        
        for attempt in range(max_attempts * 10):  # More attempts for longer duration
            current_weight = self.read_weight()
            
            if current_weight is None:
                stable_start_time = None
                stable_value = None
                time.sleep(check_interval)
                continue
            
            # Check if this weight is similar to the stable value
            if stable_value is not None:
                if abs(current_weight - stable_value) <= tolerance:
                    # Weight is still stable, check if duration met
                    elapsed = time.time() - stable_start_time
                    if elapsed >= stable_duration:
                        return stable_value
                else:
                    # Weight changed, reset stability tracking
                    stable_start_time = time.time()
                    stable_value = current_weight
            else:
                # First stable reading
                stable_start_time = time.time()
                stable_value = current_weight
            
            time.sleep(check_interval)
        
        return None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Convenience functions
def detect_scales() -> List[Dict[str, str]]:
    """Detect all available scale devices.
    
    Returns:
        List of available serial ports that might be scales
    """
    return ScaleReader.list_available_ports()


def read_scale_once(port: Optional[str] = None, baudrate: int = 9600) -> Optional[float]:
    """Quick function to read weight from scale once.
    
    Args:
        port: Serial port name, or None to auto-detect
        baudrate: Communication speed
        
    Returns:
        Weight in grams, or None if failed
    """
    with ScaleReader(port=port, baudrate=baudrate) as scale:
        if scale.serial_connection:
            return scale.get_stable_weight()
    return None
