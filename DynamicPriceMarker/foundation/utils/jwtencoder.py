""" Simple implementation of JWT token as needed by NEST
typical use is to create a JWT object and then initialize it with the authorization field of the header
     jwt = jwtObject()
     jwt.decode(request.headers["Authorization"])
"""
import json
import hmac
import base64
import uuid
import hashlib
import logging
import re
import os
import argparse
import time

from foundation.utils.jwtobject import JwtObject
from foundation.utils.customexceptions import InputError
from foundation.utils.i18N_base import ISO_CODES

logger = logging.getLogger("nest.jwt")


# Typical data in JWT token:
# {'aud': 'https://dev-api.nest-galaxy.net', 'exp': 1507103925, 'cid': 'galaxy-web-978c296fbe33',
# 'iat': 1506499125, 'uid': '502116da-f877-49db-b9ac-e897dbe7a35a'}
# with
# aud the Audience
# exp the expiration time
# cid: calling application identifier
# iat: Time of issuing the jwt token
# uid: User ID


def generate_anon_user_id():
    """Generated an anomymous user ID"""
    return "an-" + str(uuid.uuid4())


def is_anon_user_id(user_id):
    """Checks if user_id is anonymous or not"""
    return user_id.startswith("an-")


def generate_anon_token(
        header_info, environment, application=None, signature_encoder=None, domain=None, language=None, expire=3600
):
    """Generate token to be used. This token should match used token

    Args:
        header_info: dict with Additional input for header - like style of encoding
        environment: one of ["dev","test","stg", "prod" ]  the ast one being production
        application: Name of application to use
        signature_encoder: Encoder function used for validation
        domain: Add options to set a domain for API key based tokens
        expire: extra time granted for special cases
    Returns Token
    """
    if not application:
        application = "skf-bearing-calc-test"

    uid = generate_anon_user_id()
    issued = int(time.time())
    expires = issued + expire
    resources = {"ESoD-License-Manager": {"roles": [domain, "registered"]}}

    anonynmous_token = {
        "jti": str(uuid.uuid4()),
        "exp": expires,
        "nbf": 0,
        "iat": issued,
        "iss": "https://skfbearingselect.com/authentication/" + ("anonymous" if not domain else "apikey"),
        "aud": application,
        "sub": uid,
        "typ": "Bearer",
        "azp": "skf-bearing-calc-" + environment if not domain else domain,
        "nonce": str(uuid.uuid4()),
        "auth_time": issued,
        "session_state": "dd489bce-ab97-489d-9467-4ccba3d5b163",
        "acr": "0",
        "email": f"anonymous@{'skf.net' if not domain else domain}",
        "allowed-origins": [
            "http://localhost:4200",
            "https://dev.skfbearingselect.com",
            "https://test.skfbearingselect.com",
            "https://stg.skfbearingselect.com",
            "https://skfbearingselect.com",
        ],
        "resource_access": resources if domain else {},
        "name": "Anonymous",
        "preferred_username": "Anonymous" if not domain else f"Anonymous@{domain}",
    }
    if language:
        set_language(anonynmous_token, language)
    encoder = JwtEncoder(signature_encoder)
    return encoder.encode(header_info, anonynmous_token)


def refresh_anon_token(header_info, token, signature_encoder=None, language=None):
    """Update a anonymous token with new time values

    Args:
        header_info: dict with Additional input for header - like style of encoding
        token: old JWT token in dict format
        signature_encoder: Encoder function used for validation
        language: To add language to older tokens
    Returns Token
    """
    if not is_anon_user_id(token["sub"]) or not token["email"].startswith("anonymous"):
        # Only allowded to refresh anonymous token
        raise InputError("Not an anonymous token")

    domain = "" if token["azp"].startswith("skf-bearing-calc-") else token["azp"]
    issued = int(time.time())
    expires = issued + 3600 if not domain else issued + 300
    token["iat"] = issued
    token["exp"] = expires
    if language and not token.get("language"):
        token["language"] = language

    encoder = JwtEncoder(signature_encoder)
    return encoder.encode(header_info, token)


