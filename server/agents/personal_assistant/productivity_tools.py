"""
Productivity Tools for Personal Assistant
Includes calculations, conversions, timers, and alarms
"""
from typing import Dict, Any
import re
import json
from datetime import datetime, timedelta

def calculate(expression: str) -> Dict[str, Any]:
    """
    Safely evaluate mathematical expressions
    """
    try:
        # Remove any potentially dangerous characters
        safe_expr = re.sub(r'[^0-9+\-*/().%\s]', '', expression)
        
        # Evaluate the expression
        result = eval(safe_expr, {"__builtins__": {}}, {})
        
        return {
            "status": "success",
            "expression": expression,
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Calculation error: {str(e)}"
        }

def convert_units(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """
    Convert between common units
    """
    # Conversion factors to base units
    conversions = {
        # Length (to meters)
        "m": 1, "meter": 1, "meters": 1,
        "km": 1000, "kilometer": 1000, "kilometers": 1000,
        "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
        "mm": 0.001, "millimeter": 0.001, "millimeters": 0.001,
        "mile": 1609.34, "miles": 1609.34,
        "yard": 0.9144, "yards": 0.9144,
        "foot": 0.3048, "feet": 0.3048, "ft": 0.3048,
        "inch": 0.0254, "inches": 0.0254, "in": 0.0254,
        
        # Weight (to kilograms)
        "kg": 1, "kilogram": 1, "kilograms": 1,
        "g": 0.001, "gram": 0.001, "grams": 0.001,
        "mg": 0.000001, "milligram": 0.000001, "milligrams": 0.000001,
        "lb": 0.453592, "pound": 0.453592, "pounds": 0.453592,
        "oz": 0.0283495, "ounce": 0.0283495, "ounces": 0.0283495,
        
        # Temperature (special handling)
        "celsius": "C", "c": "C",
        "fahrenheit": "F", "f": "F",
        "kelvin": "K", "k": "K",
        
        # Volume (to liters)
        "l": 1, "liter": 1, "liters": 1,
        "ml": 0.001, "milliliter": 0.001, "milliliters": 0.001,
        "gal": 3.78541, "gallon": 3.78541, "gallons": 3.78541,
        "cup": 0.236588, "cups": 0.236588,
        
        # Time (to seconds)
        "s": 1, "second": 1, "seconds": 1,
        "min": 60, "minute": 60, "minutes": 60,
        "h": 3600, "hour": 3600, "hours": 3600,
        "day": 86400, "days": 86400,
    }
    
    from_unit_lower = from_unit.lower()
    to_unit_lower = to_unit.lower()
    
    # Handle temperature conversions separately
    if from_unit_lower in ["celsius", "c", "fahrenheit", "f", "kelvin", "k"]:
        return convert_temperature(value, from_unit_lower, to_unit_lower)
    
    try:
        # Convert to base unit
        from_factor = conversions.get(from_unit_lower)
        to_factor = conversions.get(to_unit_lower)
        
        if from_factor is None or to_factor is None:
            return {
                "status": "error",
                "message": f"Unknown unit: {from_unit if from_factor is None else to_unit}"
            }
        
        # Convert
        base_value = value * from_factor
        result = base_value / to_factor
        
        return {
            "status": "success",
            "value": value,
            "from_unit": from_unit,
            "to_unit": to_unit,
            "result": round(result, 6)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Conversion error: {str(e)}"
        }

def convert_temperature(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """Convert between temperature units"""
    try:
        # Normalize units
        from_u = "C" if from_unit in ["celsius", "c"] else "F" if from_unit in ["fahrenheit", "f"] else "K"
        to_u = "C" if to_unit in ["celsius", "c"] else "F" if to_unit in ["fahrenheit", "f"] else "K"
        
        # Convert to Celsius first
        if from_u == "C":
            celsius = value
        elif from_u == "F":
            celsius = (value - 32) * 5/9
        else:  # Kelvin
            celsius = value - 273.15
        
        # Convert from Celsius to target
        if to_u == "C":
            result = celsius
        elif to_u == "F":
            result = celsius * 9/5 + 32
        else:  # Kelvin
            result = celsius + 273.15
        
        return {
            "status": "success",
            "value": value,
            "from_unit": from_unit,
            "to_unit": to_unit,
            "result": round(result, 2)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Temperature conversion error: {str(e)}"
        }

def parse_duration(duration_str: str) -> int:
    """
    Parse duration string to seconds
    Examples: "5 minutes", "1 hour 30 minutes", "45s"
    """
    duration_str = duration_str.lower()
    total_seconds = 0
    
    # Parse hours
    hours_match = re.search(r'(\d+)\s*(h|hour|hours)', duration_str)
    if hours_match:
        total_seconds += int(hours_match.group(1)) * 3600
    
    # Parse minutes
    minutes_match = re.search(r'(\d+)\s*(m|min|minute|minutes)', duration_str)
    if minutes_match:
        total_seconds += int(minutes_match.group(1)) * 60
    
    # Parse seconds
    seconds_match = re.search(r'(\d+)\s*(s|sec|second|seconds)', duration_str)
    if seconds_match:
        total_seconds += int(seconds_match.group(1))
    
    # If no units found, assume minutes
    if total_seconds == 0:
        number_match = re.search(r'(\d+)', duration_str)
        if number_match:
            total_seconds = int(number_match.group(1)) * 60
    
    return total_seconds

def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration"""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        if secs > 0:
            return f"{minutes} minutes {secs} seconds"
        return f"{minutes} minutes"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours} hours {minutes} minutes"
        return f"{hours} hours"
