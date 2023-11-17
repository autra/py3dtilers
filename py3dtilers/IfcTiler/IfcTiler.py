import logging
import time
import ifcopenshell
from ifcopenshell.file import file
from ..Common import Tiler, Groups
from .ifcObjectGeom import IfcObjectsGeom
from typing import Tuple, Union
from ifcopenshell.file import file


def convert_deg_min_sec_to_float(
        coord: Union[Tuple[int, int, int], Tuple[int, int, int, int]]
    ) -> float:
    """
    Convert ifcsite lon or lat to float

    see https://standards.buildingsmart.org/IFC/RELEASE/IFC4_1/FINAL/HTML/schema/ifcmeasureresource/lexical/ifccompoundplaneanglemeasure.htm
    """
    float_coord = coord[0] + coord[1]/60. + coord[2]/3600.
    # do we have the fourth component (millionth of seconds)?
    if len(coord) == 4:
        float_coord = float_coord + coord[3]/3600.e6; 
    return float_coord


def get_first_site_lon_lat(ifc_file: file) -> dict:
    sites = ifc_file.by_type('IfcSite')
    for site in sites:
        if site.RefLatitude and site.RefLongitude:
            latitude = convert_deg_min_sec_to_float(site.RefLatitude)
            longitude = convert_deg_min_sec_to_float(site.RefLongitude)
            # elevation parsing
            if site.RefElevation is None:
                elevation = 0
            else:
                try:
                    elevation = float(site.RefElevation)
                except ValueError:
                    elevation = 0
            return {
                "latitude": latitude,
                "longitude": longitude,
                "elevation": elevation,
            }
    return {}


class IfcTiler(Tiler):

    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.ifc', '.IFC']

        self.parser.add_argument('--grouped_by',
                                 nargs='?',
                                 default='IfcTypeObject',
                                 choices=['IfcTypeObject', 'IfcGroup', 'IfcSpace'],
                                 help='Either IfcTypeObject or IfcGroup (default: %(default)s)'
                                 )
        self.parser.add_argument('--with_BTH',
                                 dest='with_BTH',
                                 action='store_true',
                                 help='Adds a Batch Table Hierarchy when defined')

    def get_output_dir(self):
        """
        Return the directory name for the tileset.
        """
        if self.args.output_dir is None:
            return "ifc_tileset"
        else:
            return self.args.output_dir

    def from_ifc(self, grouped_by, with_BTH):
        """
        :return: a tileset.
        """
        objects = []
        position = None
        for path_to_file in self.files:
            ifc_file = ifcopenshell.open(path_to_file)

            # note this works only in the case of c where I know there will be one file only
            if position is None: 
                position = get_first_site_lon_lat(ifc_file)

            print("Reading " + str(ifc_file))
            if grouped_by == 'IfcTypeObject':
                pre_tileset = IfcObjectsGeom.retrievObjByType(ifc_file, with_BTH)
            elif grouped_by == 'IfcGroup':
                pre_tileset = IfcObjectsGeom.retrievObjByGroup(ifc_file)
            elif grouped_by == 'IfcSpace':
                pre_tileset = IfcObjectsGeom.retrievObjBySpace(ifc_file, with_BTH)
            else:
                raise Exception(f"Grouping by {grouped_by} is not supported")

            objects.extend([objs for objs in pre_tileset.values() if len(objs) > 0])
        groups = Groups(objects).get_groups_as_list()

        tileset = self.create_tileset_from_groups(groups, "batch_table_hierarchy" if with_BTH else None)
        tileset.attributes["extras"] = position
        return tileset


def main():
    """
    :return: no return value

    this function creates an ifc tileset handling one ifc classe per tiles
    """
    logging.basicConfig(filename='ifctiler.log', level=logging.INFO, filemode="w")
    start_time = time.time()
    logging.info('Started')
    ifc_tiler = IfcTiler()
    ifc_tiler.parse_command_line()
    args = ifc_tiler.args
    tileset = ifc_tiler.from_ifc(args.grouped_by, args.with_BTH)

    if tileset is not None:
        tileset.write_as_json(ifc_tiler.get_output_dir())
    logging.info("--- %s seconds ---" % (time.time() - start_time))


if __name__ == '__main__':
    main()
