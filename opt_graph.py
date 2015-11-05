#!python
# -*- coding: utf-8 -*-
# Copyright (c) 2014, Sven Thiele <sthiele78@gmail.com>
#
# This file is part of iggy.
#
# iggy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# iggy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with iggy.  If not, see <http://www.gnu.org/licenses/>.

from pyasp.asp import *
import argparse
from __iggy__ import query, utils, parsers

if __name__ == '__main__':
  desc = (
    'Opt-graph confronts a biological network given as interaction graphs with '
    'sets of experimental observations given as signs that represent the '
    'concentration changes between two measured states. Opt-graph computes the '
    'networks fitting the observation data by removing (or adding) a minimal '
    'number of edges in the given network')
  parser = argparse.ArgumentParser(description=desc)
  parser.add_argument('networkfile',
                      help='influence graph in SIF format')
  parser.add_argument('observationfiles',
                      help='directory of observations in bioquali format')

  parser.add_argument('--no_zero_constraints',
    help = "turn constraints on zero variations OFF, default is ON",
    action="store_true")

  parser.add_argument('--propagate_unambiguous_influences',
    help = 'turn constraints ON that if all predecessor of a node have the '
           'same influence this must have an effect, default is OFF',
    action="store_true")

  parser.add_argument('--no_founded_constraints',
    help='turn constraints OFF that every variation must be founded in an '
         'input, default is ON',
    action="store_true")

  parser.add_argument('--depmat_elem_path',
    help='do not use steady state assumption, instead a change must be '
         'explained by an elementary path from an input.',
    action="store_true")

  parser.add_argument('--depmat_some_path',
    help='do not use steady state assumption, instead a change must be '
         'explained by a path from an input.',
    action="store_true")

  parser.add_argument('--autoinputs',
    help='compute possible inputs of the network (nodes with indegree 0)',
    action='store_true')

  parser.add_argument('--show_repairs',type=int, default=-1,
    help="number of repairs to show, default is OFF, 0=all")

  parser.add_argument('--repair_mode', type=int, default=1,
    help='choose repair mode:\n'
	 ' 1 = add edges (default),\n'
	 ' 2 = add +remove edges (opt-graph),\n'
	 ' 3 = flip edges')


  args = parser.parse_args()

  net_string = args.networkfile
  obs_dir = args.observationfiles


  LC  = args.propagate_unambiguous_influences
  CZ  = not (args.no_zero_constraints)
  FC  = not (args.no_founded_constraints)
  SP  = args.depmat_some_path
  EP  = args.depmat_elem_path

  if SP :
    print(' * Not using steady state assumption, observed changes might be '
             'transient.')
    print(' * A path from an input must exist top explain changes.')
    SS = False
    LC = False
    CZ = False
    FC = False

  if EP :
    print(' * Not using steady state assumption, observed changes might be '
             'transient.')
    print(' * An elementary path from an input must exist top explain '
             'changes.')
    SS = False
    LC = False
    CZ = False
    FC = False

  if not (SP|EP):
    print(' * Using steady state assumption, all observed changes must be '
             'explained by an predecessor.')
    SS = True
    if LC  : print(' * Unambiguous influences must propagate.')
    if CZ  : print(' * No-change observations must be explained.')
    if FC  : print(' * All observed changes must be explained by an input.')


  print('\nReading network',net_string, '... ',end='')
  net = parsers.readSIFGraph(net_string)
  print('done.')

  # gather stats on the network

  activations = set()
  inhibitions = set()
  nodes=set()
  for a in net:
    if a.pred() == 'obs_elabel' :
      if a.arg(2) == '1'  : activations.add((a.arg(0),a.arg(1)))
      if a.arg(2) == '-1' : inhibitions.add((a.arg(0),a.arg(1)))
    if a.pred() == 'vertex' : nodes.add(a.arg(0))
  unspecified = activations & inhibitions
  print("   Nodes:", len(nodes),
    " Activations:", len(activations),
    " Inhibitions:", len(inhibitions),
           " Dual:", len(unspecified))


  flist = os.listdir(obs_dir)
  print('\nReading',len(flist),'observation sets from',obs_dir,'... ',end='')
  MU = TermSet()
  for f in flist :
    exp = os.path.join(obs_dir,f)
    mu  = parsers.readProfile(exp)
    MU  = TermSet(MU.union(mu))
  print('done.')

  print('\nChecking observations ... ',end='')
  contradictions = query.get_contradictory_obs(MU)
  print('done.')
  if len(contradictions) == 0 : print('   Observations are OK.')
  else:
    print('   Contradictory observations found. Please correct manually.')
    for c in contradictions : print('  ',c)
    utils.clean_up()
    exit()

  if args.autoinputs :
    print('\nComputing input nodes ... ',end='')
    inputs = query.guess_inputs(net)
    net    = TermSet(net.union(inputs))
    print('done.')
    print('   number of inputs:', len(inputs))

  net_with_data = TermSet(net.union(MU))

  if args.repair_mode==3 :
    print('\nComputing minimal number of flipped edges ... ',end='')
    (scenfit,repairs) = query.get_opt_flip_edges(net_with_data, SS, LC, CZ, FC, EP, SP)
    print('done.')
    print('   The network and data can reach a scenfit of',scenfit,'with',repairs,'flipped edges.')

    if args.show_repairs >= 0 and repairs > 0:
      print('\nCompute optimal repairs ... ',end='')
      repairs = query.get_opt_repairs_flip_edges(net_with_data,args.show_repairs, SS, LC, CZ, FC, EP, SP)
      print('done.')
      count=0
      for r in repairs :
        count += 1
        print('Repair ',str(count),':',sep='')
        utils.print_repairs(r)

  elif args.repair_mode==2 :
    print('\nComputing minimal number of changes add/remove edges ... ',end='')
    if EP :
      print('using greedy method ... ',end='')
      (scenfit,redges) = query.get_opt_add_remove_edges_greedy(net_with_data)
     
      print('done.')
      print('   The network and data can reach a scenfit of',scenfit)
      #      ,'with', repairs,'removals and ',len(edges),'additions.')

      count_repairs = 0

      if args.show_repairs >= 0 :
        print('\nCompute optimal repairs ... ',end='')
        print(' use greedily added edges')
        for (edges,repairs) in redges:
          if repairs > 0:
            repairs = query.get_opt_repairs_add_remove_edges_greedy(net_with_data,args.show_repairs,edges)
            print('done.')
            for r in repairs :
              count_repairs+=1
              print('Repair ',str(count_repairs),':',sep='')
              for e in edges:
                print('    addedge',str(e)[10:],sep='')
              utils.print_repairs(r)
          else:
            count_repairs+=1
            print('Repair',count_repairs,':',sep='')
            for e in edges:
              print('    addedge',str(e)[10:],sep='')          

    else : 
      (scenfit,repairscore) = query.get_opt_add_remove_edges(net_with_data, SS, LC, CZ, FC, EP, SP)
      print('done.')
      print('   The network and data can reach a scenfit of',scenfit,'with repairs of score',repairscore,'.')
  
      if args.show_repairs >= 0 and repairscore > 0:
        print('\nCompute optimal repairs ... ',end='')
        repairs = query.get_opt_repairs_add_remove_edges(net_with_data,args.show_repairs, SS, LC, CZ, FC, EP, SP)
        print('done.')
        count = 0
        for r in repairs :
          count += 1
          print('Repair ',str(count),':',sep='')
          utils.print_repairs(r)

  else: # repair_mode==1
    print('\nComputing minimal number of removed edges ... ',end='')
    (scenfit,repairs) = query.get_opt_remove_edges(net_with_data, SS, LC, CZ, FC, EP, SP)
    print('done.')
    print('   The network and data can reach a scenfit of',scenfit,'with',repairs,'removed edges.')

    if args.show_repairs >= 0 and repairs > 0:
      print('\nCompute optimal repairs ... ',end='')
      repairs = query.get_opt_repairs_remove_edges(net_with_data,args.show_repairs, SS, LC, CZ, FC, EP, SP)
      print('done.')
      count=0
      for r in repairs :
        count += 1
        print('Repair ',str(count),':',sep='')
        utils.print_repairs(r)

utils.clean_up()


