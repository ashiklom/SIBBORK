#import json # import the library that can read the driver file
import zlib
import os

def run_make_template(**kw):
    from mako.template import Template
    template = Template("""
<%!
    def make_id_to_name_lut(driver):
        species_names = sorted(driver['species'].keys(), key=str.lower)
        species_code_to_name = [name for name in species_names if driver['species'][name]['ENABLED']]
        return species_code_to_name

    def make_name_to_species_code_lut(driver):
        species_code_to_name = make_id_to_name_lut(driver)
        name_to_species_code = {}
        for spp_code, name in enumerate(species_code_to_name):
            name_to_species_code[name] = spp_code
        return name_to_species_code

    def make_id_to_CP_lut(driver):
        species_code_to_name = make_id_to_name_lut(driver)
        species_code_to_CP = [driver['species'][name]['LIGHT_COMPENSATION_POINT'] for name in species_code_to_name if driver['species'][name]['ENABLED']]
        return species_code_to_CP

    def make_id_to_SEED_lut(driver):
        species_code_to_name = make_id_to_name_lut(driver)
        species_code_to_SEED = [driver['species'][name]['SEED'] for name in species_code_to_name if driver['species'][name]['ENABLED']]
        return species_code_to_SEED

    def make_id_to_LIGHT_lut(driver):
        species_code_to_name = make_id_to_name_lut(driver)
        species_code_to_LIGHT = [driver['species'][name]['LIGHT'] for name in species_code_to_name if driver['species'][name]['ENABLED']]
        return species_code_to_LIGHT

    def make_id_to_inseeding_lag_lut(driver):
        species_code_to_name = make_id_to_name_lut(driver)
        species_code_to_lag = [driver['species'][name]['INSEEDING_LAG'] for name in species_code_to_name if driver['species'][name]['ENABLED']]
        return species_code_to_lag

    def display_dict(key, dict):
        s = "#  %s:\\n" % key
        keys = sorted( dict.keys(), key=str.lower )
        for k in keys:
            v = dict[k]
        ##for k,v in dict.items():
            s += '#    %s: %s\\n' %(k,v)
        return s

    def get_nutri_coeficients(nutri_class):
        S1_look_up_table = [1.03748,1.00892,1.01712] 
        S2_look_up_table = [-4.02952,-5.38804,-4.12162] 
        S3_look_up_table = [0.17588,0.12242,0.00898]
        return S1_look_up_table[nutri_class-1], S2_look_up_table[nutri_class-1], S3_look_up_table[nutri_class-1]

    def get_light_coeficients(light_class):
        # the light tolerance constants
        # coefs for 1 to 5 integer of shade tolerance (1 is more shade tolerant, 5 is shade intolerant)
        C1_look_up_table = [1.01,1.04,1.11,1.24,1.49]  
        C2_look_up_table = [4.62,3.44,2.52,1.78,1.23]
        C3_look_up_table = [0.05,0.06,0.07,0.08,0.09]
        return C1_look_up_table[light_class-1], C2_look_up_table[light_class-1], C3_look_up_table[light_class-1]
%>
# *************
# Autogenerated from driver file ${driver_module}.py
# *************
% if use_numba_dummy:
import numba_dummy as numba
% else:
import numba
% endif
import numpy as np
from math import *
from ${driver_module} import driver

# the total number of species enabled
number_of_species = ${len(make_id_to_name_lut(driver))}

# the tree species type identifier (integer >= 0) to string name look up table
species_code_to_name = ${str(make_id_to_name_lut(driver))}

# the name to species code look up table
name_to_species_code = ${str(make_name_to_species_code_lut(driver))}

# the light compensation point (CP) by species
species_code_to_CP = ${str(make_id_to_CP_lut(driver))}

# the SEED value by species
species_code_to_SEED = ${str(make_id_to_SEED_lut(driver))}

# the inseeding lag time by species
species_code_to_inseeding_lag = ${str(make_id_to_inseeding_lag_lut(driver))}

@numba.jit()
def compute_species_factors_weather(GDD_matrix, drydays_fraction_mat, spp_in_sim):
    '''

    Parameters: GDD_matrix -- a matrix the size of the sim grid of accumulated growing degrees over this year in sim
                drydays_fraction_mat -- the fraction 0 to 1 of the growing season in drought

    Returns:    GDD_3D_spp_factor_matrix -- the species specific degree day factors, size : nx,ny,nspp
                soil_moist_3D_spp_factor_matrix -- the species specific soil moisture factors, size : nx,ny,nspp
    '''
    nx,ny = GDD_matrix.shape
    GDD_3D_spp_factor_matrix = np.zeros((nx,ny,spp_in_sim))
    soil_moist_3D_spp_factor_matrix = np.zeros((nx,ny,spp_in_sim))

    for x in range(nx):
        for y in range(ny):
            for spp in range(spp_in_sim): #address of each cell in 3-D matrix
                if spp == 0:
                    GDD_3D_spp_factor_matrix[x,y,spp] = degree_day_factor_numba_species_0(GDD_matrix[x,y])
                    soil_moist_3D_spp_factor_matrix[x,y,spp] = soil_moisture_factor_numba_species_0(drydays_fraction_mat[x,y])
% for spp in range(1, len(make_id_to_name_lut(driver))):
                elif spp == ${spp}:
                    GDD_3D_spp_factor_matrix[x,y,spp] = degree_day_factor_numba_species_${spp}(GDD_matrix[x,y])
                    soil_moist_3D_spp_factor_matrix[x,y,spp] = soil_moisture_factor_numba_species_${spp}(drydays_fraction_mat[x,y])
% endfor

    return GDD_3D_spp_factor_matrix, soil_moist_3D_spp_factor_matrix

@numba.jit()
def compute_species_factors_soil(relative_soil_fertility_matrix, spp_in_sim):
    '''

    Parameters:  relative_soil_fertility_matrix -- a matrix the size of sim grid with values 0 to 1 for each plot in sim 

    Returns:    soil_fert_3D_spp_factor_matrix -- the species specific soil fertility factors, size : nx,ny,nspp
    '''
    nx,ny = relative_soil_fertility_matrix.shape
    soil_fert_3D_spp_factor_matrix = np.zeros((nx,ny,spp_in_sim))

    for x in range(nx):
        for y in range(ny):
            for spp in range(spp_in_sim): #address of each cell in 3-D matrix
                if spp == 0:
                    soil_fert_3D_spp_factor_matrix[x,y,spp] = soil_fertility_factor_numba_species_0(relative_soil_fertility_matrix[x,y])
% for spp in range(1, len(make_id_to_name_lut(driver))):
                elif spp == ${spp}:
                    soil_fert_3D_spp_factor_matrix[x,y,spp] = soil_fertility_factor_numba_species_${spp}(relative_soil_fertility_matrix[x,y])
% endfor

    return soil_fert_3D_spp_factor_matrix


def compute_species_factors(GDD_matrix, drydays_fraction_mat, relative_soil_fertility_matrix, spp_in_sim):
    '''

    Parameters: GDD_matrix -- a matrix the size of the sim grid of accumulated growing degrees over this year in sim
                drydays_fraction_mat -- the fraction 0 to 1 of the growing season in drought
                relative_soil_fertility_matrix -- a matrix the size of sim grid with values 0 to 1 for each plot in sim 
                                                  & the conversion from site index to Mg/ha/yr productivity limitation 
                                                  already completed (table in user manual)

#TODO:    Returns:    GDD_3D_spp_factor_matrix -- 
                      soil_moist_3D_spp_factor_matrix -- 
                      soil_fert_3D_spp_factor_matrix --
    '''
    nx,ny = GDD_matrix.shape
    GDD_3D_spp_factor_matrix = np.zeros((nx,ny,spp_in_sim))
    soil_moist_3D_spp_factor_matrix = np.zeros((nx,ny,spp_in_sim))
    soil_fert_3D_spp_factor_matrix = np.zeros((nx,ny,spp_in_sim))

    return compute_species_factors_numba(GDD_matrix, GDD_3D_spp_factor_matrix, 
                                         drydays_fraction_mat, soil_moist_3D_spp_factor_matrix,
                                         relative_soil_fertility_matrix, soil_fert_3D_spp_factor_matrix,
                                         nx, ny, spp_in_sim)

@numba.jit(nopython=True)
def compute_species_factors_numba(GDD_matrix, GDD_3D_spp_factor_matrix, 
                                  drydays_fraction_mat, soil_moist_3D_spp_factor_matrix,
                                  relative_soil_fertility_matrix, soil_fert_3D_spp_factor_matrix,
                                  nx, ny, spp_in_sim):
    for x in range(nx):
        for y in range(ny):
            for spp in range(spp_in_sim): #address of each cell in 3-D matrix
                if spp == 0:
                    GDD_3D_spp_factor_matrix[x,y,spp] = degree_day_factor_numba_species_0(GDD_matrix[x,y])
                    soil_moist_3D_spp_factor_matrix[x,y,spp] = soil_moisture_factor_numba_species_0(drydays_fraction_mat[x,y])
                    soil_fert_3D_spp_factor_matrix[x,y,spp] = soil_fertility_factor_numba_species_0(relative_soil_fertility_matrix[x,y])
% for spp in range(1, len(make_id_to_name_lut(driver))):
                elif spp == ${spp}:
                    GDD_3D_spp_factor_matrix[x,y,spp] = degree_day_factor_numba_species_${spp}(GDD_matrix[x,y])
                    soil_moist_3D_spp_factor_matrix[x,y,spp] = soil_moisture_factor_numba_species_${spp}(drydays_fraction_mat[x,y])
                    soil_fert_3D_spp_factor_matrix[x,y,spp] = soil_fertility_factor_numba_species_${spp}(relative_soil_fertility_matrix[x,y])
% endfor

    return GDD_3D_spp_factor_matrix, soil_moist_3D_spp_factor_matrix, soil_fert_3D_spp_factor_matrix


@numba.jit()
def compute_available_light_factors_by_species(available_light_mat, number_of_species):
    '''
    For the input 3D matrix of available light, compute the species specific light factor for each of the 
    species in the simulation.

    Parameters: available_light_mat -- available light for every location in the simulation 3D area
                                       size 3D: nx, ny, elev (where elev is max tree height + max DEM offset)
                number_of_species -- the number of species in the simulation

    Returns: light_factor_by_species_matrix -- species specific light factors computed above ground
                                               size 4D: nx, ny, nz, number_of_species
    '''
    nx, ny, nz = available_light_mat.shape
    light_factor_by_species_matrix = np.zeros((nx,ny,nz,number_of_species))

    # iterate through each plot x,y
    for x in range(nx):
        for y in range(ny):
            # for each species compute the light factor at every location between the ground and the sky
            for z in range(nz):
                # the available light at this location (x,y,z)
                al = available_light_mat[x,y,z]
                if al > 0.:
                    # compute the factors by species
                    for spp in range(number_of_species):
                        if spp == 0:
                            light_factor_by_species_matrix[x,y,z,spp] = available_light_factor_numba_species_0(al)
% for spp in range(1, len(make_id_to_name_lut(driver))):
                        elif spp == ${spp}:
                            light_factor_by_species_matrix[x,y,z,spp] = available_light_factor_numba_species_${spp}(al)
% endfor

    return light_factor_by_species_matrix


@numba.jit()
def compute_actual_leaf_area(DBH_matrix, species_code_matrix, crown_base_matrix, tree_height_matrix, total_leaf_area_matrix, 
                               actual_leaf_area_mat):
    '''
    Take the computed foliage densities for each tree, and sum them within each plot, creating an accumulated
    foliage density profile for the plot to use as input into the light computation

    Parameters:  DBH_matrix -- records DBH for every tree in sim, size: sim grid by number of trees on each plot
                               size : nx, ny, MAX_TREES_PER_PLOT
                 species_code_matrix -- records the specie of each tree in sim, size: sim grid by number of trees on each plot
                                        size : nx, ny, MAX_TREES_PER_PLOT
                 crown_base_matrix -- records the crown base for each tree in sim, size: sim grid by number of trees 
                                      on each plot
                                      size : nx, ny, MAX_TREES_PER_PLOT
                 tree_height_matrix -- the height of each individual tree on each plot
                                       size : nx, ny, MAX_TREES_PER_PLOT
                 total_leaf_area_matrix -- the total leaf area of each individual tree on each plot
                                           size : nx, ny, MAX_TREES_PER_PLOT
                 actual_leaf_area_mat   --  pre-initialized: contains -1 below ground and 0 above ground for each plot and air space above plot
                                            size: nx, ny, vertical space = (max_tree_ht+(max elevation in sim - min elevation in sim))

    Returns:  actual_leaf_area_mat --  contains contains the actual leaf area column for each plot in the simulation grid
                                       size: nx, ny, MAX_TREE_HEIGHT
    '''
    MAX_TREE_HEIGHT = ${driver['MAX_TREE_HEIGHT']}
    nx,ny,ntrees = DBH_matrix.shape
    actual_leaf_area_mat = np.zeros( (nx,ny,MAX_TREE_HEIGHT) )
    for x in range(nx):
        for y in range(ny):
            # iterate through each tree and add to the plot foliage density popsicle
            for individual in range(ntrees): #address of each cell in 3-D matrix
                tree_dbh = DBH_matrix[x,y,individual] #get tree DBH from DBH matrix
                if tree_dbh > 0.0:
                    # foliage density is basically the leaf area / the height
                    tree_height = tree_height_matrix[x,y,individual]
                    crown_base = crown_base_matrix[x,y,individual]
                    crown_length = tree_height - crown_base
                    if crown_length > 0:
                        total_leaf_area = total_leaf_area_matrix[x,y,individual]
                        fd = total_leaf_area / crown_length
                        # accumulate the foliage density popsicle for this plot consisting of many trees on the same DEM elevation
                        for ht in range(crown_base, int(tree_height)):
                            actual_leaf_area_mat[x,y,ht] += fd

    return actual_leaf_area_mat

@numba.jit()
def compute_individual_tree_values(DBH_matrix, species_code_matrix, crown_base_matrix):
    '''
    Compute species specific values for each tree in the simulation.
    The current computed values are:
        individual height (m)
        individual total leaf area (m^2)
        individual biomass (kg)
        optimal growth increment (cm)
        individual optimal biomass (kg)
        individual basal area (m^2)
        individual biovolume (m^3)
        individual optimal biovolume (m^3)
        individual optimal biovolume increment (m^3)

    Parameters : DBH_matrix -- a dbh value (cm) for each tree in the simulation
                               size : nx, ny, ntrees
                 species_code_matrix -- the species code for every tree in the simulation
                                        size : nx, ny, ntrees
                 crown_base_matrix -- the height (m) of the base of each tree crown
                                      size : nx, ny, ntrees

    Returns : tree_height_matrix -- the species specific height (m) of each tree in the simulation
                                    size : nx, ny, ntrees
              total_leaf_area_matrix -- the total leaf area (m^2) of each tree in the simulation
                                        size : nx, ny, ntrees
              biomass_matrix -- the total biomass (kg) of each tree
                                size : nx, ny, ntrees
              opt_inc_matrix -- the optimal dbh increment (cm) that the individual tree can grow under optimal conditions
                                size : nx, ny, ntrees
              optimal_biomass_matrix -- the biomass (kg) that the tree could achieve next year under optimal conditions
                                        size : nx, ny, ntrees
              basal_area_matrix -- the basal area (m^2) for each individual tree
                                   size : nx, ny, ntrees
              biovolume_matrix -- the biovolume (m^3) for each individual tree
                                   size : nx, ny, ntrees
              optimal_biovolume_matrix -- the biovolume (m^3) that the tree could achieve next year under optimal conditions
                                          size : nx, ny, ntrees
              optimal_biovolume_increment_matrix -- the biovolume increment (m^3) that the tree could achieve next year under optimal conditions
                                                    size : nx, ny, ntrees
    '''
    nx,ny,ntrees = DBH_matrix.shape
    tree_height_matrix = np.zeros((nx,ny,ntrees))
    total_leaf_area_matrix = np.zeros((nx,ny,ntrees))
    biomass_matrix = np.zeros((nx,ny,ntrees))
    opt_inc_matrix = np.zeros((nx,ny,ntrees))
    optimal_biomass_matrix = np.zeros((nx,ny,ntrees))
    basal_area_matrix = np.zeros((nx,ny,ntrees))
    biovolume_matrix = np.zeros((nx,ny,ntrees))
    optimal_biovolume_matrix = np.zeros((nx,ny,ntrees))
    optimal_biovolume_increment_matrix = np.zeros((nx,ny,ntrees))

    for x in range(nx):
        for y in range(ny):
            for ind in range(ntrees):
                dbh = DBH_matrix[x,y,ind]
                crown_base = crown_base_matrix[x,y,ind]
                species_code = species_code_matrix[x,y,ind]
% for spp in range(0, len(make_id_to_name_lut(driver))):
    % if spp==0:
                if species_code == ${spp}:                
    % else:
                elif species_code == ${spp}:
    % endif
                    tree_height = tree_height_numba_species_${spp}(dbh)
                    tree_height_matrix[x,y,ind] = tree_height
                    total_leaf_area_matrix[x,y,ind] = total_leaf_area_numba_species_${spp}(dbh, tree_height, crown_base)
                    biomass_matrix[x,y,ind] = tree_biomass_numba_species_${spp}(dbh)
                    opt_inc = optimal_growth_increment_numba_species_${spp}(dbh)
                    opt_inc_matrix[x,y,ind] = opt_inc
                    optimal_biomass_matrix[x,y,ind] = tree_biomass_numba_species_${spp}(dbh + opt_inc)
                    basal_area_matrix[x,y,ind] = basal_area_numba_species_${spp}(dbh)
                    biovolume_matrix[x,y,ind] = tree_biovolume_numba_species_${spp}(dbh)
                    optimal_biovolume_matrix[x,y,ind] = tree_biovolume_numba_species_${spp}(dbh + opt_inc)
                    optimal_biovolume_increment_matrix[x,y,ind] = optimal_biovolume_matrix[x,y,ind] - biovolume_matrix[x,y,ind]
% endfor

    return tree_height_matrix, total_leaf_area_matrix, biomass_matrix, opt_inc_matrix, optimal_biomass_matrix, basal_area_matrix, biovolume_matrix, \
           optimal_biovolume_matrix, optimal_biovolume_increment_matrix


# ********************************
# By specie code
# ********************************

% for spp, name in enumerate(make_id_to_name_lut(driver)):
# ***** Species Code ${spp}
${display_dict(name, driver['species'][name])}

# species specific degree day factor equation (see driver)
##degree_day_factor_numba_species_${spp} = driver['species']['${name}']['DEGREE_DAY_FACTOR_EQUATION']
degree_day_factor_numba_species_${spp} = numba.jit(nopython=True)(driver['species']['${name}']['DEGREE_DAY_FACTOR_EQUATION'])

# species specific soil moisture factor equation (see driver)
##soil_moisture_factor_numba_species_${spp} = driver['species']['${name}']['SOIL_MOISTURE_FACTOR_EQUATION']
soil_moisture_factor_numba_species_${spp} = numba.jit(nopython=True)(driver['species']['${name}']['SOIL_MOISTURE_FACTOR_EQUATION'])

# species specific soil fertility factor equation (see driver)
##soil_fertility_factor_numba_species_${spp} = driver['species']['${name}']['SOIL_FERTILITY_FACTOR_EQUATION']
soil_fertility_factor_numba_species_${spp} = numba.jit(nopython=True)(driver['species']['${name}']['SOIL_FERTILITY_FACTOR_EQUATION'])

# species specific light factor equation (see driver)
##available_light_factor_numba_species_${spp} = driver['species']['${name}']['AVAILABLE_LIGHT_FACTOR_EQUATION']
available_light_factor_numba_species_${spp} = numba.jit(nopython=True)(driver['species']['${name}']['AVAILABLE_LIGHT_FACTOR_EQUATION'])

# species specific tree height equation (see driver)
##tree_height_numba_species_${spp} = driver['species']['${name}']['TREE_HEIGHT_EQUATION']
tree_height_numba_species_${spp} = numba.jit(nopython=True)(driver['species']['${name}']['TREE_HEIGHT_EQUATION'])

# species specific leaf area equation (see driver)
##leaf_area_numba_species_${spp} = driver['species']['${name}']['LEAF_AREA_EQUATION']
leaf_area_numba_species_${spp} = numba.jit(nopython=True)(driver['species']['${name}']['LEAF_AREA_EQUATION'])

@numba.jit(nopython=True)
def total_leaf_area_numba_species_${spp}(dbh, tree_height, crown_base):
    '''
    Compute the total leaf area for a single tree.

    Parameters: dbh -- the tree dbh in cm
                tree_height -- the height of the tree in meters
                crown_base -- the height of the base of the crown in meters

    Returns: the total leaf area in m^2
    '''
##    leaf_area = ${driver['species'][name]['LEAF_AREA_EQUATION']}
    leaf_area = leaf_area_numba_species_${spp}(dbh)
    adjusted_leaf_area = leaf_area * (tree_height - crown_base)/tree_height  #drop the leaves below crown base
    return adjusted_leaf_area

# species specific biomass equation (see driver)
##tree_biomass_numba_species_${spp} = driver['species']['${name}']['BIOMASS_EQUATION']
tree_biomass_numba_species_${spp} = numba.jit(nopython=True)(driver['species']['${name}']['BIOMASS_EQUATION'])

# species specific biovolume equation (see driver)
tree_biovolume_numba_species_${spp} = numba.jit(nopython=True)(driver['species']['${name}']['BIOVOLUME_EQUATION'])

# species specific optimal growth increment equation (see driver)
##optimal_growth_increment_numba_species_${spp} = driver['species']['${name}']['OPTIMAL_GROWTH_INCREMENT_EQUATION']
optimal_growth_increment_numba_species_${spp} = numba.jit(nopython=True)(driver['species']['${name}']['OPTIMAL_GROWTH_INCREMENT_EQUATION'])

# species specific basal area function (see driver)
##basal_area_numba_species_${spp} = driver['species']['${name}']['BASAL_AREA_EQUATION']
basal_area_numba_species_${spp} = numba.jit(nopython=True)(driver['species']['${name}']['BASAL_AREA_EQUATION'])

# species specific age mortality probability function (see driver)
##age_mortality_probablity_numba_species_${spp} = driver['species']['${name}']['AGE_MORTALITY_EQUATION']
age_mortality_probablity_numba_species_${spp} = numba.jit(nopython=True)(driver['species']['${name}']['AGE_MORTALITY_EQUATION'])

% endfor

# the age mortality probability functions by species
species_code_to_age_mortality_function = [ \\
% for spp in range(0, len(make_id_to_name_lut(driver))):
age_mortality_probablity_numba_species_${spp}, \\
% endfor
]

""")
    return template.render(**kw)


