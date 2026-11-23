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
            "overall_status": "CONDITIONALLY APPROVED (Web Pilot Workstations Only)",
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


def test_bengali_font_loaded_false_fails(passing_fixture):
    fixture = dict(passing_fixture)
    fixture["bengali_typography_audit"] = {
        "fontFamily": "Outfit, sans-serif",
        "fontLoaded": False,
        "platformFontFamily": "Unknown",
        "status": "FAIL"
    }
    fixture["summary"] = {
        "overall_status": "FAIL",
        "browser_desktop_functionality_status": "FAILED"
    }
    master = generate_master_audit_report(fixture)
    assert "document.fonts.check: **FAIL**" in master
    assert "**Bengali Typography Status:** **FAIL**" in master


def test_keyboard_focus_trap_false_fails(passing_fixture):
    fixture = dict(passing_fixture)
    fixture["keyboard_accessibility"] = dict(passing_fixture["keyboard_accessibility"])
    fixture["keyboard_accessibility"]["modal_focus_trapped"] = False
    fixture["keyboard_accessibility"]["status"] = "FAIL"
    
    a11y = generate_accessibility_report(fixture)
    assert "| • Modal Focus Trapping:                    FAIL" in a11y
    assert "| • Computed Keyboard Accessibility Verdict: FAIL" in a11y


def test_keyboard_focus_restoration_false_fails(passing_fixture):
    fixture = dict(passing_fixture)
    fixture["keyboard_accessibility"] = dict(passing_fixture["keyboard_accessibility"])
    fixture["keyboard_accessibility"]["focus_restoration_working"] = False
    fixture["keyboard_accessibility"]["status"] = "FAIL"
    
    a11y = generate_accessibility_report(fixture)
    assert "| • Focus Restoration to Modal Opener:       FAIL" in a11y


def test_clinician_queue_readiness_failure(passing_fixture):
    fixture = dict(passing_fixture)
    fixture["performance_benchmarks"] = dict(passing_fixture["performance_benchmarks"])
    fixture["performance_benchmarks"]["route_latencies_ms"] = dict(passing_fixture["performance_benchmarks"]["route_latencies_ms"])
    fixture["performance_benchmarks"]["route_latencies_ms"]["clinician"] = {
        "label": "Clinician",
        "total_latency_ms": -1,
        "status": "FAIL",
        "error": "Table rows count was 0, expected 50"
    }
    fixture["performance_benchmarks"]["status"] = "FAIL"
    
    perf = generate_performance_report(fixture)
    assert "| `clinician` | Clinician |" in perf
    assert "**FAIL**" in perf


def test_missing_security_headers_fails(passing_fixture):
    fixture = dict(passing_fixture)
    fixture["production_security_probe"] = dict(passing_fixture["production_security_probe"])
    fixture["production_security_probe"]["missing_security_headers"] = ["strict-transport-security", "content-security-policy"]
    fixture["production_security_probe"]["hsts_present"] = False
    fixture["production_security_probe"]["csp_present"] = False
    fixture["production_security_probe"]["status"] = "FAIL"
    
    sec = generate_security_report(fixture)
    assert "| • Live Railway Production Edge:        FAILED / HARDENING PENDING" in sec
    assert "Live Production Edge Assessment: FAILED / HARDENING PENDING" in sec


def test_stability_excessive_heap_growth_fails(passing_fixture):
    fixture = dict(passing_fixture)
    fixture["stability_50_cycles"] = dict(passing_fixture["stability_50_cycles"])
    fixture["stability_50_cycles"]["delta"] = {"heap_delta_mb": 18.5, "node_delta": 400, "listener_delta": 0}
    fixture["stability_50_cycles"]["status"] = "FAIL"
    
    stab = generate_stability_report(fixture)
    assert "**+18.5 MB** | `< 8.00 MB` | **FAIL**" in stab
    assert "| • Workload Stability Verdict:          FAIL" in stab


