import datetime, rdflib, requests, time
import pywikibot
from lxml import etree
from pywikibot import pagegenerators as pg


# Checks whether the entry for the artwork specifies it is a painting
def ispainting(physical_thing):
    typeXML = physical_thing.find('crm:P2_has_type', physical_thing.nsmap)
    type = typeXML.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
    if type == 'http://opendata.muis.ee/thesaurus/203/13540':
        return True
    else:
        return False


def findlabel(physical_thing):
    label = physical_thing.find('rdfs:label', physical_thing.nsmap).text
    return label


def findidentifier(physical_thing):
    identifier = physical_thing.find('dcterms:identifier', physical_thing.nsmap).text
    return identifier


def findtechnique(physical_thing):
    techniques = []
    psP2 = physical_thing.findall('crm:P2_has_type', physical_thing.nsmap)
    for p2 in psP2:
        techniqueSection = p2.find('muis:Technique', physical_thing.nsmap)
        technique = techniqueSection.find('crm:P130_shows_features_of', physical_thing.nsmap)
        techniqueResource = technique.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
        techniqueWDItem = decodeTechnique(techniqueResource)
        if techniqueWDItem is not None:
            techniques.append(techniqueWDItem)
        else:
            print "Technique not found: " + techniqueResource
    return techniques


def decodeTechnique(technique):
    switcher = {
        # 6li
        'http://opendata.muis.ee/thesaurus/107/5329': "Q296955",
        'http://opendata.muis.ee/thesaurus/107/33126': "Q296955",
        # segatehnika = "mixed technique" doesn't seem to be a good match for WD "material"
        'http://opendata.muis.ee/thesaurus/107/5328': None,
        # tempera
        'http://opendata.muis.ee/thesaurus/107/5259': "Q175166",
        # guass
        'http://opendata.muis.ee/thesaurus/107/5539': "Q204330"
    }
    return switcher.get(technique, None)

def findmaterial(physical_thing):
    materials = []
    psP45 = physical_thing.findall('crm:P45_consists_of', physical_thing.nsmap)
    for p45 in psP45:
        materialSection = p45.find('crm:E57_Material', physical_thing.nsmap)
        material = materialSection.find('crm:P130_shows_features_of', physical_thing.nsmap)
        materialResource = material.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
        materialWDItem = decodeMaterial(materialResource)
        if materialWDItem is not None:
            materials.append(materialWDItem)
        else:
            print "Material not found: " + materialResource
    return materials


def decodeMaterial(material):
    switcher = {
        # l6uend
        'http://opendata.muis.ee/thesaurus/112/32314': "Q219803",
        # vineer
        'http://opendata.muis.ee/thesaurus/112/2345': "Q12321255",
        'http://opendata.muis.ee/thesaurus/112/2461': "Q12321255",
        # metall
        'http://opendata.muis.ee/thesaurus/112/2139': "Q11426",
        # paber
        'http://opendata.muis.ee/thesaurus/112/2195': "Q11472",
        # masoniit
        'http://opendata.muis.ee/thesaurus/112/29672': "Q1808397",
        # kartong = cardboard
        'http://opendata.muis.ee/thesaurus/112/2203': "Q389782",
        # papp = cardboard
        'http://opendata.muis.ee/thesaurus/112/2362': "Q389782",
        # puitkiudplaat
        'http://opendata.muis.ee/thesaurus/112/2410': "Q1397443",

    }
    return switcher.get(material, None)


def finddimensions(physical_thing):
    dimensionsXML = physical_thing.findall('crm:P43_has_dimension', physical_thing.nsmap)
    # We assume if there's only two dimensions, they're likely height and width so we go on
    if len(dimensionsXML) == 2:
        dimensions = {}
        for dimension in dimensionsXML:
            dimensionXML = dimension.find('crm:E54_Dimension', physical_thing.nsmap)
            dimensionType = dimensionXML.find('crm:P2_has_type', physical_thing.nsmap)
            dimensionTypeURI = dimensionType.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
            dimensionUnit = dimensionXML.find('crm:P91_has_unit', physical_thing.nsmap)
            dimensionUnitURI = dimensionUnit.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
            # 49/2506 = height
            if dimensionTypeURI == 'http://opendata.muis.ee/thesaurus/49/2506':
                dimensions['height'] = dimensionXML.find('crm:P90_has_value', physical_thing.nsmap).text
                dimensions['height-unit'] = decodeUnit(dimensionUnitURI)
            # 49/2485 = width
            if dimensionTypeURI == 'http://opendata.muis.ee/thesaurus/49/2485':
                dimensions['width'] = dimensionXML.find('crm:P90_has_value', physical_thing.nsmap).text
                dimensions['width-unit'] = decodeUnit(dimensionUnitURI)
        # (for now) We only want to send dimensions if we have height + width + units
        if len(dimensions) == 4:
            return dimensions
        else:
            return None
    return None


