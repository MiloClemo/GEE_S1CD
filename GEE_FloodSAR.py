# Import Modules
import ee, datetime
# Check User Credentials
ee.Initialize()
# Load in AOI Fusion Table
ft2 = ee.FeatureCollection("ft:137bhlHOilFr5iTTuSMWJo7jRLCnSCHQaICzLzmJQ")
# Load in Flood Scene
flood = ee.Image('COPERNICUS/S1_GRD/S1A_IW_GRDH_1SDV_20160103T062204_20160103T062229_009326_00D7AC_C9F2')
# Determine Orbit/Track Metadata
im_meta1 = flood.getInfo()
im_meta2 = im_meta1['properties']
direction = im_meta2['orbitProperties_pass']
orbit = im_meta2['relativeOrbitNumber_start']
print 'Orbit Direction: ', direction
print 'Track Number: ', orbit
# Load in Sentinel-1 Collection
collection = ee.ImageCollection("COPERNICUS/S1_GRD")
# Filter S1 Collection
filter = collection.filterDate(datetime.datetime(2015,7,3), datetime.datetime(2015,11,5)).filterBounds(ft2)\
    .filter(ee.Filter().eq('transmitterReceiverPolarisation', 'VH')).filter(ee.Filter().eq('instrumentMode', 'IW'))\
    .filter(ee.Filter().eq('orbitProperties_pass', direction)).filter(ee.Filter().eq('relativeOrbitNumber_start', orbit))
### Be useful to get a number of images in the collection and use in the filter.toList() command
### Theoretically there could be hundreds of images going into this calculation in the future
list = filter.toList(100)
metalist = list.getInfo()
for image in metalist:
    props = image['properties']
    print props['system:index']
# Create Median reference image
ref = filter.median()
# Median 5x5 Speckle Filter on ref and flood images
ref = ref.focal_median(5, 'circle', 'pixels').select('VH')
flood = flood.focal_median(5, 'circle', 'pixels').select('VH')
# Clip images to AOI
ref = ref.clip(ft2)
flood = flood.clip(ft2)
# Calculate Diff
diff = flood.select('VH').subtract(ref.select('VH'))
### Download Image - still needs work
### Naming download zip file to something more sensible
### Make so tif downloaded is only AOI or set NoData value not to be 0
### Increase potential download size to 10x10 pixel spacing can be downloaded
path = diff.getDownloadUrl({
    'scale': 30,
    'description' : 'Jan3VH_diff',
    #'region' : ft2
    #'maxPixels' : 1000000000
})
print path