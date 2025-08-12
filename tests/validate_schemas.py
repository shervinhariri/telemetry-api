#!/usr/bin/env python3
"""
Schema validation for sample data
"""
import json
import jsonschema
import sys
from pathlib import Path

def load_schema(schema_path):
    """Load JSON schema from file"""
    with open(schema_path, 'r') as f:
        return json.load(f)

def load_sample(sample_path):
    """Load sample data from file"""
    with open(sample_path, 'r') as f:
        return json.load(f)

def validate_sample(sample_data, schema, sample_name):
    """Validate sample data against schema"""
    try:
        jsonschema.validate(instance=sample_data, schema=schema)
        print(f"✅ {sample_name} validates against schema")
        return True
    except jsonschema.exceptions.ValidationError as e:
        print(f"❌ {sample_name} validation failed: {e.message}")
        return False
    except Exception as e:
        print(f"❌ {sample_name} error: {e}")
        return False

def main():
    """Main validation function"""
    schemas_dir = Path("schemas")
    samples_dir = Path("samples")
    
    if not schemas_dir.exists():
        print("❌ schemas directory not found")
        sys.exit(1)
    
    if not samples_dir.exists():
        print("❌ samples directory not found")
        sys.exit(1)
    
    # Load schemas
    try:
        zeek_schema = load_schema(schemas_dir / "zeek.conn.v1.schema.json")
        flows_schema = load_schema(schemas_dir / "flows.v1.schema.json")
        enriched_schema = load_schema(schemas_dir / "enriched.v1.schema.json")
    except Exception as e:
        print(f"❌ Failed to load schemas: {e}")
        sys.exit(1)
    
    # Validate samples
    success = True
    
    # Validate Zeek sample
    zeek_sample = samples_dir / "zeek_conn.json"
    if zeek_sample.exists():
        sample_data = load_sample(zeek_sample)
        if not validate_sample(sample_data, zeek_schema, "zeek_conn.json"):
            success = False
    else:
        print("⚠️  zeek_conn.json not found")
    
    # Validate flows sample
    flows_sample = samples_dir / "flows_v1.json"
    if flows_sample.exists():
        sample_data = load_sample(flows_sample)
        if not validate_sample(sample_data, flows_schema, "flows_v1.json"):
            success = False
    else:
        print("⚠️  flows_v1.json not found")
    
    # Test enriched output (would need to run API to generate)
    print("ℹ️  Enriched schema validation requires API response")
    
    if success:
        print("✅ All schema validations passed")
        sys.exit(0)
    else:
        print("❌ Some schema validations failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
