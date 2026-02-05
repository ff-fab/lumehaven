*** Settings ***
Documentation    Integration tests for Lumehaven REST API endpoints.
...
...              These tests verify the full vertical slice from API request
...              through to mock OpenHAB, ensuring proper data flow and
...              response formatting.
...
...              Test coverage:
...              - Health endpoint (/health)
...              - Signals list endpoint (/api/signals)
...              - Single signal endpoint (/api/signals/{id})
...              - Metrics endpoint (/metrics)

Resource         resources/keywords.resource

Suite Setup      Start Full Backend Stack
Suite Teardown   Stop Integration Test Environment
Test Setup       Reset Test State


*** Test Cases ***
# =============================================================================
# Health Endpoint Tests
# =============================================================================

Health Endpoint Returns Healthy Status
    [Documentation]    Verify /health returns healthy status when all systems operational.
    [Tags]    health    smoke
    GET Lumehaven    /health
    Response Status Should Be    200
    Response Should Contain Key    status
    Response Key Should Equal    status    healthy

Health Endpoint Contains Required Fields
    [Documentation]    Verify /health response contains all required fields.
    [Tags]    health    smoke
    GET Lumehaven    /health
    Response Status Should Be    200
    Response Should Contain Key    status
    Response Should Contain Key    adapter


# =============================================================================
# Signals List Endpoint Tests
# =============================================================================

Signals List Returns All Items
    [Documentation]    Verify /api/signals returns all items from OpenHAB.
    [Tags]    signals    smoke
    GET Lumehaven    /api/signals
    Response Status Should Be    200
    Response Should Contain Key    signals
    # Verify we get signals from mock OpenHAB (DASHBOARD_ITEMS has 2 items)
    ${signals}=    Output    response body signals
    ${length}=    Get Length    ${signals}
    Should Be True    ${length} >= 2    Expected at least 2 signals, got ${length}

Signals List Contains Expected Signal IDs
    [Documentation]    Verify signals list contains expected signal IDs from fixtures.
    [Tags]    signals    smoke
    GET Lumehaven    /api/signals
    Response Status Should Be    200
    Signal Should Exist    LivingRoom_Temperature
    Signal Should Exist    LivingRoom_Humidity

Signal Has Required Fields
    [Documentation]    Verify each signal has required fields (id, value, unit, label).
    [Tags]    signals    smoke
    GET Lumehaven    /api/signals
    Response Status Should Be    200
    ${signals}=    Output    response body signals
    FOR    ${signal}    IN    @{signals}
        Dictionary Should Contain Key    ${signal}    id
        Dictionary Should Contain Key    ${signal}    value
        Dictionary Should Contain Key    ${signal}    unit
        Dictionary Should Contain Key    ${signal}    label
    END


# =============================================================================
# Single Signal Endpoint Tests
# =============================================================================

Get Single Signal By ID
    [Documentation]    Verify /api/signals/{id} returns correct signal.
    [Tags]    signals    smoke
    GET Lumehaven    /api/signals/LivingRoom_Temperature
    Response Status Should Be    200
    Response Key Should Equal    id    LivingRoom_Temperature

Single Signal Has Correct Value
    [Documentation]    Verify single signal endpoint returns correct value from OpenHAB.
    [Tags]    signals    smoke
    GET Lumehaven    /api/signals/LivingRoom_Temperature
    Response Status Should Be    200
    # Temperature from fixtures is 21.5
    Response Key Should Equal    value    21.5

Non-Existent Signal Returns 404
    [Documentation]    Verify non-existent signal returns 404 error.
    [Tags]    signals    error
    GET Lumehaven    /api/signals/NonExistent_Signal
    Response Status Should Be    404


# =============================================================================
# Metrics Endpoint Tests
# =============================================================================

Metrics Endpoint Returns Prometheus Format
    [Documentation]    Verify /metrics returns Prometheus-formatted metrics.
    [Tags]    metrics    smoke
    GET Lumehaven    /metrics
    Response Status Should Be    200
    # Prometheus metrics are text/plain, check we get a response
    ${body}=    Output    response body
    Should Not Be Empty    ${body}


# =============================================================================
# Data Flow Tests
# =============================================================================

Signal Value Reflects Mock OpenHAB State
    [Documentation]    Verify changing mock OpenHAB state is reflected in API response.
    [Tags]    signals    data-flow
    # First get initial value
    GET Lumehaven    /api/signals/LivingRoom_Temperature
    Response Status Should Be    200
    Response Key Should Equal    value    21.5
    # Update mock OpenHAB state
    Set Mock OpenHAB Item State    LivingRoom_Temperature    25.0
    # Verify Lumehaven returns updated value
    GET Lumehaven    /api/signals/LivingRoom_Temperature
    Response Status Should Be    200
    Response Key Should Equal    value    25.0
