# tests/test_fitness.py
import pytest
from app.observability.audit import compute_fitness

def make_audit(timeline, status=200):
    return {"timeline": timeline, "status": status}

def test_fitness_happy_path():
    """Test fitness calculation for successful request"""
    a = make_audit([
        {"event":"validated","meta":{"ok":True}},
        {"event":"exported","meta":{"splunk":"ok","elastic":"ok"}},
    ], status=202)
    f = compute_fitness(a)
    assert abs(f - 1.0) < 1e-6

def test_fitness_validation_fail():
    """Test fitness calculation when validation fails"""
    a = make_audit([
        {"event":"validated","meta":{"ok":False}},
        {"event":"exported","meta":{"splunk":"ok","elastic":"ok"}},
    ], status=400)
    f = compute_fitness(a)
    assert f <= 0.59

def test_fitness_one_export_fail():
    """Test fitness calculation when one export fails"""
    a = make_audit([
        {"event":"validated","meta":{"ok":True}},
        {"event":"exported","meta":{"splunk":"ok","elastic":"fail"}},
    ], status=200)
    f = compute_fitness(a)
    assert 0.79 <= f <= 0.81

def test_fitness_both_exports_fail():
    """Test fitness calculation when both exports fail"""
    a = make_audit([
        {"event":"validated","meta":{"ok":True}},
        {"event":"exported","meta":{"splunk":"fail","elastic":"fail"}},
    ], status=200)
    f = compute_fitness(a)
    assert 0.59 <= f <= 0.61

def test_fitness_validation_and_export_fail():
    """Test fitness calculation when validation and export fail"""
    a = make_audit([
        {"event":"validated","meta":{"ok":False}},
        {"event":"exported","meta":{"splunk":"fail","elastic":"ok"}},
    ], status=400)
    f = compute_fitness(a)
    assert f <= 0.59

def test_fitness_5xx_error():
    """Test fitness calculation for 5xx errors"""
    a = make_audit([
        {"event":"validated","meta":{"ok":True}},
        {"event":"exported","meta":{"splunk":"ok","elastic":"ok"}},
    ], status=500)
    f = compute_fitness(a)
    assert f <= 0.59

def test_fitness_4xx_error():
    """Test fitness calculation for 4xx errors"""
    a = make_audit([
        {"event":"validated","meta":{"ok":True}},
        {"event":"exported","meta":{"splunk":"ok","elastic":"ok"}},
    ], status=404)
    f = compute_fitness(a)
    assert f <= 0.59

def test_fitness_no_timeline():
    """Test fitness calculation with no timeline events"""
    a = make_audit([], status=200)
    f = compute_fitness(a)
    assert f == 1.0

def test_fitness_clamp_bounds():
    """Test that fitness is clamped to [0, 1]"""
    # Multiple failures that would exceed bounds
    a = make_audit([
        {"event":"validated","meta":{"ok":False}},
        {"event":"exported","meta":{"splunk":"fail","elastic":"fail"}},
        {"event":"exported","meta":{"splunk":"fail","elastic":"fail"}},  # Duplicate
    ], status=500)
    f = compute_fitness(a)
    assert 0.0 <= f <= 1.0

def test_fitness_export_variants():
    """Test fitness with different export status values"""
    test_cases = [
        ("ok", 1.0),
        ("success", 1.0),
        ("true", 1.0),
        ("fail", 0.8),
        ("error", 0.8),
        ("false", 0.8),
    ]
    
    for status, expected_fitness in test_cases:
        a = make_audit([
            {"event":"validated","meta":{"ok":True}},
            {"event":"exported","meta":{"splunk":status,"elastic":"ok"}},
        ], status=200)
        f = compute_fitness(a)
        assert abs(f - expected_fitness) < 0.01, f"Failed for status '{status}': expected {expected_fitness}, got {f}"
