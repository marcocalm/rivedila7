import sys
import datetime
import urllib
import urllib2
import urlparse
import HTMLParser
import htmlentitydefs

try:
    from xml.etree import ElementTree as ET
except:
    from elementtree import ElementTree as ET

import xbmcgui
import xbmcplugin
import xbmcaddon


# plugin constants
__plugin__ = 'plugin.video.rivediLa7'
__author__ = 'ranamauro'

Addon = xbmcaddon.Addon(id = __plugin__)

# plugin handle
handle = int(sys.argv[1])


# utility functions
def encode_dictionary(d):
    d2 = {}
    for k, v in d.items():
        d2[k.encode('utf-8')] = v.encode('utf-8')
    return d2

def parameters_string_to_dict(parameters):
    ''' Convert parameters encoded in a URL to a dict. '''
    paramDict = dict(urlparse.parse_qsl(parameters[1:]))
    return paramDict

def addDirectoryItem(parameters, title, thumbnailImage = None, iconImage = None):
    listItem = xbmcgui.ListItem(title, iconImage = iconImage, thumbnailImage = thumbnailImage)

    # see http://wiki.xbmc.org/?title=InfoLabels
    infoLabels = {
        'title': None,
        'tvshowtitle': None,
        'duration': None,
        'date': None,
        'airdate': None,
    }

    listItem.setInfo(type = 'Video', infoLabels = infoLabels)
    addDirectoryListItem(parameters, listItem)

def addDirectoryListItem(parameters, listItem):
    parameters = encode_dictionary(parameters);
    link = sys.argv[0] + '?' + urllib.urlencode(parameters)
    return xbmcplugin.addDirectoryItem(handle = handle, url = link, listitem = listItem, isFolder = True)

def notify(message, timeShown = 5000):
    '''Displays a notification to the user

    Parameters:
    message: the message to be shown
    timeShown: the length of time for which the notification will be shown, in milliseconds, 5 seconds by default
    '''
    xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (Addon.getAddonInfo('name'), message, timeShown, Addon.getAddonInfo('icon')))


def showError(errorMessage):
    '''
    Shows an error to the user and logs it

    Parameters:
    addonId: the current addon id
    message: the message to be shown
    '''
    notify(errorMessage)
    xbmc.log(errorMessage, xbmc.LOGERROR)

# classes

class VerboseHTMLParser(HTMLParser.HTMLParser):
    def process(self, response_body):
        self.feed(response_body)
        return []

    def handle_starttag(self, tag, attributes):
        print('Start tag:', tag)
        for attr in attributes:
            print('     attr:', attr)
    def handle_endtag(self, tag):
        print('End tag  :', tag)
    def handle_data(self, data):
        print('Data     :', data)
    def handle_comment(self, data):
        print('Comment  :', data)
    def handle_entityref(self, name):
        c = chr(htmlentitydefs.name2codepoint[name])
        print('Named ent:', c)
    def handle_charref(self, name):
        if name.startswith('x'):
            c = chr(int(name[1:], 16))
        else:
            c = chr(int(name))
        print('Num ent  :', c)
    def handle_decl(self, data):
        print('Decl     :', data)

class VideoLinkHTMLParser(HTMLParser.HTMLParser):
    list = []
    link = ''

    def process(self, response_body):
        self.list = []
        self.link = ''
        self.feed(response_body)
        self.list.sort()
        return self.list

    def handle_data(self, data):
        begin = data.find('src_mp4 : ')
        if begin >= 0:
            begin = begin + 11
            end = data.find('.mp4', begin) + 4
            link = data[begin:end]
            if link.find('http://', 1) > 0:
                x = link.find('/content/')
                y = link.find('/content/', x + 1)
                link = link[0:x] + link[y:]
            item = {
                'mode': '1',
                'link':  link
            }
            self.list.append(item)


# UI builder functions

