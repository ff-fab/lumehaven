#!/bin/bash
# Generate environment variables for docker-compose based on OS
# This is sourced by .env which is auto-loaded by docker-compose

# Detect OS and set SSH_DIR accordingly
case "$(uname -s)" in
  Darwin)
    # macOS
    SSH_DIR="${HOME}/.ssh"
    ;;
  Linux)
    # Check if running in WSL2
    if grep -qi microsoft /proc/version 2>/dev/null; then
      # Windows/WSL2 - use USERPROFILE which WSL2 sets
      SSH_DIR="${USERPROFILE}/.ssh"
    else
      # Native Linux
      SSH_DIR="${HOME}/.ssh"
    fi
    ;;
  MINGW*|MSYS*|CYGWIN*)
    # Windows/Git Bash
    SSH_DIR="${USERPROFILE}/.ssh"
    ;;
  *)
    # Default fallback to HOME
    SSH_DIR="${HOME}/.ssh"
    ;;
esac

# Export for docker-compose variable substitution
export SSH_DIR
