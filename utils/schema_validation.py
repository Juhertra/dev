"""
Schema validation helper for Phase 4A
Validates JSON data against schemas before writing
"""
import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def validate_json(data: Dict[str, Any], schema_path: str, what: str) -> bool:
    """
    Validate JSON data against a schema file.
    
    Args:
        data: JSON data to validate
        schema_path: Path to schema file (relative to forChatGPT/DATA_SCHEMA/)
        what: Description of what's being validated (for logging)
    
    Returns:
        True if valid, False if invalid
    """
    try:
        # Load schema file
        schema_file = os.path.join("forChatGPT", "DATA_SCHEMA", schema_path)
        if not os.path.exists(schema_file):
            logger.warning(f"SCHEMA_VALIDATION_FAIL schema_file_not_found={schema_file} what={what}")
            return False
        
        with open(schema_file, 'r') as f:
            schema = json.load(f)
        
        # Basic validation - check required fields exist
        if isinstance(data, list):
            # For arrays, validate each item
            for i, item in enumerate(data):
                if not _validate_item(item, schema.get('items', {}), f"{what}[{i}]"):
                    return False
        else:
            # For objects, validate the item
            if not _validate_item(data, schema, what):
                return False
        
        logger.info(f"SCHEMA_VALIDATION_OK schema={schema_path} what={what}")
        return True
        
    except Exception as e:
        logger.error(f"SCHEMA_VALIDATION_FAIL error={str(e)} schema={schema_path} what={what}")
        return False

def _validate_item(item: Dict[str, Any], schema: Dict[str, Any], what: str) -> bool:
    """Validate a single item against schema properties."""
    if not isinstance(item, dict):
        logger.warning(f"SCHEMA_VALIDATION_FAIL not_dict what={what}")
        return False
    
    # Check required fields
    required = schema.get('required', [])
    for field in required:
        if field not in item:
            logger.warning(f"SCHEMA_VALIDATION_FAIL missing_required field={field} what={what}")
            return False
    
    # Check field types and patterns
    properties = schema.get('properties', {})
    for field, field_schema in properties.items():
        if field in item:
            if not _validate_field(item[field], field_schema, f"{what}.{field}"):
                return False
    
    return True

def _validate_field(value: Any, field_schema: Dict[str, Any], field_path: str) -> bool:
    """Validate a single field against its schema."""
    field_type = field_schema.get('type')
    
    # Type validation
    if field_type == 'string':
        if not isinstance(value, str):
            logger.warning(f"SCHEMA_VALIDATION_FAIL type_mismatch field={field_path} expected=string got={type(value).__name__}")
            return False
    elif field_type == 'integer':
        if not isinstance(value, int):
            logger.warning(f"SCHEMA_VALIDATION_FAIL type_mismatch field={field_path} expected=integer got={type(value).__name__}")
            return False
    elif field_type == 'array':
        if not isinstance(value, list):
            logger.warning(f"SCHEMA_VALIDATION_FAIL type_mismatch field={field_path} expected=array got={type(value).__name__}")
            return False
    
    # Pattern validation
    pattern = field_schema.get('pattern')
    if pattern and isinstance(value, str):
        import re
        if not re.match(pattern, value):
            logger.warning(f"SCHEMA_VALIDATION_FAIL pattern_mismatch field={field_path} pattern={pattern}")
            return False
    
    # Enum validation
    enum_values = field_schema.get('enum')
    if enum_values and value not in enum_values:
        logger.warning(f"SCHEMA_VALIDATION_FAIL enum_mismatch field={field_path} value={value} allowed={enum_values}")
        return False
    
    return True
