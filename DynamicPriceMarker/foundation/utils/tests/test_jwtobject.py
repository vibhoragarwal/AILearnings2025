""" Test handling of JWT Object"""

import os
import time
import uuid
import pytest
from utils.jwtobject import (
    JwtObject,
    get_data_part,
    get_data_parts,
    decode_data_token,
    InvalidToken,
)

# pylint: disable=line-too-long


def test_get_data_part():
    """Test if we can split the data into parts"""
    assert get_data_part("abc.def.ghi") == "def"
    assert not get_data_part("abc.def")
    assert not get_data_part("abc.d.e.f")
    assert get_data_part("Bearer abc.def.ghi") == "def"


def test_get_data_parts():
    """Test if we can split the data into parts"""
    assert ("abc", "def") == get_data_parts("abc.def.ghi")
    assert (None, None) == get_data_parts("abc.def")
    assert (None, None) == get_data_parts("abc.d.e.f")
    assert ("Bearer abc", "def") == get_data_parts("Bearer abc.def.ghi")


def test_decode_data_toekn():
    """Test the decoding of a partial id"""
    jwt = JwtObject()
    jwt.jwt = decode_data_token(
        "eyJhdWQiOiJodHRwOi8vZWxiYXBpZ2F0ZXdheS0xODM2MDE2NzUwLmV1LXdlc3QtMS5lbGIuYW1hem9uYXdzLmNvbSIsInVpZCI6IjUwMjExNmRhLWY4NzctNDlkYi1iOWFjLWE4OTdkYmU3YTM1YSIsImlhdCI6MTQ4NTI1MDMxMX0"
    )
    assert jwt.get_user() == "502116da-f877-49db-b9ac-a897dbe7a35a"
    assert len(list(jwt.jwt.keys())) == 3
    assert "aud" in list(jwt.jwt.keys())
    assert "iat" in list(jwt.jwt.keys())


def test_decode():
    """Test the decoding of a partial id"""
    jwt = JwtObject()
    assert jwt.decode(
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJodHRwOi8vZWxiYXBpZ2F0ZXdheS0xODM2MDE2NzUwLmV1LXdlc3QtMS5lbGIuYW1hem9uYXdzLmNvbSIsInVpZCI6IjUwMjExNmRhLWY4NzctNDlkYi1iOWFjLWE4OTdkYmU3YTM1YSIsImlhdCI6MTQ4NTI1MDMxMX0.bZlhlSH5cgeQpawYDVgR-VcsGmpUdGBDD_Qq1_7YnRQ"
    )
    assert jwt.get_user() == "502116da-f877-49db-b9ac-a897dbe7a35a"
    assert len(list(jwt.jwt.keys())) == 3
    assert "aud" in list(jwt.jwt.keys())
    assert "iat" in list(jwt.jwt.keys())


def test_decode_with_scope():
    """Test the decoding of a partial id"""
    jwt = JwtObject()
    assert jwt.decode(
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJodHRwczovL2Rldi1hcGkubmVzdC1nYWxheHkubmV0IiwidWlkIjoiMmNlZWI3ZjgtNDMzYi00Mzc2LWI4MmItY2RkMThiMWEwN2RiIiwiY2lkIjoiZ2FsYXh5LXdlYi05NzhjMjk2ZmJlMzMiLCJzY29wZSI6WyJ0ZXN0Il0sImlhdCI6MTUwNjY3ODg5MiwiZXhwIjoxNTA3MjgzNjkyfQ.QTL-R9yBGeVo0fV5uv0d5RxZRIdg7JrvFSaB-DOTwJU"
    )
    assert jwt.get_user() == "2ceeb7f8-433b-4376-b82b-cdd18b1a07db"
    assert "scope" in list(jwt.jwt.keys())
    assert jwt.get_scope()
    assert "test" in jwt.get_scope()


def test_check_group():
    """Test the decoding of a partial id"""
    jwt = JwtObject()
    assert jwt.decode(
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJodHRwczovL2Rldi1hcGkubmVzdC1nYWxheHkubmV0IiwidWlkIjoiMmNlZWI3ZjgtNDMzYi00Mzc2LWI4MmItY2RkMThiMWEwN2RiIiwiY2lkIjoiZ2FsYXh5LXdlYi05NzhjMjk2ZmJlMzMiLCJzY29wZSI6WyJ0ZXN0Il0sImlhdCI6MTUwNjY3ODg5MiwiZXhwIjoxNTA3MjgzNjkyfQ.QTL-R9yBGeVo0fV5uv0d5RxZRIdg7JrvFSaB-DOTwJU"
    )
    # Mimic if the JWT should contain groups
    jwt.jwt["cognito:groups"] = ["KissSoft"]
    assert jwt.get_groups() == ["KissSoft"]
    os.environ["NEST_AUTHORIZATION_GROUPS"] = "KissSoft"
    assert jwt.is_allowed_group()
    jwt.jwt["cognito:groups"] = ["TestGroup"]
    assert not jwt.is_allowed_group()
    os.environ["NEST_AUTHORIZATION_GROUPS"] = "TestGroup, KissSoft"
    assert jwt.is_allowed_group()
    jwt.jwt["cognito:groups"] = ["KissSoft"]
    assert jwt.is_allowed_group()

    del os.environ["NEST_AUTHORIZATION_GROUPS"]
    assert jwt.is_allowed_group()


