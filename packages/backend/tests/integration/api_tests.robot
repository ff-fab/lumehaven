*** Settings ***
Documentation     Lumehaven Backend API Integration Tests
Library           Collections
Library           RequestsLibrary

*** Variables ***
${BASE_URL}       http://localhost:8000

*** Test Cases ***
Health Check Returns Status
    [Documentation]    Verify the health endpoint returns expected structure
    [Tags]    smoke
    Create Session    api    ${BASE_URL}
    ${response}=    GET On Session    api    /health
    Should Be Equal As Integers    ${response.status_code}    200
    Dictionary Should Contain Key    ${response.json()}    status
    Should Be Equal    ${response.json()}[status]    healthy

Get Signals Returns List
    [Documentation]    Verify the signals endpoint returns a list
    [Tags]    smoke
    Create Session    api    ${BASE_URL}
    ${response}=    GET On Session    api    /api/signals
    Should Be Equal As Integers    ${response.status_code}    200
    Dictionary Should Contain Key    ${response.json()}    signals
    Dictionary Should Contain Key    ${response.json()}    count

Get Unknown Signal Returns 404
    [Documentation]    Verify requesting unknown signal returns 404
    [Tags]    negative
    Create Session    api    ${BASE_URL}
    ${response}=    GET On Session    api    /api/signals/nonexistent    expected_status=404
    Should Be Equal As Integers    ${response.status_code}    404
