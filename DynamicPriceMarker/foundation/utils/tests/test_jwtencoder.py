import unittest
import os
import uuid
from utils.jwtencoder import JwtEncoder, generate_anon_token, generate_anon_user_id, is_anon_user_id, \
    convert_langauges, get_languages, set_language
from utils.jwtobject import JwtObject, decode_data_token

# pylint: disable=line-too-long


def test_generate_anon_user_id():
    """ Test the generation of th anon user id """
    user_id = generate_anon_user_id()
    assert user_id
    assert is_anon_user_id(user_id)
    assert not is_anon_user_id(str(uuid.uuid4()))


def test_decode_data_token():
    """ Test the decoding of a partial id """
    jwt = JwtObject()
    token = decode_data_token(
        "eyJhdWQiOiJodHRwOi8vZWxiYXBpZ2F0ZXdheS0xODM2MDE2NzUwLmV1LXdlc3QtMS5lbGIuYW1hem9uYXdzLmNvbSIsInVpZCI6IjUwMjExNmRhLWY4NzctNDlkYi1iOWFjLWE4OTdkYmU3YTM1YSIsImlhdCI6MTQ4NTI1MDMxMX0")
    # Just check that token returned something useful
    assert token["uid"] == "502116da-f877-49db-b9ac-a897dbe7a35a"

    encoder = JwtEncoder()
    jwt_token = encoder.encode(None, token)

    print(jwt_token)
    jwt.decode(jwt_token)
    assert jwt.jwt["uid"] == "502116da-f877-49db-b9ac-a897dbe7a35a"


def test_decode_anon_token():
    """ Test the decoding of a partial id """

    token = generate_anon_token(None, "dev")
    print(token)
    print(type(token))
    print(token.encode("UTF-8"))
    print(type(token.encode("UTF-8")))
    jwt = JwtObject()
    assert jwt.decode(token)
    assert jwt.get_iat()
    assert jwt.get_exp() > jwt.get_iat()
    assert jwt.get_app()
    assert jwt.get_user()

    token = generate_anon_token(None, "prod", "ratinglife", expire=4000)
    assert jwt.decode(token)
    assert jwt.get_iat()
    assert jwt.get_app()
    assert jwt.get_user()
    assert jwt.get_exp() - jwt.get_iat() == 4000


def test_generate_anon_user_id_with_domain():
    """ Test the generation of th anon user id using API key"""
    token = generate_anon_token(None, "prod", "ratinglife", domain="test-api")
    jwt = JwtObject()
    assert jwt.decode(token)
    assert jwt.get_email() == "anonymous@test-api"
    assert is_anon_user_id(jwt.get_user())
    assert jwt.jwt["resource_access"]["ESoD-License-Manager"]["roles"] == ["test-api", "registered"]


def test_language_conversion():
    """Test language conversion"""
    assert convert_langauges(["nl"]) == ["dutch; flemish"]
    assert convert_langauges(["nl", "en"]) == ["dutch; flemish", "english"]
    assert convert_langauges(["nl", "en", "madeUp"]) == ["dutch; flemish", "english"]


def test_get_languages():
    """Test splitting languages into a list"""
    languages = "en-US,en;q=0.5"
    assert get_languages(languages) == ["en"]

    languages = "en-GB,en;q=0.9,nl-NL;q=0.8,nl;q=0.7,en-US;q=0.6,de;q=0.5"
    assert get_languages(languages) == ["en", "nl", "de"]

    # chrome
    languages = "en-US,*"
    assert get_languages(languages) == ["en"]


def test_set_language():
    """Test splitting languages into a list"""
    data = {}
    languages = "en-US,en;q=0.5"
    assert set_language(data, languages) == {"languages": ["en"]}

    languages = "en-GB,en;q=0.9,nl-NL;q=0.8,nl;q=0.7,en-US;q=0.6,de;q=0.5"
    assert set_language(data, languages) == {"languages": ["en", "de"]}
