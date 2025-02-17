# -*- coding: utf-8 -*-

import csv, logging, os, sys, zipfile
if sys.platform == 'win32':
    csv.field_size_limit(2**31-1)
else:
    csv.field_size_limit(sys.maxsize)
try:
    from urllib import urlretrieve
except ImportError:
    from urllib.request import urlretrieve
from scipy.spatial import cKDTree as KDTree

# location of geocode data to download
GEOCODE_URL = 'http://download.geonames.org/export/dump/cities1000.zip'
GEOCODE_FILENAME = 'cities1000.txt'


def is_moscow_part(admin1, country_code, city_type):
    return admin1 == '48' and country_code == 'RU' and city_type != 'PPLC'


def singleton(cls):
    """Singleton pattern to avoid loading class multiple times
    """
    instances = {}

    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance


@singleton
class GeocodeData:

    def __init__(self, geocode_filename='geocode.csv', country_filename='countries.csv'):
        coordinates, self.__locations = self.__extract(rel_path(geocode_filename))
        self.__tree = KDTree(coordinates)
        self.__load_countries(rel_path(country_filename))

    def __load_countries(self, country_filename):
        """Load a map of country code to name
        """
        self.__countries = {}
        with open(country_filename, 'r') as handler:
            for code, name in csv.reader(handler):
                self.__countries[code] = name

    def query(self, coordinates):
        """Find closest match to this list of coordinates
        """
        try:
            distances, indices = self.__tree.query(coordinates, k=1)
        except ValueError as e:
            logging.info('Unable to parse coordinates: {}'.format(coordinates))
            raise e
        else:
            results = [self.__locations[index] for index in indices]
            for result in results:
                result['country'] = self.__countries.get(result['country_code'], '')
            return results

    def __download(self):
        """Download geocode file
        """
        local_filename = os.path.abspath(os.path.basename(GEOCODE_URL))
        if not os.path.exists(local_filename):
            logging.info('Downloading: {}'.format(GEOCODE_URL))
            urlretrieve(GEOCODE_URL, local_filename)
        return local_filename

    def __extract(self, local_filename):
        """Extract geocode data from zip
        """
        if os.path.exists(local_filename):
            # open compact CSV
            rows = csv.reader(open(local_filename, 'r'))
        else:
            if not os.path.exists(GEOCODE_FILENAME):
                # remove GEOCODE_FILENAME to get updated data
                downloadedFile = self.__download()
                logging.info('Extracting: {}'.format(GEOCODE_FILENAME))
                with zipfile.ZipFile(downloadedFile) as z:
                    with open(GEOCODE_FILENAME, 'wb') as fp:
                        fp.write(z.read(GEOCODE_FILENAME))

            # extract coordinates into more compact CSV for faster loading
            writer = csv.writer(open(local_filename, 'w'))
            rows = []
            for row in csv.reader(open(GEOCODE_FILENAME, 'r'), delimiter='\t'):
                latitude, longitude = row[4:6]
                country_code = row[8]
                if latitude and longitude and country_code:
                    city = row[1]
                    city_type = row[7]
                    admin1 = row[10]
                    row = latitude, longitude, country_code, city
                    if city_type not in ('PPLX', 'PPLA3', 'PPLH'):
                        if not is_moscow_part(admin1, country_code, city_type):
                            writer.writerow(row)
                            rows.append(row)
            # cleanup downloaded files
            os.remove(downloadedFile)
            os.remove(GEOCODE_FILENAME)

        # load a list of known coordinates and corresponding __locations
        coordinates, __locations = [], []
        for latitude, longitude, country_code, city in rows:
            coordinates.append((latitude, longitude))
            __locations.append(dict(country_code=country_code, city=city))
        return coordinates, __locations


def rel_path(filename):
    """Return the path of this filename relative to the current script
    """
    return os.path.join(os.getcwd(), os.path.dirname(__file__), filename)


def get(coordinate):
    """Search for closest known location to this coordinate
    """
    gd = GeocodeData()
    return gd.query([coordinate])[0]


def search(coordinates):
    """Search for closest known locations to these coordinates
    """
    gd = GeocodeData()
    return gd.query(coordinates)


if __name__ == '__main__':
    # test some coordinate lookups
    city1 = 55.68704223632812, 37.53937149047852
    city2 = 31.76, 35.21
    print(get(city1))
    print(search([city1, city2]))