def test_is_expired():
    """Test the decoding of a partial id"""
    jwt = JwtObject()
    jwt.jwt = {"none": "none"}
    assert not jwt.is_expired()

    jwt.jwt = {"exp": time.time() + 5400}
    assert not jwt.is_expired()

    jwt.jwt = {"exp": time.time() + 54}
    assert not jwt.is_expired()

    jwt.jwt = {"exp": time.time() - 1}
    assert jwt.is_expired()

    jwt.jwt = {"exp": time.time() - 3601}
    assert jwt.is_expired()

    jwt.jwt = {"exp": time.time() - 7200}
    assert jwt.is_expired()


def test_decode_in_constructor():
    """Test the decoding of a partial id"""
    jwt = JwtObject(
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJodHRwOi8vZWxiYXBpZ2F0ZXdheS0xODM2MDE2NzUwLmV1LXdlc3QtMS5lbGIuYW1hem9uYXdzLmNvbSIsInVpZCI6IjUwMjExNmRhLWY4NzctNDlkYi1iOWFjLWE4OTdkYmU3YTM1YSIsImlhdCI6MTQ4NTI1MDMxMX0.bZlhlSH5cgeQpawYDVgR-VcsGmpUdGBDD_Qq1_7YnRQ"
    )
    assert jwt.get_user() == "502116da-f877-49db-b9ac-a897dbe7a35a"
    assert len(list(jwt.jwt.keys())) == 3
    assert "aud" in list(jwt.jwt.keys())
    assert "iat" in list(jwt.jwt.keys())

    with pytest.raises(InvalidToken):
        jwt = JwtObject("ThisisNot,AValidTokenToDecode.Right")


def test_decode_padding_token():
    """THis one complained on invalid padding"""
    jwt = JwtObject()
    assert jwt.decode(
        token="eyJraWQiOiJkOHgzZUtWNmpDY0hkeEdqbFhVeDZES1FIN2V3ditUT3paeUV5YStZSVJJPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJiMGUyMDMwMS0wMmFhLTRkNmMtOTQ4OC03OGQ5MDFjMDY3M2IiLCJjb2duaXRvOmdyb3VwcyI6WyJLaXNzU29mdEdyb3VwIl0sInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoiYXdzLmNvZ25pdG8uc2lnbmluLnVzZXIuYWRtaW4iLCJhdXRoX3RpbWUiOjE1NTczMTk3NjQsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5ldS13ZXN0LTEuYW1hem9uYXdzLmNvbVwvZXUtd2VzdC0xX1NyRkJ5ZjRxUiIsImV4cCI6MTU1NzMyMzM2NCwiaWF0IjoxNTU3MzE5NzY0LCJqdGkiOiJkNDM5YmI3ZC1jZjBjLTQ2NTctOTVjNy1jNjRmZGI2YjQ2MTAiLCJjbGllbnRfaWQiOiIzNXJrMzFxanIzaTJzdTF0bzlxYWdjY25pdiIsInVzZXJuYW1lIjoiZWR3aW4uMDAxQHNrZi10ZXN0Lm5ldCJ9.mXY0Rtl1PpWsgcCAGkHDf3ZQ9wwXR8MvyvduzHS80LiyW2xFlY4W2M8hfcVD7PrWGFgWNvqFpWAPDTDIiMzpfoU2YVTIlW6o3_eJ3yU6RMjUi92HDi6at3ZqDdDgelpiYJgzGks7ja4o0xTotYwgQSeInn8Lydahx-QDrTG0q9bQazcChMIvtVGI2R0ejnOhj5pFM3X7DrdAj3q-ogn-_nRmnsgenud2xtDGdGNBGK45KDI-BYd-7Yn-LAOPnblqxn9oBUZqdbjzVwZkFfVWOYCUsLDkeAVnCzw2Hf7MPljXaokeD0BoLcqyEGxAncNP0CAmPbLMtTlkv3yCMV9OpA"
    )


