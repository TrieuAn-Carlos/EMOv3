"""
EMO Backend - Robust Tool Wrapper
==================================
Wrapper for tools with better error handling and validation.
Prevents tool_use_failed errors from LLM.
"""

from typing import Any, Callable, Optional
from functools import wraps
import traceback


def robust_tool(func: Callable) -> Callable:
    """
    Decorator to make tools more robust against errors.
    
    Features:
    - Catches all exceptions
    - Returns user-friendly error messages
    - Logs detailed errors for debugging
    - Ensures consistent string output
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> str:
        try:
            # Validate arguments
            if args and kwargs:
                # If both provided, prefer kwargs
                result = func(**kwargs)
            elif args:
                result = func(*args)
            elif kwargs:
                result = func(**kwargs)
            else:
                result = func()
            
            # Ensure string output
            if result is None:
                return "✅ Thao tác hoàn thành."
            
            if not isinstance(result, str):
                result = str(result)
            
            # Truncate very long outputs
            if len(result) > 50000:
                result = result[:50000] + "\n\n[...Nội dung quá dài, đã cắt ngắn...]"
            
            return result
            
        except TypeError as e:
            # Argument type mismatch
            error_msg = f"❌ Lỗi tham số: {str(e)[:100]}"
            print(f"Tool {func.__name__} TypeError: {e}")
            return error_msg
            
        except ValueError as e:
            # Invalid value
            error_msg = f"❌ Giá trị không hợp lệ: {str(e)[:100]}"
            print(f"Tool {func.__name__} ValueError: {e}")
            return error_msg
            
        except ImportError as e:
            # Missing dependency
            error_msg = f"❌ Thiếu module: {str(e)[:100]}"
            print(f"Tool {func.__name__} ImportError: {e}")
            return error_msg
            
        except FileNotFoundError as e:
            # File not found
            error_msg = f"❌ Không tìm thấy file: {str(e)[:100]}"
            print(f"Tool {func.__name__} FileNotFoundError: {e}")
            return error_msg
            
        except PermissionError as e:
            # Permission denied
            error_msg = f"❌ Không có quyền truy cập: {str(e)[:100]}"
            print(f"Tool {func.__name__} PermissionError: {e}")
            return error_msg
            
        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = f"❌ Lỗi không xác định: {type(e).__name__}: {str(e)[:100]}"
            print(f"Tool {func.__name__} Exception: {e}")
            print(traceback.format_exc())
            return error_msg
    
    return wrapper


def validate_tool_params(**param_rules):
    """
    Decorator to validate tool parameters before execution.
    
    Usage:
        @validate_tool_params(
            query={"type": str, "required": True},
            max_results={"type": int, "min": 1, "max": 50, "default": 5}
        )
        def my_tool(query: str, max_results: int = 5):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> str:
            # Convert args to kwargs for validation
            import inspect
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            combined_kwargs = dict(zip(param_names, args))
            combined_kwargs.update(kwargs)
            
            # Validate each parameter
            for param_name, rules in param_rules.items():
                value = combined_kwargs.get(param_name)
                
                # Check required
                if rules.get("required") and value is None:
                    return f"❌ Tham số '{param_name}' là bắt buộc."
                
                # Apply default
                if value is None and "default" in rules:
                    combined_kwargs[param_name] = rules["default"]
                    value = rules["default"]
                
                if value is not None:
                    # Check type
                    expected_type = rules.get("type")
                    if expected_type and not isinstance(value, expected_type):
                        try:
                            # Try to convert
                            combined_kwargs[param_name] = expected_type(value)
                        except:
                            return f"❌ Tham số '{param_name}' phải là {expected_type.__name__}."
                    
                    # Check min/max for numbers
                    if isinstance(value, (int, float)):
                        if "min" in rules and value < rules["min"]:
                            return f"❌ '{param_name}' phải >= {rules['min']}."
                        if "max" in rules and value > rules["max"]:
                            return f"❌ '{param_name}' phải <= {rules['max']}."
                    
                    # Check length for strings
                    if isinstance(value, str):
                        if "min_length" in rules and len(value) < rules["min_length"]:
                            return f"❌ '{param_name}' quá ngắn (tối thiểu {rules['min_length']} ký tự)."
                        if "max_length" in rules and len(value) > rules["max_length"]:
                            return f"❌ '{param_name}' quá dài (tối đa {rules['max_length']} ký tự)."
            
            # Call original function with validated params
            return func(**combined_kwargs)
        
        return wrapper
    return decorator


def safe_import(module_path: str, fallback_message: str = None) -> Any:
    """
    Safely import a module with fallback error message.
    
    Args:
        module_path: Module to import (e.g., "integrations.gmail")
        fallback_message: Custom error message if import fails
        
    Returns:
        Imported module or raises ImportError with friendly message
    """
    try:
        parts = module_path.split(".")
        module = __import__(module_path, fromlist=[parts[-1]])
        return module
    except ImportError as e:
        if fallback_message:
            raise ImportError(fallback_message) from e
        else:
            raise ImportError(f"Không thể import {module_path}: {e}") from e


def truncate_output(text: str, max_length: int = 20000, indicator: str = "\n\n[...Nội dung đã cắt ngắn...]") -> str:
    """
    Truncate text output to prevent token overflow.
    
    Args:
        text: Input text
        max_length: Maximum characters
        indicator: Truncation indicator
        
    Returns:
        Truncated text
    """
    if not isinstance(text, str):
        text = str(text)
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + indicator