def list_for_link(url):
    print('list_for_link', url)

    list = []

    # pretend we're Chrome to make the HTTP server happy
    request = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'})
    response = urllib2.urlopen(request)
    response_body = response.read()
    response.close()

    # scope to the part that is likely to be XML
    begin = response_body.find('<ul class="guida_tv clearfix">', 0)
    if (begin >= 0):
        end = response_body.find('</ul>', begin) + 5
        response_body = response_body[begin:end]

    response_body = response_body.replace('& ', '&amp; ')
    response_body = response_body.replace('&nbsp;', ' ')
    try:
        tree = ET.fromstring(response_body)
    except Exception as e:
        print('=========================== begin ===========================')
        print(response_body)
        print('=========================== error ===========================')
        print(e)
        print('=========================== end =============================')
        tree = ET.fromstring('')

    for divNode in tree.iter('div'):
        if 'id' not in divNode.attrib:
            continue

        if divNode.attrib['id'].find('item_') == 0:
            if divNode.attrib['class'].find('non_disponibile') >= 0:
                continue

            # TODO: fish metadata out of this node
            for imgNode in divNode.iter('img'):
                #print(333, imgNode, imgNode.attrib, imgNode.text)
                continue;

            index = 0
            for aNodes in divNode.iter('a'):
                #print(444, aNodes, index, aNodes.attrib, aNodes.text)

                if index == 0:
                    link = aNodes.attrib['href']
                    index = index + 1
                    continue

                if index == 1:
                    title = aNodes.text.strip()
                    name = title
                    break

            for divNode2 in divNode.iter('div'):
                #print(555, divNode2, divNode2.attrib, divNode2.text)

                if divNode2.text is None:
                    continue

                if divNode2.attrib['class'].find('titolo-replica') >= 0:
                    name = divNode2.text.strip()

                if divNode2.attrib['class'].find('orario') >= 0:
                    time = divNode2.text.strip()


            item = {
                'title': title + ' (' + str(day) + ' : ' + time + ')',
                'name':  name,
                'link':  link,
                'mode': 'play',
            }

            list.append(item)

    return list

def get_by_url(url, day):
    print('get_by_url')

    list = []

    print(url)

    # pretend we're Chrome to make the HTTP server happy
    request = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'})
    response = urllib2.urlopen(request)
    response_body = response.read()
    response.close()

    # scope to the part that is likely to be XML
    begin = response_body.find('<ul class="guida_tv clearfix">', 0)
    if (begin >= 0):
        end = response_body.find('</ul>', begin) + 5
        response_body = response_body[begin:end]

    response_body = response_body.replace('& ', '&amp; ')
    response_body = response_body.replace('&nbsp;', ' ')
    try:
        tree = ET.fromstring(response_body)
    except Exception as e:
        print('=========================== begin ===========================')
        print(response_body)
        print('=========================== error ===========================')
        print(e)
        print('=========================== end =============================')
        tree = ET.fromstring('')

    for divNode in tree.iter('div'):
        if 'id' not in divNode.attrib:
            continue

        if divNode.attrib['id'].find('item_') == 0:
            if divNode.attrib['class'].find('non_disponibile') >= 0:
                continue

            # TODO: fish metadata out of this node
            for imgNode in divNode.iter('img'):
                #print(333, imgNode, imgNode.attrib, imgNode.text)
                continue;

            index = 0
            for aNodes in divNode.iter('a'):
                #print(444, aNodes, index, aNodes.attrib, aNodes.text)

                if index == 0:
                    link = aNodes.attrib['href']
                    index = index + 1
                    continue

                if index == 1:
                    title = aNodes.text.strip()
                    name = title
                    break

            for divNode2 in divNode.iter('div'):
                #print(555, divNode2, divNode2.attrib, divNode2.text)

                if divNode2.text is None:
                    continue

                if divNode2.attrib['class'].find('titolo-replica') >= 0:
                    name = divNode2.text.strip()

                if divNode2.attrib['class'].find('orario') >= 0:
                    time = divNode2.text.strip()

            item = {
                'title': title + ' (' + str(day) + ' : ' + time + ')',
                'name':  name,
                'link':  link,
                'mode': 'play',
            }

            list.append(item)

    return list

def get_by_days_and_channels(days, channels):
    print('get_by_days_and_channels')

    list = []

    for day in days:
        for channel in channels:
            url = 'http://www.la7.it/rivedila7/' + str(day) + '/' + channel

            list2 = get_by_url(url, day)
            list.extend(list2)

    return list

def show_week_episodes(days = range(0, 7), channels = ['LA7', 'LA7D']):
    print('show_week_episodes')

    xbmcplugin.setContent(handle, 'episodes')

    list = get_by_days_and_channels(days, channels)

    list.sort(key = lambda a: a['title'])

    for item in list:
        #print(item)
        addDirectoryItem(item, item['title'].upper())

    #TODO: improve ability to customize sorting
    #xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_DATE)

    xbmcplugin.endOfDirectory(handle = handle, succeeded = True)

def show(url):
    print('show')

    xbmcplugin.setContent(handle, 'episodes')

    link = 'http://www.la7.it' + url +  '/rivedila7/archivio'
    list = get_by_url(link, 0)

    if list.count() == 0:
        link = 'http://www.la7.it' + url +  '/rivedila7'
        list = get_by_url(link, 0)

    if list.count() == 0:
        link = 'http://www.la7.it' + url
        list = get_by_url(link, 0)

    list.sort(key = lambda a: a['title'])

    for item in list:
        #print(item)
        addDirectoryItem(item, item['title'].upper())

    #TODO: improve ability to customize sorting
    #xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_DATE)

    xbmcplugin.endOfDirectory(handle = handle, succeeded = True)

