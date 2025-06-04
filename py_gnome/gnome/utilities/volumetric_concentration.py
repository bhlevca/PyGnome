"""
Code to compute volumetric concentration from surface concentration from particles. 

The volumetric concentration is calculated by dividing the surface concentrations by 
the water depth of the mesh element where the particle resides. 

MIKE 21 dfsu result file with dynamic depths will be copied to the WebGNOME server 
and used to identify the water depth for each particle at the time corresponding to 
the output time of the concentration value.

"""

import warnings
import math
import numpy as np
from gnome.concentration.dfsu_water_depth import DfsuWaterDepth
from gnome.concentration.concentration_location import ConcentrationLocation
from scipy.spatial import cKDTree
from geopy.distance import geodesic 


def haversine_vectorized(poi_lat, poi_lon, n_lat_array, n_lon_array):
    """
    Compute the Haversine distance between a single point (poi_lat, poi_lon)
    and arrays of latitude and longitude (n_lat_array, n_lon_array).
    All angles are in degrees.
    """
    R = 6371000  # Earth radius in meters

    poi_lat_rad = np.radians(poi_lat)
    poi_lon_rad = np.radians(poi_lon)
    n_lat_rad = np.radians(n_lat_array)
    n_lon_rad = np.radians(n_lon_array)

    dlat = n_lat_rad - poi_lat_rad
    dlon = n_lon_rad - poi_lon_rad

    a = np.sin(dlat / 2.0) ** 2 + \
        np.cos(poi_lat_rad) * np.cos(n_lat_rad) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    return R * c  # shape: (len(n_lat_array),)

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
            
        # Surface concentration comes in kg/particle - we need to multily by 1e^6 to convert 
        # in mg/particle so that the final result is in mg/L
        #kg2mg = 1000000.0 # in ug/L
        kg2mg = 1000.0     # in mg/L
        sc['volumetric_concentration'] = np.divide(sc['surface_concentration']*kg2mg, water_depth_value)

        #interpolation for point of interest
        if location is not None:
            if location.xy is None:
                location.transform(water_depth.project_string)
            
            #the distance threshold for the interpolation
            #100m is used here. If the the projection is long/lat, it's 0.001 degree.  perhaps 0.002 would be better
            threshold = 100
            if not water_depth.isProjection:
                threshold = 145  # meters (use consistent real-world units)
            
            idw_tree = Tree2(coordinates, sc['volumetric_concentration'], distance_threshold=threshold, isProjection=water_depth.isProjection)  # scatter data points
            sc['volumetric_concentration_poi'] = idw_tree(location.xy)[0]
            # print(f"Volumetric Concentration: {sc['volumetric_concentration_poi']}") #BH - remove


class Tree2(object):

    def __init__(self, x=None, z=None, leaf_size=10, distance_threshold=1000, isProjection=False):
        self.x = x
        self.z = z
        self.isProjection = isProjection
        self.distance_threshold = distance_threshold
        if x is not None and z is not None:
            self.tree = cKDTree(x, leafsize=leaf_size)

    def fit(self, array=None, z=None, leaf_size=10):
        self.__init__(array, z, leaf_size)

    # def __call__(self, x, k=6, eps=1e-6, p=2):
    #     # Find points within the distance_threshold
    #     neighbors_list = self.tree.query_ball_point(x, r=self.distance_threshold, eps=eps, p=p)
    #     interpolated_values = np.zeros(x.shape[0])

    #     for i, neighbors in enumerate(neighbors_list):
    #         if not neighbors:
    #             # If there are no neighbors within the threshold, you can assign a default value
    #             interpolated_values[i] = 0  # or any other default value
    #             continue
                
    #         neighbor_coords = self.x[neighbors]
    #         neighbor_z = self.z[neighbors]

    #         if self.isProjection:
    #             # Euclidean distance in projected coordinates
    #             distances = np.linalg.norm(neighbor_coords - x[i], axis=1)
    #         else:
    #             # Haversine for lat/lon
    #             lat1, lon1 = x[i][1], x[i][0]
    #             lat_neighbor = neighbor_coords[:, 1]
    #             lon_neighbor = neighbor_coords[:, 0]
    #             distances = haversine_vectorized(lat1, lon1, lat_neighbor, lon_neighbor)

    #         weights = 1 / (distances + eps)
    #         weighted_z = weights * neighbor_z
    #         interpolated_values[i] = np.sum(weighted_z) / np.sum(weights)

    #     return interpolated_values
    
    def __call__(self,poi_array, k=None, eps=1e-6, p=2):
        # Find points within the distance_threshold
        interpolated_values = np.zeros(poi_array.shape[0])

        for i, poi in enumerate(poi_array):
            if self.isProjection and self.tree is not None:
                 # Euclidean distance in projected coordinates
                neighbor_indices = self.tree.query_ball_point(poi, r=self.distance_threshold, eps=eps, p=p)
                if not neighbor_indices:
                    interpolated_values[i] = 0
                    continue
                neighbor_coords = self.x[neighbor_indices]
                neighbor_z = self.z[neighbor_indices]
                distances = np.linalg.norm(neighbor_coords - poi, axis=1)  # still Euclidean
            else:
                 # Haversine for lat/lon - transformation to meters
                poi_lon, poi_lat = poi[0], poi[1]
                n_lon_array = self.x[:, 0]
                n_lat_array = self.x[:, 1]
                distances = haversine_vectorized(poi_lat, poi_lon, n_lat_array, n_lon_array)
                mask = distances <= self.distance_threshold
                if not np.any(mask):
                    interpolated_values[i] = 0
                    continue
                neighbor_z = self.z[mask]
                distances = distances[mask]

            # Apply top-k filtering if requested
            if k is not None and len(distances) > k:
                topk_idx = np.argsort(distances)[:k]
                distances = distances[topk_idx]
                neighbor_z = neighbor_z[topk_idx]

            weights = 1.0 / (distances + eps)
            interpolated_values[i] = np.sum(weights * neighbor_z) / np.sum(weights)

        return interpolated_values

    def transform(self, x, k=6, p=2, eps=1e-6):
        return self.__call__(x, k=k, eps=eps, p=p, distance_threshold=self.distance_threshold)
    
    def latlon_distance(coord1, coord2):
        return geodesic(coord1[::-1], coord2[::-1]).meters  # reverse to (lat, lon)
    
    def meters_to_degrees(meters, latitude_deg):
        # Approximate length of 1 degree latitude and longitude at a given latitude
        lat_deg_length = 111_132  # meters
        lon_deg_length = 111_320 * math.cos(math.radians(latitude_deg))

        # Assume isotropic distance → take average of lat/lon conversion
        avg_deg_length = (lat_deg_length + lon_deg_length) / 2
        return meters / avg_deg_length
    
