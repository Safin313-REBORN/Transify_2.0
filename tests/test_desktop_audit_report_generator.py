"""
Unit tests for the status-driven audit report generator.
Verifies that:
- PASS, FAIL, SKIPPED, and NOT TESTED labels are strictly derived from the underlying data.
- Failed security checks are never represented as successful verification.
- A successful conclusion is never emitted when required test conditions failed.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from scripts.report_generator import (
    generate_execution_log,
    generate_performance_report,
    generate_security_report,
    generate_accessibility_report,
    generate_stability_report,
    generate_master_audit_report
)

@pytest.fixture
def passing_fixture():
    return {
        "audit_metadata": {
            "target_package": "com.abrarafick.transify",
            "evaluated_runtime": "Browser-based Chromium Desktop Testing (Playwright / Chromium 130.0.0.0, Linux x86_64)",
            "single_source_of_truth": "TRANSIFY_V3_RC1_4_DESKTOP_VIEWPORT_MATRIX.json",
            "host_os": "Linux 7.0.0-43-generic x86_64"
        },
        "viewports_tested": [
            {
                "viewport_name": "desktop_1280x720_hd",
                "width": 1280,
                "height": 720,
                "aspect_ratio": "16:9",
                "tier": "HD Laptop",
                "rail_width_px": 112,
                "content_width_px": 1168,
                "home_main_width_px": 884,
                "zero_horizontal_overflow": True,
                "card_clipping_issues_count": 0,
                "clipping_issues_count": 0,
                "status": "PASS"
            }
        ],
        "dpi_scaling_tested": [
            {
                "name": "100% Native Scaling",
                "scale_factor": 1.0,
                "measured_dpr": 1.0,
                "zero_horizontal_overflow": True,
                "status": "PASS"
            }
        ],
        "window_state_tests": [
            {
                "state": "Restored Viewport Simulation (1280x720)",
                "zero_overflow": True,
                "status": "PASS"
            }
        ],
        "keyboard_accessibility": {
            "tab_sequence_count": 8,
            "tab_focused_tags": ["BUTTON#rail-logo-btn", "BUTTON.rail-item"],
            "shift_tab_reverse_working": True,
            "enter_activation_working": True,
            "space_activation_working": True,
            "modal_focus_accessible": True,
            "modal_focus_trapped": True,
            "modal_escape_dismissal_working": True,
            "focus_restoration_working": True,
            "clinician_tab_keyboard_activation": True,
            "no_focus_on_hidden_content": True,
            "status": "PASS"
        },
        "zero_auto_audio_verified": {
            "unprompted_audio_playback_attempts": 0,
            "unprompted_speech_synthesis_attempts": 0,
            "explicit_user_action_speech_attempts": 1,
            "status": "PASS"
        },
        "performance_benchmarks": {
            "initial_startup_ms": 1500.0,
            "mean_route_transition_ms": 65.4,
            "status": "PASS",
            "route_latencies_ms": {
                "home": {"label": "Home", "dispatch_ms": 0.0, "activation_ms": 10.0, "first_frame_ms": 12.0, "readiness_ms": 15.0, "total_latency_ms": 15.0, "status": "PASS"},
                "clinician": {"label": "Clinician", "dispatch_ms": 0.0, "activation_ms": 5.0, "first_frame_ms": 80.0, "readiness_ms": 95.0, "total_latency_ms": 95.0, "status": "PASS"}
            },
            "raf_callback_cadence_hz": {
                "measured_cadence_hz": 50.2,
                "frames_captured": 101,
                "duration_sec": 2.01
            },
            "cdp_heap_memory": {
                "usedHeapMB": 1.5,
                "totalHeapMB": 3.5,
                "domNodes": 12000,
                "jsEventListeners": 900
            }
        },
        "stability_50_cycles": {
            "transitions_executed": 50,
            "status": "PASS",
            "baseline_metrics": {"usedHeapMB": 1.1, "domNodes": 12000, "listeners": 900},
            "post_test_metrics": {"usedHeapMB": 1.3, "domNodes": 12150, "listeners": 900},
            "delta": {"heap_delta_mb": 0.2, "node_delta": 150, "listener_delta": 0}
        },
        "production_security_probe": {
            "target_url": "https://transify20-production.up.railway.app/",
            "http_status": 200,
            "protocol": "2",
            "live_headers": {"server": "railway-hikari"},
            "missing_security_headers": [],
            "local_middleware_verified": True,
            "hsts_present": True,
            "csp_present": True,
            "status": "PASS"
        },
        "bengali_typography_audit": {
            "fontFamily": "Hind Siliguri",
            "fontSizePx": 16.0,
            "lineHeight": "24px",
            "status": "PASS"
        },
        "summary": {
            "overall_status": "PASS",
            "browser_desktop_functionality_status": "PASSED (VERIFIED)",
            "desktop_production_security_status": "VERIFIED (PASSED)"
        }
    }

@pytest.fixture
def failing_fixture():
    return {
        "audit_metadata": {
            "target_package": "com.abrarafick.transify",
            "evaluated_runtime": "Browser-based Chromium Desktop Testing",
            "single_source_of_truth": "TRANSIFY_V3_RC1_4_DESKTOP_VIEWPORT_MATRIX.json",
            "host_os": "Linux"
        },
        "viewports_tested": [
            {
                "viewport_name": "desktop_1280x720_hd",
                "width": 1280,
                "height": 720,
                "aspect_ratio": "16:9",
                "tier": "HD Laptop",
                "rail_width_px": 112,
                "content_width_px": 1168,
                "home_main_width_px": 1300,
                "zero_horizontal_overflow": False,
                "card_clipping_issues_count": 2,
                "clipping_issues_count": 2,
                "status": "FAIL"
            }
        ],
        "dpi_scaling_tested": [],
        "window_state_tests": [],
        "keyboard_accessibility": {
            "tab_sequence_count": 2,
            "shift_tab_reverse_working": False,
            "enter_activation_working": False,
            "space_activation_working": False,
            "modal_focus_accessible": False,
            "modal_focus_trapped": False,
            "modal_escape_dismissal_working": False,
            "focus_restoration_working": False,
            "clinician_tab_keyboard_activation": False,
            "no_focus_on_hidden_content": False,
            "status": "FAIL"
        },
        "zero_auto_audio_verified": {
            "unprompted_audio_playback_attempts": 2,
            "unprompted_speech_synthesis_attempts": 1,
            "explicit_user_action_speech_attempts": 0,
            "status": "FAIL"
        },
        "performance_benchmarks": {
            "initial_startup_ms": 4000.0,
            "mean_route_transition_ms": 350.0,
            "status": "FAIL",
            "route_latencies_ms": {},
            "raf_callback_cadence_hz": {},
            "cdp_heap_memory": {}
        },
        "stability_50_cycles": {
            "transitions_executed": 50,
            "status": "FAIL",
            "baseline_metrics": {"usedHeapMB": 1.0, "domNodes": 1000, "listeners": 100},
            "post_test_metrics": {"usedHeapMB": 20.0, "domNodes": 5000, "listeners": 500},
            "delta": {"heap_delta_mb": 19.0, "node_delta": 4000, "listener_delta": 400}
        },
        "production_security_probe": {
            "target_url": "https://transify20-production.up.railway.app/",
            "http_status": 200,
            "protocol": "2",
            "live_headers": {"server": "railway-hikari"},
            "missing_security_headers": ["strict-transport-security", "content-security-policy"],
            "local_middleware_verified": False,
            "hsts_present": False,
            "csp_present": False,
            "status": "FAIL"
        },
        "bengali_typography_audit": {
            "status": "FAIL"
        },
        "summary": {
            "overall_status": "FAIL",
            "browser_desktop_functionality_status": "FAILED",
            "desktop_production_security_status": "FAILED"
        }
    }

@pytest.fixture
def not_tested_fixture():
    return {
        "audit_metadata": {
            "target_package": "com.abrarafick.transify",
            "evaluated_runtime": "Browser-based Chromium Desktop Testing",
            "single_source_of_truth": "TRANSIFY_V3_RC1_4_DESKTOP_VIEWPORT_MATRIX.json",
            "host_os": "Linux"
        },
        "viewports_tested": [],
        "dpi_scaling_tested": [
            {
                "name": "200% High-DPI Scaling",
                "scale_factor": 2.0,
                "measured_dpr": 2.0,
                "zero_horizontal_overflow": True,
                "status": "NOT TESTED"
            }
        ],
        "window_state_tests": [
            {
                "state": "OS Window Maximize",
                "zero_overflow": True,
                "status": "NOT TESTED"
            }
        ],
        "keyboard_accessibility": {},
        "zero_auto_audio_verified": {},
        "performance_benchmarks": {},
        "stability_50_cycles": {},
        "production_security_probe": {
            "status": "NOT TESTED"
        },
        "bengali_typography_audit": {
            "status": "NOT TESTED"
        },
        "summary": {
            "overall_status": "INCOMPLETE"
        }
    }


def test_passing_fixture_emits_pass_and_success_conclusion(passing_fixture):
    log = generate_execution_log(passing_fixture)
    assert "[PASS] Viewport desktop_1280x720_hd" in log
    assert "[PASS] Sequential Tab Traversal" in log
    assert "[PASS] Production Edge Security Verdict: PASS" in log
    assert "[CONCLUSION] ALL REQUIRED BROWSER DESKTOP FUNCTIONALITY CHECKS PASSED EMPIRICALLY." in log
    assert "ALL DESKTOP AUDIT CHECKS PASSED EMPIRICALLY." not in log


def test_failing_fixture_emits_fail_and_never_claims_success(failing_fixture):
    log = generate_execution_log(failing_fixture)
    assert "[FAIL] Viewport desktop_1280x720_hd" in log
    assert "[FAIL] Reverse Shift+Tab: FAILED" in log
    assert "[FAIL] Production Edge HSTS: ABSENT" in log
    assert "[FAIL] Production Edge CSP: ABSENT" in log
    assert "[FAIL] Production Edge Security Verdict: FAIL" in log
    # Crucial: Must NEVER claim all checks passed!
    assert "ALL REQUIRED BROWSER DESKTOP FUNCTIONALITY CHECKS PASSED EMPIRICALLY." not in log
    assert "ALL DESKTOP AUDIT CHECKS PASSED EMPIRICALLY." not in log
    assert "[CONCLUSION] AUDIT IDENTIFIED DEFECTS / BLOCKED GATES (Overall Status: FAIL)." in log


def test_not_tested_fixture_emits_not_tested_label(not_tested_fixture):
    log = generate_execution_log(not_tested_fixture)
    assert "[NOT TESTED] Scaling 200% High-DPI Scaling" in log
    assert "[NOT TESTED] Resize State: OS Window Maximize" in log
    assert "ALL REQUIRED BROWSER DESKTOP FUNCTIONALITY CHECKS PASSED EMPIRICALLY." not in log


def test_master_report_separate_verdicts(passing_fixture):
    master = generate_master_audit_report(passing_fixture)
    assert "A. BROWSER DESKTOP FUNCTIONALITY:" in master
    assert "B. DESKTOP PRODUCTION SECURITY:" in master
    assert "C. NATIVE EMBEDDED DESKTOP WEBVIEW:" in master
    assert "D. GATE 3 — ANDROID PHYSICAL HARDWARE: OPEN / DEFERRED" in master
    assert "E. GATE 2 — CLINICAL GOVERNANCE:       PENDING PRE-DEPLOYMENT" in master
    assert "CONDITIONALLY APPROVED (Web Pilot Workstations Only)" in master
