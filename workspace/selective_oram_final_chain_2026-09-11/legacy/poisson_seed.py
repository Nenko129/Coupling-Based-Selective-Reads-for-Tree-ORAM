#!/usr/bin/env python3
"""Rigorous rational exp(-3/2) bracket, no transcendental numerical calls."""
from fractions import Fraction
from pathlib import Path
import json, math

def make_seed(terms: int = 96) -> dict:
    x=Fraction(3,2); term=partial=Fraction(1)
    for k in range(1,terms+1):
        term=term*x/k; partial+=term
    first_omitted=term*x/(terms+1)
    remainder=first_omitted/(1-x/(terms+2))
    lo,hi=1/(partial+remainder),1/partial
    lf,hf=float(lo),float(hi)
    if Fraction.from_float(lf)>lo: lf=math.nextafter(lf,-math.inf)
    if Fraction.from_float(hf)<hi: hf=math.nextafter(hf,math.inf)
    assert Fraction.from_float(lf)<=lo<=hi<=Fraction.from_float(hf)
    return dict(rate_num=3,rate_den=2,terms=terms,lower_hex=lf.hex(),upper_hex=hf.hex(),
        proof='Positive Taylor sum plus geometric remainder upper bound; invert; round outward to dyadics.',
        rational_lower=[str(lo.numerator),str(lo.denominator)],
        rational_upper=[str(hi.numerator),str(hi.denominator)])
if __name__=='__main__':
    o=make_seed();b=Path(__file__).resolve().parent
    (b/'poisson_seed.json').write_text(json.dumps(o,indent=2))
    (b/'poisson_seed.h').write_text('#pragma once\nconstexpr double POISSON_ZERO_UPPER = '+o['upper_hex']+';\n')
    print(o['lower_hex'],o['upper_hex'])
