import os
from pathlib import Path

from pcapi.scripts.iris.import_iris import import_iris_shape_file_to_table
from pcapi.utils.logger import logger

FILE_PATH = Path(os.path.dirname(os.path.realpath('sandboxes/iris/paris.shp')))


def create_industrial_iris(file_path: str):
    logger.info('load_iris_data')

    import_iris_shape_file_to_table(file_path)

    logger.info('created 1000 paris iris data')