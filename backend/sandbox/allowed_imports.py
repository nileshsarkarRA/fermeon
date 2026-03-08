"""
List of explicitly allowed packages that the dynamically generated
subprocess executor is allowed to import if using a more advanced restricted sandbox.
"""

ALLOWED_IMPORTS = [
    "math",
    "cadquery",
    "sys",
    "json",
    "traceback",
    "typing"
]
