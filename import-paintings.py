import datetime, rdflib, requests, time
import pywikibot
from lxml import etree
from pywikibot import pagegenerators as pg


# Checks whether the entry for the artwork specifies it is a painting
def findPaintingType(physical_thing):
    typeXML_list = physical_thing.findall('crm:P2_has_type', physical_thing.nsmap)
    if typeXML_list is not None:
        for typeXML in typeXML_list:
            type = typeXML.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
            if type == 'http://opendata.muis.ee/thesaurus/203/13540':
                # painting
                return "Q3305213"
            elif type == 'http://opendata.muis.ee/thesaurus/203/28549':
                # watercolor
                return "Q18761202"
        return None
    else:
        return None


def findlabel(physical_thing):
    label = physical_thing.find('rdfs:label', physical_thing.nsmap).text
    return label


def findidentifier(physical_thing):
    identifier = physical_thing.find('dcterms:identifier', physical_thing.nsmap).text
    return identifier


def findOwner(physical_thing):
    psP52 = physical_thing.find('crm:P52_has_current_owner', physical_thing.nsmap)
    ownerResource = psP52.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
    ownerID = str(ownerResource).rsplit('/', 1)[-1]
    return findOwnerID(ownerID)


def findOwnerID(ownerID):
    query = "SELECT ?item WHERE { ?item wdt:P4889 \"" + ownerID + "\" }"
    generator = pg.WikidataSPARQLPageGenerator(query, site=site)
    for item in generator:
        return item.getID()


def findCollection(physical_thing):
    collectionQIDs = []
    psP46i = physical_thing.findall('crm:P46i_forms_part_of', physical_thing.nsmap)
    for p46i in psP46i:
        collectionResource = p46i.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
        collectionID = str(collectionResource).rsplit('/', 1)[-1]
        # We only want collections, not other groupings (such as sets)
        collectionType = str(collectionResource).rsplit('/', 1)[-2]
        if collectionType == 'http://www.muis.ee/rdf/collection':
            collectionQID = findCollectionID(collectionID)
            collectionQIDs.append(collectionQID)
    return collectionQIDs


def findCollectionID(collectionID):
    query = "SELECT ?item WHERE { ?item wdt:P5656 \"" + collectionID + "\" }"
    generator = pg.WikidataSPARQLPageGenerator(query, site=site)
    for item in generator:
        return item.getID()


def findtechnique(physical_thing):
    techniques = []
    psP2 = physical_thing.findall('crm:P2_has_type', physical_thing.nsmap)
    for p2 in psP2:
        techniqueSection = p2.find('muis:Technique', physical_thing.nsmap)
        if techniqueSection is not None:
            technique = techniqueSection.find('crm:P130_shows_features_of', physical_thing.nsmap)
            techniqueResource = technique.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
            techniqueWDItem = decodeTechnique(techniqueResource)
            if techniqueWDItem is not None:
                techniques.append(techniqueWDItem)
            else:
                print("Technique not found: " + techniqueResource)
    return techniques


