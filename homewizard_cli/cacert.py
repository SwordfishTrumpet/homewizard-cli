"""Bundled HomeWizard CA certificate for SSL verification."""

# The placeholder PEM previously shipped here was broken (truncated base64)
# and caused ``ssl.SSLError: no start line`` on EVERY default v2 connection
# (CRIT-1, live-verified). A production package should bundle the official
# HomeWizard "Appliance Access CA" chain here; until that is available the
# constant stays empty and verification relies on the system trust store
# plus the user override at ~/.config/homewizard-cli/homewizard-ca.pem.

HOMEWIZARD_CA_CERT = ""
