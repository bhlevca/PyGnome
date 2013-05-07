'''
Tests for netcdf_outputter
'''
import os
from datetime import datetime

import numpy as np
import netCDF4 as nc
import pytest

import gnome

base_dir = os.path.dirname(__file__)

@pytest.fixture(scope="module")
def model(sample_model_spatial_release_spill, request):
    """ 
    use fixture sample_model_spatial_release_spill and add a few things to it for the test
    
    Fixtures adds another spill (SurfaceReleaseSpill) and a netcdf outputter
    to the model. 
    """
    model = sample_model_spatial_release_spill['model']
    
    model.cache_enabled = True  # let's enable cache
    
    model.outputters += gnome.netcdf_outputter.NetCDFOutput(os.path.join(base_dir,'sample_model.nc'))
    
    for sp in model.spills:
        st_pos = sp.start_positions[0,:]

    model.spills += gnome.spill.SurfaceReleaseSpill( num_elements=5,
                                                     start_position=st_pos,
                                                     release_time  = model.start_time,
                                                     windage_persist= 0
                                                     )
    def cleanup():
        """ cleanup outputters was added to sample_model and delete files """
        print ("\nCleaning up %s\n" % model)
        for outputter in model.outputters:
            if isinstance(outputter,gnome.netcdf_outputter.NetCDFOutput):   # there should only be 1! 
                o_put = model.outputters[outputter.id]
                
        if os.path.exists(o_put.netcdf_filename):
            os.remove(o_put.netcdf_filename)
            
        if os.path.exists(o_put._u_netcdf_filename):
            os.remove(o_put._u_netcdf_filename)
        
    request.addfinalizer(cleanup)
    return model


def test_exceptions():
    """ test all exceptions are raised """
    with pytest.raises(ValueError):
        gnome.netcdf_outputter.NetCDFOutput(os.path.join(base_dir,'SampleData','MapBounds_Island.bna')) # file exists
        
    with pytest.raises(ValueError):
        gnome.netcdf_outputter.NetCDFOutput(os.path.abspath(os.path.dirname(__file__))) # must be filename, not dir name
        
    with pytest.raises(ValueError):
        gnome.netcdf_outputter.NetCDFOutput('junk_path_to_file/file.nc') # invalid path
        
    # Test exceptions raised after object creation
    t_file = os.path.join(base_dir,'temp.nc')
    netcdf = gnome.netcdf_outputter.NetCDFOutput(t_file)
    with pytest.raises(TypeError):
        netcdf.prepare_for_model_run(num_time_steps=4)
        
    with pytest.raises(TypeError):
        netcdf.prepare_for_model_run()
        
    netcdf.prepare_for_model_run(model_start_time=datetime.now(), num_time_steps=4)
    with pytest.raises(ValueError):
        netcdf.write_output(0)
        
    # clean up temporary file
    if os.path.exists(t_file):
        print ("remove temporary file {0}".format(t_file))
        os.remove(t_file)
        
        
def test_prepare_for_model_run(model):
    """ 
    use model fixture. Call prepare_for_model_run for netcdf_outputter 
    """
    for outputter in model.outputters:
        if isinstance(outputter,gnome.netcdf_outputter.NetCDFOutput):   # there should only be 1! 
            o_put = model.outputters[outputter.id]
            
    model.rewind()
    model.step()    # should call prepare_for_model_step
    
    assert os.path.exists(o_put.netcdf_filename)
    
    if model.uncertain:
        assert os.path.exists(o_put._u_netcdf_filename)
    else:
        assert not os.path.exists(o_put._u_netcdf_filename)
        

