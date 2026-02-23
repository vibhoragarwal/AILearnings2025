"""Simple implementation of JWT token as needed by NEST
typical use is to create a JWT object and then initialize it with
 the authorization field of the header
     jwt = jwtObject()
     jwt.decode(request.headers["Authorization"])
"""

import base64
import json
import os

import argparse
import time

import logging

# pylint: disable=invalid-name
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

DRIFT_TOLERANCE = 3600
# Development test automation user,
# SPE,
# SPQ,
# SPS,
# SD,
# General user
SKF_TEST_USERS = [
    "test.automation.6309@gmail.com",
    "internal.spe.basic02@outlook.com",
    "internal.spe.flex02@outlook.com",
    "internal.spe.friction02@outlook.com",
    "internal.spq.basic02@outlook.com",
    "internal.sps.basic02@outlook.com",
    "internal.sd.basic02@outlook.com",
    "internal.general.simpro01@outlook.com",
    "batchuser01@outlook.com",
    "batchuser02@outlook.com",
]


class InvalidToken(Exception):
    """Custom exception to replace the abort handler to clean up first"""

    def __init__(self, token):
        """Constructor"""
        Exception.__init__(self, "Provided token is not a valid token")
        ## Message (optional) for further explanation
        self.my_message = "Invalid token"
        logger.warning("Invalid token: %s", token)

    def __str__(self):
        """Conversion to string"""
        return self.my_message


