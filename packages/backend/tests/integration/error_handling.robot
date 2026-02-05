*** Settings ***
Documentation    Integration tests for error handling scenarios.
...
...              These tests verify Lumehaven handles failures gracefully:
...              - OpenHAB connection failures
...              - OpenHAB returning errors
...              - Invalid requests
...              - Degraded health states

Resource         resources/keywords.resource

Suite Setup      Start Full Backend Stack
Suite Teardown   Stop Integration Test Environment
Test Setup       Reset Test State


*** Test Cases ***
# =============================================================================
# OpenHAB Failure Scenarios
# =============================================================================

Health Degrades When OpenHAB Returns Error
    [Documentation]    Verify health status degrades when OpenHAB returns errors.
    [Tags]    error    health
    # Configure mock OpenHAB to return 500 errors
    Configure Mock OpenHAB Failure    status_code=500
    # Health should indicate degraded state
    GET Lumehaven    /health
    Response Status Should Be    200
    # Status may be degraded or unhealthy depending on implementation
    ${body}=    Output    response body
    ${status}=    Get From Dictionary    ${body}    status
    Should Not Be Equal    ${status}    healthy

Health Returns To Healthy After Recovery
    [Documentation]    Verify health returns to healthy when OpenHAB recovers.
    [Tags]    error    health
    # First degrade by causing errors
    Configure Mock OpenHAB Failure    status_code=500
    GET Lumehaven    /health
    # Clear the failure
    Clear Mock OpenHAB Failure
    # Health should recover
    GET Lumehaven    /health
    Response Status Should Be    200
    Response Key Should Equal    status    healthy


# =============================================================================
# API Error Responses
# =============================================================================

Non-Existent Signal Returns 404
    [Documentation]    Verify requesting non-existent signal returns 404.
    [Tags]    error    signals
    GET Lumehaven    /api/signals/Signal_That_Does_Not_Exist
    Response Status Should Be    404

Invalid Endpoint Returns 404
    [Documentation]    Verify invalid endpoints return 404.
    [Tags]    error    api
    GET Lumehaven    /api/invalid/endpoint
    Response Status Should Be    404


# =============================================================================
# Timeout and Connection Scenarios
# =============================================================================

Signals Endpoint Handles OpenHAB Timeout
    [Documentation]    Verify signals endpoint handles OpenHAB timeout gracefully.
    [Tags]    error    timeout
    # Configure mock to simulate timeout (very slow response)
    Configure Mock OpenHAB Failure    timeout=30
    # Request should fail gracefully (connection error or timeout)
    # Note: This may return 500 or 503 depending on implementation
    GET Lumehaven    /api/signals
    ${status}=    Output    response status
    Should Be True    ${status} >= 500    Expected server error status, got ${status}


# =============================================================================
# Data Integrity Tests
# =============================================================================

Malformed OpenHAB Response Handled Gracefully
    [Documentation]    Verify malformed OpenHAB data doesn't crash the backend.
    [Tags]    error    data
    # Configure mock to return malformed JSON
    Configure Mock OpenHAB Failure    malformed=True
    # Request should handle gracefully
    GET Lumehaven    /api/signals
    ${status}=    Output    response status
    # Should return error, not crash
    Should Be True    ${status} >= 400    Expected error status, got ${status}
