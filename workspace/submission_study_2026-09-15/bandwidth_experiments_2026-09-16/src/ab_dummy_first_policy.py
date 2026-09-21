"""Explicit CB policy: target, otherwise an unused dummy, otherwise green.

AB-ORAM section III-C describes using green when reserved dummies run out;
String ORAM permits either selection while the green quota is available.
This policy is distinct from the preserved uniform-unused CB implementation.
It is not a strict-dummy guarantee: a full D=0 bucket can require green.
"""
from cb_oram import need


def eligible_slots(c,h,address):
    matches=tuple(j for j,x in h.live.items() if x.address==address)
    need(len(matches)<=1,'multiple target slots')
    if matches:return matches
    unused=tuple(j for j in range(c.n) if not(h.used>>j&1))
    dummy=tuple(j for j in unused if j not in h.live)
    if dummy:return dummy
    need(h.green<c.Y and bool(unused),'no CB dummy or permitted green slot')
    return unused
