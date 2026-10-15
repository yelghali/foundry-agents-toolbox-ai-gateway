"""Register the real C OAuth callback and produce a validated Windows consent shortcut."""

import json
import argparse
import base64
import webbrowser
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import requests

import common as cm


def microsoft_consent(url: str):
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or not parts.hostname.endswith(
        (".consent.azure-apim.net", ".consent.azure-apihub.net")
    ):
        raise RuntimeError("Unexpected Microsoft consent endpoint.")
    return parts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    config = cm.load_config()
    cohort = next(item for item in config["cohorts"] if item["label"] == "c")
    oauth = cohort["oauthFallback"]
    consent = json.loads((cm.ROOT / ".oauth-consent.json").read_text())
    link = consent["consent_link"]
    source = microsoft_consent(link)
    encoded = parse_qs(source.query)["data"][0]
    envelope = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    expiry = datetime.fromisoformat(envelope["ExpirationTime"].replace("Z", "+00:00"))
    if expiry <= datetime.now(timezone.utc) + timedelta(minutes=1):
        raise RuntimeError("The consent challenge has expired or is about to expire; request a fresh one.")
    response = requests.get(link, allow_redirects=False, timeout=60)
    if response.status_code not in (302, 303):
        raise RuntimeError(f"Expected a Microsoft consent redirect, received HTTP {response.status_code}.")
    location = urlsplit(response.headers["Location"])
    if location.scheme != "https" or location.hostname != "login.microsoftonline.com":
        raise RuntimeError("The consent link did not redirect to Entra.")
    parameters = parse_qs(location.query)
    if parameters["client_id"] != [oauth["clientId"]]:
        raise RuntimeError("The consent redirect uses a different application.")
    if oauth["scope"] not in parameters.get("scope", [""])[0].split():
        raise RuntimeError("The authorization request is missing the configured Search delegated scope.")
    callback = parameters["redirect_uri"][0]
    microsoft_consent(callback)
    headers = {"Authorization": "Bearer " + cm.credential(config).get_token("https://graph.microsoft.com/.default").token}
    app_url = f"https://graph.microsoft.com/v1.0/applications/{oauth['applicationId']}"
    app = requests.get(app_url, params={"$select": "web"}, headers=headers, timeout=60)
    app.raise_for_status()
    web = app.json()["web"]
    if callback not in web["redirectUris"]:
        result = requests.patch(
            app_url, headers=headers, json={"web": {**web, "redirectUris": [*web["redirectUris"], callback]}},
            timeout=60,
        )
        result.raise_for_status()
    shortcut = cm.ROOT / ".oauth-consent.url"
    shortcut.write_text("[InternetShortcut]\r\nURL=" + link + "\r\n", encoding="ascii", newline="")
    if shortcut.read_text(encoding="ascii").splitlines()[1] != "URL=" + link:
        raise RuntimeError("The Windows shortcut changed the provider's opaque consent URL.")
    oauth["callbackRegistered"] = True
    oauth["redirectUri"] = callback
    cm.save_config(config, "c")
    print("Registered the actual C callback and wrote the ignored .oauth-consent.url shortcut.")
    print("Open the shortcut with the lab-tenant user. No token or client secret is included.")
    if args.open:
        if not webbrowser.open(link):
            raise RuntimeError("The default browser could not open the validated consent link.")
        print("Opened the validated C consent link in the default browser.")


if __name__ == "__main__":
    main()
