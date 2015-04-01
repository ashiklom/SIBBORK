"""
Investigate a results HDF files generated by SibBork.
"""

import numpy as np
import h5py
import dill
from math import *


###################################################
###################
# TODO : move this into a helper file
###################
import numba
#import numba_dummy as numba
import inspect


def add_species_specific_ufuncs(driver):
    # go through all of the species specific functions and use numba to create numpy ufuncs for them
    # all ufuncs that were created are under the name ORIG_KEY+_ufn
    for species in driver['species']:
        if driver['species'][species]['ENABLED']:
            for key in driver['species'][species]:
                # only vectorize values that are functions
                # Note! it is assumed that all functions accept float64(s) and return a single float64
                if type(driver['species'][species][key]) == type(lambda: None):
                    fn = driver['species'][species][key]
                    args, varargs, varkw, defaults = inspect.getargspec(fn)
                    nargs = len(args)
                    args_str = 'float64, ' * nargs
                    #driver['species'][species][key+'_ufn'] = numba.vectorize('float64(%s)' % args_str)(fn)
                    driver['species'][species][key] = numba.vectorize('float64(%s)' % args_str)(fn)
    return driver

def add_species_specific_ufuncs_numpy(driver):
    # go through all of the species specific functions and use numba to create numpy ufuncs for them
    # all ufuncs that were created are under the name ORIG_KEY+_ufn
    for species in driver['species']:
        for key in driver['species'][species]:
            # only vectorize values that are functions
            # Note! it is assumed that all functions accept float64(s) and return a single float64
            if type(driver['species'][species][key]) == type(lambda: None):
                fn = driver['species'][species][key]
                args, varargs, varkw, defaults = inspect.getargspec(fn)
                nargs = len(args)
                args_str = 'float64, ' * nargs
                driver['species'][species][key] = np.vectorize(fn) #numba.vectorize('float64(%s)' % args_str)(fn)
    return driver

###################################################


def load_driver(hdf_filename, vectorize=None):
    # open the h5 file that the simulation was dumped to
    h5file = h5py.File(hdf_filename, "r")
    # load the driver code (from a string of the original driver file)

    # load the driver from the (dill) pickled representation in the hdf file
    driver = dill.loads( np.array(h5file['driver']).tostring() )
    #print driver.keys()
    info = ''
    info += '##################################################\n'
    info += 'Driver from : %s\n' %(hdf_filename)
    info += '##################################################\n'
    info += 'Simulation : %s\n' %(driver['TITLE'])
    NWx, NWy = driver['north_west_corner_coordinates']
    info += 'Location : %s [%s W, %s N]\n' %(driver['LOCALE'], NWx, NWy)
    info += 'Simulation Area : %s Ha\n' % driver['sim_area_ha']
    info += '%s X %s Plots with %s trees per Plot\n' %(driver['EW_number_of_plots'], driver['NS_number_of_plots'], driver['MAX_TREES_PER_PLOT'])
    info += 'Max Number of Trees in Simulation : %s trees\n' % driver['max_trees_in_simulation']
    info += 'Plot Size = %s m X %s m = %s m^2\n' % (driver['EW_plot_length_m'], driver['NS_plot_length_m'], driver['plot_area_m2'])
    info += 'Start Year = %s, Stop Year = %s\n' % (driver['sim_start_year'], driver['sim_stop_year'])
    info += 'Number of Species in Simulation : %s\n' % len(driver['name_to_species_code'].keys())
    info += 'Species in Simulation :  (species name : species code)\n'
    for species_name, species_code in driver['name_to_species_code'].items():
        info += '  %s : %s\n' %(species_name, species_code)
    info += 'Specific Simulation Information :: \n%s\n' % driver['run_description']
    info += '##################################################\n'
    if vectorize:
        if vectorize == "numba":
            driver = add_species_specific_ufuncs(driver)
        elif vectorize == "numpy":
            driver = add_species_specific_ufuncs_numpy(driver)
        else:
            raise Exception("Unknown vectorize type %s." % vectorize)

    return driver, h5file, info


