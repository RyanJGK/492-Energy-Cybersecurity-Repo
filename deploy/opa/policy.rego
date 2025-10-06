package control

# Default deny
default allow = false

# Allowed actions list is sourced from data.config.allowed_actions
allowed_actions := data.config.allowed_actions

# Permit only if requested action is explicitly allowed
allow {
  action := input.action
  action != null
  action in allowed_actions
}
