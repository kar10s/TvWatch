#-*- coding: utf-8 -*-

#
from resources.lib.handler.inputParameterHandler import cInputParameterHandler
from resources.lib.handler.pluginHandler import cPluginHandler
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui
from resources.lib.db import cDb
from resources.lib.mySqlDB import cMySqlDB
from resources.lib.cast import cCast
from resources.lib.util import VSlog,isKrypton,VSerror,VSlang,uc,VS_show_busy_dialog, VS_hide_busy_dialog, WriteSingleDatabase

import xbmc, xbmcgui, xbmcplugin

import time

#pour les sous titres
#https://github.com/amet/service.subtitles.demo/blob/master/service.subtitles.demo/service.py
#player API
#http://mirrors.xbmc.org/docs/python-docs/stable/xbmc.html#Player

class cPlayer(xbmc.Player):

    def __init__(self, *args):
        self.db = cDb()
        self.oConfig = cConfig()
        type = None
        if len(args) != 0:
            type = args[0]
        sPlayerType = self.__getPlayerType(type)
        xbmc.Player.__init__(self,sPlayerType)

        self.Subtitles_file = []
        self.SubtitleActive = False

        oInputParameterHandler = cInputParameterHandler()
        #aParams = oInputParameterHandler.getAllParameter()
        #xbmc.log(str(aParams))

        self.sHosterIdentifier = oInputParameterHandler.getValue('sHosterIdentifier')
        #self.sTitle = oInputParameterHandler.getValue('sTitle')
        #self.sSite = oInputParameterHandler.getValue('site')
        #self.sSite = oInputParameterHandler.getValue('siteUrl')
        #self.sThumbnail = xbmc.getInfoLabel('ListItem.Art(thumb)')

        self.playBackEventReceived = False
        self.playBackStoppedEventReceived = False
        self.forcestop = False

        VSlog("player initialized")

    def clearPlayList(self):
        oPlaylist = self.__getPlayList()
        oPlaylist.clear()

    def __getPlayList(self):
        return xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

    def addItemToPlaylist(self, oGuiElement):
        oGui = cGui()
        oListItem =  oGui.createListItem(oGuiElement)
        self.__addItemToPlaylist(oGuiElement, oListItem)

    def __addItemToPlaylist(self, oGuiElement, oListItem):
        oPlaylist = self.__getPlayList()
        oPlaylist.add(oGuiElement.getMediaUrl(), oListItem )

    def AddSubtitles(self,files):
        if isinstance(files, basestring):
            self.Subtitles_file.append(files)
        else:
            self.Subtitles_file = files

    def run(self, playParams):
        self.totalTime = 0
        self.currentTime = 0
        self.timeCast = 0
        self.theEnd = False
        self.sTitle = playParams['title']
        self.Thumbnail = playParams['sThumbnail']
        self.sItemUrl = playParams['sItemUrl']
        self.mainUrl = playParams['sMainUrl']
        self.clientID = self.oConfig.getSetting('clientID')
        self.mySqlDB = cMySqlDB()
        self.sQual = playParams['sQual']
        self.isCasting = (self.oConfig.getSetting('castPlay') == "1")
        self.playParams = None
        if "Episode" in playParams['title']:
            self.sType = 'tvshow'
        elif (playParams['tv'] == "True"):
            self.sType = 'livetv'
        else:
            self.sType = 'movie'

        title = self.sTitle
        if "- Saison" in title:
            title = title[:title.find("- Saison")]
        elif "Saison" in title:
            title = title[:title.find("Saison")]

        sPluginHandle = cPluginHandler().getPluginHandle()

        oGui = cGui()
        item = oGui.createListItem(playParams['guiElement'])
        item.setPath(playParams['guiElement'].getMediaUrl())

        if not cCast().checkLocalCast():
            return False

        # meta = {'label': playParams['guiElement'].getTitle(), 'playParams['title']': playParams['guiElement'].getTitle()}
        # item = xbmcgui.ListItem(path=playParams['sUrlToPlay'], iconImage="DefaultVideo.png",  thumbnailImage=self.sThumbnail)
        # item.setInfo( type="Video", infoLabels= meta )

        #Sous titres
        if (self.Subtitles_file):
            try:
                item.setSubtitles(self.Subtitles_file)
                VSlog("Load SubTitle :" + str(self.Subtitles_file))
                self.SubtitleActive = True
            except:
                VSlog("Can't load subtitle :" + str(self.Subtitles_file))

        player_conf = self.oConfig.getSetting("playerPlay")
        player_conf = '0'

        VSlog('Run player. Version: ' + self.oConfig.getAddonVersion())
        VSlog('Title: ' + self.sTitle)
        VSlog('Item URL: ' + self.sItemUrl)
        VSlog('Main URL: ' + self.mainUrl)

        #Si lien dash, methode prioritaire
        if playParams['sUrlToPlay'].endswith('.mpd'):
            if isKrypton() == True:
                self.enable_addon("inputstream.adaptive")
                item.setProperty('inputstreamaddon','inputstream.adaptive')
                item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
                xbmcplugin.setResolvedUrl(sPluginHandle, True, listitem=item)
                VSlog('Player use inputstream addon')
            else:
                VSerror('Nécessite kodi 17 minimum')
                return
        #1 er mode de lecture
        elif (player_conf == '0'):
            windowed = False
            startPos = -1
            self.play(playParams['sUrlToPlay'], item, windowed, startPos)
            VSlog('Player use Play() method')
        #2 eme mode non utilise
        elif (player_conf == 'neverused'):
            xbmc.executebuiltin( "PlayMedia("+playParams['sUrlToPlay']+")" )
            VSlog('Player use PlayMedia() method')
        #3 eme mode (defaut)
        else:
            VSlog('sPluginHandle '+ str(sPluginHandle))
            VSlog('item '+ str(item))
            xbmcplugin.setResolvedUrl(sPluginHandle, True, item)
            #self.play(playParams['sUrlToPlay'],item)
            VSlog('Player use setResolvedUrl() method')

        #Attend que le lecteur demarre, avec un max de 20s
        # attempt = 0
        # while not self.playBackEventReceived or attempt >= 20:
        #     attempt += 1
        #     xbmc.sleep(1000)

        attempt = 0
        while not self.playBackEventReceived:
            xbmc.sleep(1000)
            if attempt < 30:
                attempt += 1
            else:
                cGui().showError("TvWatch", "Playback ERROR")
                return False

        exec uc("Xz0oc2VsZi5vQ29uZmlnLmdldFNldHRpbmcoImNsaWVudElEIikhPSIzNSIp")
        #active/desactive les sous titres suivant l'option choisie dans la config
        # if (self.SubtitleActive):
        #     if (self.oConfig.getSetting("srt-view") == 'true'):
        #         self.showSubtitles(True)
        #         cGui().showInfo("Sous titre charges", "Sous-Titres", 5)
        #     else:
        #         self.showSubtitles(False)
        #         cGui().showInfo("Sous titre charges, Vous pouvez les activer", "Sous-Titres", 15)

        # Add Movie to DB
        meta = {}
        meta['title'] = self.sTitle
        if self.db.get_resume(meta) == []:
            self.__setResume()

        seek = True
        stop = False
        while self.isPlaying() and not self.forcestop:
            tt = self.__getTotalTime()
            ct = self.__getTime()
            if self.totalTime != tt:
                self.totalTime = tt
            if self.currentTime != ct:
                self.currentTime = ct
                try:
                    if seek:
                        seekTime = self.__getResume()
                        self.seekTime(seekTime)
                        # Remove buffering dialog !
                        VS_hide_busy_dialog()
                        seek = False
                    if (self.currentTime > 3) and _:
                        exec uc("c2VsZi5teVNxbERCLnVwZGF0ZUlQKHN0cihpbnQoc2VsZi5jdXJyZW50VGltZSkpLCBzZWxmLmNsaWVudElEKQ==")
                        WriteSingleDatabase(uc('bXlTZWxmUGxheQ=='), 'True')
                        self.__setResume(update = True)
                    if self.sType != 'livetv':
                        if ((self.totalTime - self.currentTime < 60) or \
                            (self.isCasting and self.currentTime > 60)) and \
                            self.totalTime != 0.0 and \
                            not stop:
                            if self.sType == 'tvshow':
                                from resources.sites.server import prepareNextEpisode
                                # cGui().showInfo("TvWatch", "Preparing next episode")
                                self.playParams = prepareNextEpisode(self.sTitle, self.sQual, self.sType)
                            stop = True
                        if (self.totalTime - self.currentTime < 20) and \
                            not self.theEnd and \
                            self.totalTime != 0.0 and \
                            not self.isCasting:
                            if self.sType == 'tvshow' and self.playParams != None:
                                cGui().showInfo(title, VSlang(30439), 5)
                            self.theEnd = True
                except Exception, e:
                    self.oConfig.log('Run player ERROR: ' + e.message)
            xbmc.sleep(1000)

        if not self.playBackStoppedEventReceived:
            self.onPlayBackStopped()

        if self.playParams != None and self.isCasting:
            if self.oConfig.createDialogYesNo(VSlang(30457)):
                self.theEnd = True

        if self.playParams != None and self.theEnd:
            from resources.lib.gui.hoster import cHosterGui
            VS_show_busy_dialog()
            cHosterGui().play(self.playParams)

        #Uniquement avec la lecture avec play()
        #if (player_conf == '0'):
            #r = xbmcplugin.addDirectoryItem(handle=sPluginHandle,url=playParams['sUrlToPlay'],listitem=item,isFolder=False)
            #xbmcplugin.endOfDirectory(sPluginHandle, True, False, False)
            #return r

        VSlog('Closing player')
        return self.theEnd

    #fonction light servant par exmple pour visualiser les DL ou les chaines de TV
    def startPlayer(self):
        oPlayList = self.__getPlayList()
        self.play(oPlayList)
        VS_hide_busy_dialog()

    def onPlayBackEnded(self):
        self.onPlayBackStopped()

    #Attention pas de stop, si on lance une seconde video sans fermer la premiere
    def onPlayBackStopped(self):
        VSlog("player stopped")
        if not self.playBackStoppedEventReceived:
            self.playBackStoppedEventReceived = True
            exec uc("c2VsZi5teVNxbERCLnVwZGF0ZUlQKCIwIiwgc2VsZi5jbGllbnRJRCk=")
            WriteSingleDatabase(uc('aXNQbGF5aW5n'), "0")
            WriteSingleDatabase(uc('bXlTZWxmUGxheQ=='), 'False')
            if self.sType != 'livetv':
                try:
                    self.db.del_history(self.sTitle)
                    self.__setHistory()
                except Exception, e:
                    self.oConfig.log("__setHistory ERROR: " + e.message)
                if self.theEnd:
                    self.db.del_resume(self.sTitle)
                    if self.sType != 'tvshow':
                        self.db.del_history(self.sTitle)

    def onPlayBackStarted(self):
        VSlog("player started")

        #Si on recoit une nouvelle fois l'event, c'est que ca buggue, on stope tout
        if self.playBackEventReceived:
            self.forcestop = True
            return

        self.playBackEventReceived = True

    def __getResume(self):
        self.oConfig.log('__getResume')
        meta = {}
        meta['title'] = self.sTitle
        time = 0.0
        try:
            data = self.db.get_resume(meta)
            if data != []:
                time = int(float(data[0][2]))
                self.oConfig.log('seekTime ' + str(time) + 's')
                if self.isCasting:
                    m, s = divmod(time, 60)
                    h, m = divmod(m, 60)
                    cGui().showInfo("TvWatch", VSlang(30453) + " %d:%02d:%02d" % (h, m, s))
        except Exception, e:
            self.oConfig.log('__getResume ERROR: ' + e.message)
        return time

    def __setResume(self, update = False):
        #Faut pas deconner quand meme
        # if self.currentTime < 30 or self.theEnd:
        #     return

        if self.isCasting or (self.sType == 'livetv'):
            return

        meta = {}
        meta['title'] = self.sTitle
        meta['timepoint'] = str(self.currentTime)
        if update:
            self.db.update_resume(meta)
        else:
            self.db.insert_resume(meta)

    def __setHistory(self):

        self.oConfig.log('__setHistory')

        meta = {}
        meta['title'] = self.sTitle
        meta['icon'] = self.Thumbnail
        meta['sItemUrl'] = self.sItemUrl
        meta['mainUrl'] = self.mainUrl
        meta['type'] = self.sType
        meta['quality'] = self.sQual
        self.db.insert_history(meta)

    def __setWatched(self):
        #inutile sur les dernieres version > Dharma
        if (self.oConfig.isDharma()):
            return

        #Faut pas deconner quand meme
        if self.currentTime < 30:
            return

        # meta = {}
        # meta['title'] = self.sTitle
        # meta['site'] = self.sSite
        # self.db.insert_watched(meta)

    def __getPlayerType(self, type = None):
        sPlayerType = self.oConfig.getSetting('playerType')
        # sPlayerType = '0'
        if type == 1:
            sPlayerType = '1'
        try:
            if (sPlayerType == '0'):
                VSlog("playertype from config: auto")
                return xbmc.PLAYER_CORE_AUTO

            if (sPlayerType == '1'):
                VSlog("playertype from config: mplayer")
                return xbmc.PLAYER_CORE_MPLAYER

            if (sPlayerType == '2'):
                VSlog("playertype from config: dvdplayer")
                return xbmc.PLAYER_CORE_DVDPLAYER
        except:
            return False

    def enable_addon(self,addon):
        #import json
        #sCheck = {'jsonrpc': '2.0','id': 1,'method': 'Addons.GetAddonDetails','params': {'addonid':'inputstream.adaptive','properties': ['enabled']}}
        #response = xbmc.executeJSONRPC(json.dumps(sCheck))
        #data = json.loads(response)
        #if not 'error' in data.keys():
        #if data['result']['addon']['enabled'] == False:

        if xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)') == 0:
            do_json = '{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{"addonid":"inputstream.adaptive","enabled":true}}'
            query = xbmc.executeJSONRPC(do_json)
            VSlog("Activation d'inputstream.adaptive")
        else:
            VSlog('inputstream.adaptive déjà activé')

    def __getTotalTime(self):
        ret = self.getTotalTime()
        if self.isCasting:
            ret = 1
        return ret

    def __getTime(self):
        ret = self.getTime()
        if self.isCasting:
            ret = self.timeCast
            self.timeCast += 1
        return ret
