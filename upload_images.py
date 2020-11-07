#!/usr/bin/python
# -*- coding: utf-8 -*-

## 
## uploads image files (that already have metadata in Wikidata) from muis.ee to Commons and adds image claim to Wikidata item
## work list is stored in local MongoDB in format:
## {'_id': 'http://www.wikidata.org/entity/Q55869691', 'MuIS': 248095, 'muislink': 'https://www.muis.ee/museaalview/248095', 'commons': '', 'looja': 'http://www.wikidata.org/entity/Q3742903', 'loojaLabel': 'Jaan Koort'}
## inital mongo db is populated from Wikidata Query:   https://w.wiki/ihh
## 

from pymongo import MongoClient
import urllib.request
from PIL import ImageFile
import rdflib
from rdflib import URIRef
import pywikibot
from pywikibot.specialbots import UploadRobot
import os.path, re
from io import BytesIO
import hashlib, base64


def cleanUpTitle(title):
    
    ''' Clean up the title of a potential mediawiki page. Otherwise the title of
    the page might not be allowed by the software.
    '''
    title = title.strip()
    title = re.sub(u"[<{\\[]", u"(", title)
    title = re.sub(u"[>}\\]]", u")", title)
    title = re.sub(u"[ _]?\\(!\\)", u"", title)
    title = re.sub(u"\"", u"", title)
    title = re.sub(u",:[ _]", u", ", title)
    title = re.sub(u"[;:][ _]", u", ", title)
    title = re.sub(u"[\t\n ]+", u" ", title)
    title = re.sub(u"[\r\n ]+", u" ", title)
    title = re.sub(u"[\n]+", u"", title)
    title = re.sub(u"[?!]([.\"]|$)", u"\\1", title)
    title = re.sub(u"[&#%?!]", u"^", title)
    title = re.sub(u"[;]", u",", title)
    title = re.sub(u"[/+\\\\:=]", u"-", title)
    title = re.sub(u"--+", u"-", title)
    title = re.sub(u",,+", u",", title)
    title = re.sub(u"[-,^]([.]|$)", u"\\1", title)
    title = title.replace(u" ", u"_")
    
    return title 
 
 
def generateFileMetadata(wditem):
    
    PART_MAX_LEN = 30
    filename = ''
    wd_image = None
    
    wd_id = wditem['_id']
    wd_id = wd_id.replace('http://www.wikidata.org/entity/', '')
    
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()
    item = pywikibot.ItemPage(repo, wd_id)
    
    item_dict = item.get() #Get the item dictionary
    
    if "et" in item_dict["labels"]:
        filename =  item_dict["labels"]["et"][:PART_MAX_LEN]
    
    clm_dict = item_dict["claims"] # Get the claim dictionary
    
    ## image
    if "P18" in clm_dict:
        wd_image = clm_dict["P18"][0].getTarget()
    
    ## author
    if "P170" in clm_dict:
        wd_author = clm_dict["P170"][0].getTarget()
        author_dict = wd_author.get()
        if "et" in author_dict["labels"] :
            filename =  "%s, %s" % (filename, author_dict["labels"]["et"][:PART_MAX_LEN]) 
        elif "en" in author_dict["labels"] :
            filename =  "%s, %s" % (filename, author_dict["labels"]["en"][:PART_MAX_LEN]) 
            
    ## P217  inventory_nr
    inventory_nr = ''
    if "P217" in clm_dict:
        inventory_nr = clm_dict["P217"][0].getTarget()
        filename =  "%s, %s" % (filename, inventory_nr[:PART_MAX_LEN])
    
    if filename:
        desc = """=={{int:filedesc}}==
{{Artwork
|wikidata=%s
|source=[%s %s]
}}

=={{int:license-header}}==
{{PD-Art|PD-old-auto}}
""" % (wd_id, wditem['muislink'], inventory_nr)

    filename = cleanUpTitle(filename)
    
    return (filename, desc, wd_image)


def findDuplicateImage(photo=None, site=pywikibot.Site(u'commons', u'commons')):
    ''' Takes the photo as BytesIO object, calculates the SHA1 hash and asks the mediawiki api
    for a duplicate
    '''
    
    sha1 = hashlib.sha1()
    sha1.update(photo.getvalue())
    for page in site.allimages(sha1=base64.b16encode(sha1.digest())):
        return page.title(underscore=True)
 
    return None
 
 
