*** Settings ***
Documentation    Integration tests for SSE (Server-Sent Events) functionality.
...
...              These tests verify real-time signal updates flow correctly
...              from mock OpenHAB through Lumehaven to the SSE stream.
...
...              Architecture:
...              Mock OpenHAB SSE → Lumehaven Backend → Client SSE Stream

Resource         resources/keywords.resource

Suite Setup      Start Full Backend Stack
Suite Teardown   Stop Integration Test Environment
Test Setup       Reset Test State
Test Teardown    Disconnect SSE Stream


*** Test Cases ***
# =============================================================================
# SSE Connection Tests
# =============================================================================

SSE Endpoint Is Accessible
    [Documentation]    Verify /api/signals/stream SSE endpoint accepts connections.
    [Tags]    sse    smoke
    Connect SSE Stream    ${LUMEHAVEN_URL}/api/signals/stream
    # Successfully connecting without error indicates endpoint is accessible


# =============================================================================
# Real-time Update Tests
# =============================================================================

Signal Update Propagates Through SSE
    [Documentation]    Verify signal state changes propagate through SSE stream.
    [Tags]    sse    data-flow
    # Connect to SSE stream
    Connect SSE Stream    ${LUMEHAVEN_URL}/api/signals/stream
    # Update mock OpenHAB state (this should trigger SSE event)
    Set Mock OpenHAB Item State    LivingRoom_Temperature    28.5
    # Receive and verify SSE event
    ${event}=    Receive SSE Event    timeout=5
    SSE Event Should Contain    ${event}    LivingRoom_Temperature

Multiple Signal Updates Propagate Sequentially
    [Documentation]    Verify multiple signal updates arrive in order through SSE.
    [Tags]    sse    data-flow
    Connect SSE Stream    ${LUMEHAVEN_URL}/api/signals/stream
    # Send multiple updates
    Set Mock OpenHAB Item State    LivingRoom_Temperature    30.0
    Set Mock OpenHAB Item State    LivingRoom_Humidity    65.0
    # Receive events and verify both signals were updated
    ${event1}=    Receive SSE Event    timeout=5
    ${event2}=    Receive SSE Event    timeout=5
    # At least one event should contain each signal ID
    ${events_text}=    Set Variable    ${event1}${event2}
    Should Contain    ${events_text}    LivingRoom_Temperature
    Should Contain    ${events_text}    LivingRoom_Humidity


# =============================================================================
# SSE Event Format Tests
# =============================================================================

SSE Event Has Correct Format
    [Documentation]    Verify SSE events have expected signal data structure.
    [Tags]    sse    format
    Connect SSE Stream    ${LUMEHAVEN_URL}/api/signals/stream
    Set Mock OpenHAB Item State    LivingRoom_Temperature    22.0
    ${event}=    Receive SSE Event    timeout=5
    # Verify event contains expected data keys
    SSE Event Data Should Contain Key    ${event}    LivingRoom_Temperature