def generate_refresh_token(
        header_info, environment, application=None, signature_encoder=None, domain=None
):
    """Generate token to be used. This token should match used token

    Args:
        header_info: dict with Additional input for header - like style of encoding
        environment: one of ["dev","test","stg", "prod" ]  the ast one being production
        application: Name of application to use
        signature_encoder: Encoder function used for validation
        domain: Add options to set a domain for API key based tokens
    Returns Token
    """
    if not application:
        application = "skf-bearing-calc-test"

    uid = generate_anon_user_id()
    issued = int(time.time())
    expires = issued + 3600
    resources = {"ESoD-License-Manager": {"roles": [domain, "registered"]}}

    # "aud": hashlib.sha1(apikey.encode('utf-8')).hexdigest(),
    refresh_token = {
        "jti": str(uuid.uuid4()),
        "exp": expires,
        "nbf": 0,
        "iat": issued,
        "iss": "https://skfbearingselect.com/authentication/" + ("anonymous" if not domain else "apikey"),
        "aud": application,
        "sub": uid,
        "typ": "Refresh",
        "azp": "skf-bearing-calc-" + environment if not domain else domain,
        "nonce": str(uuid.uuid4()),
        "auth_time": issued,
        "session_state": "dd489bce-ab97-489d-9467-4ccba3d5b163",
        "acr": "0",
        "email": f"anonymous@refresh{'skf.net' if not domain else domain}",
        "allowed-origins": [
            "http://localhost:4200",
            "https://dev.skfbearingselect.com",
            "https://test.skfbearingselect.com",
            "https://stg.skfbearingselect.com",
            "https://skfbearingselect.com",
        ],
        "resource_access": resources if domain else {},
        "name": "Anonymous",
        "preferred_username": "Anonymous" if not domain else f"Anonymous@refresh{domain}",
    }
    encoder = JwtEncoder(signature_encoder)
    return encoder.encode(header_info, refresh_token)


def set_language(token_dict: dict, languages: str):
    """Set language in token based on language from header

    for languages, it will have format like "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
    Args:
        token_dict: Dictionary that will become token
        language: List of user available languages from header
    """
    # token_dict["languages"] = convert_langauges(get_languages(languages))
    # return short form
    token_dict["languages"] = [language for language in get_languages(languages) if language in ISO_CODES]

    return token_dict
    # Now convert two letter codes to our internal format


def get_languages(language_string: str) -> list:
    """Transforms an html supported lamguage string into ordered list of language codes"""
    query = re.compile("([a-z]+)[-;]?.*")
    languages = []
    for language in language_string.split(","):
        if lang := query.match(language):
            # Likely that the same language occurs mutiple times - only add the first
            if lang.group(1) not in languages:
                languages.append(lang.group(1))
    return languages
    # Now convert two letter codes to our internal format


def convert_langauges(languages: list) -> list:
    """Convert languages from short form into english form"""
    path = os.path.dirname(__file__)
    with open(os.path.join(path, "languages.json"), "r", encoding="UTF-8") as json_input:
        known = json.load(json_input)
    # If a language is not known - silently ignore it
    return [known[language] for language in languages if language in known]


