import unittest
from argparse import Namespace
from pathlib import Path

import ifcopenshell
from ifcopenshell.file import file
from ifcopenshell.api import run
from pytest import fixture

from py3dtilers.IfcTiler.IfcTiler import (
    IfcTiler,
    convert_deg_min_sec_to_float,
    get_first_site_lon_lat,
)


@fixture
def blank_ifc_model():
    # Create a blank model
    model = ifcopenshell.file()

    # All projects must have one IFC Project element
    project = run("root.create_entity", model, ifc_class="IfcProject", name="My Project")

    # Create a site, building, and storey. Many hierarchies are possible.
    for i in range(5):
        run("root.create_entity", model, ifc_class="IfcSite", name=f"My Site n°{i}")

    return model


@fixture
def ifc_model_with_lon_lat(blank_ifc_model: file):
    sites = blank_ifc_model.by_type('IfcSite')
    # arbitrarily set stuff in 4th site
    sites[3].RefLatitude = (49, 0, 0)
    sites[3].RefLongitude = (8, 0, 0)
    sites[3].RefElevation = 16.1
    return blank_ifc_model


def get_default_namespace():
    return Namespace(obj=None, loa=None, lod1=False, crs_in='EPSG:3946',
                     crs_out='EPSG:3946', offset=[0, 0, 0], with_texture=False, grouped_by='IfcTypeObject', scale=1,
                     output_dir=None, geometric_error=[None, None, None], kd_tree_max=None, texture_lods=0)


class Test_Tile(unittest.TestCase):

    def test_IFC4_case(self):
        ifc_tiler = IfcTiler()
        ifc_tiler.files = [Path('tests/ifc_tiler_test_data/FZK.ifc')]
        ifc_tiler.args = get_default_namespace()
        ifc_tiler.args.output_dir = Path("tests/ifc_tiler_test_data/generated_tilesets/")

        tileset = ifc_tiler.from_ifc(ifc_tiler.args.grouped_by, with_BTH=False)
        if tileset is not None:
            tileset.write_as_json(ifc_tiler.args.output_dir)

        assert tileset.attributes["extras"] is not None
        assert tileset.attributes["extras"]["latitude"] == 49.100435
        assert tileset.attributes["extras"]["longitude"] == 8.436539
        assert tileset.attributes["extras"]["elevation"] == 110.0


def test_convert_deg_min_sec_to_float():
    assert convert_deg_min_sec_to_float((49, 0, 0)) == 49
    assert convert_deg_min_sec_to_float((49, 0, 0, 0)) == 49
    assert convert_deg_min_sec_to_float((49,6,1,566000)) == 49.100435
    assert convert_deg_min_sec_to_float((8,26,11,540400)) == 8.436539


def test_get_first_site_lon_lat_non_existent(blank_ifc_model: file):
    assert get_first_site_lon_lat(blank_ifc_model) == {}


def test_get_first_site_lon_lat(ifc_model_with_lon_lat: file):
    assert get_first_site_lon_lat(ifc_model_with_lon_lat) == {
                "latitude": 49.0,
                "longitude": 8.0,
                "elevation": 16.1
            }


if __name__ == '__main__':
    unittest.main()
