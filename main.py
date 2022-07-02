from kivy.lang import Builder
import os
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, Screen

import base64
import ctypes
import json
import random
import ssl
import sys
import warnings
from typing import Dict, List, Optional, Sequence, Tuple, Union
from urllib.parse import parse_qsl, urlsplit
import aiohttp

class MainWindow(Screen):
    pass


class LoginWindow(Screen):
    pass


class WindowManager(ScreenManager):
    pass


class App(MDApp):

    def build(self):
        self.theme_cls.material_style = "M3"
        return Builder.load_string(
            '''
#:import get_color_from_hex kivy.utils.get_color_from_hex

WindowManager:
    MainWindow:
    LoginWindow:

<MainWindow>:
    name: 'main'
    MDBottomNavigation:
        panel_color: get_color_from_hex("#eeeaea")
        selected_color_background: get_color_from_hex("#97ecf8")
        text_color_active: 0, 0, 0, 1

        MDBottomNavigationItem:
            name: 'screen 1'
            text: 'Shop'
            icon: 'shopping-outline'
            badge_icon: "numeric-10"

            MDLabel:
                text: 'Shop'
                halign: 'center'

        MDBottomNavigationItem:
            name: 'screen 2'
            text: 'Matches'
            icon: "format-list-bulleted"
            badge_icon: "numeric-5"

            MDLabel:
                text: 'Matches'
                halign: 'center'

        MDBottomNavigationItem:
            name: 'screen 3'
            text: 'Accounts'
            icon: "account-circle"

            MDLabel:
                
                text: 'Accounts'
                halign: 'center'
                
            MDFlatButton:
                theme_text_color: "Custom"
                text_color: 0, 0, 1, 1
                text: "Submit"
                on_release:
                    app.root.current = "login"
                    root.manager.transition.direction = "left"


<LoginWindow>:
    name: 'login'
    FloatLayout:
        size: root.width, root.height
        MDTextField:
            id: user
            mode: "rectangle"
            helper_text_mode: "persistent"
            hint_text: "Riot Username"
            size_hint : 0.4, 0.1
            halign: 'center'
            pos_hint : {"x":0.3, "top":0.65}
        MDTextField:
            id: passwd
            mode: "rectangle"
            helper_text_mode: "persistent"
            hint_text: "Riot Password"
            halign: 'center'
            size_hint : 0.4, 0.1
            pos_hint : {"x":0.3, "top":0.55}
        MDFlatButton:
            theme_text_color: "Custom"
            text_color: 0, 0, 1, 1
            text: "Submit"
            halign: 'center'
            size_hint : 0.25, 0.1
            pos_hint : {"x":0.375, "top":0.45}
            on_release:
                app.confirm_creds(user=user.text, passwd=passwd.text)
                root.manager.transition.direction = "down"
'''
    )
    def confirm_creds(self, user, passwd):
        print('userid')
        print(user)
        print('pass')
        print(passwd)

