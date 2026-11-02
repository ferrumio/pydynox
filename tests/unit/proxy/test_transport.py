"""Proxy routing and timeout regression tests through the public Python API."""

import pytest

_ROLE = "arn:aws:iam::123456789012:role/AppRole"


@pytest.mark.parametrize("mode", ["async", "sync"])
@pytest.mark.parametrize("timeout_name", ["connect_timeout", "read_timeout"])
@pytest.mark.parametrize("timeout", [0.05, 2.0], ids=["expires", "completes"])
def test_proxy_preserves_timeouts(proxy_server, proxy_client, mode, timeout_name, timeout):
    # GIVEN a proxy that delays connection setup or the service response
    delay_name = "connect_delay" if timeout_name == "connect_timeout" else "read_delay"
    proxy, targets, _ = proxy_server(**{delay_name: 0.3})

    # WHEN a real client sends a request with a shorter or longer timeout
    response = proxy_client([proxy], mode, **{timeout_name: timeout})

    # THEN the configured limit controls whether the request succeeds
    assert targets == ["dynamodb.invalid:443"]
    if timeout < 0.3:
        assert response.get("error") == "ConnectionException", response
        assert "timed out" in response["message"].lower()
    else:
        assert response == {"items": [{"pk": "example"}]}


@pytest.mark.parametrize("mode", ["async", "sync"])
@pytest.mark.parametrize(
    "options,source_keys",
    [
        pytest.param({"role_arn": _ROLE}, ["ENVKEY"], id="role-with-env"),
        pytest.param(
            {"role_arn": _ROLE, "profile": "source"}, ["SOURCEKEY"], id="role-with-profile"
        ),
        pytest.param({"profile": "chained"}, ["SOURCEKEY"], id="profile-role"),
        pytest.param(
            {"role_arn": _ROLE, "profile": "chained"},
            ["SOURCEKEY", "ASSUMEDKEY"],
            id="chained-profile-and-role",
        ),
    ],
)
def test_proxy_routes_credential_requests(proxy_server, proxy_client, mode, options, source_keys):
    # GIVEN STS and DynamoDB endpoints that are reachable only through this proxy
    proxy, targets, calls = proxy_server()

    # WHEN credentials come from an explicit role or a role configured in a profile
    response = proxy_client([proxy], mode, **options)

    # THEN every STS request uses this proxy and the expected source identity
    assert response == {"items": [{"pk": "example"}]}, (response, targets, calls)
    assert targets.count("sts.invalid:443") >= 1
    assert "dynamodb.invalid:443" in targets
    assert [call["service"] for call in calls] == ["sts"] * len(source_keys) + ["dynamodb"]
    for call, key in zip(calls, [*source_keys, "ASSUMEDKEY"], strict=True):
        assert f"Credential={key}/" in call["authorization"]
    assert calls[-1]["token"] == "assumed-token"


@pytest.mark.parametrize("mode", ["async", "sync"])
def test_concurrent_clients_keep_separate_proxies(proxy_server, proxy_client, mode):
    # GIVEN two clients with their own proxy
    proxies = [proxy_server(), proxy_server()]

    # WHEN both clients send requests concurrently
    response = proxy_client([proxy[0] for proxy in proxies], mode)

    # THEN each proxy receives exactly its client's request
    assert response == {"items": [{"pk": "example"}, {"pk": "example"}]}
    for _, targets, calls in proxies:
        assert targets == ["dynamodb.invalid:443"]
        assert len(calls) == 1
        assert calls[0]["service"] == "dynamodb"
