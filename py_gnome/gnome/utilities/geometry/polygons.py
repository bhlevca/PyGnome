"""
Polygon module, part of the geometry package

Assorted stuff for working with polygons
"""

import copy

import numpy as np

import BBox

class Polygon(np.ndarray):
    """
    A Polygon class
    
    This is a subclass of np.ndarray, so that it can be used in place of a
    simple array of points, but also can hold extra meta-data in a "metadata"
    dict.
    
    """
    def __new__(Polygon, points, metadata=None, copy=True, dtype=np.float):
        ## fixme: this needs a better way to index and loop to get a point
        """
        Takes Points as an array. Data is any python sequence that can be turned into a 
        Nx2 numpy array of floats. The data will be copied unless the copy argument is set
        to False.
        
        metadata is a dict of meta-data. This can hold anything.
        
        """
        # convert to array, copying data unless not requested.
        arr = np.array(points, dtype, copy=copy)
        arr.shape = (-1,2) # assure it's the right shape
        # Transform to a Polygon
        arr = arr.view(Polygon)
        # add the attribute
        # Use the specified 'metadata' parameter if given
        if metadata is not None:
            arr.metadata = metadata
        # Otherwise, use points metadata attribute if it exists
        else:
            arr.metadata = getattr(points, 'metadata', {})

        return arr

    def __array_finalize__(self, obj):
        ## I'm not entirely sure why this is required, but I copied it from:
        ##   http://www.scipy.org/Subclasses
       
        # We use the getattr method to set a defaults if 'obj' doesn't have the attributes
        self.metadata = getattr(obj, 'metadata', {})
 
    def  __getitem__(self, index):
        """
        override __getitem__ to return a simple (2, ) ndarray, rather than a Polygon object
        """
        print "__getitem__ called", index
        return np.asarray( np.ndarray.__getitem__(self, index) )

    def __eq__(self, other):
        if not isinstance(other, Polygon):
            # a Polygon is never equal to anything else
            return False
        else:
            return np.array_equal(self, other) and (self.metadata == other.metadata)

    def __str__(self):
        return "Polygon with %i points.\nmetadata: %s"%(self.shape[0], self.metadata)

    def __repr__(self):
        msg = ["Polygon( [",]
        pstr = []
        for point in self:
            try:
                pstr.append("[%s, %s]"%(point[0], point[1]) )
            except IndexError:
                print "IndexError in __repr__: an error in a point?"
                pass
        msg.append( ",\n          ".join(pstr) )
        msg.append("],\n         metadata=%s\n       )"%repr(self.metadata) )
        return "".join(msg)


    @property
    def points(self):
        """
        the points as a regular np.ndarray
        """
        return np.asarray(self)

    @property
    def bounding_box(self):
        return BBox.fromPoints(self)

   
