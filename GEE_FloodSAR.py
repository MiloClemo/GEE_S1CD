import ee
import datetime
import requests
import zipfile
import numpy as np
import os
import gdal
from osgeo.gdalconst import GA_ReadOnly, GDT_Float32


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

    ### Original attempt at thresholding
    #def threshold(self):
        # Calculate Mean of Image
        #array = np.array(self.results)
        #print array.shape
        #print array.ndim
        #print array.dtype.name
        #print type(array)
        #self.mean = array.mean()
        #print self.mean


    def download(self):

        self.path = self.results.getDownloadUrl({
            'scale': 20,
            'geometry': self.fusion_table,
            'description' : 'Test',
        })
        print self.path

        request = requests.get(self.path, stream=True)

        with open('test.zip', 'wb') as f:
            for chunk in request.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        zipped_results = zipfile.ZipFile('test.zip')
        zipped_results.extractall()


    def threshold(self):
        gdal.AllRegister()
        os.getcwd()
        driver = gdal.GetDriverByName('GTiff')
        pathname = 'E:/PyCharm/' + self.path[55:87] + '.VH.tif'
        opengd = gdal.Open(pathname, GA_ReadOnly)
        array = opengd.ReadAsArray(0, 0, opengd.RasterXSize, opengd.RasterYSize)
        # Set 0 as NoData as not set in GEE
        array[array == 0] = np.nan
        # Calculate Mean, SD and Threshold Value
        mean = np.nanmean(array)
        sd = np.nanstd(array)
        threshold = mean - (1.5*sd)
        print 'Mean: ', mean
        print 'Standard Deviation: ', sd
        print 'Threshold Value: ', threshold
        # Reset NoData to 0 (as crashes otherwise)
        array = np.nan_to_num(array)
        # Threshold the data
        array[array > threshold] = np.nan
        # Output
        outDataSet = driver.Create('E:/PyCharm/testing.tif', opengd.RasterXSize,\
                                   opengd.RasterYSize, 1, GDT_Float32)
        outBand = outDataSet.GetRasterBand(1)
        outBand.WriteArray(array, 0, 0)
        outBand.SetNoDataValue(-9999)
        outDataSet.SetProjection(opengd.GetProjection())
        outDataSet.SetGeoTransform(opengd.GetGeoTransform())
        outBand.FlushCache()
        outDataSet.FlushCache()

if __name__ == '__main__':
    run = Aoi('ft:1u3KrTf5vz1ntE5hqVCRU_7I5_afqEkM-NYrDyurL',
              'COPERNICUS/S1_GRD/S1A_IW_GRDH_1SDV_20151229T061403_20151229T061428_009253_00D59B_CC2A')

    run.print_orbit_and_track()
    run.analyse()
    run.download()
    run.threshold()


