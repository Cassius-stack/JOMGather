1. Data Integrity & Validation
Schema Enforcement: Every incoming action or payload must be validated against a strict JSON schema before processing. Reject any action containing unrecognized keys or malformed data types.

Sanitization: All string inputs must be stripped of executable code, script tags, and hidden control characters.

Type Safety: Coerce inputs into expected types (integers, booleans, UUIDs) immediately upon receipt to prevent "type juggling" exploits.

2. Database & Persistence Security
Row-Level Security (RLS): Every database query must be scoped to the authenticated user_id or org_id. The agent is strictly forbidden from querying tables without an explicit RLS filter in the WHERE clause.

Parameterized Queries Only: Use prepared statements for all database interactions. Direct string concatenation in SQL is a critical failure.

Principle of Least Privilege: The agent’s database credentials must only have permissions for the specific tables and actions (SELECT, INSERT, UPDATE) required for its current scope.

3. Execution & Rate Guardrails
Action Rate Limiting: Implement a sliding window rate limit (e.g., 10 actions per minute per user). If the limit is exceeded, return a 429 Too Many Requests error and log the event.

State Verification: Before executing a "Write" action, verify that the current state of the system allows it (e.g., don't "Delete" a file that is already marked as "Processing").

Circuit Breakers: If an external API dependency fails three times consecutively, the agent must pause all related actions for 60 seconds to prevent cascading failures.

4. Privacy & Compliance
PII Masking: Never log Personally Identifiable Information (PII) to standard output or third-party monitoring tools. Use hashing or masking for sensitive identifiers.

Audit Logging: Every state-changing action must generate an immutable audit log entry containing: timestamp, actor_id, action_type, and status.

5. Error Handling
Fail-Safe Defaults: If a permission check or validation step encounters an error, the default response must be "Access Denied."

Obfuscated Errors: Do not return raw stack traces or database error messages to the end-user. Return generic error codes (e.g., ERR_AUTH_001) while logging the full detail internally.