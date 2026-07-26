"""In-process assembly of Vertex service-account credentials.

Secrets never touch disk or logs here. The nine non-secret fields come from
``vertex-creds-minimal.json``; the private key (and, optionally, its id) are
read from the environment at runtime and merged into the credential info in
memory only:

    GCP_SA_PRIVATE_KEY      the PEM private key (literal ``\\n`` are un-escaped)
    GCP_SA_PRIVATE_KEY_ID   the key id (recommended; used as the JWT 'kid')

Nothing in this module prints or returns the secret material.
"""
import os
import json
from google.oauth2 import service_account

LOCATION = "us-east5"
_MINIMAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "vertex-creds-minimal.json")
_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)


def load_credentials(minimal_path: str = _MINIMAL_PATH):
    """Return ``(credentials, project_id)``.

    Raises RuntimeError if the private-key env var is absent so the failure is
    obvious rather than surfacing later as an opaque auth error.
    """
    with open(minimal_path) as f:
        info = json.load(f)  # non-secret fields only

    private_key = os.environ.get("GCP_SA_PRIVATE_KEY")
    if not private_key:
        raise RuntimeError(
            "GCP_SA_PRIVATE_KEY is not set. Export the service-account private key "
            "(and ideally GCP_SA_PRIVATE_KEY_ID) in the environment; they are merged "
            "in-process and never written to disk or logged."
        )
    # Env vars typically carry the PEM with literal backslash-n; restore real newlines.
    info["private_key"] = private_key.replace("\\n", "\n")
    key_id = os.environ.get("GCP_SA_PRIVATE_KEY_ID")
    if key_id:
        info["private_key_id"] = key_id

    creds = service_account.Credentials.from_service_account_info(info, scopes=list(_SCOPES))
    return creds, info["project_id"]