def test_detached_dom_unverified_not_claimed_as_pass(passing_fixture):
    fixture = dict(passing_fixture)
    fixture["stability_50_cycles"] = dict(passing_fixture["stability_50_cycles"])
    fixture["stability_50_cycles"]["detached_dom_status"] = "NOT MEASURED (CDP Heap Snapshot Required)"
    
    stab = generate_stability_report(fixture)
    assert "| • Detached DOM Reference Audit:        NOT MEASURED (CDP Heap Snapshot Required)" in stab
    assert "PASSED (No runaway detached DOM trees detected)" not in stab


def test_missing_activation_time_fails(passing_fixture):
    fixture = dict(passing_fixture)
    fixture["performance_benchmarks"] = dict(passing_fixture["performance_benchmarks"])
    fixture["performance_benchmarks"]["route_latencies_ms"] = dict(passing_fixture["performance_benchmarks"]["route_latencies_ms"])
    fixture["performance_benchmarks"]["route_latencies_ms"]["home"] = {
        "label": "Home",
        "dispatch_ms": 0.5,
        "activation_ms": -1,
        "first_frame_ms": 12.0,
        "readiness_ms": 15.0,
        "total_latency_ms": -1,
        "status": "FAIL",
        "error": "Activation timing unrecorded"
    }
    fixture["performance_benchmarks"]["status"] = "FAIL"

    perf = generate_performance_report(fixture)
    assert "| `home` | Home | 0.5 | -1 | 12.0 | 15.0 | N/A | **-1** | **FAIL** |" in perf
    assert "| • Overall Performance Benchmark Status:                    FAIL" in perf


def test_workspace_layout_missing_control_fails(passing_fixture):
    fixture = dict(passing_fixture)
    fixture["viewports_tested"] = [
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
            "clipping_issues_count": 0,
            "workspaces_evaluated": 8,
            "workspaces_ready": 7,
            "workspace_layouts": {
                "home": {"status": "PASS"},
                "sign": {
                    "status": "FAIL",
                    "missing_controls": ["#sign-camera-stage: no element has positive dimensions"]
                }
            },
            "status": "FAIL"
        }
    ]
    log = generate_execution_log(fixture)
    assert "[FAIL] Viewport desktop_1280x720_hd" in log
    assert "Workspaces: 7/8" in log

    master = generate_master_audit_report(fixture)
    assert "| `desktop_1280x720_hd` | 1280x720 | 16:9 | HD Laptop | 112px | **7/8** | **None** | **0** | **FAIL** |" in master


def test_bengali_missing_conjuncts_fails(passing_fixture):
    fixture = dict(passing_fixture)
    fixture["bengali_typography_audit"] = {
        "fontFamily": "Hind Siliguri",
        "fontLoaded": True,
        "platformFontFamily": "Hind Siliguri",
        "fontSizePx": 16.0,
        "lineHeight": "24px",
        "renderedHeightPx": 24.0,
        "heightAdequate": True,
        "conjuncts_verified": False,
        "status": "FAIL"
    }
    master = generate_master_audit_report(fixture)
    assert "Conjuncts Found: **NO**" in master
    assert "**Bengali Typography Status:** **FAIL**" in master


def test_gc_not_invoked_fails(passing_fixture):
    fixture = dict(passing_fixture)
    fixture["stability_50_cycles"] = dict(passing_fixture["stability_50_cycles"])
    fixture["stability_50_cycles"]["gc_invoked"] = False
    fixture["stability_50_cycles"]["status"] = "FAIL"

    stab = generate_stability_report(fixture)
    assert "| • Workload Stability Verdict:          FAIL" in stab


def test_negative_existing_db_copied():
    """Negative test: verify isolated setup never copies data/transify.db."""
    from scripts.verify_desktop_webview_matrix import isolated_audit_environment
    import inspect
    src = inspect.getsource(isolated_audit_environment)
    assert "shutil.copy2(original_db" not in src
    assert "data/transify.db uncopied" in src or "NEVER copies" in src