class JwtEncoder:
    """Support class to decode and access a JWT token. Now also support for cognito access"""

    def __init__(self, encoder=None):
        """Constructor"""
        ## JWT contents
        self.encoder = encoder

    def encode(self, header_token, token):
        """Create a signed JWT Token from header and body parts

        Args:
            header_token: (dict) additional key-values to ba added to jwt header
            token: token to be encoded
        Return:
          False if failed or True otherwise
        """
        # get part between '.'
        # add padding and decode
        # decode
        # parse result
        if header_token:
            header_dict = {**{"alg": "HS256", "typ": "JWT"}, **header_token}
        else:
            header_dict = {"alg": "HS256", "typ": "JWT"}
        header = self.encode_data_token(header_dict)
        payload = self.encode_data_token(token)
        signature = self.create_signature(header, payload)
        point = ".".encode("UTF-8")

        jw_token = point.join([header, payload, signature])
        print("-----------------------------------")
        print(jw_token)
        return jw_token.decode('UTF-8')

    def encode_data_token(self, token):
        """Adds missing '=' characters on base64 encoded data

        Args:
         token: base64 to be decoded
        Returns:
         True if successful decoded
        """
        token_data = json.dumps(token)
        encoded = base64.urlsafe_b64encode(token_data.encode("utf-8"))
        logger.debug(encoded)
        return encoded

    def create_signature(self, header, payload):
        """Creates a signature based on payload and header

        Args:
          header: base64 to be decoded
          payload: payload info
        Returns:
          Encoded binary list
        """
        input_data = ".".encode("UTF-8").join([header, payload])
        if self.encoder:
            # Returns base 64 encoded value
            sig = self.encoder(input_data)
        else:
            my_mac = hmac.new("OnlyForTestMode".encode("UTF-8"), input_data, digestmod=hashlib.sha256)
            sig = my_mac.digest()

        return base64.urlsafe_b64encode(sig)

    def verify_token(self, header, payload, signature, decoder):
        """Creates a signature based on payload and header

        Requires an decoder to be set

        Args:
            header: string with base 64 encoded jwt header
            payload: string with base 64 encoded jwt payload
            signature: string with base 64 encoded jwt signature
        Returns:
            True if signature is valid
        """
        input_data = ".".encode("UTF-8").join([header, payload])
        encoded = decoder(signature)
        return input_data == encoded


def generate_secure_user_id():
    """Generated an anomymous user ID"""
    return "su-" + str(uuid.uuid4())


def generate_secure_token(
        header_info, environment, application=None, signature_encoder=None, domain=None, language=None, expire=3600
):
    """Generate token to be used. This token should match used token

    Args:
        header_info: dict with Additional input for header - like style of encoding
        environment: one of ["dev","test","stg", "prod" ]  the ast one being production
        application: Name of application to use
        signature_encoder: Encoder function used for validation
        domain: Add options to set a domain for API key based tokens
        expire: extra time granted for special cases
    Returns Token
    """
    if not application:
        application = "skf-bearing-calc-test"

    uid = generate_secure_user_id()
    issued = int(time.time())
    expires = issued + expire
    resources = {"ESoD-License-Manager": {"roles": [domain, "registered"]}}

    secure_token = {
        "jti": str(uuid.uuid4()),
        "exp": expires,
        "nbf": 0,
        "iat": issued,
        "iss": "https://secure.skfbearingselect.com/authentication/secure/token",
        "aud": application,
        "sub": uid,
        "typ": "Bearer",
        "azp": "skf-bearing-calc-" + environment if not domain else domain,
        "nonce": str(uuid.uuid4()),
        "auth_time": issued,
        "session_state": "dd489bce-ab97-489d-9467-4ccba3d5b163",
        "acr": "0",
        "email": f"secure@{'skf.net' if not domain else domain}",
        "allowed-origins": [
            "http://localhost:4200",
            "https://dev.skfbearingselect.com",
            "https://test.skfbearingselect.com",
            "https://stg.skfbearingselect.com",
            "https://skfbearingselect.com",
        ],
        "resource_access": resources if domain else {},
        "name": "Secure",
        "preferred_username": "Secure" if not domain else f"Secure@{domain}",
    }
    if language:
        set_language(secure_token, language)
    encoder = JwtEncoder(signature_encoder)
    return encoder.encode(header_info, secure_token)

# Note: the three parts are as follows: header.payload.signature.
# signature = HMAC-SHA256(secret_key, encodeBase64Url(header) + '.' + encodeBase64Url(payload))

def main():
    """Main function"""
    arguments = argparse.ArgumentParser(description="extract token from command line")
    arguments.add_argument("token", help="Token to extract")
    args = arguments.parse_args()

    jwt = JwtObject()
    if jwt.decode(args.token):
        print("Decoded:")
        print(json.dumps(jwt.jwt, indent=2))
        print()
        print(f"Current system time: {jwt.get_exp() - int(time.time())}")
        print(f"Issues seconds ago : {int(time.time()) - jwt.get_iat()}")
        print(f"User: {jwt.get_user()}")
        print(f"email: {jwt.get_email()}")
        print(f"app: {jwt.get_app()}")


if __name__ == "__main__":
    main()