def test_get_groups():
    """Test the get groups"""
    my_token = {
        "resource_access": {"ESoD-License-Manager": {"roles": ["stiffness-test"]}}
    }
    jwt = JwtObject()
    jwt.jwt = my_token
    assert jwt.get_groups() == ["stiffness-test"]

    my_token = {
        "resource_access": {"Another-License-Manager": {"roles": ["stiffness-test"]}}
    }
    jwt = JwtObject()
    jwt.jwt = my_token
    assert not jwt.get_groups()

    my_token = {"some_access": {"ESoD-License-Manager": {"roles": ["stiffness-test"]}}}
    jwt = JwtObject()
    jwt.jwt = my_token
    assert not jwt.get_groups()

    jwt = JwtObject()
    assert jwt.decode(
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJodHRwczovL2Rldi1hcGkubmVzdC1nYWxheHkubmV0IiwidWlkIjoiMmNlZWI3ZjgtNDMzYi00Mzc2LWI4MmItY2RkMThiMWEwN2RiIiwiY2lkIjoiZ2FsYXh5LXdlYi05NzhjMjk2ZmJlMzMiLCJzY29wZSI6WyJ0ZXN0Il0sImlhdCI6MTUwNjY3ODg5MiwiZXhwIjoxNTA3MjgzNjkyfQ.QTL-R9yBGeVo0fV5uv0d5RxZRIdg7JrvFSaB-DOTwJU"
    )
    jwt.jwt["cognito:groups"] = ["KissSoft"]
    assert jwt.get_groups() == ["KissSoft"]


def test_various_getters_redhat():
    """Test some getters with a few RedHat token"""
    token = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJaWXk1N2lDMFBuSzFWdU8tUTBZZzhzZ1JXaWNmcHNJX0pYdkxEY0FaN0xNIn0.eyJqdGkiOiI1ZmFkYjY5MS0zNTE0LTRkZGMtYmRmMC05OGQ5NmE0NTc2MWMiLCJleHAiOjE2NDU3MTIwOTAsIm5iZiI6MCwiaWF0IjoxNjQ1NzExNzkwLCJpc3MiOiJodHRwczovL3Nzby1xYS5za2YuY29tL2F1dGgvcmVhbG1zL1NLRiIsImF1ZCI6WyJFU29ELUxpY2Vuc2UtTWFuYWdlciIsInNrZi5jb20iLCJhY2NvdW50Il0sInN1YiI6IjE2M2U4Mzg5LWE0MzEtNGRjNC04ZDEwLTM2NmViYzhkMTZhZCIsInR5cCI6IkJlYXJlciIsImF6cCI6InNrZmJlYXJpbmdzZWxlY3QtZGV2Iiwibm9uY2UiOiI5NDVmZTc4ZS1iNGRlLTQwMjAtOTZiMC0wZjhiODljMWZlOGMiLCJhdXRoX3RpbWUiOjE2NDU3MTE3ODksInNlc3Npb25fc3RhdGUiOiI3YWUwNDNlNC1jYzExLTQ3NjYtOWNkNS1mOTBjNzVlYzM5N2UiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly9kZXYuc2tmYmVhcmluZ3NlbGVjdC5jb20iLCJodHRwOi8vZGV2LnNrZi1iYy5uZXQiLCJodHRwczovL2Rldi5za2YtYmMubmV0IiwiaHR0cHM6Ly9kZXYuc2tmYmVhcmluZ3NlbGVjdC5jb20iLCJodHRwOi8vbG9jYWxob3N0OjQyMDAiXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iXX0sInJlc291cmNlX2FjY2VzcyI6eyJFU29ELUxpY2Vuc2UtTWFuYWdlciI6eyJyb2xlcyI6WyJzdGlmZm5lc3MtdGVzdCJdfSwic2tmLmNvbSI6eyJyb2xlcyI6WyJHcm91cCAtIEF1dGhvcmlzZWQgRGlzdHJpYnV0b3IiLCJCZW5lbHV4IC0gQXV0aG9yaXNlZCBEaXN0cmlidXRvciAoTkwpIiwiU0tGIEVtcGxveWVlIl19LCJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6Im9wZW5pZCIsImNvdW50cnlpc28iOiJubGQiLCJuYW1lIjoiRWR3aW4gRXNzZW5pdXMiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJlZHdpbi5lc3Nlbml1c0Bza2YuY29tIiwiZ2l2ZW5fbmFtZSI6IkVkd2luIiwiZmFtaWx5X25hbWUiOiJFc3Nlbml1cyIsImVtYWlsIjoiZWR3aW4uZXNzZW5pdXNAc2tmLmNvbSJ9.fcbW4KNoIBE_uT56whOTA5korC95BIDFOZ5a4o5zz02BgNuC8sdDVMCBKTT4nPmlaeSg-RbS_PXS3Xr1TMqNkD1OMAvS_CEgB8j-6fBNM2mMZp2jzlLwM-ro4pTPsxHsZTPvKLLW0jK4v33WczL8Ld83Q8ai500izPWbcv5zmL40rJfRDKdHjOoo4Ses6rexJ7Srv_9F3F5DxHPY3fStzo0usQoYouQSjHmQkTx2lBE8UNXppDRc1VRWbB6z9PTTQrr53jFLPkHF2kwJexfhVvm6Egbzh4_IKVMkXO8jE5I0SuX-jyZa6AFYJ_B-N__FAaBTb3rDTygyPQAQeQpgyg"
    jwt = JwtObject(token=token)
    assert (
        jwt.get_user() == "163e8389-a431-4dc4-8d10-366ebc8d16ad"
    )  # This is the most important one
    assert jwt.get_app() == "skfbearingselect-dev"
    assert jwt.get_aud() == ["ESoD-License-Manager", "skf.com", "account"]
    assert jwt.get_exp() == 1645712090
    assert jwt.get_iat() == 1645711790
    assert jwt.get_email() == "edwin.essenius@skf.com"
    assert jwt.get_given_name() == "Edwin"
    assert jwt.get_family_name() == "Essenius"
    assert jwt.get_country() == "nld"
    assert jwt.get_groups() == ["stiffness-test"]
    assert jwt.get_scope() == "openid"
    assert jwt.is_expired()


