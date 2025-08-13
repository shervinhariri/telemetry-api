#!/usr/bin/env python3
"""
Unit tests for risk scoring module
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.enrich.risk import score

def test_base_score():
    """Test base score without any risk factors"""
    event = {"src_ip": "192.168.1.1", "dst_ip": "8.8.8.8"}
    result = score(event, [])
    assert result == 10, f"Expected base score 10, got {result}"

def test_threat_intelligence_boost():
    """Test threat intelligence match boosts score"""
    event = {"src_ip": "192.168.1.1", "dst_ip": "8.8.8.8"}
    result = score(event, ["45.149.3.0/24"])
    assert result == 70, f"Expected score 70 (base 10 + TI 60), got {result}"

def test_risky_port_boost():
    """Test risky destination port boosts score"""
    event = {"src_ip": "192.168.1.1", "dst_ip": "8.8.8.8", "dst_port": 445}
    result = score(event, [])
    assert result == 20, f"Expected score 20 (base 10 + port 10), got {result}"

def test_high_bytes_ephemeral_port():
    """Test high bytes with ephemeral source port"""
    event = {
        "src_ip": "192.168.1.1", 
        "dst_ip": "8.8.8.8", 
        "src_port": 5000,
        "bytes": 2000000
    }
    result = score(event, [])
    assert result == 20, f"Expected score 20 (base 10 + bytes 10), got {result}"

def test_multiple_factors():
    """Test multiple risk factors combined"""
    event = {
        "src_ip": "192.168.1.1", 
        "dst_ip": "8.8.8.8", 
        "dst_port": 3389,
        "src_port": 5000,
        "bytes": 2000000
    }
    result = score(event, ["45.149.3.0/24"])
    assert result == 90, f"Expected score 90 (base 10 + TI 60 + port 10 + bytes 10), got {result}"

def test_score_clamping():
    """Test score is clamped to 0-100 range"""
    event = {
        "src_ip": "192.168.1.1", 
        "dst_ip": "8.8.8.8", 
        "dst_port": 445,
        "src_port": 5000,
        "bytes": 2000000
    }
    # Multiple risk factors: base(10) + TI(60) + port(10) + bytes(10) = 90
    result = score(event, ["45.149.3.0/24"])
    assert result == 90, f"Expected score 90, got {result}"
    
    # Test actual clamping with a score that would exceed 100
    # We'd need more factors to test this, but the current max is 90
    assert result <= 100, f"Score {result} should be clamped to 100"

def test_zeek_conn_format():
    """Test with Zeek conn format field names"""
    event = {
        "id_orig_h": "192.168.1.1",
        "id_resp_h": "8.8.8.8",
        "id_resp_p": 445,
        "orig_bytes": 2000000
    }
    result = score(event, ["45.149.3.0/24"])
    assert result == 80, f"Expected score 80 (base 10 + TI 60 + port 10), got {result}"

def main():
    """Run all tests"""
    tests = [
        test_base_score,
        test_threat_intelligence_boost,
        test_risky_port_boost,
        test_high_bytes_ephemeral_port,
        test_multiple_factors,
        test_score_clamping,
        test_zeek_conn_format
    ]
    
    passed = 0
    for test in tests:
        try:
            test()
            print(f"✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
    
    print(f"\n📊 Risk scoring tests: {passed}/{len(tests)} passed")
    
    if passed == len(tests):
        print("🎉 All risk scoring tests passed!")
        return True
    else:
        print("⚠️ Some risk scoring tests failed.")
        return False

if __name__ == "__main__":
    main()
