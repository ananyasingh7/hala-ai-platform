# WHOOP API Deep Dive (Official Platform)

## 1) Overview
WHOOP's developer platform is built on OAuth 2.0 + REST APIs + webhooks. The primary API surface is the v2 REST API, with UUIDs for activities and webhooks. There is also a v1 -> v2 activity ID mapping endpoint to help migrate legacy IDs.

## 2) Authentication (OAuth 2.0)
WHOOP uses OAuth 2.0 authorization code flow.

Auth endpoints:
- Authorization URL: `https://api.prod.whoop.com/oauth/oauth2/auth`
- Token URL: `https://api.prod.whoop.com/oauth/oauth2/token`

Scopes (per API docs):
- `read:recovery`
- `read:cycles`
- `read:workout`
- `read:sleep`
- `read:profile`
- `read:body_measurement`

## 3) Base URL and endpoints (v2)
Base host for REST calls (as shown in the API docs):
- `https://api.prod.whoop.com/developer/v2/...`

User
- `GET /developer/v2/user/profile/basic`
- `GET /developer/v2/user/measurement/body`
- `DELETE /developer/v2/user/access` (deauthorize)

Cycles
- `GET /developer/v2/cycle`
- `GET /developer/v2/cycle/{cycleId}`

Sleep
- `GET /developer/v2/activity/sleep`
- `GET /developer/v2/activity/sleep/{sleepId}`
- `GET /developer/v2/cycle/{cycleId}/sleep`

Recovery
- `GET /developer/v2/recovery`
- `GET /developer/v2/cycle/{cycleId}/recovery`

Workouts
- `GET /developer/v2/activity/workout`
- `GET /developer/v2/activity/workout/{workoutId}`

Activity ID mapping (legacy)
- `GET /developer/v1/activity-mapping/{activityV1Id}`

## 4) What data you can get (key fields)
The API returns structured metrics; below are highlights from the official data models.

User Profile
- `user_id`, `email`, `first_name`, `last_name`

Body Measurements
- `height_meter`, `weight_kilogram`, `max_heart_rate`

Cycle
- `start`, `end`, `timezone_offset`, `score_state`
- `score`: `strain`, `kilojoule`, `average_heart_rate`, `max_heart_rate`

Sleep
- `start`, `end`, `timezone_offset`, `nap`, `score_state`
- `score.stage_summary`: total time in bed/awake/light/SWS/REM, `sleep_cycle_count`, `disturbance_count`
- `score.sleep_needed`: baseline + adjustments (sleep debt, recent strain, recent nap)
- `score.respiratory_rate`, `score.sleep_performance_percentage`, `score.sleep_consistency_percentage`, `score.sleep_efficiency_percentage`

Recovery
- `score_state`
- `score`: `recovery_score`, `resting_heart_rate`, `hrv_rmssd_milli`, `spo2_percentage`, `skin_temp_celsius`

Workout
- `start`, `end`, `timezone_offset`, `sport_name`, `score_state`
- `score`: `strain`, `average_heart_rate`, `max_heart_rate`, `kilojoule`, `percent_recorded`
- `score`: `distance_meter`, `altitude_gain_meter`, `altitude_change_meter`
- `score.zone_durations`: time in HR zones

## 5) Pagination and filters
Collection endpoints use:
- `limit` (<= 25)
- `start` and `end` time filters
- `nextToken` for pagination; responses include `next_token`

Most endpoints document `429` responses for rate limiting, but public docs do not list a specific quota.

## 6) Webhooks
WHOOP sends webhook events over HTTPS POST. Core event types include:
- `workout.updated`, `workout.deleted`
- `sleep.updated`, `sleep.deleted`
- `recovery.updated`, `recovery.deleted`

Webhook payload fields:
- `user_id`
- `id` (v2 UUID; v1 integer)
- `type`
- `trace_id`

Security:
- Headers: `X-WHOOP-Signature`, `X-WHOOP-Signature-Timestamp`
- Validation: HMAC-SHA256 over `timestamp + raw_body`, then base64-encode and compare to the signature header.

## 7) Versioning and migration notes
- v2 API launched 2025-07-01.
- v1 webhooks are no longer published.
- Activity ID mapping endpoint exists for v1 -> v2 migration.

## 8) Practical integration pattern
1. OAuth consent flow -> store tokens per user.
2. Use webhooks to learn *when* data changes.
3. On webhook, fetch the affected resource via the v2 REST endpoint.
4. Periodically reconcile via collection endpoints in case a webhook was missed.

## 9) Official source links
- API reference: https://developer.whoop.com/api/
- OAuth docs: https://developer.whoop.com/docs/developing/oauth
- User data models: https://developer.whoop.com/docs/developing/user-data/user
- Cycle data model: https://developer.whoop.com/docs/developing/user-data/cycle/
- Sleep data model: https://developer.whoop.com/docs/developing/user-data/sleep/
- Workout data model: https://developer.whoop.com/docs/developing/user-data/workout
- Recovery data model: https://developer.whoop.com/docs/developing/user-data/recovery/
- Webhooks: https://developer.whoop.com/docs/developing/webhooks/
- API changelog: https://developer.whoop.com/docs/api-changelog/