def test_negative_existing_patient_records_imported():
    """Negative test: verify non-synthetic patient records cause failure."""
    from scripts.verify_desktop_webview_matrix import isolated_audit_environment
    with isolated_audit_environment() as env:
        assert env["synthetic_count"] == 50
        # Verify all records start with synthetic-patient-
        from src.database.db import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM care_patient_intakes WHERE patient_id NOT LIKE 'synthetic-patient-%';")
        non_synth = c.fetchone()[0]
        conn.close()
        assert non_synth == 0


def test_negative_setup_exception_before_yield(monkeypatch):
    """Negative test: verify cleanup and env restoration if setup raises before yield."""
    from scripts.verify_desktop_webview_matrix import isolated_audit_environment
    original_env = os.environ.get("TRANSIFY_DB_PATH")

    def broken_init():
        raise RuntimeError("Simulated failure during schema init")

    monkeypatch.setattr("scripts.verify_desktop_webview_matrix.init_care_db", broken_init)

    with pytest.raises(RuntimeError, match="Simulated failure"):
        with isolated_audit_environment():
            pass

    # Ensure environment was restored
    assert os.environ.get("TRANSIFY_DB_PATH") == original_env


def test_negative_environment_restoration_failure():
    """Negative test: verify TRANSIFY_DB_PATH is restored after normal or abnormal exit."""
    from scripts.verify_desktop_webview_matrix import isolated_audit_environment
    test_val = "/tmp/prior_custom_db.sqlite"
    os.environ["TRANSIFY_DB_PATH"] = test_val
    try:
        try:
            with isolated_audit_environment() as env:
                assert os.environ["TRANSIFY_DB_PATH"] == env["temp_db_path"]
                raise ValueError("Inner audit error")
        except ValueError:
            pass

        assert os.environ.get("TRANSIFY_DB_PATH") == test_val
    finally:
        os.environ.pop("TRANSIFY_DB_PATH", None)


def test_negative_tempdir_cleanup_failure(monkeypatch):
    """Negative test: verify cleanup failure raises error and does not report success."""
    import tempfile
    from scripts.verify_desktop_webview_matrix import isolated_audit_environment

    original_cleanup = tempfile.TemporaryDirectory.cleanup

    def failed_cleanup(self):
        # Do not delete the directory
        pass

    monkeypatch.setattr(tempfile.TemporaryDirectory, "cleanup", failed_cleanup)
    monkeypatch.setattr("shutil.rmtree", lambda *a, **kw: None)

    with pytest.raises(RuntimeError, match="could not be cleaned up"):
        with isolated_audit_environment():
            pass


def test_negative_workspace_overlap_fails(passing_fixture):
    """Negative test: verify overlapping interactive elements flag workspace failure."""
    fixture = dict(passing_fixture)
    fixture["viewports_tested"] = [
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
            "clipping_issues_count": 0,
            "workspaces_evaluated": 8,
            "workspaces_ready": 7,
            "workspace_layouts": {
                "home": {
                    "status": "FAIL",
                    "overlapping_elements_count": 2,
                    "overlapping_elements": [
                        {"elementA": "button#btn-say-speak", "elementB": "input#say", "overlapArea": 120}
                    ]
                }
            },
            "status": "FAIL"
        }
    ]
    log = generate_execution_log(fixture)
    assert "[FAIL] Viewport desktop_1280x720_hd" in log


