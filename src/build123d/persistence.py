"""
build123d pickle support

name: persistence.py
by:   Jojain & bernhard-42
date: September 8th, 2023

desc:
    This python module enables build123d objects to be pickled.

license:

    Copyright 2023 Jojain & bernhard-42

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""
# pylint has trouble with the OCP imports
# pylint: disable=no-name-in-module, import-error

import copyreg
import io
import struct

from OCP.BinTools import BinTools
from OCP.gp import gp_Quaternion, gp_Trsf, gp_Vec
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import (
    TopoDS_Compound,
    TopoDS_CompSolid,
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Shape,
    TopoDS_Shell,
    TopoDS_Solid,
    TopoDS_Vertex,
    TopoDS_Wire,
)

from build123d.topology import downcast


import ocp_serializer


def serialize_shape(shape: TopoDS_Shape) -> bytes:
    """
    Serialize a OCP shape, this method can be used to provide a custom serialization algo for pickle
    """
    if shape is None:
        return None

    return ocp_serializer.serialize_shape(shape)


def deserialize_shape(buffer: bytes) -> TopoDS_Shape:
    """
    This does the opposite as serialize, it construct a TopoDS_Shape from bytes.
    """
    if buffer is None:
        return None

    return downcast(ocp_serializer.deserialize_shape(buffer))


def serialize_location(location: TopLoc_Location) -> bytes:
    """
    Serialize a OCP location, this method can be used to provide
    a custom serialization algo for pickle
    """
    if location is None:
        return None

    return ocp_serializer.serialize_location(location)


def deserialize_location(buffer: bytes) -> TopLoc_Location:
    """
    This does the opposite as serialize, it construct a TopLoc_Location from bytes.
    """
    if buffer is None:
        return None



def reduce_shape(shape: TopoDS_Shape) -> tuple:
    """Special function used by pickle to serialize or deserialize OCP Shapes objects"""
    return (deserialize_shape, (serialize_shape(shape),))


def reduce_location(location: TopLoc_Location) -> tuple:
    """Special function used by pickle to serialize or deserialize OCP Location objects"""
    return (deserialize_location, (serialize_location(location),))


def modify_copyreg():
    """
    Modify the copyreg so that pickle knows what to look for when it tries to pickle an OCP Shape
    """
    copyreg.pickle(TopoDS_Shape, reduce_shape)
    copyreg.pickle(TopoDS_Compound, reduce_shape)
    copyreg.pickle(TopoDS_CompSolid, reduce_shape)
    copyreg.pickle(TopoDS_Solid, reduce_shape)
    copyreg.pickle(TopoDS_Shell, reduce_shape)
    copyreg.pickle(TopoDS_Face, reduce_shape)
    copyreg.pickle(TopoDS_Wire, reduce_shape)
    copyreg.pickle(TopoDS_Edge, reduce_shape)
    copyreg.pickle(TopoDS_Vertex, reduce_shape)
    copyreg.pickle(TopLoc_Location, reduce_location)
