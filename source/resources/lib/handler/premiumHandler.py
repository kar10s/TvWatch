#-*- coding: utf-8 -*-
#Primatech.
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui
from resources.lib.parser import cParser
from resources.lib.config import GestionCookie
from resources.lib.util import VSlog,VSlang,uc

import urllib2,urllib
import xbmc
import xbmcaddon
import re,os

UA = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; de-DE; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
headers = { 'User-Agent' : UA }

class cPremiumHandler:

    def __init__(self, sHosterIdentifier):
        self.__sHosterIdentifier = sHosterIdentifier.lower()
        self.__sDisplayName = 'Premium mode'
        self.isLogin = False
        self.__LoginTry = False
        self.__ssl = False
        self.oConfig = cConfig()

        self.__Ispremium = False
        bIsPremium = self.oConfig.getSetting('hoster_' + str(self.__sHosterIdentifier) + '_premium')
        if str(self.__sHosterIdentifier) == 'uptobox':
            bIsPremium = 'true'
        if (bIsPremium == 'true'):
            VSlog("Utilise compte premium pour hoster " +  str(self.__sHosterIdentifier))
            self.__Ispremium = True
        else:
            VSlog("Utilise compte gratuit pour hoster: " + str(self.__sHosterIdentifier))

    def isPremiumModeAvailable(self):
        return self.__Ispremium

    def getUsername(self):
        sUsername = self.oConfig.getSetting('hoster_' + str(self.__sHosterIdentifier) + '_username')
        if str(self.__sHosterIdentifier) == 'uptobox':
            sUsername = self.oConfig.getSetting('userN')
        return sUsername

    def getPassword(self):
        sPassword = self.oConfig.getSetting('hoster_' + str(self.__sHosterIdentifier) + '_password')
        if str(self.__sHosterIdentifier) == 'uptobox':
            sPassword = self.oConfig.getSetting('passW')
        return sPassword

    def AddCookies(self):
        cookies = GestionCookie().Readcookie(self.__sHosterIdentifier)
        return 'Cookie=' + cookies

    def Checklogged(self,code):
        if 'uptobox' in self.__sHosterIdentifier:
            if '?op=logout' in code:
                return True
        return False

    def CheckCookie(self):
        cookies = GestionCookie().Readcookie(self.__sHosterIdentifier)
        if cookies != '':
            return True
        return False

    def Authentificate(self):

        #un seul essais par session, pas besoin de bombarder le serveur
        if self.__LoginTry:
            return False
        self.__LoginTry = True

        if not self.__Ispremium:
            return False

        post_data = {}

        if 'uptobox' in self.__sHosterIdentifier:
            url = 'https://uptobox.com/'
            post_data['op'] = 'login'
            post_data['login'] = self.getUsername()
            post_data['password'] = self.getPassword()

        elif 'onefichier' in self.__sHosterIdentifier:
            url = 'https://1fichier.com/login.pl'
            post_data['mail'] = self.getUsername()
            post_data['pass'] = self.getPassword()
            post_data['lt'] = 'on'
            post_data['purge'] = 'on'
            post_data['valider'] = 'Send'
            self.__ssl = True
        elif 'uploaded' in self.__sHosterIdentifier:
            url = 'http://uploaded.net/io/login'
            post_data['id'] = self.getUsername()
            post_data['pw'] = self.getPassword()

        #si aucun de trouve on retourne
        else:
            return False

        #print url
        #print post_data
        if (self.__ssl):
            try:
                import ssl
                context = ssl._create_unverified_context()
            except:
                self.__ssl = False

        req = urllib2.Request(url, urllib.urlencode(post_data), headers)
        if 'uptobox' in self.__sHosterIdentifier:
            XFSS = self.oConfig.getSetting('xfss')
            req.add_header('cookie', 'xfss=%s;' % XFSS)

        try:
            if (self.__ssl):
                response = urllib2.urlopen(req,context=context)
            else:
                response = urllib2.urlopen(req)
        except urllib2.URLError, e:
            if getattr(e, "code", None) == 403 or \
               getattr(e, "code", None) == 502 or \
               getattr(e, "code", None) == 234 :
                #login denied
                cGui().showInfo(self.__sDisplayName, 'Authentification error %d' % getattr(e, "code", None) , 5)
            else:
                VSlog("debug" + str(getattr(e, "code", None)))
                VSlog("debug" + str(getattr(e, "reason", None)))

            self.isLogin = False
            return False

        sHtmlContent = response.read()
        head = response.headers
        response.close()

        # VSlog(sHtmlContent)
        # VSlog(head)

        if 'uptobox' in self.__sHosterIdentifier:
            if 'op=my_account' in sHtmlContent:
                self.isLogin = True
            else:
                cGui().showInfo(self.__sDisplayName, 'Authentification failed' , 5)
                return False
        elif 'onefichier' in self.__sHosterIdentifier:
            if 'You are logged in. This page will redirect you.' in sHtmlContent:
                self.isLogin = True
            else:
                cGui().showInfo(self.__sDisplayName, 'Authentification failed' , 5)
                return False
        elif 'uploaded' in self.__sHosterIdentifier:
            if sHtmlContent == '':
                self.isLogin = True
            else:
                cGui().showInfo(self.__sDisplayName, 'Authentification failed' , 5)
                return False
        else:
            return False

        #get cookie
        cookies = ''
        if 'Set-Cookie' in head:
            oParser = cParser()
            sPattern = '(?:^|,) *([^;,]+?)=([^;,\/]+?);'
            aResult = oParser.parse(str(head['Set-Cookie']), sPattern)
            #print aResult
            if (aResult[0] == True):
                for cook in aResult[1]:
                    cookies = cookies + cook[0] + '=' + cook[1]+ ';'
            # VSlog(cookies)

        #save cookie
        GestionCookie().SaveCookie(self.__sHosterIdentifier,cookies)

        # cGui().showInfo(self.__sDisplayName, 'Authentification reussie' , 5)
        VSlog( 'Auhentification reussie' )

        return True

    def GetHtmlwithcookies(self,url,data,cookies):
        req = urllib2.Request(url, data, headers)

        if not (data == None):
            req.add_header('Referer', url)

        # req.add_header('Cookie', cookies)
        XFSS = self.oConfig.getSetting('xfss')
        req.add_header('cookie', 'xfss='+XFSS+'; ' + cookies)

        try:
            response = urllib2.urlopen(req)
        except urllib2.URLError, e:
            xbmc.log( str(e.code))
            xbmc.log( e.reason )
            return ''

        sHtmlContent = response.read()
        response.close()
        return sHtmlContent

    def GetHtml(self,url,data = None):
        cookies = GestionCookie().Readcookie(self.__sHosterIdentifier)

        #aucun ne marche sans cookies
        if (cookies== '') and not (self.__LoginTry) and self.__Ispremium:
            self.Authentificate()
            if not (self.isLogin):
                return ''
            cookies = GestionCookie().Readcookie(self.__sHosterIdentifier)

        sHtmlContent = self.GetHtmlwithcookies(url,data,cookies)

        #fh = open('c:\\premium.txt', "w")
        #fh.write(sHtmlContent)
        #fh.close()

        #Les cookies ne sont plus valables, mais on teste QUE si la personne n'a pas essaye de s'authentifier
        if not(self.Checklogged(sHtmlContent)) and not self.__LoginTry and self.__Ispremium :
            VSlog('Cookies non valables')
            self.Authentificate()
            if (self.isLogin):
                cookies = GestionCookie().Readcookie(self.__sHosterIdentifier)
                sHtmlContent = self.GetHtmlwithcookies(url,data,cookies)
            else:
                return ''

        return sHtmlContent