def decodeUnit(unit):
    switcher = {
        # cm
        'http://opendata.muis.ee/thesaurus/200/2526': "http://www.wikidata.org/entity/Q174728",
    }
    return switcher.get(unit, "nothing")


def findcreationevent(physical_thing):
    eventsXML = physical_thing.findall('crm:P12_occurred_in_the_presence_of', physical_thing.nsmap)
    for event in eventsXML:
        # We take the event resource to find more info
        eventURI = event.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
        # We parse the event page
        eventXML = etree.fromstring(requests.get(eventURI).content)
        # We find the Event section in it
        eventSection = eventXML.find('crm:E5_Event', physical_thing.nsmap)
        # We find the type and extract its URI
        eventTypeXML = eventSection.find('crm:P2_has_type', physical_thing.nsmap)
        eventType = eventTypeXML.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
        # Type should be "k2sitski valmistamine" = "making by hand" = 61/11175 or "valmistamine" = making" = 61/11273
        if (eventType == 'http://opendata.muis.ee/thesaurus/61/11175') or (eventType == 'http://opendata.muis.ee/thesaurus/61/11273'):
            return eventSection
        else:
            print "Not a creation event"


def findauthors(creation_event):
    authors = []
    participants = creation_event.findall('crm:P11_had_participant', physical_thing.nsmap)
    for participant in participants:
        # We take the "Actor" section
        participantXML = participant.find('crm:E39_Actor', physical_thing.nsmap)
        # We extract the type of participant
        participantTypeXML = participantXML.find('crm:P2_has_type', physical_thing.nsmap)
        participantType = participantTypeXML.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
        # We check if it's "valmistaja" = "maker" = 58/11400 or "autor" = "author" = 58/11401
        if (participantType == 'http://opendata.muis.ee/thesaurus/58/11400') or (participantType == 'http://opendata.muis.ee/thesaurus/58/11401'):
            # We find the entry for the author and take its URI
            authorXML = participantXML.find('owl:sameAs', physical_thing.nsmap)
            authorURI = authorXML.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
            authors.append(str(authorURI).rsplit('/', 1)[-1])
    authorItems = findAuthorItems(authors)
    return authorItems


def findAuthorItems(authorList):
    itemList = []
    for author in authorList:
        query = "SELECT ?item WHERE { ?item wdt:P4889 \"" + author + "\" }"
        generator = pg.WikidataSPARQLPageGenerator(query, site=site)
        for item in generator:
            itemList.append(item.getID())
    return itemList


def findinceptiondate(creation_event):
    dateString = creation_event.find('dcterms:date', physical_thing.nsmap).text
    dateList = dateString.split(' - ')
    inceptiondate = max(dateList)
    if validateDate(inceptiondate):
        return inceptiondate
    else:
        return None


def validateDate(date_string):
    try:
        datetime.datetime.strptime(date_string, '%Y')
        return True
    except ValueError:
        return False


def findExistingItems():
    existingIDs = []
    query = u'SELECT ?item ?id WHERE { ?item wdt:P195 wd:Q12376420 . ?item wdt:P4525 ?id }'
    generator = pg.WikidataSPARQLPageGenerator(query, site=site)
    for item in generator:
        itemData = item.get()
        existingIDs.append(itemData['claims'][u'P4525'][0].target)
    return existingIDs


def create_item(site, labels):
    new_item = pywikibot.ItemPage(site)
    new_item.editLabels(labels = labels, summary="Setting Estonian label from MuIS")
    return new_item.getID()


