import ee
import datetime
import urllib2
import zipfile
import requests
import zipfile
import StringIO

# Check User Credentials
ee.Initialize()

# Load in Sentinel-1 Collection
collection = ee.ImageCollection("COPERNICUS/S1_GRD")


class Aoi:
    def __init__(self, fusion_table, flood_scene):
        self.fusion_table = ee.FeatureCollection(fusion_table)
        self.flood_scene = ee.Image(flood_scene)

        # Get direction and orbit from metadata
        self.metadata = self.flood_scene.getInfo()
        self.properties = self.metadata['properties']
        self.direction = self.properties['orbitProperties_pass']
        self.orbit = self.properties['relativeOrbitNumber_start']

        # Filter S1 Collection
        self.filter = collection.filterDate(datetime.datetime(2015, 7, 3), datetime.datetime(2015, 11, 5))\
            .filterBounds(self.fusion_table)\
            .filter(ee.Filter().eq('transmitterReceiverPolarisation', 'VH'))\
            .filter(ee.Filter().eq('instrumentMode', 'IW'))\
            .filter(ee.Filter().eq('orbitProperties_pass', self.direction))\
            .filter(ee.Filter().eq('relativeOrbitNumber_start', self.orbit))

        self.filter_list = self.filter.toList(100)
        self.meta_list = self.filter_list.getInfo()

        self.results = None

    def print_orbit_and_track(self):

        print 'Orbit Direction: ', self.direction
        print 'Track Number: ', self.orbit

    def print_filter_metadata(self):
        for image in self.meta_list:
            props = image['properties']
            print props['system:index']

    def analyse(self):
        # Create Median reference image
        median_reference_image = self.filter.median()

        # Median 5x5 Speckle Filter on ref and flood images
        focal_median = median_reference_image.focal_median(5, 'circle', 'pixels').select('VH')
        flood = self.flood_scene.focal_median(5, 'circle', 'pixels').select('VH')

        # Clip images to AOI
        clipped_median_image = focal_median.clip(self.fusion_table)
        clipped_flood_image = flood.clip(self.fusion_table)

        # Calculate Diff
        self.results = clipped_flood_image.select('VH').subtract(clipped_median_image.select('VH'))

    def download(self):

        path = self.results.getDownloadUrl({
            'scale': 30,
            'description' : 'Jan3VH_diff',
        })
        print path

        request = requests.get(path, stream=True)

        with open('test.zip', 'wb') as f:
            for chunk in request.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        zipped_results = zipfile.ZipFile('test.zip')
        zipped_results.extractall()




if __name__ == '__main__':
    run = Aoi('ft:137bhlHOilFr5iTTuSMWJo7jRLCnSCHQaICzLzmJQ',
              'COPERNICUS/S1_GRD/S1A_IW_GRDH_1SDV_20160103T062204_20160103T062229_009326_00D7AC_C9F2')

    run.print_orbit_and_track()
    run.analyse()
    run.download()

