from gnome.persist.base_schema import LongLat, ObjTypeSchema
from gnome.gnomeobject import GnomeId
from pyproj import Transformer, CRS
import numpy as np

class ConcentrationLocationSchema(ObjTypeSchema):
    locations = LongLat(
        save=True, update=True
    )

class ConcentrationLocation(GnomeId):
    _schema = ConcentrationLocationSchema

    def __init__(self,
                 long=0.0,
                 lat=0.0,
                 **kwargs):

        super(ConcentrationLocation, self).__init__(**kwargs)
        
        self.long = long
        self.lat = lat
    

    def transform(self, projection_string):
        crs_4326 = CRS.from_epsg(4326)
        crs_project = CRS.from_string(projection_string)
        crs_transformer = Transformer.from_crs(crs_4326, crs_project)
        transformed = crs_transformer.transform(self.lat, self.long)
        self._x = transformed[0]
        self._y = transformed[1]
        self._xy = np.array([[self._x, self._y]])

    @property
    def x(self):
        if hasattr(self, '_x'):
            return self._x
        else:
            return None

    @property
    def y(self):
        if hasattr(self, '_y'):
            return self._y
        else:
            return None
        
    @property
    def xy(self):
        if hasattr(self, '_xy'):
            return self._xy
        else:
            return None