def test_write_output_standard(model):
    """ 
    rewind model defined by model fixture.
    invoke model.step() till model runs all 5 steps
    
    For each step, compare the standard variables in the model.cache to the data read back in from netcdf files.
    Compare uncertain and uncertain data.
    
    Since 'latitude', 'longitude' and 'depth' are float 32 while the data in cache is float64, use np.allclose to
    check it is within 1e-5 tolerance - till about 5 decimal places.
    """
    model.rewind()
    while True:
        try:
            model.step()
        except StopIteration:
            break
        
    # check contents of netcdf File at multiple time steps (there should only be 1!)
    o_put = [model.outputters[outputter.id] for outputter in model.outputters if isinstance(outputter,gnome.netcdf_outputter.NetCDFOutput)][0]     
    
    atol=1e-5
    rtol=0
    
    uncertain = False
    for file_ in (o_put.netcdf_filename, o_put._u_netcdf_filename):
        with nc.Dataset(file_) as data:
            time_ = nc.num2date( data.variables['time'], data.variables['time'].units, calendar=data.variables['time'].calendar)
            idx = np.cumsum( data.variables['particle_count'][:])
            idx = np.insert( idx, 0, 0) # add starting index of 0 
             
            for step in range(model.num_time_steps):
                scp = model._cache.load_timestep(step)
                
                # check time
                assert scp.LE('current_time_stamp',uncertain) == time_[step]
                
                # check standard variables
                #assert np.all( scp.LE('positions',uncertain)[:,0] == data.variables['longitude'][idx[step]:idx[step+1]] )
                #assert np.all( scp.LE('positions',uncertain)[:,1] == data.variables['latitude'][idx[step]:idx[step+1]] )
                #assert np.all( scp.LE('positions',uncertain)[:,2] == data.variables['depth'][idx[step]:idx[step+1]] )
                
                assert np.allclose( scp.LE('positions',uncertain)[:,0], data.variables['longitude'][idx[step]:idx[step+1]], rtol, atol)
                assert np.allclose( scp.LE('positions',uncertain)[:,1], data.variables['latitude'][idx[step]:idx[step+1]], rtol, atol)
                assert np.allclose( scp.LE('positions',uncertain)[:,2], data.variables['depth'][idx[step]:idx[step+1]], rtol, atol)
                
                assert np.all( scp.LE('spill_num',uncertain)[:] == data.variables['id'][idx[step]:idx[step+1]] )
                assert np.all( scp.LE('status_codes',uncertain)[:] == data.variables['status'][idx[step]:idx[step+1]] )
                
                # flag variable is not currently set or checked
                if 'mass' in scp.LE_data:
                    assert np.all( scp.LE('mass',uncertain)[:] == data.variables['mass'][idx[step]:idx[step+1]] )
                    
                if 'age' in scp.LE_data:
                    assert np.all( scp.LE('age',uncertain)[:] == data.variables['age'][idx[step]:idx[step+1]] )
            
            print "data in model matches output in {0}".format(file_)
        # 2nd time around, we are looking at uncertain filename so toggle uncertain flag
        uncertain = True
            
            
def test_write_output_all_data(model):
    """ 
    rewind model defined by model fixture.
    invoke model.step() till model runs all 5 steps
    
    For each step, compare the standard variables in the model.cache to the data read back in from netcdf files.
    Compare uncertain and uncertain data.
    
    Only compare the remaining data not already checked in test_write_output_standard
    """
    model.rewind()
    
    # check contents of netcdf File at multiple time steps (there should only be 1!)
    o_put = [model.outputters[outputter.id] for outputter in model.outputters if isinstance(outputter,gnome.netcdf_outputter.NetCDFOutput)][0]
    o_put.all_data = True   # write all data
    while True:
        try:
            model.step()
        except StopIteration:
            break
        
    uncertain = False
    for file_ in (o_put.netcdf_filename, o_put._u_netcdf_filename):
        with nc.Dataset(file_) as data:
            idx = np.cumsum( data.variables['particle_count'][:])
            idx = np.insert( idx, 0, 0) # add starting index of 0 
             
            for step in range(model.num_time_steps):
                scp = model._cache.load_timestep(step)
                
                for key,val in o_put.arr_types.iteritems():
                    if len(val.shape) == 0:
                        assert np.all( data.variables[key][idx[step]:idx[step+1]] == scp.LE(key, uncertain) )
                    else:      
                        assert np.all( data.variables[key][idx[step]:idx[step+1],:] == scp.LE(key, uncertain) )
                
        # 2nd time around, we are looking at uncertain filename so toggle uncertain flag
        uncertain = True