def uploadToCommons(filename, desc, file_url):
    
    targetSite = pywikibot.Site('commons', 'commons')
    upFile = None
    
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)

    file = urllib.request.urlopen(file_url)
    ##img_data = requests.get(file_url).content
    img_data = file.read()
    with open(TEMP_FILE, 'wb') as handler:
        handler.write(img_data)  
    file.close()
    duplicate = findDuplicateImage( BytesIO(img_data) )
    if duplicate:
        pywikibot.output(u'Found duplicate at %s' % ( duplicate ) )
    else:
        bot = UploadRobot(TEMP_FILE, description=desc, useFilename=filename, keepFilename=True, verifyDescription=False, targetSite=targetSite)
        upFile = bot.run()
    
    return (upFile, duplicate)


def addImageClaim(wd_id, full_filename):
    
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()
    item = pywikibot.ItemPage(repo, wd_id)

    newclaim = pywikibot.Claim(repo, u'P18')
    commonssite = pywikibot.Site('commons', 'commons')
    imagelink = pywikibot.Link(full_filename, source=commonssite,
            default_namespace=6)
    image = pywikibot.FilePage(imagelink)
    newclaim.setTarget(image) 
    item.addClaim(newclaim)  
    
    return


def getFileSizeAndType(uri):
    # get file size, image size and file type (None if not known)
    
    file = urllib.request.urlopen(uri)
    size = file.headers.get("content-length")
    if size: size = int(size)
    p = ImageFile.Parser()
    while 1:
        data = file.read(1024)
        if not data:
            break
        p.feed(data)
        if p.image:
            break
    file.close()
    if p.image:
        return size, p.image.size, p.image.format
 
    return size, None, None
    

def processItem(wditem):
    
    MAX_FILE_SIZE = 15*1024*1024  #bytes
    MIN_SIDE_LEN = 400 #pixels
    allowed_file_types = {
        "JPEG":  "jpg", 
        "TIFF": "tif"
    }

    wd_id = wditem['_id']
    wd_id = wd_id.replace('http://www.wikidata.org/entity/', '')
    
    rdf_url = "https://www.muis.ee/rdf/media-list/%s" % (wditem['MuIS'])
    # create a Graph
    g = rdflib.Graph()

    g.parse(rdf_url)

    cur_list = URIRef("http://opendata.muis.ee/media-list/%s" % (wditem['MuIS']) )
    min_side = 0
    selected_url = ''
    selected_desc = ''
    wd_image = None
    full_filename = ''
    oversized = False
    
    for img_url in g.objects(subject=cur_list, predicate=None):
        if 'muis' in img_url:
            print(img_url)
            prev_min_side = min_side
            (size_bytes, (img_length, img_height), img_type) = getFileSizeAndType(img_url)
            if size_bytes > MAX_FILE_SIZE :
                oversized = True
                print("file size exeeds limit")
                break
            min_side = img_height
            if (img_length < img_height):
                min_side = img_length
            if min_side > MIN_SIDE_LEN:
                if img_type in allowed_file_types and min_side > prev_min_side:
                    (shortname, selected_desc, wd_image) = generateFileMetadata(wditem)
                    full_filename = shortname + '.' + allowed_file_types[img_type]
                    selected_url = img_url
                    
    print (full_filename)
    print (selected_desc)
    print (selected_url)
    print (wd_image)
    
    if oversized:
        mycol.update_one({"_id": wditem['_id']}, {"$set": {"status": "oversize"}})
    elif full_filename and not wd_image:
        (uploaded, duplicate) = uploadToCommons(full_filename, selected_desc, selected_url) 
        if uploaded:
            addImageClaim(wd_id, full_filename)
            
            #update mongodb
            mycol.update_one({"_id": wditem['_id']}, {"$set": {"status": "uploaded"}})
        elif (duplicate):
            addImageClaim(wd_id, duplicate)
            mycol.update_one({"_id": wditem['_id']}, {"$set": {"status": "updated_wd"}})
    else:
        print ("----skipped\n\n")       # no image or image is too small
        mycol.update_one({"_id": wditem['_id']}, {"$set": {"status": "skipped"}})



## main

TEMP_FILE = 'temp_image'
MAX_ITEM_COUNT = 50

client = MongoClient()

mydb = client["muis"]
mycol = mydb["pildid"]
item_count = 0

for wditem in mycol.find({ "status" : { "$exists" : False } }):
    if not wditem['commons']:
        print( wditem )
        processItem(wditem)
        item_count += 1
    if item_count >= MAX_ITEM_COUNT:
        break

pywikibot.stopme()
