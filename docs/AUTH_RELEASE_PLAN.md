# Auth Modernization Release Plan

## Summary

- Ship the auth modernization as three complete releases: `v1.2.0`, `v1.3.0`,
  and `v2.0.0`.
- Each tag must have a GitHub Release because every tag represents a usable
  functional version.
- The first execution step records this plan, then implements and releases
  `v1.2.0`.
- Later tags must include cleanup for older auth modes as described below.

## v1.2.0 - JWT as the primary production mode

- Make JWT the default mode: `AUTH_REQUIRED=true` in application settings and
  `.env.example`.
- Keep `.env.test` explicitly in legacy mode for compatibility tests.
- Require `Authorization: Bearer <access_token>` for parcel endpoints by default.
- Keep `X-Session-Id` only as a deprecated fallback when `AUTH_REQUIRED=false`.
- Add deprecation warnings for legacy mode:
  - startup log warning;
  - `Deprecation: true` response header;
  - `Sunset` response header on responses that include `X-Session-Id`.
- Update OpenAPI and documentation so examples register or log in first, then
  call parcel endpoints with a Bearer token.
- Synchronize release metadata through a single application version source:
  `app/version.py`, `pyproject.toml`, FastAPI metadata, and Sentry release.

## v1.3.0 - Stronger JWT and refresh rotation

- Add refresh tokens through an HTTP-only cookie.
- Pair refresh tokens with a readable CSRF cookie and require
  `X-CSRF-Token` for `/auth/refresh` and `/auth/logout`.
- Keep access tokens in JSON responses from `/auth/register` and `/auth/login`.
- Add endpoints:
  - `POST /auth/refresh`;
  - `POST /auth/logout`;
  - `POST /auth/logout-all`.
- Add a refresh token table with `jti`, `user_id`, `token_hash`, `family_id`,
  `expires_at`, `revoked_at`, `replaced_by_jti`, and timestamps.
- Rotate refresh tokens on every refresh request.
- Treat reuse of a revoked refresh token as compromise and revoke the whole
  token family.
- Extend access token claims to include `sub`, `exp`, `iat`, `nbf`, `jti`,
  `iss`, `aud`, `role`, and `scope`.
- Validate issuer and audience on every access token decode.
- Add user roles with default role `user`.
- Add minimum scopes: `parcels:read` and `parcels:write`.
- Fail startup in production when `JWT_SECRET_KEY` is default or too short.
- Move legacy `X-Session-Id` documentation into migration/deprecation notes.
- Preserve the v1.2.0 compatibility-test shape:
  - unit parcel-service tests stay in legacy mode by default;
  - new JWT-mode service tests must opt into `AUTH_REQUIRED=true`;
  - integration `auth_context` keeps the session-scoped event loop and reads
    user IDs from typed JWT claims.
- Update integration cleanup order to delete `refresh_token`, then `parcel`,
  then `user` so foreign-key constraints remain satisfied.
- Keep `/parcel-types` public and `/tasks/*` protected by `X-Admin-Token`.

## v2.0.0 - Dedicated OAuth2.1/OIDC auth server

- Add a separate `auth-server` service in `docker-compose.yml`.
- Keep the auth server in this repository, but run it as a separate FastAPI
  application/service.
- Make the parcel API a resource server only.
- Move ownership of users, passwords, refresh tokens, clients, authorization
  codes, and JWKS to the auth server.
- Support first-party clients through a static client registry.
- Implement Authorization Code + PKCE.
- Add OIDC discovery and token infrastructure:
  - `/.well-known/openid-configuration`;
  - `/oauth/authorize`;
  - `/oauth/token`;
  - `/oauth/revoke`;
  - `/oauth/jwks.json`.
- Remove local password token issuing from the parcel API.
- Make the parcel API verify access tokens through JWKS, issuer, audience, and
  scopes.
- Remove runtime legacy session support:
  - `X-Session-Id` middleware;
  - OpenAPI `SessionAuth`;
  - `AUTH_REQUIRED`;
  - legacy docs and tests.
- Because anonymous parcel migration is intentionally out of scope, release
  notes must clearly state the breaking data behavior.
- The v2.0 migration must either delete or archive anonymous-only parcels before
  removing legacy ownership and making `parcel.user_id` mandatory.

## Release and test requirements

- For every tag, run:
  - unit tests;
  - integration tests;
  - Ruff format check;
  - Ruff lint;
  - mypy;
  - Bandit;
  - coverage gate;
  - Docker build.
- `v1.2.0` acceptance:
  - JWT-required parcel flow works;
  - legacy fallback works when `AUTH_REQUIRED=false`;
  - OpenAPI uses Bearer auth by default;
  - legacy responses include deprecation headers.
- `v1.3.0` acceptance:
  - refresh rotation works;
  - refresh reuse detection works;
  - logout and logout-all revoke refresh tokens;
  - expired/revoked tokens are rejected;
  - issuer, audience, and scope validation are enforced;
  - production startup rejects weak JWT secrets.
- `v2.0.0` acceptance:
  - OIDC discovery and JWKS are available;
  - PKCE code flow works for first-party clients;
  - parcel API verifies resource-server JWTs;
  - scope enforcement works;
  - legacy session behavior is absent.
- After each successful release step:
  - commit the release changes;
  - push `master`;
  - create an annotated tag;
  - push the tag;
  - create a GitHub Release with changelog and migration notes.
