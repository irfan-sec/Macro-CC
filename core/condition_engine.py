import re
import ctypes
from typing import Any, Tuple

class ConditionEngine:
    """Evaluates conditional statements for macro branching and loops."""

    def __init__(self, variables):
        # Reference to the Player's variable store
        self.variables = variables

    def evaluate(self, condition: str) -> bool:
        """
        Evaluate a condition string.
        Examples:
        - "{my_var} == 10"
        - "{status} != error"
        - "window_title contains Chrome"
        - "pixel_color(100,200) == #FF0000"
        """
        # 1. Substitute variables in the condition string first
        condition = self.variables.substitute(condition).strip()

        # 2. Check for specialized functions
        if condition.startswith("pixel_color"):
            return self._eval_pixel_color(condition)
        if condition.startswith("window_title"):
            return self._eval_window_title(condition)

        # 3. Standard operator evaluation
        operators = ["==", "!=", ">=", "<=", ">", "<", " not contains ", " contains "]
        
        for op in operators:
            if op in condition:
                parts = condition.split(op, 1)
                left = parts[0].strip()
                right = parts[1].strip()
                return self._compare(left, op.strip(), right)
                
        # If it's just a variable or string, evaluate truthiness
        if condition.lower() in ("true", "1", "yes"): return True
        if condition.lower() in ("false", "0", "no", ""): return False
        
        return bool(condition)

    def _compare(self, left: str, op: str, right: str) -> bool:
        """Compare two values based on the operator."""
        
        # Try to cast to numbers if both look numeric
        try:
            if "." in left or "." in right:
                left_val = float(left)
                right_val = float(right)
            else:
                left_val = int(left)
                right_val = int(right)
        except ValueError:
            left_val = left
            right_val = right

        if op == "==": return left_val == right_val
        if op == "!=": return left_val != right_val
        if op == "contains": return str(right_val).lower() in str(left_val).lower()
        if op == "not contains": return str(right_val).lower() not in str(left_val).lower()
        
        # Numeric only operators
        if isinstance(left_val, (int, float)) and isinstance(right_val, (int, float)):
            if op == ">": return left_val > right_val
            if op == "<": return left_val < right_val
            if op == ">=": return left_val >= right_val
            if op == "<=": return left_val <= right_val
            
        return False

    def _eval_pixel_color(self, condition: str) -> bool:
        """Evaluate pixel_color(x,y) == #RRGGBB"""
        # Parse pixel_color(100, 200) == #FF0000
        match = re.match(r"pixel_color\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*(==|!=)\s*(#[A-Fa-f0-9]{6})", condition)
        if not match:
            print(f"[Player] Invalid pixel_color condition: {condition}")
            return False
            
        x = int(match.group(1))
        y = int(match.group(2))
        op = match.group(3)
        expected_hex = match.group(4).upper()
        
        # Get actual color
        actual_color = self._get_pixel_color(x, y)
        actual_hex = "#{:02X}{:02X}{:02X}".format(*actual_color)
        
        if op == "==": return actual_hex == expected_hex
        if op == "!=": return actual_hex != expected_hex
        return False

    def _eval_window_title(self, condition: str) -> bool:
        """Evaluate window_title contains XYZ"""
        match = re.match(r"window_title\s+(contains|not contains|==|!=)\s+(.*)", condition)
        if not match:
            print(f"[Player] Invalid window_title condition: {condition}")
            return False
            
        op = match.group(1)
        expected = match.group(2).strip()
        
        import win32gui
        active_title = win32gui.GetWindowText(win32gui.GetForegroundWindow())
        
        return self._compare(active_title, op, expected)
        
    def _get_pixel_color(self, x: int, y: int) -> Tuple[int, int, int]:
        """Read a single pixel color from the screen using Win32 GDI."""
        hdc = ctypes.windll.user32.GetDC(0)
        color = ctypes.windll.gdi32.GetPixel(hdc, x, y)
        ctypes.windll.user32.ReleaseDC(0, hdc)
        
        r = color & 0xFF
        g = (color >> 8) & 0xFF
        b = (color >> 16) & 0xFF
        return (r, g, b)
