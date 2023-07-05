from colander import (String, SchemaNode)
from gnome.persist.base_schema import (ObjTypeSchema,
                                       LongLat,
                                       GeneralGnomeObjectSchema)
from gnome.persist.extend_colander import OrderedCollectionSchema
from gnome.gnomeobject import GnomeId
from gnome.utilities.orderedcollection import OrderedCollection
from gnome.spills.release import StartPositions

class ConcentrationSchema(ObjTypeSchema):
    locations = StartPositions(save=True, update=True)
    

class Concentration(GnomeId):
    _schema = ConcentrationSchema

    def __init__(self,
                 name='Concentration',
                 locations=None,
                 **kwargs):

        super(Concentration, self).__init__(name=name, **kwargs)
        self.locations = locations
