#!/usr/bin/env python

# Script to run temoa_model.py to create Price data for a 
# reference Demand for elastic demand case. The elasticities 
# are exogenous, and are supplied in this script.
# The Prices are the duals of the DemandConstraint constraints.
# The search range for the variable V_Demand, (MinDemand, MaxDemand)
# is determined using DEMAND_RANGE. The Price, MinDemand and MaxDemand
# are written to the file, price.dat.

# Usage: same as temoa_model.py.
# Addition output: writes file price.dat in the current directory.

DEMAND_RANGE = 0.3 # Max/MinDemand = (1 +/- DEMAND_RANGE)* Demand
DEMAND_SEGMENTS = 27  # Keep this an odd number to reproduce fixed demand results!

from temoa_model import temoa_create_model, temoa_create_model_container
from temoa_lib import temoa_solve
import sys

model = temoa_create_model()
model_data = temoa_create_model_container(model)
temoa_solve(model_data)
instance = model_data.instance
price_data = open("price.dat", "w")

ConstantDemandConstraint = instance.DemandConstraint
Demand = instance.Demand

print >> price_data, """\
data;

param: MinDemand    MaxDemand  :=
    # year      # min    # max
"""

for key in sorted(Demand.sparse_keys()):
    for l in key:
        print >> price_data, "%10s" % l,
    print >> price_data, "    %10g    %10g    " % \
        ((1 - DEMAND_RANGE) * Demand[key],
         (1 + DEMAND_RANGE) * Demand[key])
print >> price_data, "    ;\n"

print >> price_data, """\
param: Price    Elast:=
    # year   # season   # time_of_day   # demand    # price    # elasticity
"""

for key in sorted(ConstantDemandConstraint.keys()):
    for l in key:
        print >> price_data, "%20s" % l,
    price = ConstantDemandConstraint[key].dual
    print >> price_data, "    %10g   %10g" % \
        (price, 0.3)
    if 0.0 <= price <= 1.0e-6:
        print >> price_data, "Price too low! Aborting!!"
        print "Price too low! Aborting!!"
        sys.exit(1)
print >> price_data, "    ;\n"
print >> price_data, "param num_demand_segments := %d ;\
    # number of segments in the demand range" % DEMAND_SEGMENTS
