"""Error codes and messages.

These constants define machine-readable error codes and human-readable
messages used throughout the application.
"""

# Authentication errors
AUTHENTICATION_REQUIRED = "authentication_required"
INVALID_CREDENTIALS = "invalid_credentials"
TOKEN_EXPIRED = "token_expired"
TOKEN_INVALID = "token_invalid"
UNAUTHORIZED = "unauthorized"

# Authorization errors
FORBIDDEN = "forbidden"
INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
WORKSPACE_ACCESS_DENIED = "workspace_access_denied"
PROJECT_ACCESS_DENIED = "project_access_denied"

# Resource errors
NOT_FOUND = "not_found"
RESOURCE_NOT_FOUND = "resource_not_found"
USER_NOT_FOUND = "user_not_found"
WORKSPACE_NOT_FOUND = "workspace_not_found"
PROJECT_NOT_FOUND = "project_not_found"
OPPORTUNITY_NOT_FOUND = "opportunity_not_found"
DRAFT_NOT_FOUND = "draft_not_found"
PERSONA_NOT_FOUND = "persona_not_found"
KEYWORD_NOT_FOUND = "keyword_not_found"
SUBREDDIT_NOT_FOUND = "subreddit_not_found"

# Validation errors
VALIDATION_ERROR = "validation_error"
INVALID_INPUT = "invalid_input"
INVALID_EMAIL = "invalid_email"
INVALID_SLUG = "invalid_slug"
INVALID_URL = "invalid_url"
MISSING_REQUIRED_FIELD = "missing_required_field"
FIELD_TOO_LONG = "field_too_long"
FIELD_TOO_SHORT = "field_too_short"

# Conflict errors
CONFLICT = "conflict"
RESOURCE_EXISTS = "resource_exists"
DUPLICATE_EMAIL = "duplicate_email"
DUPLICATE_SLUG = "duplicate_slug"
DUPLICATE_USERNAME = "duplicate_username"

# Business rule errors
BUSINESS_RULE_ERROR = "business_rule_error"
INVALID_TRANSITION = "invalid_transition"
QUOTA_EXCEEDED = "quota_exceeded"
LIMIT_REACHED = "limit_reached"
SUBSCRIPTION_REQUIRED = "subscription_required"
PLAN_UPGRADE_REQUIRED = "plan_upgrade_required"

# Rate limiting errors
RATE_LIMITED = "rate_limited"
TOO_MANY_REQUESTS = "too_many_requests"
SCAN_RATE_LIMIT_EXCEEDED = "scan_rate_limit_exceeded"
GENERATE_RATE_LIMIT_EXCEEDED = "generate_rate_limit_exceeded"

# Service errors
SERVICE_UNAVAILABLE = "service_unavailable"
EXTERNAL_SERVICE_ERROR = "external_service_error"
LLM_SERVICE_ERROR = "llm_service_error"
LLM_PROVIDER_UNAVAILABLE = "llm_provider_unavailable"
DATABASE_ERROR = "database_error"
EMAIL_SEND_FAILED = "email_send_failed"
WEBHOOK_DELIVERY_FAILED = "webhook_delivery_failed"

# Scan errors
SCAN_FAILED = "scan_failed"
SCAN_TIMEOUT = "scan_timeout"
NO_KEYWORDS_CONFIGURED = "no_keywords_configured"
NO_SUBREDDITS_CONFIGURED = "no_subreddits_configured"

# Content generation errors
GENERATION_FAILED = "generation_failed"
GENERATION_TIMEOUT = "generation_timeout"
INVALID_PERSONA = "invalid_persona"
INVALID_PROMPT = "invalid_prompt"

# Invitation errors
INVITATION_EXPIRED = "invitation_expired"
INVITATION_NOT_FOUND = "invitation_not_found"
INVITATION_ALREADY_ACCEPTED = "invitation_already_accepted"
INVITATION_EMAIL_MISMATCH = "invitation_email_mismatch"

# Subscription errors
SUBSCRIPTION_NOT_FOUND = "subscription_not_found"
SUBSCRIPTION_ALREADY_ACTIVE = "subscription_already_active"
SUBSCRIPTION_CANCELLED = "subscription_cancelled"
PAYMENT_FAILED = "payment_failed"
INVALID_PLAN = "invalid_plan"

# Webhook errors
WEBHOOK_NOT_FOUND = "webhook_not_found"
WEBHOOK_INVALID_URL = "webhook_invalid_url"
WEBHOOK_SECRET_REQUIRED = "webhook_secret_required"

# Integration errors
INTEGRATION_NOT_FOUND = "integration_not_found"
INTEGRATION_NOT_CONFIGURED = "integration_not_configured"
INTEGRATION_AUTH_FAILED = "integration_auth_failed"
REDDIT_ACCOUNT_NOT_CONNECTED = "reddit_account_not_connected"

# Error messages (human-readable)
ERROR_MESSAGES = {
    AUTHENTICATION_REQUIRED: "Authentication is required to access this resource.",
    INVALID_CREDENTIALS: "Invalid email or password.",
    TOKEN_EXPIRED: "Your session has expired. Please log in again.",
    TOKEN_INVALID: "Invalid authentication token.",
    UNAUTHORIZED: "You are not authorized to perform this action.",
    FORBIDDEN: "You do not have permission to access this resource.",
    NOT_FOUND: "The requested resource was not found.",
    VALIDATION_ERROR: "The request contains invalid data.",
    CONFLICT: "A conflict occurred while processing your request.",
    BUSINESS_RULE_ERROR: "This operation violates a business rule.",
    RATE_LIMITED: "Too many requests. Please try again later.",
    SERVICE_UNAVAILABLE: "The service is temporarily unavailable.",
    SCAN_FAILED: "Failed to scan Reddit. Please try again.",
    GENERATION_FAILED: "Failed to generate content. Please try again.",
    QUOTA_EXCEEDED: "You have exceeded your quota for this period.",
    LIMIT_REACHED: "You have reached the maximum limit for this resource.",
}
