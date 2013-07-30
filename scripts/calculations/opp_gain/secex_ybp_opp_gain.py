# -*- coding: utf-8 -*-
"""
    Calculate opportunity gain (using domestic RCA)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This script utilizes the growth library to calculate opportunity gain
    according to the atlas method. The script takes the following steps:
     - calculates RCA for given year and geo level (state, meso, micro, munic)
     - calculates proximity based on RCA matrix
     - calculates complexity based on RCA matrix
     - calculates opportunity gain based on RCAs, proximities and complexities
     - erases current oppotunity gain values in DB
     - adds new opportunity gain values to DB
"""

import MySQLdb, os, argparse
import pandas as pd, pandas.io.sql as sql
import numpy as np
import sys

from os import environ

this_dir = os.path.abspath(os.path.dirname(__file__))
base_dir = os.path.abspath(os.path.join(this_dir, '../../../'))

growth_lib_dir = os.path.abspath(os.path.join(base_dir, 'scripts/growth_lib/'))
sys.path.append(growth_lib_dir)
import growth

rca_dir = os.path.abspath(os.path.join(base_dir, 'scripts/calculations/rca/'))
sys.path.append(rca_dir)
import secex_ybp_rca

# print secex_ybp_rca.get_rca(2011, 2).ix["mg"]

''' Connect to DB '''
db = MySQLdb.connect(host="localhost", user=environ["VISUAL_DB_USER"], 
                        passwd=environ["VISUAL_DB_PW"], 
                        db=environ["VISUAL_DB_NAME"])
db.autocommit(1)
cursor = db.cursor()

def delete_old_opp_gain_from_db(year, geo_level):
    '''clear old opp_gain vals'''
    q = "update secex_ybp set opp_gain=NULL " \
        "where year = {0} and length(bra_id) = {1} and " \
        "length(hs_id) = 6".format(year, geo_level)
    cursor.execute(q)

def add_new_opp_gain_to_db(year, opp_gain):
    '''add new opp_gain vals'''
    for hs in opp_gain.columns:
        to_add = []
        for bra in opp_gain.index:
            to_add.append([opp_gain[hs][bra], year, bra, hs])
        cursor.executemany("update secex_ybp set opp_gain=%s where year=%s " \
                                "and bra_id=%s and hs_id=%s", to_add)

def calculate_opp_gain(year, geo_level):
    
    '''step 1 in calculating opportunity gain, get RCA'''
    print "Calculating RCAs..."
    rca = secex_ybp_rca.get_rca(year, geo_level)
    '''conver nominal RCA values to 0s and 1s'''
    rca[rca >= 1] = 1
    rca[rca < 1] = 0
    
    '''calculate proximity for opportunity gain calculation'''
    print "Calculating proximities..."
    proximity = growth.proximity(rca)
    
    '''calculate product complexity'''
    print "Calculating complexity..."
    pci = growth.complexity(rca)[1]
    
    '''calculate opportunity gain'''
    print "Calculating opportunity gain..."
    opp_gain = growth.opportunity_gain(rca, proximity, pci)
    
    '''delete database'''
    print "Deleteing old opportunity gain values..."
    delete_old_opp_gain_from_db(year, geo_level)
    
    '''delete database'''
    print "Adding new opportunity gain values..."
    add_new_opp_gain_to_db(year, opp_gain)

def get_all_years():
    '''Get all years in the database'''
    cursor.execute("select distinct year from secex_ybp")
    years = [row[0] for row in cursor.fetchall()]
    return years

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-y", "--year", help="year for calculations to be run")
    parser.add_argument("-g", "--geo_level", help="level of geo nesting",
                            choices=['2', '4', '6', '8', 'all'])
    args = parser.parse_args()
    
    year = args.year
    if not year:
        year = raw_input("Year for calculations (or all): ")
    if year == "all":
        year = get_all_years()
    else:
        year = [int(year)]
    
    geo_level = args.geo_level
    if not geo_level:
        geo_level = raw_input("Geo Level {2:state, 4:meso, 6:micro, " \
                                "8:munic, all}: ")
    if geo_level == "all":
        geo_level = range(2, 10, 2)
    else:
        geo_level = [geo_level]
    
    for y in year:
        print
        print "Year: {0}".format(y);
        for g in geo_level:
            print
            print " --- Geo Level: {0} --- ".format(g);
            calculate_opp_gain(y, g)