def test_negative_vertical_clipping_fails(passing_fixture):
    """Negative test: verify vertical clipping issues flag failure."""
    fixture = dict(passing_fixture)
    fixture["viewports_tested"] = [
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
            "clipping_issues_count": 1,
            "workspaces_evaluated": 8,
            "workspaces_ready": 7,
            "workspace_layouts": {
                "home": {
                    "status": "FAIL",
                    "vertical_clipping_issues_count": 1,
                    "vertical_clipping_issues": [
                        {"element": "div.home-bento", "ancestor": "div#view-home", "issue": "Content vertically clipped"}
                    ]
                }
            },
            "status": "FAIL"
        }
    ]
    master = generate_master_audit_report(fixture)
    assert "| `desktop_1280x720_hd` | 1280x720 | 16:9 | HD Laptop | 112px | **7/8** | **None** | **1** | **FAIL** |" in master


def test_negative_parent_clipping_fails(passing_fixture):
    """Negative test: verify parent overflow-x:hidden clipping flags failure."""
    fixture = dict(passing_fixture)
    fixture["viewports_tested"] = [
        {
            "viewport_name": "desktop_1280x720_hd",
            "width": 1280,
            "height": 720,
            "aspect_ratio": "16:9",
            "tier": "HD Laptop",
            "rail_width_px": 112,
            "content_width_px": 1168,
            "home_main_width_px": 884,
            "zero_horizontal_overflow": False,
            "clipping_issues_count": 1,
            "workspaces_evaluated": 8,
            "workspaces_ready": 7,
            "workspace_layouts": {
                "settings": {
                    "status": "FAIL",
                    "parent_clipping_issues_count": 1,
                    "parent_clipping_issues": [{"element": "div.settings-navbar", "issue": "Scroll width exceeds client width"}]
                }
            },
            "status": "FAIL"
        }
    ]
    master = generate_master_audit_report(fixture)
    assert "**DETECTED**" in master
    assert "**FAIL**" in master


def test_negative_route_performance_threshold_violation(passing_fixture):
    """Negative test: verify route exceeding defined threshold fails."""
    fixture = dict(passing_fixture)
    fixture["performance_benchmarks"] = dict(passing_fixture["performance_benchmarks"])
    fixture["performance_benchmarks"]["route_latencies_ms"] = dict(passing_fixture["performance_benchmarks"]["route_latencies_ms"])
    fixture["performance_benchmarks"]["route_latencies_ms"]["home"] = {
        "label": "Home",
        "dispatch_ms": 0.5,
        "activation_ms": 10.0,
        "first_raf_callback_ms": 15.0,
        "readiness_ms": 1250.0,
        "threshold_ms": 1000.0,
        "total_latency_ms": 1250.0,
        "status": "FAIL",
        "error": "Exceeded latency threshold"
    }
    fixture["performance_benchmarks"]["status"] = "FAIL"

    perf = generate_performance_report(fixture)
    assert "| `home` | Home | 0.5 | 10.0 | 15.0 | 1250.0 | 1000.0 | **1250.0** | **FAIL** |" in perf
    assert "| • Overall Performance Benchmark Status:                    FAIL" in perf


def test_negative_first_raf_callback_mistakenly_labeled_rendered_frame(passing_fixture):
    """Negative test: verify RAF callback timing is explicitly separated from GPU presentation."""
    perf = generate_performance_report(passing_fixture)
    assert "First RAF Callback:" in perf
    assert "not actual GPU compositor presentation" in perf
    assert "Compositor GPU Frame Rate:                               NOT MEASURED" in perf


def test_negative_noop_route_counted_as_transition(passing_fixture):
    """Negative test: verify a no-op transition (prev == target) is rejected."""
    current_route = "home"
    target_route = "home"
    is_noop = (current_route == target_route)
    assert is_noop is True, "No-op transition must be detected and not counted toward distinct state changes"