class PolygonSet:
    """
    A set of polygons (or polylines) stored as a single array of vertex data,
    and indexes into that array.
    """
     
    def __init__(self, data = None, dtype=np.float64):
        """
        create a new PolygonSet object
        
        if no data is passed in, and empty set is created.
        
        if data is passed in, it must a a tuple:
        (PointsArray, IndexArray, DataList)

        """
        self.dtype = dtype
        if data is  None:
            self._PointsArray = np.zeros((0,2), self.dtype)
            self._IndexArray = np.array( (0,), dtype=np.int)
            self._MetaDataList = []
        else:
            self._PointsArray = np.array(data[0])
            self._IndexArray  = np.array(data[1])
            self._MetaDataList  = np.array(data[2])
        
    def append(self, polygon, metadata=None):

        """
        polygon should be a Polygon object or a  NX2 array (or something that
           can be turned into one)

        So that polygon[n,0] is the x coordinate of the nth point and 
                polygon[n,1] is the y coordinate of the nth point 

        """
        if metadata is None:
            metadata = getattr(polygon, 'metadata', {})
        polygon = np.asarray(polygon, dtype=self.dtype).reshape((-1, 2))
        self._PointsArray = np.r_[self._PointsArray, polygon]
        self._IndexArray  = np.r_[self._IndexArray, (self._PointsArray.shape[0],) ]
        self._MetaDataList.append(metadata)

    def _get_bounding_box(self):
        return BBox.fromPoints(self._PointsArray)
    bounding_box = property(_get_bounding_box)

    def _get_total_num_points(self):
        return len(self._PointsArray)
    total_num_points = property(_get_total_num_points)

    def GetPointsData(self):
        """
        returns a copy of the points and indexes arrays
        """
        return (self._PointsArray.copy(), self._IndexArray.copy())

    def GetMetaData(self):
        """
        returns a (shallow) copy of the metadata list
        """
        return copy.copy(self._MetaDataList)

    def SetPointsData(self, PointData, MetaData = None):
        """

        SetPointsData(PointData)

        where PointData is a tuple of two NX2 arrays, or objects that can be converted to arrays:
        PointData = (PointsArray, IndexArray)

        Sets the data for a polygon set. Be careful with this one, it
        destroys all the current data, and doesn't check for a match
        between your PointsArray and IndexArray.
        
        The data type is preserved for the points, but it should probably be a float type.

        It can be useful for setting the data in one PolygonSet to the same as another set:
            set1.SetPointsData(set2.GetPointsData)

        A copy is made, so the two sets will be distinct

        """
        
        self._PointsArray = np.array(PointData[0], self.dtype)
        self._IndexArray = np.array(PointData[1], dtype=np.int)
        if MetaData is not None:
            self._DataArray = MetaData
        else:
            self._DataArray = [None] * len(self.PointsArray)
    
    def Copy(self):
        """
        returns a "deep copy" of the PolygonSet Object -- 
          i.e. it does not share any data with the original
        """
        cp =  PolygonSet()
        cp._PointsArray = self._PointsArray.copy()
        cp._IndexArray = self._IndexArray.copy()
        cp._MetaDataList = copy.deepcopy(self._MetaDataList)  
        
        return cp      
        
    def TransformData(self, TransformFunction, args=(), kwargs={}):
        ## fixme: if this was a ndarray subclass, it would "just work"
        """

        TransformData(Transform Function, args=(), kwargs={})

        Transforms the data for a polygon set. It applies the passed in
        Transform Function to all the points in the polygon set. The
        function needs to accept a NX2 NumPy array of Floats, and return
        a NX2 NumPy array of floats

        the optional arguments, args or kwargs are passed through to
        the TransformFuntion, so it is called as:

        NewPoints = TransformFunction(OldPoints, *args, **kwargs)

        """
        self._PointsArray = TransformFunction(self._PointsArray, *args, **kwargs)
    
    def __len__(self):
        return len(self._IndexArray) - 1 # there is an extra index at the end, so that IndexArray[i+1] works
        
    def __getitem__(self,index):
        """
        returns a Polygon object
        """
        if index > (len(self._IndexArray) - 1):
            raise IndexError
        if  index < 0:
             if index < - (len(self._IndexArray) -1 ):
                 raise IndexError
             index = len(self._IndexArray) -1 + index
        poly = Polygon(self._PointsArray[self._IndexArray[index]:self._IndexArray[index+1]],
                       metadata = self._MetaDataList[index],
                       dtype = self.dtype)
        return poly

    def __str__(self):
        return "PolygonSet instance with %i polygons, %i total points"%(len(self), len(self._PointsArray))

    def __repr__(self):
        """ same as __str__ -- not good but more informative than nothing"""
        return self.__str__()

    def __eq__(self, other):
        if not isinstance(other, PolygonSet):
            #a PolygonSet is never equal to anything else
            return False
        else:
            return np.array_equal(self._PointsArray, other._PointsArray) and self._MetaDataList == other._MetaDataList

    def thin(self, scale):
        """
        Returns a new PolygonSet object, with the points thinned.

        :param scale: The scale to use: it is the ratio of world coords
                      (usually lat-lon degrees) to pixels.
        :type scale: (x_scale, y_scale): tuple of floats

        This is an algorithm designed for rendering. What is does
        is scale the points as you would to draw them (integer pixels).
        Then it removes any sequential duplicate points. Thus the rendered
        results should be exactly the same as if you rendered the pre-thinned
        polygons.

        Polygons that are reduced to 1 point are removed.

        NOTE: in a sequence of close points, the first point is retained.
              Perhaps it would be better for the mean location of the
              sequence to be used instead? It should make no difference
              for rendering, but could make a difference for other purposes 
        """
        scale = np.asarray(scale, dtype=np.float64)

        # Scale the polygons:

        def scaling_fun(arr):
            " scales, rounds, then re-scales back"
            return np.round(arr * scale) / scale

        scaled_polys = self.Copy()
        scaled_polys.TransformData(scaling_fun)
        # remove the duplicates:
        new_polys = PolygonSet()
        for i in xrange(len(scaled_polys)):
            sc_poly = scaled_polys[i]
            orig_poly = self[i]
            last_point = np.asarray(sc_poly[0])
            thinned = [orig_poly[0]]
            for j in xrange(len(sc_poly)):
                point = sc_poly[j]
                print "comparing:", point, last_point
                if not np.array_equal(point, last_point):
                    thinned.append(orig_poly[j])
                last_point = point
            if len(thinned) > 1:
                print "adding:", thinned
                new_polys.append(Polygon(thinned, metadata=orig_poly.metadata))

        return new_polys






def test():
    #  a test function

    p1 = np.array([[1,2],[3,4],[5,6],[7,8]])
    p2 = p1 * 5

    set = PolygonSet()
    set.append(p1)
    set.append(p2)

    print set[0]
    print set[1]

    
    print "minimum is: ",set.GetBoundingBox()[0]
    print "maximum is: ",set.GetBoundingBox()[1]



if __name__ == "__main__":
    # run a test function
    test()