class JwtObject:
    """Support class to decode and access a JWT token. Now also support for cognito access"""

    def __init__(self, token=None):
        """Constructor

        if a token is specified and is invalid an InvalidToken exception is raised

        Args:
            token: optional token to decode
        Raises:
            InvalidToken exception when token is passed which is invalid
        """
        ## JWT contents
        self.jwt = {}
        ## Header contents
        self.header = {}
        self.token = token
        if token:
            if not self.decode(token):
                raise InvalidToken(token)

    # pylint: disable=too-many-arguments
    def mock(self, user, domain, app, country, scope):
        """Mock JWT for testing purposes"""
        self.jwt["uid"] = user
        self.jwt["azp"] = app
        self.jwt["countryiso"] = country
        self.jwt["email"] = f"tester@{domain}"
        self.jwt["scope"] = scope

    def get_user(self):
        """Return the user as found by uid

        Returns:
             the found user as string
        """
        if "uid" in self.jwt:
            return self.jwt["uid"]

        # SUpport for AD TOken - oid is global while sub is lodal to app
        if "oid" in self.jwt:
            return self.jwt["oid"]

        # Support for cognito generated jwt
        if "sub" in self.jwt:
            return self.jwt["sub"]
        
        # Prefer to raise exeption instead of returning "default" User id is important
        # TODO: Check if this is the right approach
        return "default"

    def get_country(self):
        """Return the country as found by uid

        Returns:
             the found country as string
        """
        if "countryiso" in self.jwt:
            return self.jwt["countryiso"]
        if "custom:country_iso" in self.jwt:
            return self.jwt["custom:country_iso"]
        if "country" in self.jwt:
            # This should be the ISO code of the country in B2C Token
            return self.jwt["country"]
        return ""

    def get_language(self):
        """Return the country as found by uid

        Returns:
             the found country as string
        """
        if "language" in self.jwt:
            # Seems to return the ISO Language Name (e.g. Dutch)
            return self.jwt["language"]
        return ""

    def get_given_name(self):
        """Return the given name as found by uid
        Returns:
             the found given name as string
        """
        if "given_name" in self.jwt:
            return self.jwt["given_name"]
        if "name" in self.jwt:
            return self.jwt["name"]
        return ""

    def get_family_name(self):
        """Return the family name as found in token
        Returns:
             the found family name as string
        """
        if "family_name" in self.jwt:
            return self.jwt["family_name"]

        return ""

    def get_app(self):
        """Return the application as found by cid  or azp

        Returns:
            the application name as string
        """
        if "azp" in self.jwt:
            return self.jwt["azp"]

        if "cid" in self.jwt:
            return self.jwt["cid"]

        # Support for cognito generated jwt
        if "client_id" in self.jwt:
            return self.jwt["client_id"]
        if "cognito:groups" in self.jwt:
            return self.jwt["cognito:groups"]

        return "default"

    def get_scope(self):
        """Return the scope from the jwt token if present

        Returns:
             the scope ir present else 'all'
        """
        if "scope" in self.jwt:
            return self.jwt["scope"]

        return "all"

    def get_groups(self):
        """Return the groups from the jwt token if present else return None

        Returns:
             the scope ir present else 'all'
        """
        if "cognito:groups" in self.jwt:
            return self.jwt["cognito:groups"]

        lic_man = self.jwt.get("resource_access", {}).get("ESoD-License-Manager", {})
        if "roles" in lic_man:
            return lic_man["roles"]
        return []

    def get_aud(self):
        """Return the URL that is contacted"""
        return self.jwt.get("aud")

    def get_exp(self):
        """Return the expiration Date of the token"""
        return self.jwt.get("exp")

    def get_iat(self):
        """Return the issued at time"""
        return self.jwt.get("iat")

    def get_email(self):
        """Get an email from token if present"""
        # Cognito tokens have email in username
        if self.jwt.get("scope", "none").startswith("aws.cognito.signin"):
            return self.jwt.get("username")
        return self.jwt.get("email")

    def is_skf_user(self):
        """Returns true is user is an SKF employee or should be regarded as one"""
        email = self.get_email()
        # TODO: Limit to only few providers - like Azure AD/B2C
        if not email:
            return False
        return (
            email.endswith("@skf.com")
            or email in SKF_TEST_USERS
            or (email.startswith("api-skf") and email.endswith("@skf.net"))
        )

    def is_reg_user(self):
        """Returns true is user is an SKF employee or should be regarded as one"""
        user = self.get_user()
        if not user:
            return False

        return not user.startswith("an-")

    def is_allowed(self, name):
        """legacy function for backwards compatibility: Return true if name is allowed with in scope

        Returns:
             boolean  True upon a direct match or false
        """
        if "scope" in self.jwt:
            return self.is_allowed_scope(name)
        return self.is_allowed_group(name)

    def is_allowed_scope(self, name):
        """Check whether name is in scope available"""
        # Grant access based on scope
        scope = self.get_scope()
        if name and name in scope:
            logger.debug("Found a match on name of scope %s", name)
            return True

        if "all" in name or "test" in scope:
            logger.debug("Allowing access by wildcard %s", name)
            return True

        env_name = os.environ.get("NEST_AUTHENTICATION_GROUP")
        if env_name and env_name in scope:
            logger.debug("Allowing access by Environment")
            return True

        return False

    def is_allowed_group(self, name=None):
        """Check whether group name from jwt is in list of allowed groups"""
        groups = self.get_groups()
        allowed = os.environ.get("NEST_AUTHORIZATION_GROUPS", "")
        allowed_names = [name.strip().lower() for name in allowed.split(",")]
        if not allowed_names or len(allowed_names) == 1 and not allowed_names[0]:
            logger.info("NO configured groups - Granting access")
            return True
        if not groups:
            logger.warning("NO groups configured for user")
            print(groups)
            return False
        for group in groups:
            if group.lower() in allowed_names:
                logger.info("Found match on %s - access allowed", group)
                return True
            if name and group == name:
                logger.info("Found match on name: %s - access allowed", group)
                return True

        logger.info(
            "Found no match on user %s in groups: %s - access denied", name, groups
        )
        return False

    def is_expired(self):
        """Return true if token is expired
        Returns:
             boolean  True upon expiring
        """
        if "exp" not in self.jwt:
            # No Expiration present - so it will not expire
            return False
        lifetime = self.jwt["exp"] - int(time.time())
        return lifetime < 0

    def decode(self, token):
        """Translate a JWT taken and stored results in jwt

        Args:
          token: token to be decoded
        Return:
          False if failed or True otherwise
        """
        # get part between '.'
        # add padding and decode
        # decode
        # parse result
        if not token:
            return False
        self.token = token

        # Clean previous values in case it is overwritten
        self.jwt = {}
        self.header = {}

        if token[0] == token[-1] == '"':
            token = token[1:-1]
        header, data = get_data_parts(token)
        if not data:
            return False

        self.header = decode_data_token(header)
        self.jwt = decode_data_token(data)
        return self.header and self.jwt


def get_data_parts(token):
    """Get the data part from the JWT token
    Args:
      token: full token
    Returns:
     the data part
    """
    splitted = token.split(".")
    if len(splitted) != 3:
        logger.error("Invalid Token: %s", token)
        return None, None
    # The format is <header>.<data>.signature
    # we need to return the header and data part
    return splitted[0], splitted[1]


def get_data_part(token):
    """Get the data part from the JWT token
    Args:
      token: full token
    Returns:
     the data part
    """
    splitted = token.split(".")
    if len(splitted) != 3:
        logger.error("Invalid Token: %s", token)
        return None
    # The format is <header>.<data>.valid
    # we need to return the data part
    return splitted[1]


def add_padding(token):
    """Adds missing '=' characters on base64 encoded data

    Args:
     token: base64 to be decoded
    Returns:
     base64 encoded with sufficient '=' at the end
    """
    size = len(token)
    if size % 4 != 0:
        # need to add one or more '=' characters
        token += "=" * (4 - (size % 4))
    return token


def decode_data_token(token):
    """Returns dictionary obtained from token part

    Args:
        token: base64 token part to be decoded
    Returns:
        decoded token
    """
    # See Wikipedia/Base64  - section URL Application
    decoded = base64.urlsafe_b64decode(add_padding(token))
    logger.debug(decoded)
    return json.loads(decoded.decode("utf-8"))


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
