# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Shim de retro-compatibilite.

Ce module a ete deplace vers `carnaval.recognizers.regex.address.fr`.
Les imports historiques continuent de fonctionner via cette redirection.

DEPRECATED : preferer
    from carnaval.recognizers.regex.address import recognize_address
"""

from carnaval.recognizers.regex.address.fr import (  # noqa: F401
    BP_PATTERN,
    POSTAL_CITY_PATTERN,
    STREET_GLUED_PATTERN,
    STREET_PATTERN_WITH_NUMBER,
    STREET_PATTERN_WITHOUT_NUMBER,
    ZONE_PATTERN,
    recognize_address_fr,
    recognize_bp,
    recognize_postal_city_fr,
    recognize_street_fr,
    recognize_zone_fr,
)
