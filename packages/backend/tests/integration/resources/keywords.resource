*** Settings ***
Documentation    Common resources and keywords for integration tests.
...
...              This resource file provides shared variables, keywords,
...              and setup/teardown procedures for all integration tests.

Library          REST
Library          Collections
Library          ../libraries/ServerKeywords.py
Library          ../libraries/SSEKeywords.py


*** Variables ***
# Server URLs (ports defined here, used by keywords)
${MOCK_OPENHAB_PORT}       8081
${LUMEHAVEN_PORT}          8000
${MOCK_OPENHAB_URL}        http://localhost:${MOCK_OPENHAB_PORT}
${LUMEHAVEN_URL}           http://localhost:${LUMEHAVEN_PORT}

# Timeouts
${SERVER_STARTUP_TIMEOUT}    10
${REQUEST_TIMEOUT}           5


*** Keywords ***
# =============================================================================
# Suite Setup/Teardown
# =============================================================================

Start Integration Test Environment
    [Documentation]    Start mock OpenHAB and Lumehaven backend servers.
    ...                Called from Suite Setup.
    Start Mock OpenHAB Server    port=${MOCK_OPENHAB_PORT}
    Wait For Server Ready    ${MOCK_OPENHAB_URL}/rest/items    timeout=${SERVER_STARTUP_TIMEOUT}
    # Note: Lumehaven backend is not started by default as it depends on the test scenario
    # Tests that need the full backend should call Start Lumehaven Backend explicitly

Stop Integration Test Environment
    [Documentation]    Stop all servers. Called from Suite Teardown.
    Stop Lumehaven Backend
    Stop Mock OpenHAB Server

Start Full Backend Stack
    [Documentation]    Start both mock OpenHAB and Lumehaven backend.
    Start Mock OpenHAB Server    port=${MOCK_OPENHAB_PORT}
    Wait For Server Ready    ${MOCK_OPENHAB_URL}/rest/items    timeout=${SERVER_STARTUP_TIMEOUT}
    Start Lumehaven Backend    port=${LUMEHAVEN_PORT}
    Wait For Server Ready    ${LUMEHAVEN_URL}/health    timeout=${SERVER_STARTUP_TIMEOUT}


# =============================================================================
# Test Setup/Teardown
# =============================================================================

Reset Test State
    [Documentation]    Reset mock OpenHAB to default state before each test.
    Reset Mock OpenHAB State
    Clear Mock OpenHAB Failure


# =============================================================================
# API Request Keywords
# =============================================================================

GET Lumehaven
    [Documentation]    Make a GET request to Lumehaven backend.
    [Arguments]    ${endpoint}
    GET    ${LUMEHAVEN_URL}${endpoint}

GET Mock OpenHAB
    [Documentation]    Make a GET request to mock OpenHAB server.
    [Arguments]    ${endpoint}
    GET    ${MOCK_OPENHAB_URL}${endpoint}


# =============================================================================
# Assertion Keywords
# =============================================================================

Response Status Should Be
    [Documentation]    Verify HTTP response status code.
    [Arguments]    ${expected_status}
    Integer    response status    ${expected_status}

Response Should Contain Key
    [Documentation]    Verify response body contains a key.
    [Arguments]    ${key}
    ${body}=    Output    response body
    Dictionary Should Contain Key    ${body}    ${key}

Response Key Should Equal
    [Documentation]    Verify a response body key has expected value.
    [Arguments]    ${key}    ${expected_value}
    ${actual}=    Output    response body ${key}
    Should Be Equal As Strings    ${actual}    ${expected_value}

Response Should Be List With Length
    [Documentation]    Verify response body is a list with expected length.
    [Arguments]    ${expected_length}
    ${body}=    Output    response body
    ${length}=    Get Length    ${body}
    Should Be Equal As Integers    ${length}    ${expected_length}


# =============================================================================
# Signal-Specific Keywords
# =============================================================================

Signal Should Exist
    [Documentation]    Verify a signal exists in the signals list response.
    [Arguments]    ${signal_id}
    ${signals}=    Output    response body signals
    ${found}=    Set Variable    ${FALSE}
    FOR    ${signal}    IN    @{signals}
        IF    "${signal}[id]" == "${signal_id}"
            ${found}=    Set Variable    ${TRUE}
            BREAK
        END
    END
    Should Be True    ${found}    Signal '${signal_id}' not found in response

Signal Should Have Value
    [Documentation]    Verify a signal has the expected value.
    [Arguments]    ${signal_id}    ${expected_value}
    ${signals}=    Output    response body signals
    FOR    ${signal}    IN    @{signals}
        IF    "${signal}[id]" == "${signal_id}"
            Should Be Equal As Strings    ${signal}[value]    ${expected_value}
            RETURN
        END
    END
    Fail    Signal '${signal_id}' not found in response


# =============================================================================
# Health Check Keywords
# =============================================================================

Health Status Should Be
    [Documentation]    Verify health endpoint returns expected status.
    [Arguments]    ${expected_status}
    GET Lumehaven    /health
    Response Status Should Be    200
    Response Key Should Equal    status    ${expected_status}


# =============================================================================
# SSE Testing Keywords
# =============================================================================

Connect And Wait For SSE Subscription
    [Documentation]    Connect to SSE stream and wait until Lumehaven registers the subscriber.
    ...                This provides a synchronization barrier to prevent race conditions
    ...                where events are published before the subscriber is ready.
    [Arguments]    ${timeout}=${SERVER_STARTUP_TIMEOUT}
    Connect SSE Stream    ${LUMEHAVEN_URL}/api/events/signals
    Wait For Lumehaven SSE Subscribers    min_count=1    timeout=${timeout}    lumehaven_url=${LUMEHAVEN_URL}

Trigger And Wait For Signal Update
    [Documentation]    Trigger a signal update in mock OpenHAB and wait for it via SSE.
    ...                This keyword:
    ...                1. Sets the mock OpenHAB item state (triggers SSE chain)
    ...                2. Polls for SSE event with matching signal ID
    ...                3. Returns the received event for further assertions
    [Arguments]    ${item_name}    ${new_value}    ${timeout}=5
    Set Mock OpenHAB Item State    ${item_name}    ${new_value}
    ${event}=    Wait For SSE Event Matching    data.id    oh:${item_name}    timeout=${timeout}
    RETURN    ${event}

Verify SSE Event Signal Value
    [Documentation]    Verify an SSE event contains expected signal value.
    [Arguments]    ${event}    ${expected_value}
    ${data}=    Get From Dictionary    ${event}    data
    ${actual_value}=    Get From Dictionary    ${data}    value
    Should Be Equal As Strings    ${actual_value}    ${expected_value}