def test_various_getters_b2c():
    """Test some getters with a B2C token"""
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IkFFM0NBNzVBRDlDNzVGNDAzNjkxQjQ1QTU3MEM3Q0E3NUM3Qzk4MkUiLCJ4NXQiOiJyanluV3RuSFgwQTJrYlJhVnd4OHAxeDhtQzQifQ.eyJleHAiOjE2NTIwMTMxMDUsIm5iZiI6MTY1MjAwOTUwNSwidmVyIjoiMS4wIiwiaXNzIjoiaHR0cHM6Ly9za2Zncm91cGIyY2Rldi5iMmNsb2dpbi5jb20vNzYyN2VkNWMtZTYzNS00ODUwLWE5MzctYWYzYWE5ZWVmZTgzL3YyLjAvIiwic3ViIjoiMTBkZDViOTAtMTdlYi00NTE1LTkyMDctMDNkNTIxNDk4YTBlIiwiYXVkIjoiNGRmMWI1ZmMtNmQ5OC00ZDgyLTgzOGQtYzQwM2VhYTgxM2UxIiwiYWNyIjoiYjJjXzFhX3NrZmZvcm1lLWRldi1zaWdudXBfc2lnbmluIiwibm9uY2UiOiIyMGRjZjdmMy01YzgyLTQ0NjMtOTA5ZS1jMjYzNjhlYzM2ZTgiLCJpYXQiOjE2NTIwMDk1MDUsImF1dGhfdGltZSI6MTY1MjAwOTUwNCwidGlkIjoiNDE4NzVmMmItMzNlOC00NjcwLTkyYTgtZjY0M2FmYmIyNDNhIiwiZ2l2ZW5fbmFtZSI6IkVkd2luIiwiZmFtaWx5X25hbWUiOiJFc3Nlbml1cyIsIm5hbWUiOiJFZHdpbiBFc3Nlbml1cyIsImVtYWlsIjoiRWR3aW4uRXNzZW5pdXNAc2tmLmNvbSIsImFwcHJvdmVkIjpmYWxzZX0.B-_jEfvKi6iuSfekBsB1CzVeMsOmKUyPVS2xnK_t9aBUT7aUwumej9X4p5EJ2Afoa4BkWVpy_gjs6FJ03k8LnWANyo-XpQAxJ_xeG0FpI9VvCfEQaG21eMFVDkZBrkMRHSFIXQgE0LuFmTSdXpocnDglX6CJrw88xu7lWw7I3hwYbJDepN9ye7PSU7HJgiH8jqJrzaIC4jv6HRYpxD0eq42WqsIU5kFS6K4pBdh6a_DefT4UtYa4CSzRgf-zfezkZZ9Gd8nxCiUhpZ3qVVOAtrdX5JKiAbDa0hyq8vQ0WZYK8va-e66z0zmVSCsY7UgIZtNzoZ5vLlnlqnWRnOCP4g"
    jwt = JwtObject(token=token)
    assert jwt.get_user() == "10dd5b90-17eb-4515-9207-03d521498a0e"
    assert jwt.get_aud() == "4df1b5fc-6d98-4d82-838d-c403eaa813e1"
    assert jwt.get_exp() == 1652013105
    assert jwt.get_iat() == 1652009505
    assert jwt.get_email() == "Edwin.Essenius@skf.com"
    assert jwt.get_given_name() == "Edwin"
    assert jwt.get_family_name() == "Essenius"
    assert not jwt.get_country()
    assert not jwt.get_groups()
    assert jwt.get_scope() == "all"
    assert jwt.is_expired()