def compute_results_biovolume(h5file, driver, min_dbh=0.0, mask=None):
    years_in_sim_lst, \
    year_agg_mat, \
    num_species = compute_results_vs_time(h5file, driver,
                                          fn_key='BIOVOLUME_EQUATION',
                                          normalize_value=driver['sim_area_ha'],
                                          min_dbh=min_dbh,
                                          mask=mask)
    return years_in_sim_lst, year_agg_mat, num_species

def compute_results_biomass(h5file, driver, min_dbh=0.0, mask=None):
    years_in_sim_lst, \
    year_agg_mat, \
    num_species = compute_results_vs_time(h5file, driver,
                                          fn_key='BIOMASS_EQUATION',
                                          normalize_value=driver['sim_area_ha'],
                                          min_dbh=min_dbh,
                                          mask=mask)
    return years_in_sim_lst, year_agg_mat, num_species

def compute_results_leaf_area(h5file, driver, min_dbh=0.0, mask=None):
    years_in_sim_lst, \
    year_agg_mat, \
    num_species = compute_results_vs_time(h5file, driver,
                                          fn_key='LEAF_AREA_EQUATION',
                                          normalize_value=driver['sim_area_ha'],
                                          min_dbh=min_dbh,
                                          mask=mask)
    return years_in_sim_lst, year_agg_mat, num_species

# TODO: foliar biomass

def compute_results_basal_area(h5file, driver, min_dbh=0.0, mask=None):
    years_in_sim_lst, \
    year_agg_mat, \
    num_species = compute_results_vs_time(h5file, driver,
                                          fn_key='BASAL_AREA_EQUATION',
                                          normalize_value=driver['sim_area_ha'],
                                          min_dbh=min_dbh,
                                          mask=mask)
    return years_in_sim_lst, year_agg_mat, num_species


def compute_results_stems(h5file, driver, min_dbh=0.0, mask=None):
    def count_stems_fn(dbh_vec):
        return np.count_nonzero(dbh_vec)

    years_in_sim_lst, \
    year_agg_mat, \
    num_species = compute_results_vs_time(h5file, driver,
                                          func=count_stems_fn,
                                          normalize_value=driver['sim_area_ha'],
                                          min_dbh=min_dbh,
                                          mask=mask)
    return years_in_sim_lst, year_agg_mat, num_species


def compute_results_average_dbh(h5file, driver, min_dbh=0.0, mask=None):
    def avg_dbh_fn(dbh_vec):
        if np.any(dbh_vec):
            return np.mean(dbh_vec)
        else:
            return 0.0

    years_in_sim_lst, \
    year_agg_mat, \
    num_species = compute_results_vs_time(h5file, driver,
                                          func=avg_dbh_fn,
                                          aggregate_fn=np.mean,
                                          normalize_value=1.0,
                                          min_dbh=min_dbh,
                                          mask=mask)
    return years_in_sim_lst, year_agg_mat, num_species


def compute_results_average_height(h5file, driver, min_dbh=0.0, mask=None):
    years_in_sim_lst, \
    year_agg_mat, \
    num_species = compute_results_vs_time(h5file, driver,
                                          fn_key='TREE_HEIGHT_EQUATION',
                                          aggregate_fn=np.mean,
                                          normalize_value=1.0,
                                          min_dbh=min_dbh,
                                          mask=mask)
    return years_in_sim_lst, year_agg_mat, num_species