def decodeTechnique(technique):
    switcher = {
        # 6li / 6liv2rvimine = oil
        'http://opendata.muis.ee/thesaurus/107/5329': "Q296955",
        'http://opendata.muis.ee/thesaurus/107/5290': "Q296955",
        'http://opendata.muis.ee/thesaurus/107/33126': "Q296955",
        # segatehnika = "mixed technique" doesn't seem to be a good match for WD "material"
        'http://opendata.muis.ee/thesaurus/107/5328': None,
        'http://opendata.muis.ee/thesaurus/107/32869': None,
        # tempera
        'http://opendata.muis.ee/thesaurus/107/5259': "Q175166",
        # guass
        'http://opendata.muis.ee/thesaurus/107/5539': "Q204330",
        'http://opendata.muis.ee/thesaurus/107/33123': "Q204330",
        # akryyl
        'http://opendata.muis.ee/thesaurus/107/5324': "Q207849",
        'http://opendata.muis.ee/thesaurus/107/33127': "Q207849",
        # akvarell
        'http://opendata.muis.ee/thesaurus/107/5325': "Q22915256",
        'http://opendata.muis.ee/thesaurus/107/33122': "Q22915256",
        # lehtkuldamine = gilding = material is gold leaf
        'http://opendata.muis.ee/thesaurus/107/5666': "Q929186",
        # kuldamine = gilding = material is gold leaf
        'http://opendata.muis.ee/thesaurus/107/5664': "Q929186",
        # maalimine = painting = not detailed enough to send anything
        'http://opendata.muis.ee/thesaurus/107/5573': None,
        # lakkmaal = lacquer painting = lacquer
        'http://opendata.muis.ee/thesaurus/107/5542': "Q11236878",
        # tushshimaal = India ink painting = India ink
        'http://opendata.muis.ee/thesaurus/107/5541': "Q12981547",
        'http://opendata.muis.ee/thesaurus/107/5278': "Q12981547",
        # emailmaal/emailimine = enamel painting = enamel
        'http://opendata.muis.ee/thesaurus/107/5538': "Q2386424",
        'http://opendata.muis.ee/thesaurus/107/5283': "Q2386424",
        # aerograafia = airbrushing, not sure what material
        'http://opendata.muis.ee/thesaurus/107/5477': None,
        # kruntimine = ???
        'http://opendata.muis.ee/thesaurus/107/5457': None,
        # transparentmaal (liimv2rvi- ehk dekoratsioonimaal) = liimv2rv (not sure of English term?)
        'http://opendata.muis.ee/thesaurus/107/5441': "Q50825569",
        # grafiit = graphite
        'http://opendata.muis.ee/thesaurus/107/5424': "Q5309",
        # kollaazh = collage = not a material as such I guess?
        'http://opendata.muis.ee/thesaurus/107/5344': None,
        # assamblaazh = similar to collage above
        'http://opendata.muis.ee/thesaurus/107/29675': None,
        'http://opendata.muis.ee/thesaurus/107/23637': None,
        # pliiats = pencil
        'http://opendata.muis.ee/thesaurus/107/5276': "Q14674",
        # 6lipastell = oil pastel
        'http://opendata.muis.ee/thesaurus/107/5257': "Q297081",
        # monotyypia = monotype = not a material?
        'http://opendata.muis.ee/thesaurus/107/5256': None,
        'http://opendata.muis.ee/thesaurus/107/33075': None,
        # viltpliiats = marker
        'http://opendata.muis.ee/thesaurus/107/30014': "Q493615",
        # pastell = pastel
        'http://opendata.muis.ee/thesaurus/107/5540': "Q189085",
        'http://opendata.muis.ee/thesaurus/107/29685': "Q189085",
        'http://opendata.muis.ee/thesaurus/107/33124': "Q189085",
        # v2rviline pliiats = colored pencil
        'http://opendata.muis.ee/thesaurus/107/26072': "Q1783255",
        # v2rvipliiatsijoonistus = colored pencil drawing = colored pencil
        'http://opendata.muis.ee/thesaurus/107/5277': "Q1783255",
        # sysi = charcoal
        'http://opendata.muis.ee/thesaurus/107/5450': "Q1424515",
        # sulekiri = ?
        'http://opendata.muis.ee/thesaurus/107/5660': None,
        # kriit = chalk
        'http://opendata.muis.ee/thesaurus/107/5449': "Q183670",
        # seepia = ?
        'http://opendata.muis.ee/thesaurus/107/5448': None,

    }
    return switcher.get(technique, None)


def findmaterial(physical_thing):
    materials = []
    psP45 = physical_thing.findall('crm:P45_consists_of', physical_thing.nsmap)
    for p45 in psP45:
        materialSection = p45.find('crm:E57_Material', physical_thing.nsmap)
        if materialSection is not None:
            material = materialSection.find('crm:P130_shows_features_of', physical_thing.nsmap)
            materialResource = material.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
            materialWDItem = decodeMaterial(materialResource)
            if materialWDItem is not None:
                materials.append(materialWDItem)
            else:
                print("Material not found: " + materialResource)
    return materials