# TODO Test also with recent B2C Access token with recent


def test_various_getters_cognito():
    """Test some getters with a B2C token"""
    token = "eyJraWQiOiJrSGt0eDdhMFU2RlZaQnpnOExPTkpFbmtVUDNXZm9JUVZoK29lbDkxc0dFPSIsImFsZyI6IlJTMjU2In0.eyJhdF9oYXNoIjoidmZac09ZX0RVdXotRHl2WjNEY3N3ZyIsInN1YiI6ImI4YWJkMWJiLTYwZjMtNDk3ZS05MDExLTIwNzgyZTU5NThlZCIsImNvZ25pdG86Z3JvdXBzIjpbIlNLRlVzZXJzR3JvdXAiLCJldS13ZXN0LTFfOE43Y2NWVENYX1NLRnBvY0NvZ25pdG9SSFNTTy1RQS1wcm92aWRlciJdLCJjdXN0b206c3RyZWV0Ijoia2VsdmluYmFhbiAxNiIsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5ldS13ZXN0LTEuYW1hem9uYXdzLmNvbVwvZXUtd2VzdC0xXzhON2NjVlRDWCIsImN1c3RvbTpwb3N0YWxfY29kZSI6IjM0MzlOVCIsImxvY2FsZSI6ImVuLXVzIiwiaWRlbnRpdGllcyI6W3sidXNlcklkIjoiMTYzZTgzODktYTQzMS00ZGM0LThkMTAtMzY2ZWJjOGQxNmFkIiwicHJvdmlkZXJOYW1lIjoiU0tGcG9jQ29nbml0b1JIU1NPLVFBLXByb3ZpZGVyIiwicHJvdmlkZXJUeXBlIjoiT0lEQyIsImlzc3VlciI6bnVsbCwicHJpbWFyeSI6InRydWUiLCJkYXRlQ3JlYXRlZCI6IjE2MzYzNzk2NjY3MjcifV0sImF1dGhfdGltZSI6MTY0NTcxNTI0NiwiZXhwIjoxNjQ1NzE4ODQ2LCJpYXQiOjE2NDU3MTUyNDYsImN1c3RvbTpwcmVmZXJyZWRfbGFuZ3VhZ2UiOiJlbi1HQiIsImp0aSI6ImVjZWJhOWRlLThlNDEtNGE3My1iZmU2LTQyNzBkNTRlM2NhZiIsImVtYWlsIjoiZWR3aW4uZXNzZW5pdXNAc2tmLmNvbSIsImN1c3RvbTpjb3VudHJ5IjoiTmV0aGVybGFuZHMiLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiY3VzdG9tOmNvdW50cnlfaXNvIjoibmxkIiwiY29nbml0bzp1c2VybmFtZSI6InNrZnBvY2NvZ25pdG9yaHNzby1xYS1wcm92aWRlcl8xNjNlODM4OS1hNDMxLTRkYzQtOGQxMC0zNjZlYmM4ZDE2YWQiLCJnaXZlbl9uYW1lIjoiRWR3aW4iLCJub25jZSI6IlFjb1EyOGMyb0o5QzVHRlZ4bnFLVExTMS1fbC1CUTMxOGtwdmJGOXdoMXo5Y2RVd0E3c3BQa242Z1ZUcWhqT05oYlVtbVFkU0hfZ0dIRFRLLUozaHN1bkhELWpMb3dham04TU55TFNKQlB1bkVTMUF6ZlEwSURSQ0dmQ0xXWHNqTWM5YnJtR0RHZ180ZE5VM2pmTlJyY2NLYzlsdHI0dWFvaUUtYnFKM3d2cyIsImN1c3RvbTpjaXR5IjoiUEFQRU5EUkVDSFQiLCJhdWQiOiI0ZTU2aWl0aHRvNGtzdm9iMnVnYWI2dmY2ZCIsInRva2VuX3VzZSI6ImlkIiwibmFtZSI6IkVkd2luIEVzc2VuaXVzIiwiY3VzdG9tOmNvbXBhbnlOYW1lIjoiU0tGIiwiZmFtaWx5X25hbWUiOiJFc3Nlbml1cyJ9.eKghUOp5iuokwb7xlMvG5Yhy_MrAjffm5jATssPgkzd1vAWpNh-vpxIJEIilh5v9jZLS6hD0B6paObFH40Sjj9TToLxxPfpYS8Gg7Or1M7zUFiEpIfIjDD45Pvwp6_rMAh6A5XFSP9PcyBKR-NoUAowOD8RE2MfrTugDSmnwAZcI0x-akudezjCgJVrFPljYLET7av6m0sPWt4DFRWW2LC8EnRynJA8XpoYydmgL262gV2wNQ7UdIvghheXJMOkkXs56KWK-xF0CoHUPvEjVU5z-sJ_yeZ7L9ZkRNYMchCnled3QyYEwxrw6leMrcoHAZt6KtrIRpC3HcEAv9MQyXQ"
    jwt = JwtObject(token=token)
    assert jwt.get_user() == "b8abd1bb-60f3-497e-9011-20782e5958ed"
    assert jwt.get_aud() == "4e56iithto4ksvob2ugab6vf6d"
    assert jwt.get_iat() == 1645715246
    assert jwt.get_exp() == 1645718846
    assert jwt.get_email() == "edwin.essenius@skf.com"
    assert jwt.get_given_name() == "Edwin"
    assert jwt.get_family_name() == "Essenius"
    assert jwt.get_country() == "nld"
    assert "SKFUsersGroup" in jwt.get_groups()
    assert jwt.get_scope() == "all"
    assert jwt.is_expired()


