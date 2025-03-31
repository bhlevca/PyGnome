"""
Code to compute volumetric concentration from surface concentration from particles. 

The volumetric concentration is calculated by dividing the surface concentrations by 
the water depth of the mesh element where the particle resides. 

MIKE 21 dfsu result file with dynamic depths will be copied to the WebGNOME server 
and used to identify the water depth for each particle at the time corresponding to 
the output time of the concentration value.

"""

import warnings
import numpy as np
from gnome.concentration.dfsu_water_depth import DfsuWaterDepth
from gnome.concentration.concentration_location import ConcentrationLocation
from scipy.spatial import cKDTree

def compute_volumetric_concentration(sc, water_depth:DfsuWaterDepth, location:ConcentrationLocation):
    #initialize as 0
    sc['volumetric_concentration'] = np.zeros(sc['spill_num'].shape[0],) 
    sc['volumetric_concentration_poi'] = 0.0

    #get hd water depth at each particle position
    water_depth_value, coordinates = water_depth.at(sc['positions'], sc['current_time_stamp'].item())

    #calculate the volumetric concentration
    if water_depth_value is not None:
        #save depth to position z so it will be wrote to the depth column in shapefile
        for k, p in enumerate(sc['positions']):
            p[2] = water_depth_value[k]

        sc['volumetric_concentration'] = np.divide(sc['surface_concentration'], water_depth_value)

        #interpolation for point of interest
        if location is not None:
            if location.xy is None:
                location.transform(water_depth.project_string)
            
            #the distance threshold for the interpolation
            #100m is used here. If the the projection is long/lat, it's 0.001 degree.
            threshold = 100
            if not water_depth.isProjection:
                threshold = 0.001

            idw_tree = Tree2(coordinates, sc['volumetric_concentration'], distance_threshold = threshold)  # scatter data points
            sc['volumetric_concentration_poi'] = idw_tree(location.xy)[0]
            print(f"Volumetric Concentration: {sc['volumetric_concentration_poi']}")


class Tree2(object):

    def __init__(self, x=None, z=None, leaf_size=10, distance_threshold=1000):
        self.x = x
        self.z = z
        self.distance_threshold = distance_threshold
        if x is not None and z is not None:
            self.tree = cKDTree(x, leafsize=leaf_size)

    def fit(self, array=None, z=None, leaf_size=10):
        self.__init__(array, z, leaf_size)

    def __call__(self, x, k=6, eps=1e-6, p=2):
        # Find points within the distance_threshold
        neighbors_list = self.tree.query_ball_point(x, r=self.distance_threshold, eps=eps, p=p)
        interpolated_values = np.zeros(x.shape[0])

        for i, neighbors in enumerate(neighbors_list):
            if neighbors:
                # Retrieve the distances and corresponding z values
                distances = np.linalg.norm(self.x[neighbors] - x[i], axis=1)
                weights = 1 / (distances + eps)
                weighted_z = weights * self.z[neighbors]
                interpolated_values[i] = np.sum(weighted_z) / np.sum(weights)
            else:
                # If there are no neighbors within the threshold, you can assign a default value
                interpolated_values[i] = 0  # or any other default value

        return interpolated_values

    def transform(self, x, k=6, p=2, eps=1e-6):
        return self.__call__(x, k=k, eps=eps, p=p, distance_threshold=self.distance_threshold)