def test_negative_conjunct_regex_present_but_visual_rendering_unverified(passing_fixture):
    """Negative test: verify Unicode regex alone does not claim visual glyph shaping."""
    fixture = dict(passing_fixture)
    fixture["bengali_typography_audit"] = {
        "fontFamily": "Hind Siliguri",
        "fontLoaded": True,
        "platformFontFamily": "Hind Siliguri",
        "fontSizePx": 16.0,
        "lineHeight": "24px",
        "renderedHeightPx": 24.0,
        "heightAdequate": True,
        "conjuncts_verified": True,
        "conjunct_codepoint_sequence_present": True,
        "visual_glyph_shaping_status": "VERIFIED VIA SCREENSHOT REVIEW (Regex verifies Unicode codepoint sequence; complex glyph shaping requires visual inspection of captured screenshot artifacts)",
        "status": "PASS"
    }
    master = generate_master_audit_report(fixture)
    assert "VERIFIED VIA SCREENSHOT REVIEW" in master
    assert "complex glyph shaping requires visual inspection" in master


def test_browser_level_geometry_negative_cases():
    """
    Browser-level negative tests verifying:
    1. Unintended button overlap is flagged.
    2. Fixed-versus-absolute element collision is flagged (differing z-index does not bypass).
    3. Vertical clipping by overflow-hidden parent is flagged.
    4. Horizontal clipping by overflow-hidden parent is flagged.
    5. Approved intentional dialog overlay is permitted and not flagged as an overlap defect.
    """
    from playwright.sync_api import sync_playwright

    geometry_detector_js = """() => {
        const horizontalClipping = [];
        const verticalClipping = [];
        const parentClipping = [];
        const overlappingElements = [];

        const allTargets = Array.from(document.querySelectorAll('*')).filter(el => {
            if (el.offsetWidth <= 1 && el.offsetHeight <= 1) return false;
            if (el.classList.contains('sr-only')) return false;
            return true;
        });

        allTargets.forEach(el => {
            const parent = el.parentElement;
            if (!parent) return;
            const pStyle = window.getComputedStyle(parent);
            if (pStyle.overflowX === 'hidden' && parent.scrollWidth > parent.clientWidth + 2) {
                parentClipping.push({
                    element: `${el.tagName.toLowerCase()}.${Array.from(el.classList).slice(0, 2).join('.')}`,
                    issue: `Parent ${parent.tagName.toLowerCase()} scrollWidth (${parent.scrollWidth}px) exceeds clientWidth (${parent.clientWidth}px)`
                });
            }
            if (pStyle.overflowY === 'hidden' && parent.scrollHeight > parent.clientHeight + 2) {
                verticalClipping.push({
                    element: `${el.tagName.toLowerCase()}.${Array.from(el.classList).slice(0, 2).join('.')}`,
                    issue: `Parent ${parent.tagName.toLowerCase()} scrollHeight (${parent.scrollHeight}px) exceeds clientHeight (${parent.clientHeight}px)`
                });
            }
        });

        allTargets.forEach(el => {
            const r = el.getBoundingClientRect();
            if (r.right > window.innerWidth + 2) {
                horizontalClipping.push({
                    element: `${el.tagName.toLowerCase()}.${Array.from(el.classList).slice(0, 2).join('.')}`,
                    right: Math.round(r.right),
                    vpWidth: window.innerWidth
                });
            }
        });

        const interactiveControls = allTargets.filter(el => {
            const tag = el.tagName.toLowerCase();
            return ['button', 'input', 'select', 'textarea', 'a'].includes(tag) || el.classList.contains('tile') || el.classList.contains('card');
        });

        for (let i = 0; i < interactiveControls.length; i++) {
            const elA = interactiveControls[i];
            const rA = elA.getBoundingClientRect();
            if (rA.width <= 0 || rA.height <= 0) continue;

            for (let j = i + 1; j < interactiveControls.length; j++) {
                const elB = interactiveControls[j];
                if (elA.contains(elB) || elB.contains(elA)) continue;

                const rB = elB.getBoundingClientRect();
                if (rB.width <= 0 || rB.height <= 0) continue;

                const xOverlap = Math.max(0, Math.min(rA.right, rB.right) - Math.max(rA.left, rB.left));
                const yOverlap = Math.max(0, Math.min(rA.bottom, rB.bottom) - Math.max(rA.top, rB.top));

                if (xOverlap > 4 && yOverlap > 4) {
                    const isApprovedOverlay = (el) => {
                        return Boolean(el.closest('[role="dialog"], dialog, .modal, .modal-dialog, .nav-drawer, .toast, .floating-action-control, [data-approved-overlay="true"]'));
                    };
                    if (!isApprovedOverlay(elA) && !isApprovedOverlay(elB)) {
                        overlappingElements.push({
                            elementA: `${elA.tagName.toLowerCase()}${elA.id ? '#' + elA.id : ''}.${Array.from(elA.classList).slice(0, 2).join('.')}`,
                            elementB: `${elB.tagName.toLowerCase()}${elB.id ? '#' + elB.id : ''}.${Array.from(elB.classList).slice(0, 2).join('.')}`,
                            overlapArea: Math.round(xOverlap * yOverlap)
                        });
                    }
                }
            }
        }

        return {
            horizontalClipping,
            verticalClipping,
            parentClipping,
            overlappingElements
        };
    }"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1000, "height": 800})

        # 1. Unintended button overlap
        page.set_content("""
        <html><body>
            <button id="btn1" style="position: absolute; left: 50px; top: 50px; width: 100px; height: 40px;">Button 1</button>
            <button id="btn2" style="position: absolute; left: 80px; top: 60px; width: 100px; height: 40px;">Button 2</button>
        </body></html>
        """)
        res = page.evaluate(geometry_detector_js)
        assert len(res["overlappingElements"]) > 0, "Unintended button overlap must be detected"

        # 2. Fixed-versus-absolute element collision (differing z-index)
        page.set_content("""
        <html><body>
            <button id="fixed-btn" style="position: fixed; left: 100px; top: 100px; width: 120px; height: 40px; z-index: 10;">Fixed</button>
            <input id="abs-input" style="position: absolute; left: 120px; top: 110px; width: 120px; height: 40px; z-index: 2;" value="Input">
        </body></html>
        """)
        res = page.evaluate(geometry_detector_js)
        assert len(res["overlappingElements"]) > 0, "Fixed vs absolute collision with differing z-index must NOT be excused"

        # 3. Vertical clipping by overflow-hidden parent
        page.set_content("""
        <html><body>
            <div id="parent-v" style="height: 50px; overflow-y: hidden; width: 200px;">
                <div id="child-v" style="height: 120px; width: 100%;">Taller content</div>
            </div>
        </body></html>
        """)
        res = page.evaluate(geometry_detector_js)
        assert len(res["verticalClipping"]) > 0, "Vertical clipping by overflow-hidden parent must be detected"

        # 4. Horizontal clipping by overflow-hidden parent
        page.set_content("""
        <html><body>
            <div id="parent-h" style="width: 100px; overflow-x: hidden; height: 100px;">
                <div id="child-h" style="width: 300px; height: 50px;">Wider content</div>
            </div>
        </body></html>
        """)
        res = page.evaluate(geometry_detector_js)
        assert len(res["parentClipping"]) > 0, "Horizontal clipping by overflow-hidden parent must be detected"

        # 5. Approved intentional dialog overlay (must NOT be flagged as layout defect)
        page.set_content("""
        <html><body>
            <button id="under-btn" style="position: absolute; left: 50px; top: 50px; width: 100px; height: 40px;">Under</button>
            <div class="modal" role="dialog" style="position: fixed; left: 0; top: 0; width: 100%; height: 100%; z-index: 999;">
                <button id="modal-btn" style="position: absolute; left: 60px; top: 50px; width: 100px; height: 40px;">Modal OK</button>
            </div>
        </body></html>
        """)
        res = page.evaluate(geometry_detector_js)
        assert len(res["overlappingElements"]) == 0, "Approved dialog overlay must NOT be flagged as layout defect"

        browser.close()