def test_language_country_b2c():
    """Test language and Country detection in B2C Token"""
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IkFFM0NBNzVBRDlDNzVGNDAzNjkxQjQ1QTU3MEM3Q0E3NUM3Qzk4MkUiLCJ4NXQiOiJyanluV3RuSFgwQTJrYlJhVnd4OHAxeDhtQzQifQ.eyJleHAiOjE2NTM4OTM0MTYsIm5iZiI6MTY1Mzg4OTgxNiwidmVyIjoiMS4wIiwiaXNzIjoiaHR0cHM6Ly9za2Zncm91cGIyY2Rldi5iMmNsb2dpbi5jb20vNzYyN2VkNWMtZTYzNS00ODUwLWE5MzctYWYzYWE5ZWVmZTgzL3YyLjAvIiwic3ViIjoiNzFmZGY0NzgtOTc3ZC00MzBiLTkwOGEtNWMyNTlkNDUyOTg0IiwiYXVkIjoiNGRmMWI1ZmMtNmQ5OC00ZDgyLTgzOGQtYzQwM2VhYTgxM2UxIiwiYWNyIjoiYjJjXzFhX3NrZmZvcm1lLWRldi1zaWdudXBfc2lnbmluIiwibm9uY2UiOiJiNWRlNGE2OC1lN2I1LTQ0MTQtOTM1Zi1hMzkxMzMwMWFkMjYiLCJpYXQiOjE2NTM4ODk4MTYsImF1dGhfdGltZSI6MTY1Mzg4OTgxNSwidGlkIjoiNDE4NzVmMmItMzNlOC00NjcwLTkyYTgtZjY0M2FmYmIyNDNhIiwiZ2l2ZW5fbmFtZSI6IkVkd2luIiwiZmFtaWx5X25hbWUiOiJFc3Nlbml1cyIsIm5hbWUiOiJFZHdpbiBFc3Nlbml1cyIsImVtYWlsIjoiRWR3aW4uRXNzZW5pdXNAc2tmLmNvbSIsImlkcCI6InNrZi5jb20iLCJjb3VudHJ5IjoiTkxEIiwibGFuZ3VhZ2UiOiJEdXRjaCIsImFwcHJvdmVkIjpmYWxzZSwiZ2xvYmFsUm9sZXMiOltdfQ.Ni5RJNg1Htx_plI3JXhC2YqXDcAppaGWOhkYnH02cDNMkhN0fewzgIa96qD2lfMUEiSpliEvKDcF1uW2HLgor-gJK59p1H4PW8VtlK_pNYscijZqMP-TztBSQqT_fyKa0VTas5ox-xWe_ioNiN7BBW1c1zz2zZiayEDvzH5p48g7ali3_XGBqotnDb-ZPWma3vRpIW9I0xjpAi5qoro6jsnf2PBkV79ggEAgVjxuRxjIm44AxbInxJaLOeoCXn3iU4o6DaCn9zJATLSJQIKuAYkyjxTunD0RAef_oIslrAYUBUdfGj5eMT0jHX6yZjOxvEZY3Njt2GNYdll5LNbOsQ"
    jwt = JwtObject(token=token)
    assert jwt.get_country() == "NLD"
    assert jwt.get_language() == "Dutch"


