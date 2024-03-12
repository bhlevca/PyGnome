from colander import (String, SchemaNode)
from gnome.persist.base_schema import (ObjTypeSchema,
                                       LongLat,
                                       GeneralGnomeObjectSchema)
from gnome.persist.extend_colander import OrderedCollectionSchema
from gnome.gnomeobject import GnomeId
from gnome.utilities.orderedcollection import OrderedCollection
import mikeio
import numpy as np
import os
from pyproj import Transformer, CRS


class DfsuWaterDepthSchema(ObjTypeSchema):
    pass
    

class DfsuWaterDepth(GnomeId):
    '''
    Water depth in dfsu file
    '''

    _schema = DfsuWaterDepthSchema

    def __init__(self,
                 name='DfsuWaterDepth',
                 dfsufilename=None,
                 **kwargs):

        super(DfsuWaterDepth, self).__init__(name=name, **kwargs)
        self._filename = dfsufilename
        self._crs_4326 = CRS.from_epsg(4326)
        self.read_dfsu()        

    def transform(self, location:LongLat):
        return self._crs_transformer.transform(location.long, location.lat)

    def _locate_time(self, time):
        first_time = self._ds.time[self._ds.time - time < self._time_interval][0]
        second_time = first_time + self._time_interval
        if second_time > self._ds.time[-1]:
            second_time = self._ds.time[-1]
        return first_time, second_time

    def at(self, points=None, time=None):
        """
        Follow the example of VectorVariable.at() function to get the 
        """
        if self.filename is not None and self._ds is not None:
            try:
                coordinates = self._crs_transformer.transform(points[:,1],points[:,0])
                coordinates = np.array(coordinates).transpose()

                first_time, second_time = self._locate_time(time)
                first_value = np.array([self._ds.sel(x=p[0], y=p[1])[0][first_time].values for p in coordinates])
                second_value = np.array([self._ds.sel(x=p[0], y=p[1])[0][second_time].values for p in coordinates])
                interpolated_value = first_value + (second_value - first_value) * (time - first_time) / self._time_interval
                return interpolated_value, coordinates
            except:
                return None, None
        else:
            return None, None
    
    def read_dfsu(self):
        if self.filename is not None and os.path.exists(self.filename):
            self._ds = mikeio.read(self.filename, items=["Total water depth"])
            self._project_string = self._ds.geometry.projection
            self._crs_dfsu = CRS.from_string(self._ds.geometry.projection)
            self._crs_transformer = Transformer.from_crs(self._crs_4326, self._crs_dfsu)
            self._time_interval = self._ds.time[1] - self._ds.time[0]

    @property
    def project_string(self):
        if hasattr(self, '_project_string'):
            return self._project_string
        else:
            return None

    @property
    def filename(self):
        if hasattr(self, '_filename'):
            return self._filename
        else:
            return None

    @filename.setter
    def filename(self, fn):
        self._filename = fn
        self.read_dfsu()

