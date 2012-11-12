#!/usr/bin/env coopr_python

__all__ = ('temoa_create_model', )

from temoa_rules import *


def temoa_create_model(name='TEMOA Entire Energy System Economic Optimization Model'):
    """\
Returns an abstract instance of the TEMOA model.  (Abstract because it will yet
need to be populated with "dot dat" file data.)

Model characteristics:

A '*' next to a Set or Parameter indicates that it is automatically deduced.
It is not possible to directly set this Set or Parameter in a "dot dat" file.

SETS
time_exist   - the periods prior to the model.  Mainly utilized to populate the
           capacity of installed technologies prior to those the
           optimization is allowed to alter.
time_horizon - the periods of interest.  Though the model will optimize through
           time_future, Temoa will report results only for this set.
time_future  - the periods following time_horizon.
*time_optimize - the union of time_horizon and time_future, less the final
             period.  The model will optimize over this set.
*time_report - the union of time_exist and time_horizon.
*time_all    - the union of time_optimize and time_exist
*vintage_exist  - copy of time_exist, for unambiguous contextual use
*vintage_future - copy of time_future, for unambiguous contextual use
*vintage_all - a copy of time_all, for unambiguous contextual use.

time_season  - the seasons of interest.  For example, winter might have
           different cooling demand characteristics than summer.
time_of_day  - the parts of the day of interest.  For example, the night hours
           might have a different lighting demand than the daylight hours.

tech_resource   - "base" energy resources, like imported coal, imported
              electricity, or mined natural gas.
tech_production - technologies that convert energy, like a coal plant (coal to
              electricity), electric boiler (electricity to heat), or
              electric car (electricity to vehicle miles traveled)
*tech_all       - the union of tech_resource and tech_production

commodity_emissions - emission outputs of concern, like co2.
commodity_physical  - energy carriers, like coal, oil, or electricity
commodity_demand    - end use demands, like residential heating, commercial
                  lighting, or vehicle miles traveled
*commodity_all      - The union of commodity_{emissions, physical, demand}

PARAMETERS
ExistingCapacity(tech_all, vintage_exist)
[default: 0] ExistingCapacity allows the modeler to define any vintage of
existing technology prior to the model optimization periods.
Efficiency(commodity_all, tech_all, vintage_all, commodity_all)
[default: 0] Efficiency allows the modeler to define the efficiency
associated with a particular process, identified by an input commodity,
technology, vintage, and output commodity.
Lifetime(tech_all, vintage_all)
[default: 0] Lifetime enables the modeler to define the usable lifetime of
any particular
technology or vintage of technology.
Demand(time_optimize, time_season, time_of_day, commodity_demand)
Demand sets the exogenous amount of a commodity demand in each optimization
time period, season, and time of day.  In some sense, this is the parameter
that drives everything in the Temoa model.
ResourceBound(time_optimize, commodity_physical)
[default: 0] ResourceBound enables the modeler to set limits on how much of
a given resource the model may "mine" or "import" in any given optimization
period.
CommodityProductionCost(time_optimize, tech_all, vintage_all)
[default: 0] CommodityProductionCost enables the modeler to set the price
per unit to operate a technology.  The modeler may, for example, choose to
change the price to operate a vintage of a technology between optimization
periods.
CapacityFactor(tech_all, vintage_all)
[default: 0] CapacityFactor enables the modeler to set the capacity factor
for any vintage of technology.
    """
    M = AbstractModel(name)

    M.time_exist = Set(ordered=True, within=Integers)
    M.time_horizon = Set(ordered=True, within=Integers)
    M.time_future = Set(ordered=True, within=Integers)
    M.time_optimize = Set(ordered=True, initialize=init_set_time_optimize)
    M.time_all = M.time_exist | M.time_optimize

    # These next sets are just various copies of the time_ sets, but
    # unfortunately must be manually copied because of a few outstanding bugs
    # within Pyomo (Jul 2011)
    M.vintage_exist = Set(ordered=True, initialize=init_set_vintage_exist)
    M.vintage_future = Set(ordered=True, initialize=init_set_vintage_future)
    M.vintage_optimize = Set(ordered=True, initialize=init_set_vintage_optimize)
    M.vintage_all = Set(ordered=True, initialize=init_set_vintage_all)

	 # Use BuildAction to perform inter-Set or inter-Param validation
    M.validate_time = BuildAction(rule=validate_time)

    M.time_season = Set()
    M.time_of_day = Set()

    M.tech_resource = Set()
    M.tech_production = Set()
    M.tech_all = M.tech_resource | M.tech_production  # '|' = union operator
    M.tech_baseload = Set(within=M.tech_all)
    M.tech_storage = Set(within=M.tech_all)

    M.commodity_demand = Set()
    M.commodity_emissions = Set()
    M.commodity_physical = Set()

    M.commodity_carrier = M.commodity_physical | M.commodity_demand
    M.commodity_all = M.commodity_carrier | M.commodity_emissions

    M.GlobalDiscountRate = Param()
    M.PeriodLength = Param(M.time_optimize, initialize=ParamPeriodLength)
    M.PeriodRate = Param(M.time_optimize, initialize=ParamPeriodRate)

    M.SegFrac = Param(M.time_season, M.time_of_day)

    # Use BuildAction to perform inter-Set or inter-Param validation
    M.validate_SegFrac = BuildAction(rule=validate_SegFrac)

    M.CapacityToActivity = Param(M.tech_all, default=1)

    M.ExistingCapacity = Param(M.tech_all, M.vintage_exist)
    M.Efficiency = Param(M.commodity_physical, M.tech_all, M.vintage_all, M.commodity_carrier)

    M.CapacityFactor_sdtv = Set(dimen=4, rule=CapacityFactorIndices)
    M.CapacityFactor = Param(M.CapacityFactor_sdtv, default=1)

    M.LifetimeTech_tv = Set(dimen=2, rule=LifetimeTechIndices)
    M.LifetimeLoan_tv = Set(dimen=2, rule=LifetimeLoanIndices)
    M.LifetimeTech = Param(M.LifetimeTech_tv, default=30)  # in years
    M.LifetimeLoan = Param(M.LifetimeLoan_tv, default=10)  # in years

    # Use BuildAction like the validation hacks above.  Temoa uses a couple
    # of global variables to precalculate some oft-used results in constraint
    # generation.  This is therefore intentially placed after all Set and Param
    # definitions and initializations, but before the Var, Objectives, and
    # Constraints.
    M.IntializeProcessParameters = BuildAction(rule=InitializeProcessParameters)

    M.DemandDefaultDistribution = Param(M.time_season, M.time_of_day)
    M.DemandSpecificDistribution = Param(M.time_season, M.time_of_day, M.commodity_demand)
    M.Demand = Param(M.time_optimize, M.commodity_demand)

    # Use BuildAction: hack to perform Demand initialization and validation
    M.initialize_Demands = BuildAction(rule=CreateDemands)

    M.ResourceBound = Param(M.time_optimize, M.commodity_physical)

    M.CostFixed_ptv = Set(dimen=3, rule=CostFixedIndices)
    M.CostMarginal_ptv = Set(dimen=3, rule=CostMarginalIndices)
    M.CostInvest_tv = Set(dimen=2, rule=CostInvestIndices)
    M.CostFixed = Param(M.CostFixed_ptv)
    M.CostMarginal = Param(M.CostMarginal_ptv)
    M.CostInvest = Param(M.CostInvest_tv)

    M.Loan_tv = Set(dimen=2, rule=lambda M: M.CostInvest.keys())
    M.ModelLoanLife_tv = Set(dimen=2, rule=lambda M: M.CostInvest.keys())
    M.ModelTechLife_tv = Set(dimen=3, rule=ModelTechLifeIndices)
    M.ModelLoanLife = Param(M.ModelLoanLife_tv, rule=ParamModelLoanLife_rule)
    M.ModelTechLife = Param(M.ModelTechLife_tv, rule=ParamModelTechLife_rule)

    M.DiscountRate_tv = Set(dimen=2, rule=lambda M: M.CostInvest.keys())
    M.LoanLifeFrac_ptv = Set(dimen=3, rule=LoanLifeFracIndices)
    M.TechLifeFrac_ptv = Set(dimen=3, rule=TechLifeFracIndices)

    M.DiscountRate = Param(M.DiscountRate_tv, default=0.05)
    M.TechLifeFrac = Param(M.TechLifeFrac_ptv, rule=ParamTechLifeFraction_rule)
    M.LoanAnnualize = Param(M.Loan_tv, rule=ParamLoanAnnualize_rule)

    M.TechOutputSplit = Param(M.commodity_physical, M.tech_all, M.commodity_carrier)

    # Use BuildAction to perform inter-Set or inter-Param validation
    M.validate_TechOutputSplit = BuildAction(rule=validate_TechOutputSplit)

    M.MinCapacity = Param(M.time_optimize, M.tech_all)
    M.MaxCapacity = Param(M.time_optimize, M.tech_all)

    M.EmissionLimit = Param(M.time_optimize, M.commodity_emissions)
    M.EmissionActivity_eitvo = Set(dimen=5, rule=EmissionActivityIndices)
    M.EmissionActivity = Param(M.EmissionActivity_eitvo)

    M.ActivityVar_psdtv = Set(dimen=5, rule=ActivityVariableIndices)
    M.ActivityByPeriodTechAndVintageVar_ptv = Set(
        dimen=3, rule=ActivityByPeriodTechAndVintageVarIndices)

    M.CapacityVar_tv = Set(dimen=2, rule=CapacityVariableIndices)
    M.CapacityAvailableVar_pt = Set(
        dimen=2, rule=CapacityAvailableVariableIndices)

    M.FlowVar_psditvo = Set(dimen=7, rule=FlowVariableIndices)

    # Variables
    #   Base decision variables
    M.V_FlowIn = Var(M.FlowVar_psditvo, domain=NonNegativeReals)
    M.V_FlowOut = Var(M.FlowVar_psditvo, domain=NonNegativeReals)

    #   Derived decision variables
    M.V_Activity = Var(M.ActivityVar_psdtv, domain=NonNegativeReals)

    M.V_Capacity = Var(M.CapacityVar_tv, domain=NonNegativeReals)

    M.V_ActivityByPeriodTechAndVintage = Var(
        M.ActivityByPeriodTechAndVintageVar_ptv,
        domain=NonNegativeReals
    )

    M.V_CapacityAvailableByPeriodAndTech = Var(
        M.CapacityAvailableVar_pt,
        domain=NonNegativeReals
    )

    M.V_CapacityInvest = Var(M.CapacityVar_tv, domain=NonNegativeReals)
    M.V_CapacityFixed = Var(M.CapacityVar_tv, domain=NonNegativeReals)

    AddReportingVariables(M)

    M.BaseloadDiurnalConstraint_psdtv = Set(
        dimen=5, rule=BaseloadDiurnalConstraintIndices)
    M.CapacityByOutputConstraint_psdtvo = Set(
        dimen=6, rule=CapacityByOutputConstraintIndices)
    M.CommodityBalanceConstraint_psdc = Set(
        dimen=4, rule=CommodityBalanceConstraintIndices)
    M.DemandConstraint_psdc = Set(dimen=4, rule=DemandConstraintIndices)
    M.DemandActivityConstraint_psdtv_dem_s0d0 = Set(dimen=8, rule=DemandActivityConstraintIndices)
    M.ExistingCapacityConstraint_tv = Set(
        dimen=2, rule=lambda M: M.ExistingCapacity.sparse_iterkeys())
    M.FractionalLifeActivityLimitConstraint_psdtvo = Set(
        dimen=6, rule=FractionalLifeActivityLimitConstraintIndices)
    M.MaxCapacityConstraint_pt = Set(
        dimen=2, rule=lambda M: M.MaxCapacity.sparse_iterkeys())
    M.MinCapacityConstraint_pt = Set(
        dimen=2, rule=lambda M: M.MinCapacity.sparse_iterkeys())
    M.ProcessBalanceConstraint_psditvo = Set(
        dimen=7, rule=ProcessBalanceConstraintIndices)
    M.ResourceConstraint_pr = Set(
        dimen=2, rule=lambda M: M.ResourceBound.sparse_iterkeys())
    M.StorageConstraint_psitvo = Set(dimen=6, rule=StorageConstraintIndices)
    M.TechOutputSplitConstraint_psditvo = Set(
        dimen=7, rule=TechOutputSplitConstraintIndices)

    M.EmissionLimitConstraint_pe = Set(
        dimen=2, rule=lambda M: M.EmissionLimit.sparse_iterkeys())

    # Objective
    M.TotalCost = Objective(rule=TotalCost_rule, sense=minimize)

    # Constraints

    #   "Bookkeeping" constraints
    M.ActivityConstraint = Constraint(M.ActivityVar_psdtv, rule=Activity_Constraint)
    M.ActivityByPeriodTechAndVintageConstraint = Constraint(M.ActivityByPeriodTechAndVintageVar_ptv, rule=ActivityByPeriodTechAndVintage_Constraint)

    M.CapacityConstraint = Constraint(M.ActivityVar_psdtv, rule=Capacity_Constraint)

    M.ExistingCapacityConstraint = Constraint(M.ExistingCapacityConstraint_tv, rule=ExistingCapacity_Constraint)

    M.CapacityInvestConstraint = Constraint(M.CapacityVar_tv, rule=CapacityInvest_Constraint)
    M.CapacityFixedConstraint = Constraint(M.CapacityVar_tv, rule=CapacityFixed_Constraint)

    #   Model Constraints
    #    - in driving order.  (e.g., without Demand, none of the others are
    #      very useful.)
    M.DemandConstraint = Constraint(M.DemandConstraint_psdc, rule=Demand_Constraint)
    M.DemandActivityConstraint = Constraint(M.DemandActivityConstraint_psdtv_dem_s0d0, rule=DemandActivity_Constraint)
    M.ProcessBalanceConstraint = Constraint(M.ProcessBalanceConstraint_psditvo, rule=ProcessBalance_Constraint)
    M.CommodityBalanceConstraint = Constraint(M.CommodityBalanceConstraint_psdc, rule=CommodityBalance_Constraint)

    M.ResourceExtractionConstraint = Constraint(M.ResourceConstraint_pr, rule=ResourceExtraction_Constraint)

    M.BaseloadDiurnalConstraint = Constraint(M.BaseloadDiurnalConstraint_psdtv, rule=BaseloadDiurnal_Constraint)

    M.StorageConstraint = Constraint(M.StorageConstraint_psitvo, rule=Storage_Constraint)

    M.TechOutputSplitConstraint = Constraint(M.TechOutputSplitConstraint_psditvo, rule=TechOutputSplit_Constraint)

    M.CapacityAvailableByPeriodAndTechConstraint = Constraint(M.CapacityAvailableVar_pt, rule=CapacityAvailableByPeriodAndTech_Constraint)

    M.FractionalLifeActivityLimitConstraint = Constraint(M.FractionalLifeActivityLimitConstraint_psdtvo, rule=FractionalLifeActivityLimit_Constraint)

    M.MinCapacityConstraint = Constraint(M.MinCapacityConstraint_pt, rule=MinCapacity_Constraint)
    M.MaxCapacityConstraint = Constraint(M.MaxCapacityConstraint_pt, rule=MaxCapacity_Constraint)

    M.EmissionLimitConstraint = Constraint(M.EmissionLimitConstraint_pe, rule=EmissionLimit_Constraint)

    return M


model = temoa_create_model()


if '__main__' == __name__:
    # This script was apparently invoked directly, rather than through Pyomo.
    # $ ./model.py  test.dat           # called directly
    # $ lpython  model.py  test.dat    # called directly
    # $ pyomo    model.py  test.dat    # through Pyomo

    # Calling this script directly enables a cleaner formatting than Pyomo's
    # default output, but (currently) forces the choice of solver to GLPK.
    from temoa_lib import temoa_solve
    temoa_solve(model)
