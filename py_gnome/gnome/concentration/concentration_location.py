from colander import SequenceSchema
from gnome.persist.base_schema import LongLat, ObjTypeSchema,WorldPoint
from gnome.gnomeobject import GnomeId
from pyproj import Transformer, CRS
import numpy as np

class Positions(SequenceSchema):
    position = WorldPoint(save=True, update=True)

class ConcentrationLocationSchema(ObjTypeSchema):
    locations = Positions(save=True, update=True)

class ConcentrationLocation(GnomeId):
    _schema = ConcentrationLocationSchema

    def __init__(self,
                 locations=None,
                 **kwargs):

        super(ConcentrationLocation, self).__init__(**kwargs)
        
        self.locations = locations
        print(f"Initializing ConcentrationLocation with locations={locations}")   #BH -remove

    def transform(self, projection_string):
        print(f"Transforming locations: {self.locations}")  #BH -remove
        if self.locations is not None and len(self.locations) > 0:
            crs_4326 = CRS.from_epsg(4326)
            crs_project = CRS.from_string(projection_string)
            crs_transformer = Transformer.from_crs(crs_4326, crs_project)
            if crs_transformer.source_crs == crs_transformer.target_crs:
                transformed = crs_transformer.transform(self.locations[0][0], self.locations[0][1])
            else:
                transformed = crs_transformer.transform(self.locations[0][1], self.locations[0][0])
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