class ProgramNamesParserHTMLParser(HTMLParser.HTMLParser):
    class State:
        lookForTP = 0
        lookForDiv = 1
        lookForA = 2
        lookForData = 3

    state = State.lookForTP
    list = []
    link = ''

    def process(self, response_body):
        self.list = []
        self.link = ''
        self.feed(response_body)
        self.list.sort(key = lambda a: a['name'])
        return self.list

    def handle_data(self, data):
        #TODO: if the text contains a ' this gets two callbacks, which is broken (EG: "l'ispettore Barnaby' only shows up as "L")
        if self.state == ProgramNamesParserHTMLParser.State.lookForData:
            item = {
                'title': data.upper(),
                'mode': '1',
                'name': data,
                'link': self.link
            }
            self.list.append(item)
            self.state = ProgramNamesParserHTMLParser.State.lookForDiv

    def handle_starttag(self, tag, attributes):
        if self.state == ProgramNamesParserHTMLParser.State.lookForTP:
            if tag == 'div' and len(attributes) == 1 and attributes[0][0] == 'class' and attributes[0][1] == 'itemTuttiProgrammi clearfix':
                self.state = ProgramNamesParserHTMLParser.State.lookForDiv
        elif self.state == ProgramNamesParserHTMLParser.State.lookForDiv:
            if tag == 'div' and len(attributes) == 1 and attributes[0][0] == 'class' and attributes[0][1] == 'views-field views-field-title':
                self.state = ProgramNamesParserHTMLParser.State.lookForA
        elif self.state == ProgramNamesParserHTMLParser.State.lookForA:
            if tag == 'a' and len(attributes) == 1 and attributes[0][0] == 'href':
                self.link = attributes[0][1]
                self.state = ProgramNamesParserHTMLParser.State.lookForData
        elif self.state == ProgramNamesParserHTMLParser.State.lookForData:
            self.state = ProgramNamesParserHTMLParser.State.lookForDiv

def show_shows():
    print('show_shows')

    xbmcplugin.setContent(handle, 'tvshows')

    url = 'http://www.la7.it/tutti-i-programmi'
    print(url)

    # pretend we're Chrome to make the HTTP server happy
    request = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'})
    response = urllib2.urlopen(request)
    response_body = response.read()
    response.close()

    parser = ProgramNamesParserHTMLParser()
    list = parser.process(response_body)

    for item in list:
        #print(item)
        try:
            addDirectoryItem(item, item['title'].upper())
        except:
            # ignore
            continue

    xbmcplugin.endOfDirectory(handle = handle, succeeded = True)

def play_video(name, link):
    print('play_video')

    url = link
    if link.find('http://') != 0:
        url = 'http://www.la7.it' + link
    print(link, url)

    # pretend we're Chrome to make the HTTP server happy
    request = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'})
    response = urllib2.urlopen(request)
    response_body = response.read()
    response.close()

    parser = VideoLinkHTMLParser()
    list = parser.process(response_body)

    item = list[0]

    listItem = xbmcgui.ListItem(name)
    listItem.setInfo('video', {'Title': name})
    xbmc.Player().play(item['link'], listItem)

def show_root_menu():
    print('show_root_menu')

    addDirectoryItem({'mode': '1'}, 'Tutti i Programmi (NOT WORKING YET)')
    addDirectoryItem({'mode': '2'}, 'La Settimana (Tutti i Giorni)')

    for day in range(0, 7):
        # fuso orario
        actualDate = datetime.datetime.now() + datetime.timedelta(hours = 9) - datetime.timedelta(days = day)
        addDirectoryItem({'mode': '3', 'name': str(day)}, 'La Settimana Giorno: ' + actualDate.strftime('%d/%m/%Y'))

    xbmcplugin.endOfDirectory(handle = handle, succeeded = True)

# parameter values
print('ENTERING PLUGIN', sys.argv)
params = parameters_string_to_dict(sys.argv[2])

mode = str(params.get('mode', ''))
name = str(params.get('name', ''))
link = str(params.get('link', ''))

print('ENTERING PLUGIN', 'mode', mode, 'name', name, 'link', link)

if mode == '1':
    if name == '':
        show_shows()
    else:
        show(link)
elif mode == '2':
    show_week_episodes()
elif mode == '3':
    show_week_episodes(days = [name])
elif mode == 'play':
    play_video(name, link)
else:
    show_root_menu()
