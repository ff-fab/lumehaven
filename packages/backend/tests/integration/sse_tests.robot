*** Settings ***
Documentation    Integration tests for SSE (Server-Sent Events) functionality.
...
...              These tests verify real-time signal updates flow correctly
...              from mock OpenHAB through Lumehaven to the SSE stream.
...
...              Architecture:
...              Mock OpenHAB SSE → Lumehaven Backend → Client SSE Stream
...
...              Synchronization Strategy:
...              1. Connect to SSE stream
...              2. Wait for Lumehaven to register the subscriber (/metrics check)
...              3. Trigger the event via mock OpenHAB
...              4. Poll for matching SSE event with timeout
...              This ensures no race conditions where events are missed.

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
    [Documentation]    Verify /api/events/signals SSE endpoint accepts connections.
    [Tags]    sse    smoke
    Connect SSE Stream    ${LUMEHAVEN_URL}/api/events/signals
    # Successfully connecting without error indicates endpoint is accessible


# =============================================================================
# Real-time Update Tests
# =============================================================================

Signal Update Propagates Through SSE
    [Documentation]    Verify signal state changes propagate through SSE stream.
    ...                Uses synchronization barrier to ensure subscriber is ready.
    [Tags]    sse    data-flow
    # Connect and wait for subscription to be registered
    Connect And Wait For SSE Subscription
    # Trigger update and wait for event
    ${event}=    Trigger And Wait For Signal Update    LivingRoom_Temperature    28.5
    # Verify event structure
    SSE Event Should Contain    event    signal
    SSE Event Data Should Contain Key    id    oh:LivingRoom_Temperature
    SSE Event Data Should Contain Key    value    28.5

Multiple Signal Updates Propagate Sequentially
    [Documentation]    Verify multiple signal updates arrive through SSE.
    [Tags]    sse    data-flow
    Connect And Wait For SSE Subscription
    # First update
    ${event1}=    Trigger And Wait For Signal Update    LivingRoom_Temperature    25.0
    Verify SSE Event Signal Value    ${event1}    25.0
    # Second update - using Bathroom_Humidity which exists in fixtures
    # Note: Value is formatted to 1 decimal place per item's pattern (%.1f %%)
    ${event2}=    Trigger And Wait For Signal Update    Bathroom_Humidity    65.0
    Verify SSE Event Signal Value    ${event2}    65.0

SSE Event Has Correct Format
    [Documentation]    Verify SSE events have expected signal data structure.
    [Tags]    sse    format
    Connect And Wait For SSE Subscription
    ${event}=    Trigger And Wait For Signal Update    LivingRoom_Temperature    22.0
    # Verify all required signal fields are present
    ${data}=    Get From Dictionary    ${event}    data
    Dictionary Should Contain Key    ${data}    id
    Dictionary Should Contain Key    ${data}    value
    Dictionary Should Contain Key    ${data}    unit
    Dictionary Should Contain Key    ${data}    label