def test_body_token_aad():
    """Test body extraction of Azure AD V2 token"""
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ii1LSTNROW5OUjdiUm9meG1lWm9YcWJIWkdldyJ9.eyJhdWQiOiJhOGI4MmI0ZC0yYmJiLTQ1MDYtODRiYS01ZTYyZDZhNWYwMzEiLCJpc3MiOiJodHRwczovL2xvZ2luLm1pY3Jvc29mdG9ubGluZS5jb20vNDE4NzVmMmItMzNlOC00NjcwLTkyYTgtZjY0M2FmYmIyNDNhL3YyLjAiLCJpYXQiOjE2ODQwMDQ3NTMsIm5iZiI6MTY4NDAwNDc1MywiZXhwIjoxNjg0MDEwMDE3LCJhaW8iOiJBWVFBZS84VEFBQUFPZUtUTUoxN28xNGVJRENOcUtERDlqQjhqSGNmQlJiZHFnL2tzRnJETXI4Q0VmNXc5RXVVcFJlb1FUamlIZ2Z2L044azRONldpbVo3aHBwZ3RsS1FGYUpJamYzR2NSWFZucmhvRHpPWEpiUDlKRTRiOVVzTW9tbEVjZUZDRUVtUzdyNE1ORUNwSVdWZlU3Q0JHMExnb1gzZlpOK3V4Qy9SRzN0SHJaRzV5RTg9IiwiYXpwIjoiYThiODJiNGQtMmJiYi00NTA2LTg0YmEtNWU2MmQ2YTVmMDMxIiwiYXpwYWNyIjoiMCIsImN0cnkiOiJOTCIsImVtYWlsIjoiRWR3aW4uRXNzZW5pdXNAc2tmLmNvbSIsImZhbWlseV9uYW1lIjoiRXNzZW5pdXMiLCJnaXZlbl9uYW1lIjoiRWR3aW4iLCJuYW1lIjoiRWR3aW4gRXNzZW5pdXMiLCJvaWQiOiI2MmUyNDE4Mi1mMWJkLTRkOGYtYjI1NS1hMzdkYzg5NTJjYWQiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJFZHdpbi5Fc3Nlbml1c0Bza2YuY29tIiwicmgiOiIwLkFRd0FLMS1IUWVnemNFYVNxUFpEcjdza09rMHJ1S2k3S3daRmhMcGVZdGFsOERFTUFLYy4iLCJzY3AiOiJjYWxjdWxhdGUiLCJzdWIiOiJrZ05JYnRWbEc0UzkzZkhGcUYyRGtQenZOV3A3dzl4bGt4b1BjSGRoLUlnIiwidGlkIjoiNDE4NzVmMmItMzNlOC00NjcwLTkyYTgtZjY0M2FmYmIyNDNhIiwidXRpIjoiaUNJSjc4SVlIVXl2NjRmWDlwTVpBQSIsInZlciI6IjIuMCJ9.jRsoij-msc8C6W0I5b0aZd5dHU4E51F8RH6TG4YP190k6I1LmGVou2SKX4ZCPP8e-IbjmFolEewkYK4Bjefd_piW6k_B1CRzOR2TwgsfaQzQTXbujJFXkI4Wlb1Pg82FaeDV-ru_kzJYYsL65IB-jcXABulFuLWEDdahFSLxTaFDv4gayjCRgbwx3K2q6vOo2mVYXVk1PGz707--sWF9r4p8zbeN_u47v_8ICuagtKDJMUn6utDKuei3gLcchcqE14GJiIe9hN9UY8LcUfynRZ62MCiFY3R15T5TygirerCHl2mXWtz4hgt6duREUi2gZi7ivSem6CIXpQnhOcIlEw"
    jwt = JwtObject(token=token)
# TODO: Fix me . for Azure AD token use oid in stead oif sub
# assert jwt.get_user() == "62e24182-f1bd-4d8f-b255-a37dc8952cad"
    assert jwt.get_aud() == "a8b82b4d-2bbb-4506-84ba-5e62d6a5f031"
    assert jwt.get_iat() == 1684004753
    assert jwt.get_exp() == 1684010017
    assert jwt.get_email() == "Edwin.Essenius@skf.com"
    assert jwt.get_given_name() == "Edwin"
    assert jwt.get_family_name() == "Essenius"


