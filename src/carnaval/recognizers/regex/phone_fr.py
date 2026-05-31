# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Shim de retro-compatibilite.

Ce module a ete deplace vers `carnaval.recognizers.regex.phone.fr`.

DEPRECATED : preferer
    from carnaval.recognizers.regex.phone import recognize_phone
"""

from carnaval.recognizers.regex.phone.fr import (  # noqa: F401
    PHONE_FR_PATTERN,
    recognize_phone_fr,
)