class RiotAuth:
    RIOT_CLIENT_USER_AGENT = (
        "RiotClient/53.0.0.4494832.4470164 %s (Windows;10;;Professional, x64)"
    )
    CIPHERS13 = ":".join(  # https://docs.python.org/3/library/ssl.html#tls-1-3
        (
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_AES_128_GCM_SHA256",
            "TLS_AES_256_GCM_SHA384",
        )
    )
    CIPHERS = ":".join(
        (
            "ECDHE-ECDSA-CHACHA20-POLY1305",
            "ECDHE-RSA-CHACHA20-POLY1305",
            "ECDHE-ECDSA-AES128-GCM-SHA256",
            "ECDHE-RSA-AES128-GCM-SHA256",
            "ECDHE-ECDSA-AES256-GCM-SHA384",
            "ECDHE-RSA-AES256-GCM-SHA384",
            "ECDHE-ECDSA-AES128-SHA",
            "ECDHE-RSA-AES128-SHA",
            "ECDHE-ECDSA-AES256-SHA",
            "ECDHE-RSA-AES256-SHA",
            "AES128-GCM-SHA256",
            "AES256-GCM-SHA384",
            "AES128-SHA",
            "AES256-SHA",
            "DES-CBC3-SHA",  # most likely not available
        )
    )
    SIGALGS = ":".join(
        (
            "ecdsa_secp256r1_sha256",
            "rsa_pss_rsae_sha256",
            "rsa_pkcs1_sha256",
            "ecdsa_secp384r1_sha384",
            "rsa_pss_rsae_sha384",
            "rsa_pkcs1_sha384",
            "rsa_pss_rsae_sha512",
            "rsa_pkcs1_sha512",
            "rsa_pkcs1_sha1",  # will get ignored and won't be negotiated
        )
    )

    def __init__(self) -> None:
        self._auth_ssl_ctx = RiotAuth.create_riot_auth_ssl_ctx()
        self.access_token: Optional[str] = None
        self.scope: Optional[str] = None
        self.id_token: Optional[str] = None
        self.token_type: Optional[str] = None
        self.expires_at: int = 0
        self.user_id: Optional[str] = None
        self.entitlements_token: Optional[str] = None

    @staticmethod
    def create_riot_auth_ssl_ctx() -> ssl.SSLContext:
        ssl_ctx = ssl.create_default_context()

        # https://github.com/python/cpython/issues/88068
        addr = id(ssl_ctx) + sys.getsizeof(object())
        ssl_ctx_addr = ctypes.cast(addr, ctypes.POINTER(ctypes.c_void_p)).contents

        if sys.platform == "win32":
            libssl = ctypes.CDLL("libssl-1_1.dll")
        elif sys.platform.startswith("linux"):
            libssl = ctypes.CDLL(ssl._ssl.__file__)
        else:
            raise NotImplementedError(
                "Only Windows (win32) and Linux (linux) are supported atm."
            )

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1
        ssl_ctx.set_alpn_protocols(["http/1.1"])
        ssl_ctx.options |= 1 << 19  # SSL_OP_NO_ENCRYPT_THEN_MAC
        libssl.SSL_CTX_set_ciphersuites(ssl_ctx_addr, RiotAuth.CIPHERS13.encode())
        libssl.SSL_CTX_set_cipher_list(ssl_ctx_addr, RiotAuth.CIPHERS.encode())
        # setting SSL_CTRL_SET_SIGALGS_LIST
        libssl.SSL_CTX_ctrl(ssl_ctx_addr, 98, 0, RiotAuth.SIGALGS.encode())

        # print([cipher["name"] for cipher in ssl_ctx.get_ciphers()])
        return ssl_ctx

    def update(
        self,
        extract_jwt: bool = False,
        keys_attr_pairs: Sequence[Tuple[str, str]] = (
            ("sub", "user_id"),
            ("exp", "expires_at"),
        ),
        **kwargs,
    ) -> None:
        # ONLY PREDEFINED PUBLIC KEYS ARE SET! (see __init__()), rest is silently ignored
        predefined_keys = [key for key in self.__dict__.keys() if key[0] != "_"]

        self.__dict__.update(
            (key, val) for key, val in kwargs.items() if key in predefined_keys
        )

        if extract_jwt:  # extract additional data from JWT
            additional_data = self.get_keys_from_access_token(keys_attr_pairs)
            self.__dict__.update(
                (key, val) for key, val in additional_data if key in predefined_keys
            )

    def get_keys_from_access_token(
        self, keys_attr_pairs: Sequence[Tuple[str, str]]
    ) -> List[
        Tuple[str, Union[str, int, List, Dict, None]]
    ]:  # List[Tuple[str, JSONType]]
        payload = self.access_token.split(".")[1]
        decoded = base64.urlsafe_b64decode(payload + "===")
        temp_dict: Dict = json.loads(decoded)
        return [(attr, temp_dict.get(key)) for key, attr in keys_attr_pairs]

    @staticmethod
    def generate_random_string(
        length: int = 22,
        chars: str = "_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    ) -> str:
        return "".join(random.choice(chars) for _ in range(length))

    async def authorize(
        self, username: str, password: str, use_query_response_mode: bool = False
    ) -> None:
        conn = aiohttp.TCPConnector(ssl=self._auth_ssl_ctx)
        async with aiohttp.ClientSession(
            connector=conn, raise_for_status=True
        ) as session:
            headers = {
                "Accept-Encoding": "deflate, gzip, zstd",
                "user-agent": RiotAuth.RIOT_CLIENT_USER_AGENT % "rso-auth",
                "Cache-Control": "no-cache",
                "Accept": "application/json",
            }
            body = {
                "acr_values": "",
                "claims": "",
                "client_id": "riot-client",
                "code_challenge": "",
                "code_challenge_method": "",
                "nonce": RiotAuth.generate_random_string(22),
                "redirect_uri": "http://localhost/redirect",
                "response_type": "token id_token",
                "scope": "openid link ban lol_region account",
            }
            if use_query_response_mode:
                body["response_mode"] = "query"
            async with session.post(
                "https://auth.riotgames.com/api/v1/authorization",
                json=body,
                headers=headers,
            ) as r:
                ...

            body = {
                "language": "en_US",
                "password": password,
                "region": None,
                "remember": False,
                "type": "auth",
                "username": username,
            }
            async with session.put(
                "https://auth.riotgames.com/api/v1/authorization",
                json=body,
                headers=headers,
            ) as r:
                data: Dict = await r.json()
                type_ = data["type"]
                if type_ == "response":
                    ...
                elif type_ == "auth":
                    raise RuntimeError(f"Wrong credentials; `{data.get('error')}`.")
                elif type_ == "multifactor":
                    raise NotImplementedError(
                        "Multifactor authentication is not supported."
                    )
                else:
                    raise NotImplementedError(
                        f"Unhandled type returned during authentication: `{type_}`."
                    )

            mode = data["response"]["mode"]
            uri = data["response"]["parameters"]["uri"]

            result = getattr(urlsplit(uri), mode)
            data = dict(parse_qsl(result))
            self.update(extract_jwt=True, **data)

            headers["Authorization"] = f"{self.token_type} {self.access_token}"

            async with session.post(
                "https://entitlements.auth.riotgames.com/api/token/v1",
                headers=headers,
                json={},
                # json={"urn": "urn:entitlement:%"},
            ) as r:
                entitlements_resp = await r.json()
                self.entitlements_token = entitlements_resp["entitlements_token"]



App().run()