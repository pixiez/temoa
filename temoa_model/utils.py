
__all__ = ['results_writer']
#import sys
#import time
import types
from coopr.pyomo import *


def results_writer(results, instance, file=None, mode='w'):
    """\
results_writer is  a function that writes the results of solve process for the
temoa models.
NOTE: Some columns report None which is equivalent to no value (or NaN).
results_writer(instance,file=FILE, mode=MODE) takes the relevant
instance, results returned by the solver and prints the
1.  Solver summary
2. Objective,
3. Variables [lower bound, value, upper bound, reduced cost (if available)]
4. Constraints [lower bound, value, upper bound, dual (if available)]
in space delimited format. FILE is the name of the output file.
MODE is write mode: 'w' (write) or 'a' (append). The defaults are:
(FILE: results.txt, MODE: 'w')\
    """
    if file is not None:
        fp = open(file, mode)
    else:
        fp = open('results.txt', mode)

    instance.load(results)
    print >>fp, '\"', instance.name, '\"'
    print >>fp, '\"Model Documentation: ', instance.doc, '\"'
    print >>fp, '\"Solver Summary\"'
    print >>fp, '\"', results['Solver'][0], '\"'
    # Objective
    obj = instance.active_components(Objective)
    if len(obj) > 1:
        print >>fp, """
        Warning: More than one objective.  Using first objective.
        """
    print >>fp, "Objective\n", '\"Notes: ', obj[obj.keys()[0]].doc, '\"'

# This takes care of solvers that use the asl interface (nl problem files)
# which does not return objective values. We evaluate the Objective
# expression instead.
    print >>fp, "\"Value: %s\"" % (obj[obj.keys()[0]][None].expr())
    # Variables
    for v in instance.active_components(Var):
        varobject = getattr(instance, v)
        print >> fp, ""
        print >> fp, "\"Variable: %s\", \"Notes: %s\"" % (v, varobject.doc)
        print >> fp, "\"" + v + "\"", 'LOWER', 'VALUE', 'UPPER', 'REDUCED-COST'
    # Special condition for singleton Variable which has no index
        if type(varobject.index) is types.NoneType:
            print>>fp, "\"" + v + "\"", varobject.lb is None and '-INF' or varobject.lb, \
                varobject.value, varobject.ub is None and '+INF' or varobject.ub,
# FIXME: check if solver returned reduced cost. THIS IS EXPENSIVE: SHOULD CHECK ONLY ONCE!!
            try:
                print >> fp, varobject.get_suffix_value('Rc')
            except KeyError:
                print >> fp, 'NaN'
        else:
            keys = sorted(varobject.keys())
            for index in keys:
                print >> fp, "\"" + varobject[index].name + "\"", \
                    varobject[index].lb is None and '-INF' or varobject[index].lb, \
                    varobject[index].value, varobject[index].ub is None and '+INF' or varobject[index].ub,
# FIXME: check if solver returned reduced cost. THIS IS EXPENSIVE: SHOULD CHECK ONLY ONCE!!
                try:
                    print >> fp, varobject[index].get_suffix_value('Rc')
                except KeyError:
                    print >> fp, 'NaN'

    # Constraints (duals, if available)
#    print >> fp, "\n\nConstraints\n"
    for c in instance.active_components(Constraint):
        cobject = getattr(instance, c)
        print >> fp, ""
        print >> fp, "\"Constraint: %s\", \"Notes: %s\"" % (c, cobject.doc)
        print >> fp, "\"" + c + "\"", 'LOWER', 'VALUE', 'UPPER', 'DUAL'
    # Special condition for singleton Constraint which has no index
#        if type(cobject.index()) is dict and cobject.index().keys()[0] is None:
        if cobject.index is None:
            print >> fp, "\"" + cobject.name + "\"", \
                cobject.lower() is None and '-INF' or cobject.lower(), \
                cobject.body(), \
                cobject[None].upper is None and '+INF' or cobject[None].upper(), \
                cobject[None].dual
            #print "singleton"
            #print "\"" + cobject.name + "\"", \
            #cobject.lower() is None and '-INF' or cobject.lower(), \
            #cobject.body(), \
            #cobject[None].upper is None and '+INF' or cobject[None].upper(), \
            #cobject[None].dual
        else:
            keys = sorted(cobject.keys())
            for index in keys:
                print >> fp, "\"" + cobject[index].name + "\"", \
                cobject[index].lower is None and '-INF' or cobject[index].lower(), \
                cobject[index].body(), \
                cobject[index].upper is None and '+INF' or cobject[index].upper(), \
                cobject[index].dual
