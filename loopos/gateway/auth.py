"""Mock Gateway authentication and allowlist enforcement."""

from __future__ import annotations

from loopos.gateway.models import GatewayAuthResult, GatewayChannel


class GatewayAuthPolicy:
    def __init__(
        self,
        *,
        allowlists: dict[GatewayChannel, set[str]] | None = None,
        tokens: dict[GatewayChannel, str] | None = None,
    ) -> None:
        self.allowlists = allowlists or {}
        self.tokens = tokens or {}

    def authorize(
        self,
        channel: GatewayChannel,
        user_id: str,
        *,
        token: str | None = None,
    ) -> GatewayAuthResult:
        allowed_users = self.allowlists.get(channel)
        if allowed_users is not None and user_id not in allowed_users:
            return GatewayAuthResult(
                channel=channel,
                user_id=user_id,
                allowed=False,
                reason_code="gateway.user_not_allowlisted",
            )
        expected = self.tokens.get(channel)
        if expected is not None and token != expected:
            return GatewayAuthResult(
                channel=channel,
                user_id=user_id,
                allowed=False,
                reason_code="gateway.invalid_token",
            )
        return GatewayAuthResult(
            channel=channel,
            user_id=user_id,
            allowed=True,
            reason_code="gateway.authenticated",
        )