def getItemByMuisID(id):
    query = "SELECT ?item WHERE { ?item wdt:P4525 \"" + id + "\" } LIMIT 1"
    generator = pg.WikidataSPARQLPageGenerator(query, site=site)
    for item in generator:
        return item


site = pywikibot.Site("wikidata", "wikidata")
repo = site.data_repository()


# We take the IDs for all TKM paintings already in WD
existingIDs = findExistingItems()

print existingIDs

# We create a general "stated in" claim for MuIS to reuse every time
statedin = pywikibot.Claim(repo, "P248")
muis = pywikibot.ItemPage(repo, "Q50211618")
statedin.setTarget(muis)

# We take the painting collection from Tartu Art Museum and extract the IDs of all the artworks in it
collection = rdflib.Graph()
collection.parse("https://www.muis.ee/rdf/collection/442")

artworkIDs = []


for artworkURI in collection.objects(predicate=rdflib.term.URIRef(u'http://www.cidoc-crm.org/cidoc-crm/P46_is_composed_of')):
    artworkIDs.append(str(artworkURI).rsplit('/', 1)[-1])

# If we want to limit the number: for id in artworkIDs[:n]:
for id in artworkIDs:
    # We take a painting and take all the info we can find
    artworkxml = etree.fromstring(requests.get("https://www.muis.ee/rdf/object/" + id).content)
    physical_thing = artworkxml.find('crm:E18_Physical_Thing', artworkxml.nsmap)
    wdItem = None
    # If it's a painting, we want to add data!
    if ispainting(physical_thing):

        # If the painting is not in WD yet, we create an item
        if not id in existingIDs:
            # We extract the provided name for the item and add it as the Estonian label to a new item
            label = findlabel(physical_thing)
            print "Creating item with Estonian label " + label
            new_item_id = create_item(site, {"et": label})
            # We wait a bit to make sure the new item is available
            time.sleep(10)
            # We take the new item
            wdItem = pywikibot.ItemPage(repo, new_item_id)
            # We add the MuIS ID to the item
            muisID = pywikibot.Claim(repo, "P4525")
            muisID.setTarget(id)
            wdItem.addClaim(muisID, summary="Importing painting data from the Estonian Museum Portal MuIS")
            muisID.addSources([statedin],
                       summary="Importing painting data from the Estonian Museum Portal MuIS")
            print "Adding MuIS ID " + id
            # We add it to existingIDs to make sure we don't create it again somehow
            existingIDs.append(id)
        else:
            print "This painting is already in WD - not creating item"

        # The rest we want to do for everything, to add any missing data
        if wdItem is None:
            wdItem = getItemByMuisID(id)

        # We extract the claims
        wdItemData = wdItem.get()
        wdItemClaims = wdItemData.get("claims")

        # We add the claim the item is an instance of painting
        if u'P31' not in wdItemClaims:
            instanceOf = pywikibot.Claim(repo, "P31")
            paintingQ = pywikibot.ItemPage(repo, "Q3305213")
            instanceOf.setTarget(paintingQ)
            wdItem.addClaim(instanceOf, summary="Importing painting data from the Estonian Museum Portal MuIS")
            instanceOf.addSources([statedin],
                          summary="Importing painting data from the Estonian Museum Portal MuIS")
            print "Adding instance of painting"

        # We store the collection WD ID for use in collection and inventory claims
        TKMQ = pywikibot.ItemPage(repo, "Q12376420")

        # We set the collection to Tartu Art Museum
        if u'P195' not in wdItemClaims:
            collectionClaim = pywikibot.Claim(repo, "P195")
            collectionClaim.setTarget(TKMQ)
            wdItem.addClaim(collectionClaim, summary="Importing painting data from the Estonian Museum Portal MuIS")
            collectionClaim.addSources([statedin],
                              summary="Importing painting data from the Estonian Museum Portal MuIS")
            print "Adding collection Tartu Art Museum"

        # We find the inventory number and send it to WD
        if u'P217' not in wdItemClaims:
            identifier = findidentifier(physical_thing)
            inventoryNr = pywikibot.Claim(repo, "P217")
            inventoryNr.setTarget(identifier)
            wdItem.addClaim(inventoryNr, summary="Importing painting data from the Estonian Museum Portal MuIS")
            qualifier = pywikibot.Claim(repo, "P195")
            qualifier.setTarget(TKMQ)
            inventoryNr.addQualifier(qualifier,
                           summary="Importing painting data from the Estonian Museum Portal MuIS")
            inventoryNr.addSources([statedin],
                           summary="Importing painting data from the Estonian Museum Portal MuIS")
            print "Adding inventory number " + identifier
        creation_event = findcreationevent(physical_thing)

        # We send author data
        # TODO: check author by author and send any that are missing
        if u'P170' not in wdItemClaims:
            authors = findauthors(creation_event)
            for author in authors:
                authorClaim = pywikibot.Claim(repo, "P170")
                authorQ = pywikibot.ItemPage(repo, author)
                authorClaim.setTarget(authorQ)
                wdItem.addClaim(authorClaim, summary="Importing painting data from the Estonian Museum Portal MuIS")
                authorClaim.addSources([statedin],
                                           summary="Importing painting data from the Estonian Museum Portal MuIS")
                print "Adding author: " + author

        # We send the inception date
        if u'P571' not in wdItemClaims:
            inception = findinceptiondate(creation_event)
            if inception is not None:
                wikiInception = pywikibot.WbTime(year=inception)
                inceptionClaim = pywikibot.Claim(repo, "P571")
                inceptionClaim.setTarget(wikiInception)
                wdItem.addClaim(inceptionClaim, summary="Importing painting data from the Estonian Museum Portal MuIS")
                inceptionClaim.addSources([statedin],
                                   summary="Importing painting data from the Estonian Museum Portal MuIS")
                print "Adding inception date: " + inception
            else:
                print "Couldn't process the inception date"

        # We extract the info about the "physical thing"
        composedOf = physical_thing.find('crm:P46_is_composed_of', physical_thing.nsmap)
        second_physical_thing = composedOf.find('crm:E18_Physical_Thing', physical_thing.nsmap)

        # Material and technique in MuIS are both stored as "material used" (P186) in WD
        # TODO: check material by material and send any that are missing
        if u'P186' not in wdItemClaims:
            techniques = findtechnique(second_physical_thing)
            materials = findmaterial(second_physical_thing)
            wdMaterials = list(set().union(techniques, materials))
            for wdMaterial in wdMaterials:
                materialClaim = pywikibot.Claim(repo, "P186")
                wdMaterialQ = pywikibot.ItemPage(repo, wdMaterial)
                materialClaim.setTarget(wdMaterialQ)
                wdItem.addClaim(materialClaim, summary="Importing painting data from the Estonian Museum Portal MuIS")
                materialClaim.addSources([statedin],
                                           summary="Importing painting data from the Estonian Museum Portal MuIS")
                print "Adding technique / material: " + wdMaterial

        # We extract the item dimensions
        dimensions = finddimensions(second_physical_thing)

        # We submit the height. Currently, we do it only if it's a unit in cm
        if u'P2048' not in wdItemClaims and dimensions['height-unit'] == "http://www.wikidata.org/entity/Q174728":
            heightClaim = pywikibot.Claim(repo, "P2048")
            height = pywikibot.WbQuantity(amount=dimensions['height'],
                                         unit=dimensions['height-unit'],
                                         site=repo)
            heightClaim.setTarget(height)
            wdItem.addClaim(heightClaim, summary="Importing painting data from the Estonian Museum Portal MuIS")
            heightClaim.addSources([statedin],
                                     summary="Importing painting data from the Estonian Museum Portal MuIS")
            print "Adding height: " + dimensions['height'] + " cm"

        # We submit the width. Currently, we do it only if it's a unit in cm
        if u'P2049' not in wdItemClaims and dimensions['width-unit'] == "http://www.wikidata.org/entity/Q174728":
            widthClaim = pywikibot.Claim(repo, "P2049")
            width = pywikibot.WbQuantity(amount=dimensions['width'],
                                          unit=dimensions['width-unit'],
                                          site=repo)
            widthClaim.setTarget(width)
            wdItem.addClaim(widthClaim, summary="Importing painting data from the Estonian Museum Portal MuIS")
            widthClaim.addSources([statedin],
                                   summary="Importing painting data from the Estonian Museum Portal MuIS")
            print "Adding width: " + dimensions['width'] + " cm"
    else:
        print "Not a painting! ID: " + id