def compute_results_loreys_height(h5file, driver, min_dbh=0.0, mask=None):

    """
    Compute Lorey's mean height and return a time series by species.

    Parameters : h5file -- storage of model output by year, plot, species, tree
                 driver -- dictionary containing initial conditions, site & species-specific parameters
                 min_dbh -- only use trees with a dbh larger than this value
                 mask -- T/F array (DEM.shape) to select plots from which results should be computed, 
                         e.g. from where site index = 4, temperature adjustment = +2C

    Returns : years_in_sim_lst -- list of the years in the simulation: size: nyears
              year_agg_mat -- the aggregate results by year and species: size: nspp,nyears
              num_species -- number of species in the simulation : size: 1
    """

    num_species = len(driver['species_code_to_name'])

    years_in_sim_lst = driver['simulation_years_logged']
    num_years = len(years_in_sim_lst)
    year_agg_mat = np.zeros((num_species, num_years))

    for index, year in enumerate(years_in_sim_lst):
        year_str = '%.4d' % year
        # pull the current year dbh matrix from the hdf file
        dbh_matrix = np.array(h5file['DBH'][year_str])
        # pull the current year species code matrix from the hdf file
        species_code_matrix = np.array(h5file['SpeciesCode'][year_str])
        if mask is not None:  #this is a hack
            species_code_matrix[np.logical_not(mask)] = -1  #set spp code for trees on plots that don't satisfy mask criteria to -1 (no tree); tree-level values are computed only w/in masked area

        for current_species_code in range(num_species):
            species_name = driver['species_code_to_name'][current_species_code]

            height_fn = driver['species'][species_name]['TREE_HEIGHT_EQUATION']  #pull spp-specific height eq from driver
            # get all of the dbh values for the species code of interest
            dbh_vec = dbh_matrix[species_code_matrix == current_species_code]
            filtered_dbh_vec = dbh_vec[dbh_vec >= min_dbh]
            #print species_name, current_species_code, (species_code_matrix == current_species_code)
            if np.any(filtered_dbh_vec):
                # non species-specific equation, because basal area is compute the same way for all trees
                basal_area_vec = pi*(filtered_dbh_vec/2.0)**2  
                height_vec = height_fn(filtered_dbh_vec)
                basal_area_sum = np.sum(basal_area_vec)
                loreys_height = (np.sum(basal_area_vec*height_vec))/basal_area_sum
            else:
                loreys_height = np.nan
            # store the sum for this species and this year
            year_agg_mat[current_species_code, index] = loreys_height

    return years_in_sim_lst, year_agg_mat, num_species



def compute_results_vs_time(h5file, driver,
                            normalize_value,
                            min_dbh,
                            mask,
                            fn_key=None,
                            func=None,
                            aggregate_fn=None):
    """
    Compute aggregate results and return a time series.

    Parameters : normalize_value -- the yearly accumulated values will be divided by this number
                 min_dbh -- only use trees with a dbh larger than this value
                 mask -- T/F array (DEM.shape) to select plots from which results should be computed, e.g. from where site index = 4, temperature adjustment = +2C
                 fn_key -- [default: None] the key name of the species specific equation that will compute values from dbh
                 func -- [default: None] a custom function that will be called with a vector of dbh
                 aggregate_fn -- [default: np.sum] the aggregate function; could be sum, mean, etc..

    Returns : years_in_sim_lst -- list of the years in the simulation: size: nyears
              year_agg_mat -- the aggregate results by year and species: size: nspp,nyears
              num_species -- number of species in the simulation : size: 1
    """
    if aggregate_fn is None:
        aggregate_fn = np.sum
    num_species = len(driver['species_code_to_name'])

    years_in_sim_lst = driver['simulation_years_logged']
    num_years = len(years_in_sim_lst)
    year_agg_mat = np.zeros((num_species, num_years))

    for index, year in enumerate(years_in_sim_lst):
        year_str = '%.4d' % year
        # pull the current year dbh matrix from the hdf file (size: nx,ny,ntrees)
        dbh_matrix = np.array(h5file['DBH'][year_str])
        # pull the current year species code matrix from the hdf file (size: nx,ny,ntrees)
        species_code_matrix = np.array(h5file['SpeciesCode'][year_str])
        if mask is not None:  #this is a hack
            species_code_matrix[np.logical_not(mask)] = -1  #set spp code for trees on plots that don't satisfy mask criteria to -1 (no tree); tree-level values are computed only w/in masked area

        for current_species_code in range(num_species):
            species_name = driver['species_code_to_name'][current_species_code]
            if func:
                fn = func
            else:
                fn = driver['species'][species_name][fn_key]
            # get all of the dbh values for the species code of interest
            dbh_vec = dbh_matrix[species_code_matrix == current_species_code]
            filtered_dbh_vec = dbh_vec[dbh_vec >= min_dbh]
            #print species_name, current_species_code, (species_code_matrix == current_species_code)
            if np.any(filtered_dbh_vec):
                # compute the total for this species this year and normalize to per ha
                year_total = aggregate_fn( fn(filtered_dbh_vec) )
            else:
                year_total = np.nan
            # store the sum for this species and this year
            year_agg_mat[current_species_code, index] = year_total / normalize_value

    return years_in_sim_lst, year_agg_mat, num_species

