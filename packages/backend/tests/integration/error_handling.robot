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

# NOTE: Health degradation tests are tricky because Lumehaven connects to
# OpenHAB at startup. To test degraded states properly, we would need to
# either restart the backend with mock in failed state, or wait for the
# SSE reconnection logic to detect the failure.

Health Shows Adapter Status
    [Documentation]    Verify health endpoint shows adapter connection status.
    [Tags]    health    smoke
    GET Lumehaven    /health
    Response Status Should Be    200
    # Verify adapters array contains our OpenHAB adapter
    ${body}=    Output    response body
    ${adapters}=    Get From Dictionary    ${body}    adapters
    ${length}=    Get Length    ${adapters}
    Should Be True    ${length} > 0    Expected at least one adapter
    # First adapter should be OpenHAB
    ${adapter}=    Get From List    ${adapters}    0
    ${type}=    Get From Dictionary    ${adapter}    type
    Should Be Equal    ${type}    openhab

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

# NOTE: The following tests are commented out because they test scenarios
# that don't match the Lumehaven architecture. Lumehaven caches signals at
# startup and updates them via SSE. Once signals are loaded, the backend
# returns cached data regardless of the mock's current state.
#
# To properly test these scenarios, we would need to:
# 1. Start the backend with the mock already in a failed state
# 2. Test SSE reconnection behavior (covered in sse_tests.robot)

# Signals Endpoint Handles OpenHAB Timeout
#     [Documentation]    Verify signals endpoint handles OpenHAB timeout gracefully.
#     [Tags]    error    timeout
#     # Configure mock to simulate timeout (very slow response)
#     Configure Mock OpenHAB Failure    timeout=30
#     # Request should fail gracefully (connection error or timeout)
#     # Note: This may return 500 or 503 depending on implementation
#     GET Lumehaven    /api/signals
#     ${status}=    Output    response status
#     Should Be True    ${status} >= 500    Expected server error status, got ${status}


# =============================================================================
# Data Integrity Tests
# =============================================================================

# Malformed OpenHAB Response Handled Gracefully
#     [Documentation]    Verify malformed OpenHAB data doesn't crash the backend.
#     [Tags]    error    data
#     # Configure mock to return malformed JSON
#     Configure Mock OpenHAB Failure    malformed=True
#     # Request should handle gracefully
#     GET Lumehaven    /api/signals
#     ${status}=    Output    response status
#     # Should return error, not crash
#     Should Be True    ${status} >= 400    Expected error status, got ${status}