def make_numba_driver_code(driver_file, output_file, use_numba_dummy=False, force_rewrite=False):
    """
    This function creates specialized numba code from the driver file. This is necessary to sqeeze additional
    performance out of python (using numba) while allowing species specific functions to be written in regular
    python in the driver file.
    
    Parameters: driver_file -- file name of the .py driver file
                output_file -- file name of the numba specialization file to be written

    Returns: None
    """
    # In order to get the best performance from numba, some specialized code has to be written taking inputs
    # from the driver. This specialized file should only be rewritten once whenever the driver changes, and
    # not be written when the driver has not changed (such as replicates running on the cluster).
    # To detect when the driver has changed, we will compute a CRC of the file contents and compare that
    # against a locally stored version of the last used driver CRC value. 
    # You can think of this as sort of like the make tool.

    # calculate the checksum of the current driver
    f = open(driver_file)
    current_crc32_checksum = zlib.crc32(f.read()) & 0xffffffff
    f.close()

    # compare the current CRC to the previously used CRC
    # check if the CRC file already exists
    CRC_file = '.pyzelig.crc32'
    if os.access(CRC_file, os.F_OK) and os.access(output_file, os.F_OK):
        # read in the CRC value from file
        previous_crc32_checksum = int(open(CRC_file).read())
        if current_crc32_checksum == previous_crc32_checksum: 
            # we do not need to regenerate
            write_output = False
        else:
            # we need to regenerate the specialization file
            write_output = True
    else:
        # we need to regenerate the specialization file
        write_output = True

    if force_rewrite:
        write_output = True

    # generate the numba specialization code using the template above
    if write_output:
        print 'Info :: Creating a new driver specialization file : %s' % output_file

        # load the 'driver' dictionary from the driver file
        driver_module = driver_file.split('.')[0]
        globals_dict = {}; locals_dict = {}
        exec('from %s import driver' % driver_module, globals_dict, locals_dict)
        ## write the driver specialization code
        code_str = run_make_template(driver_module=driver_module, driver=locals_dict['driver'], use_numba_dummy=use_numba_dummy)
        f = open(output_file, 'w')
        f.write(code_str)
        f.close()
        # write the CRC file
        f = open(CRC_file, 'w')
        f.write(str(current_crc32_checksum))
        f.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("driver_file", help="specify the driver file and path (if not in same directory)")
    args = parser.parse_args()
    driver_file = args.driver_file

    # generate the specialization code from the driver file
    make_numba_driver_code(driver_file, 'specialized_driver_numba.py')