def decodeMaterial(material):
    switcher = {
        # vineer = plywood
        'http://opendata.muis.ee/thesaurus/112/32314': "Q219803",
        'http://opendata.muis.ee/thesaurus/112/2461': "Q219803",
        # l6uend = canvas
        'http://opendata.muis.ee/thesaurus/112/2345': "Q12321255",
        'http://opendata.muis.ee/thesaurus/112/32493': "Q12321255",
        # metall = metal
        'http://opendata.muis.ee/thesaurus/112/2139': "Q11426",
        # paber = paper
        'http://opendata.muis.ee/thesaurus/112/2195': "Q11472",
        'http://opendata.muis.ee/thesaurus/112/32512': "Q11472",
        # masoniit = masonite
        'http://opendata.muis.ee/thesaurus/112/29672': "Q1808397",
        # kartong = cardboard
        'http://opendata.muis.ee/thesaurus/112/2203': "Q389782",
        'http://opendata.muis.ee/thesaurus/112/32527': "Q389782",
        # papp = cardboard
        'http://opendata.muis.ee/thesaurus/112/2362': "Q389782",
        'http://opendata.muis.ee/thesaurus/112/32528': "Q389782",
        # puitkiudplaat = fiberboard
        'http://opendata.muis.ee/thesaurus/112/2410': "Q1397443",
        # puit = wood
        'http://opendata.muis.ee/thesaurus/112/2276': "Q287",
        'http://opendata.muis.ee/thesaurus/112/32303': "Q287",
        # lateks = latex
        'http://opendata.muis.ee/thesaurus/112/2072': "Q244680",
        # 6li = oil
        'http://opendata.muis.ee/thesaurus/112/2076': "Q296955",
        'http://opendata.muis.ee/thesaurus/112/2419': "Q296955",
        # <anorgaanilise/orgaanilise aine kombinatsioonid> doesn't fit anything really
        'http://opendata.muis.ee/thesaurus/112/2086': None,
        # klaas = glass
        'http://opendata.muis.ee/thesaurus/112/2138': "Q11469",
        # tekstiil = textile
        'http://opendata.muis.ee/thesaurus/112/2209': "Q28823",
        # purjeriie has an unclear WD matching
        'http://opendata.muis.ee/thesaurus/112/2232': None,
        # p2rlmutter = nacre
        'http://opendata.muis.ee/thesaurus/112/2366': "Q215865",
        # pleksiklaas = plexiglas = Polymethyl methacrylate
        'http://opendata.muis.ee/thesaurus/112/2374': "Q146123",
        # tempera
        'http://opendata.muis.ee/thesaurus/112/2445': "Q175166",
        # lainepapp = corrugated fiberboard
        'http://opendata.muis.ee/thesaurus/112/2462': "Q7463524",
        # penoplast = vahtpolystyreen = extruded polystyrene
        'http://opendata.muis.ee/thesaurus/112/30155': "Q46998058",
        # kips = gypsum = gypsum plaster
        'http://opendata.muis.ee/thesaurus/112/32615': "Q25816410",
        'http://opendata.muis.ee/thesaurus/112/1972': "Q25816410",
        # guass
        'http://opendata.muis.ee/thesaurus/112/2422': "Q204330",
        # akryyl
        'http://opendata.muis.ee/thesaurus/112/2431': "Q207849",
        # kriit = chalk
        'http://opendata.muis.ee/thesaurus/112/1944': "Q183670",
        # akvarell
        'http://opendata.muis.ee/thesaurus/112/32725': "Q22915256",
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


def findcreationevents(physical_thing):
    creation_events = []
    eventsXML = physical_thing.findall('crm:P12_occurred_in_the_presence_of', physical_thing.nsmap)
    for event in eventsXML:
        # We take the event resource to find more info
        eventURI = event.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
        # We parse the event page
        try:
            eventRaw = requests.get(eventURI)
            if eventRaw.ok == True:
                eventXML = etree.fromstring(eventRaw.content)
                # We find the Event section in it
                eventSection = eventXML.find('crm:E5_Event', physical_thing.nsmap)
                # We find the type and extract its URI
                eventTypeXML = eventSection.find('crm:P2_has_type', physical_thing.nsmap)
                eventType = eventTypeXML.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
                # Type should be "k2sitski valmistamine" = "making by hand" = 61/11175 or "valmistamine" = making" = 61/11273 or "valmistamine/tekkimine" = 61/11145
                acceptable_types = ['http://opendata.muis.ee/thesaurus/61/11175',
                                    'http://opendata.muis.ee/thesaurus/61/11273',
                                    'http://opendata.muis.ee/thesaurus/61/11145']
                if eventType in acceptable_types:
                    creation_events.append(eventSection)
        except requests.exceptions.RequestException as e:
            print(e)
    return creation_events


def findauthors(creation_events):
    authors = []
    participants = []
    for creation_event in creation_events:
        participants = list(
            set().union(participants, creation_event.findall('crm:P11_had_participant', physical_thing.nsmap)))
    for participant in participants:
        # We take the "Actor" section
        participantXML = participant.find('crm:E39_Actor', physical_thing.nsmap)
        # We extract the type of participant
        participantTypeXML = participantXML.find('crm:P2_has_type', physical_thing.nsmap)
        participantType = participantTypeXML.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
        # We check if it's "valmistaja" = "maker" = 58/11400 or "autor" = "author" = 58/11401
        if (participantType == 'http://opendata.muis.ee/thesaurus/58/11400') or (
                participantType == 'http://opendata.muis.ee/thesaurus/58/11401'):
            # We find the entry for the author and take its URI
            authorXML = participantXML.find('owl:sameAs', physical_thing.nsmap)
            authorURI = authorXML.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
            authorID = str(authorURI).rsplit('/', 1)[-1]
            if authorID not in authors:
                authors.append(authorID)
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


def addinceptiondate(creation_events, wdItem):
    dateString = None
    for creation_event in creation_events:
        try:
            dateString = creation_event.find('dcterms:date', physical_thing.nsmap).text
        except AttributeError:
            print("No date string")
    if dateString is None:
        return None
    else:
        dateList = dateString.split(' - ')
        # If there's one and only one year in the result, just send that
        if all(x == dateList[0] for x in dateList) and validateDate(dateList[0]):
            wikiInception = pywikibot.WbTime(year=dateList[0])
            inceptionClaim = pywikibot.Claim(repo, "P571")
            inceptionClaim.setTarget(wikiInception)
            wdItem.addClaim(inceptionClaim,
                            summary="Importing painting data from the Estonian Museum Portal MuIS")
            inceptionClaim.addSources([statedin, muisidref, refdate],
                                      summary="Importing painting data from the Estonian Museum Portal MuIS")
            print("Adding inception date")
        # If there's a year range, and the decade is the same, send decade + start and end of range as qualifiers
        elif len(dateList) == 2 and dateList[0][:3] == dateList[1][:3] and dateList[0].isdigit() and dateList[1].isdigit():
            wikiInception = pywikibot.WbTime(year=dateList[0], precision="decade")
            inceptionClaim = pywikibot.Claim(repo, "P571")
            inceptionClaim.setTarget(wikiInception)
            wdItem.addClaim(inceptionClaim,
                            summary="Importing painting data from the Estonian Museum Portal MuIS")
            earliestQual = pywikibot.Claim(repo, "P1319")
            earliestQual.setTarget(pywikibot.WbTime(year=dateList[0]))
            inceptionClaim.addQualifier(earliestQual,
                                     summary="Importing painting data from the Estonian Museum Portal MuIS")
            latestQual = pywikibot.Claim(repo, "P1326")
            latestQual.setTarget(pywikibot.WbTime(year=dateList[1]))
            inceptionClaim.addQualifier(latestQual,
                                     summary="Importing painting data from the Estonian Museum Portal MuIS")

            inceptionClaim.addSources([statedin, muisidref, refdate],
                                      summary="Importing painting data from the Estonian Museum Portal MuIS")
            print("Adding inception date")
        # Otherwise, it's too complicated and risks being bullcrap, so skip and do manually
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
    print("Querying for existing items")
    query = u'SELECT ?id WHERE { ?item wdt:P31/wdt:P279* wd:Q3305213 . ?item wdt:P4525 ?id }'
    response = requests.get("https://query.wikidata.org/bigdata/namespace/wdq/sparql",
                            params={'query': query, 'format': 'json'}).json()
    results = response[u'results'][u'bindings']
    for result in results:
        existingIDs.append(str(result[u'id'][u'value']))
    return existingIDs


def create_item(site, labels):
    new_item = pywikibot.ItemPage(site)
    new_item.editLabels(labels=labels, summary="Setting Estonian label from MuIS")
    return new_item.getID()


def getItemByMuisID(id):
    query = "SELECT ?item WHERE { ?item wdt:P4525 \"" + id + "\" } LIMIT 1"
    generator = pg.WikidataSPARQLPageGenerator(query, site=site)
    for item in generator:
        return item


def extractCollectionIds(collection):
    artworkIDs = []
    for artworkURI in collection.objects(
            predicate=rdflib.term.URIRef(u'http://www.cidoc-crm.org/cidoc-crm/P46_is_composed_of')):
        artworkIDs.append(str(artworkURI).rsplit('/', 1)[-1])
    return artworkIDs


site = pywikibot.Site("wikidata", "wikidata")
repo = site.data_repository()

# We take the IDs for all paintings with MuIS IDs already in WD
existingIDs = findExistingItems()
print("Found " + str(len(existingIDs)) + " existing items")

# We create a general "stated in" claim for MuIS to reuse every time
statedin = pywikibot.Claim(repo, "P248")
muis = pywikibot.ItemPage(repo, "Q50211618")
statedin.setTarget(muis)
refdate = pywikibot.Claim(repo, "P813")
today = datetime.datetime.today()
date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
refdate.setTarget(date)

# We take the desired painting collections and extract the IDs of all the artworks in them
print("Finding all IDs in collections")
# 149 = Estonian Art Museum foreign paintings, 154 = EAM Mikkeli, 289 = EAM paintings, 402 = EAM Adamson-Eric collection
# 1110 = Kristian Raud collection
EKMcollectionIDs = ["149", "154", "289", "402", "1110"]
# 419 = Tartu Art Museum watercolors, 442 = TAM paintings
TKMcollectionIDs = ["419", "442"]
TartuLinMuscollectionIDs = ["518"]
P2rnuMuscollectionIDs =  ["305"]
V6rumaaMuscollectionIDs = ["750"]
TartuUniArtMuscollectionIDs = ["1171"]
TartuUniMuscollectionIDs = ["1187"]
NarvaMuscollectionIDs = ["508"]
J2rvamaaMuscollectionIDs = ["389"]
# 352 = Music Museum, 552 = History Museum
HistoryMuseumcollectionIDs = ["352", "552"]
# 633 = ERM art col, 1590 = Tartumaa Museum art col
NationalMuseumcollectionIDs = ["633", "1590"]
ViljandiMuseumcollectionIDs = ["666"]
MaritimeMuseumcollectionIDs = ["280"]
VirumaaMuseumscollectionIDs = ["685"]
HaapsaluMuseumscollectionIDs = ["737"]
TallinnCityMuseumcollectionIDs = ["877"]
SaaremaaMuseumcollectionIDs = ["472"]

collectionIDs = list(set().union(EKMcollectionIDs, TKMcollectionIDs, TartuLinMuscollectionIDs, P2rnuMuscollectionIDs, V6rumaaMuscollectionIDs, TartuUniArtMuscollectionIDs, TartuUniMuscollectionIDs, NarvaMuscollectionIDs, J2rvamaaMuscollectionIDs, HistoryMuseumcollectionIDs, NationalMuseumcollectionIDs, ViljandiMuseumcollectionIDs, MaritimeMuseumcollectionIDs, VirumaaMuseumscollectionIDs, HaapsaluMuseumscollectionIDs, TallinnCityMuseumcollectionIDs, SaaremaaMuseumcollectionIDs))

artworkIDs = []

for id in collectionIDs:
    collection = rdflib.Graph()
    collection.parse("https://www.muis.ee/rdf/collection/" + id)
    artworkIDs.extend(extractCollectionIds(collection))

# We want to know how far we are
numberOfIds = len(artworkIDs)
print("Found a total of " + str(numberOfIds) + " items")
currentNumber = 0

# If we want to limit the number: for id in artworkIDs[:n]:
for id in artworkIDs:
    currentNumber += 1
    # We prepare a link to the MuIS ID to use in reference sections
    muisidref = pywikibot.Claim(repo, "P4525")
    muisidref.setTarget(id)
    # We take a painting and take all the info we can find
    print("Working with id: " + id + " (" + str(currentNumber) + "/" + str(numberOfIds) + ")")
    artworkraw = requests.get("https://www.muis.ee/rdf/object/" + id)
    if artworkraw.status_code == 404:
        print("Couldn't find item")
    else:
        try:
            artworkxml = etree.fromstring(artworkraw.content)
            physical_thing = artworkxml.find('crm:E18_Physical_Thing', artworkxml.nsmap)
            wdItem = None
            paintingType = findPaintingType(physical_thing)
            # If it's a painting, we want to add data!
            if paintingType is not None:

                # If the painting is not in WD yet, we create an item
                if not id in existingIDs:
                    # We extract the provided name for the item and add it as the Estonian label to a new item
                    label = findlabel(physical_thing)
                    print("Creating item with Estonian label " + label)
                    new_item_id = create_item(site, {"et": label})
                    # We wait a bit to make sure the new item is available
                    time.sleep(10)
                    # We take the new item
                    wdItem = pywikibot.ItemPage(repo, new_item_id)
                    # We add the MuIS ID to the item
                    muisID = pywikibot.Claim(repo, "P4525")
                    muisID.setTarget(id)
                    wdItem.addClaim(muisID, summary="Importing painting data from the Estonian Museum Portal MuIS")
                    muisID.addSources([statedin, muisidref, refdate],
                                      summary="Importing painting data from the Estonian Museum Portal MuIS")
                    print("Adding MuIS ID " + id)
                    # We add it to existingIDs to make sure we don't create it again somehow
                    existingIDs.append(id)
                else:
                    print("This painting is already in WD - not creating item")

                # The rest we want to do for everything, to add any missing data
                if wdItem is None:
                    wdItem = getItemByMuisID(id)

                # We extract the claims
                wdItemData = wdItem.get()
                wdItemClaims = wdItemData.get("claims")

                # We add the claim the item is an instance of painting
                if u'P31' not in wdItemClaims:
                    instanceOf = pywikibot.Claim(repo, "P31")
                    paintingQ = pywikibot.ItemPage(repo, paintingType)
                    instanceOf.setTarget(paintingQ)
                    wdItem.addClaim(instanceOf, summary="Importing painting data from the Estonian Museum Portal MuIS")
                    instanceOf.addSources([statedin, muisidref, refdate],
                                          summary="Importing painting data from the Estonian Museum Portal MuIS")
                    print("Adding instance of painting")

                # We set the collection, owner and catno based on the owner data
                owner = findOwner(physical_thing)
                ownerQ = pywikibot.ItemPage(repo, owner)
                collections = findCollection(physical_thing)
                # In almost all (all?) cases, there's just one actual collection. If not, skip for now
                if len(collections) == 1:
                    collection = collections[0]
                    collectionQ = pywikibot.ItemPage(repo, collection)
                else:
                    collection = None

                if u'P195' not in wdItemClaims:
                    if collection is not None:
                        collectionClaim = pywikibot.Claim(repo, "P195")
                        collectionClaim.setTarget(collectionQ)
                        wdItem.addClaim(collectionClaim, summary="Importing painting data from the Estonian Museum Portal MuIS")
                        collectionClaim.addSources([statedin, muisidref, refdate],
                                               summary="Importing painting data from the Estonian Museum Portal MuIS")
                        print("Adding collection: " + collection)

                # We set the owner when appropriate
                if u'P127' not in wdItemClaims:
                    if owner is not None:
                        ownerClaim = pywikibot.Claim(repo, "P127")
                        ownerClaim.setTarget(ownerQ)
                        wdItem.addClaim(ownerClaim, summary="Importing painting data from the Estonian Museum Portal MuIS")
                        ownerClaim.addSources([statedin, muisidref, refdate],
                                              summary="Importing painting data from the Estonian Museum Portal MuIS")
                        print("Adding owner: " + owner)

                # We find the inventory number and send it to WD
                if u'P217' not in wdItemClaims:
                    identifier = findidentifier(physical_thing)
                    inventoryNr = pywikibot.Claim(repo, "P217")
                    inventoryNr.setTarget(identifier)
                    if collection is not None:
                        wdItem.addClaim(inventoryNr, summary="Importing painting data from the Estonian Museum Portal MuIS")
                        qualifier = pywikibot.Claim(repo, "P195")
                        qualifier.setTarget(collectionQ)
                        inventoryNr.addQualifier(qualifier,
                                             summary="Importing painting data from the Estonian Museum Portal MuIS")
                        inventoryNr.addSources([statedin, muisidref, refdate],
                                           summary="Importing painting data from the Estonian Museum Portal MuIS")
                        print("Adding inventory number " + identifier)
                creation_events = findcreationevents(physical_thing)

                # We send author data
                # We check the authors against the existing authors, and add any that are missing
                existingAuthors = []
                if u'P170' in wdItemClaims:
                    for claim in wdItemClaims[u'P170']:
                        existingAuthors.append(claim.target.getID())
                authors = findauthors(creation_events)
                for author in authors:
                    if author not in existingAuthors:
                        authorClaim = pywikibot.Claim(repo, "P170")
                        authorQ = pywikibot.ItemPage(repo, author)
                        authorClaim.setTarget(authorQ)
                        wdItem.addClaim(authorClaim, summary="Importing painting data from the Estonian Museum Portal MuIS")
                        authorClaim.addSources([statedin, muisidref, refdate],
                                               summary="Importing painting data from the Estonian Museum Portal MuIS")
                        print("Adding author: " + author)

                # We send the inception date
                if u'P571' not in wdItemClaims:
                    addinceptiondate(creation_events, wdItem)

                # We extract the info about the "physical thing"
                composedOf = physical_thing.find('crm:P46_is_composed_of', physical_thing.nsmap)
                if composedOf is not None:
                    second_physical_thing = composedOf.find('crm:E18_Physical_Thing', physical_thing.nsmap)

                    if second_physical_thing is not None:
                        # Material and technique in MuIS are both stored as "material used" (P186) in WD
                        # We check the materials against the existing materials, and add any that are missing
                        existingMaterials = []
                        if u'P186' in wdItemClaims:
                            for claim in wdItemClaims[u'P186']:
                                existingMaterials.append(claim.target.getID())
                        techniques = findtechnique(second_physical_thing)
                        materials = findmaterial(second_physical_thing)
                        wdMaterials = list(set().union(techniques, materials))
                        for wdMaterial in wdMaterials:
                            if wdMaterial not in existingMaterials:
                                materialClaim = pywikibot.Claim(repo, "P186")
                                wdMaterialQ = pywikibot.ItemPage(repo, wdMaterial)
                                materialClaim.setTarget(wdMaterialQ)
                                wdItem.addClaim(materialClaim,
                                                summary="Importing painting data from the Estonian Museum Portal MuIS")
                                materialClaim.addSources([statedin, muisidref, refdate],
                                                         summary="Importing painting data from the Estonian Museum Portal MuIS")
                                print("Adding technique / material: " + wdMaterial)

                        # We extract the item dimensions
                        dimensions = finddimensions(second_physical_thing)
                        if dimensions is not None:
                            # We submit the height. Currently, we do it only if it's a unit in cm
                            if u'P2048' not in wdItemClaims and dimensions[
                                'height-unit'] == "http://www.wikidata.org/entity/Q174728":
                                heightClaim = pywikibot.Claim(repo, "P2048")
                                height = pywikibot.WbQuantity(amount=dimensions['height'],
                                                              unit=dimensions['height-unit'],
                                                              site=repo)
                                heightClaim.setTarget(height)
                                wdItem.addClaim(heightClaim,
                                                summary="Importing painting data from the Estonian Museum Portal MuIS")
                                heightClaim.addSources([statedin, muisidref, refdate],
                                                       summary="Importing painting data from the Estonian Museum Portal MuIS")
                                print("Adding height: " + dimensions['height'] + " cm")

                            # We submit the width. Currently, we do it only if it's a unit in cm
                            if u'P2049' not in wdItemClaims and dimensions[
                                'width-unit'] == "http://www.wikidata.org/entity/Q174728":
                                widthClaim = pywikibot.Claim(repo, "P2049")
                                width = pywikibot.WbQuantity(amount=dimensions['width'],
                                                             unit=dimensions['width-unit'],
                                                             site=repo)
                                widthClaim.setTarget(width)
                                wdItem.addClaim(widthClaim,
                                                summary="Importing painting data from the Estonian Museum Portal MuIS")
                                widthClaim.addSources([statedin, muisidref, refdate],
                                                      summary="Importing painting data from the Estonian Museum Portal MuIS")
                                print("Adding width: " + dimensions['width'] + " cm")
                        else:
                            print("No dimensions found")
            else:
                print("Not a painting! ID: " + id)

        except etree.XMLSyntaxError:
            print("XML reading failed")