# TODO Fix me as country is not selected property
# assert jwt.get_country() == "NL"
    # assert "SKFUsersGroup" in jwt.get_groups()
# TODO: Fix me. Expecting group calculate
# assert jwt.get_scope() == "calculate"
    # assert jwt.is_expired()


def test_is_skf_user():
    """Test the is skf user functionality"""
    my_token = {"email": "some.user@skf.com"}
    jwt = JwtObject()
    jwt.jwt = my_token
    assert jwt.is_skf_user()

    my_token = {"email": "some.user@skf.net"}
    jwt = JwtObject()
    jwt.jwt = my_token
    assert not jwt.is_skf_user()

    my_token = {"email": "test.automation.6309@gmail.com"}
    jwt = JwtObject()
    jwt.jwt = my_token
    assert jwt.is_skf_user()

    my_token = {"email": "test.automation.6310@gmail.com"}
    jwt = JwtObject()
    jwt.jwt = my_token
    assert not jwt.is_skf_user()


def test_is_reg_user():
    """Test the is registerd user"""
    my_token = {"email": "some.user@skf.com", "sub": str(uuid.uuid4())}
    jwt = JwtObject()
    jwt.jwt = my_token
    assert jwt.is_reg_user()

    my_token = {"email": "some.user@skf.net", "sub": f"an-{uuid.uuid4()}"}
    jwt = JwtObject()
    jwt.jwt = my_token
    assert not jwt.is_skf_user()


def test_trusted_system_token():
    my_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ik1HTHFqOThWTkxvWGFGZnBKQ0JwZ0I0SmFLcyJ9.eyJhdWQiOiJhOGI4MmI0ZC0yYmJiLTQ1MDYtODRiYS01ZTYyZDZhNWYwMzEiLCJpc3MiOiJodHRwczovL2xvZ2luLm1pY3Jvc29mdG9ubGluZS5jb20vNDE4NzVmMmItMzNlOC00NjcwLTkyYTgtZjY0M2FmYmIyNDNhL3YyLjAiLCJpYXQiOjE3MjI2MDAyMzQsIm5iZiI6MTcyMjYwMDIzNCwiZXhwIjoxNzIyNjA0MTM0LCJhaW8iOiJFMmRnWUhBei8ybDFtT1BpR3U3U3YvWU1xZTFML25heTNCWFJXdnhnNXVwSkpzZUZOWDBBIiwiYXpwIjoiZjgzZWE4ODUtYjlkNy00OWFiLTg1OTgtYWQxZTg2YjJhOWRiIiwiYXpwYWNyIjoiMiIsIm9pZCI6IjA1Yzc4ZGQyLTA1MTQtNDlhYy04ZWY5LTc3ZjI2NjE2ZTE1ZiIsInJoIjoiMC5BUXdBSzEtSFFlZ3pjRWFTcVBaRHI3c2tPazBydUtpN0t3WkZoTHBlWXRhbDhERU1BQUEuIiwic3ViIjoiMDVjNzhkZDItMDUxNC00OWFjLThlZjktNzdmMjY2MTZlMTVmIiwidGlkIjoiNDE4NzVmMmItMzNlOC00NjcwLTkyYTgtZjY0M2FmYmIyNDNhIiwidXRpIjoiZGVaNUg5cUFORWFZMU1ieWRNdUhBQSIsInZlciI6IjIuMCJ9.jq3FXWFhb7N1nSVzDjFmPreU1B6fS5HoMXOh4KhcRQ19jXUU4G-6SEIXGLElC471Gr2xU_Ke_sYRIqd0_55XK38nywAtdCu9N1gdQadSlJsnf5QZOCHOhDXud0BBcW_lzkO7taMMvjxRG7K10MmKlx_SoCUK6ycw1NSBpx5jTp1varkvEjyXI6qf-p5dLEL9sq6yLDLv-eryk9bBTlM5XYhhTG_Em2fIPxvy8H67MAM0ENSYlkZ_x7CC9JeaJoB1d4-yv_u34YDIl_0b5DdITUBMDGHRwuAwUI6_S1oDOvevrWTCP8bH2pRCh_N34KHasDnMPAGvaxnINupPwzdC9g"

    jwt = JwtObject(my_token)
    assert jwt.is_reg_user()
    assert not jwt.is_skf_user()
    assert jwt.get_aud() == "a8b82b4d-2bbb-4506-84ba-5e62d6a5f031"
    assert jwt.get_iat() == 1722600234
    assert jwt.get_exp() == 1722604134
    assert not jwt.get_email()
    assert not jwt.get_given_name()
    assert not jwt.get_family_name()

    # azp is authorized party - consider as user or use oid or sub?
    
