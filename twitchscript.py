#!/usr/bin/env python

VERSION = '0.0.3'

CONFIGFILE_ERROR = 3

try:
    import simplejson as json
except ImportError:
    try:
        import json
        json.dumps ; json.dumps
    except (ImportError, AttributeError):
        quit("Please install simplejson or Python 2.6 or higher.")

import ConfigParser
from optparse import OptionParser, SUPPRESS_HELP
from livestreamer import Livestreamer, StreamError, PluginError, NoPluginError
import requests
import urllib2
import requests
import sys
import os

config = ConfigParser.SafeConfigParser()
config.add_section('settings')
config.set('settings', 'channel', '15')
config.set('settings', 'game', '15')
config.set('settings', 'favorites', '')
config.set('settings', 'favgames', '')
config.set('settings', 'player', 'mplayer')
config.set('settings', 'quality', '720p')
config.set('settings', 'twitchapiurl', 'https://api.twitch.tv/kraken/')

# Handle request to twitch API

class TwitchApiRequest:
    def __init__(self, method):        
        self.method = method
        
    def send_request(self):
        try:
#            self.open_request = 'open'
	    self.open_request = requests.get(self.method)
        except AttributeError:
            pass
        except urllib2.HTTPError, e:
            try:
                msg = html2text(str(e.read()))
            except:
                msg = str(e)
        except urllib2.URLError, msg:
            try:
                reason = msg.reason[1]
            except IndexError:
                reason = str(msg.reason)
                                            
    def get_response(self):
        if self.open_request == None:
            return { 'result' : 'no open request'}
        
        #response = self.open_request.read()
        
        try:
            #data = json.loads(response)
	    data = self.open_request.json()
        except ValueError:
            quit("Cannot parse response: %s\n" % response, JSON_ERROR)
        self.open_request = None
        return data
    
# End of class TwitchApiRequest

# Wrapper to manage twitch API calls

class Twitch:
    def __init__(self, base_url, channel_limit, game_limit):        
        self.base_url = base_url
        self.channel_limit = channel_limit
        self.game_limit = game_limit        
        
    
    def get_game_list(self):
        parameter = ('%sgames/top?limit=%s' % (self.base_url, self.game_limit)).encode('utf-8')        
        request = TwitchApiRequest(parameter)
        request.send_request()        
        return request.get_response()
    
    def get_channel_for_game(self, game_name):        
        parameter = ('%sstreams?limit=%s&game=%s' % (self.base_url, self.channel_limit, game_name)).encode('utf-8')
        request = TwitchApiRequest(parameter)
        request.send_request()        
        return request.get_response()
        
    def get_favorites_streams_status(self, favs):
        parameter = ('%sstreams?channel=%s' % (self.base_url, favs)).encode('utf-8')        
        request = TwitchApiRequest(parameter)
        request.send_request()        
        return request.get_response()
                
# End of class Twitch

# Main loop

class Main:
    def __init__(self):    
        self.gchoice = -1
        self.cchoice = -1    
        self.exit_now = False
        self.state = 'none'
        self.keybingings = {
            ord('q'):       self.quit,
            ord('f'):       self.get_favorites,
            ord('s'):       self.get_fav_games,
            ord('g'):       self.get_games,
            ord('n'):       self.get_next,
            ord('r'):       self.refresh,
            ord('p'):       self.get_previous            
        }
        
        self.games = []
        self.favs = []
        self.channels = []        
        self.twitch = Twitch(config.get('settings', 'twitchapiurl'), config.get('settings', 'channel'), config.get('settings', 'game'))
        self.livestreamer = Livestreamer()
        
        try:
            self.run()
        except Exception as e:
            print e.message
        
    def run(self):
        
        while True:            
            self.display_message()                                            
            if self.exit_now:
                return
    
    def quit(self, c):
        self.exit_now = True
        
    def display_message(self):
                               
        if self.state == 'none':
            clear_screen()                      
            self.handle_user_input('Choose an option : (F)avorites, (G)ame, (Q)uit')            
        
        if self.state == 'favs':
            clear_screen()            
            print 'Showing online favorites stream :'
            print '-' * 40
            if(len(self.favs) > 0):                            
                self.show_content(self.favs)            
                self.handle_user_input('Choose a channel by number (r to refresh, g to list by games and q to quit', range(len(self.favs) + 1))
                clear_screen()
            else:
                self.handle_user_input('No favorites channel online (r to refresh, g to list by games and q to quit', range(len(self.favs) + 1))
                clear_screen()            
                
        if self.state == 'games':
            clear_screen()            
            print 'Showing top %d games:' % config.getint('settings', 'game')
            print '-' * 40
            if(len(self.games) > 0):                            
                self.show_content(self.games)            
                self.gchoice = self.handle_user_input('Choose a game by number (r to refresh, f to check your favorite channels and q to quit', range(len(self.games) + 1))
                if self.gchoice != -1:
                    self.state = 'channels'
                    clear_screen()                                                 
                    
        if self.state == 'favgames':
            clear_screen()            
            print 'Showing favorites games:'
            print '-' * 40
            if(len(self.games) > 0):                        
                self.show_content(self.games)            
                self.gchoice = self.handle_user_input('Choose a game by number (r to refresh, f to check your favorite channels and q to quit', range(len(self.games) + 1))
                if self.gchoice != -1:
                    self.state = 'channels'
                    clear_screen()
        
        if self.state == 'channels':
            clear_screen()            
            print 'Showing top %d channel for %s:' % (config.getint('settings', 'channel'), self.games[self.gchoice - 1])
            print '-' * 40            
            self.get_channels(self.gchoice)
            if(len(self.channels) > 0):                            
                self.show_content(self.channels)            
                self.cchoice = self.handle_user_input('Choose a channel by number (r to refresh, f to check your favorite channels, g to reload game list and q to quit', range(len(self.channels) + 1))
                if self.cchoice != -1:
                    self.play_stream(self.channels[self.cchoice - 1])
                    self.state = 'channels'
                    clear_screen()
       
    def play_stream(self, channel):
        clear_screen()
        
        try:
            plugin = self.livestreamer.resolve_url(("twitch.tv/{0}").format(channel))
        except Exception as e:
            print e.message                   
        
        try:
            streams = plugin.get_streams()
        except PluginError as err:
            exit("Plugin error: {0}".format(err))
            
        quality = config.get('settings', 'quality')
        if quality not in streams:
            quality = "Source"
            print "Can't open streams with quality requested ({0}), opening best one".format(config.get('settings', 'quality'))
                        
        channel = transform_spaces(channel)
        if os.name == 'nt':
            os.system('livestreamer twitch.tv/%s %s' % (channel, quality))
            #os.system('livestreamer twitch.tv/%s best -p "%s"' % (channel, config.get('settings', 'player')))
        else:
            os.system('livestreamer twitch.tv/%s %s' % (channel, quality))
            #os.system('livestreamer twitch.tv/%s best -np "%s"' % (channel, config.get('settings', 'player')))
            
    def show_content(self, content):
        for i in range(len(content)):
            if i < 9:
                print '',
            if i < 99:
                print '',
            print '%d %s' % (i + 1, content[i])
            
    def handle_user_input(self, message, valid = None):
        self.state = 'none'
        validinput = False
        while not validinput:
            input = raw_input('%s\n ' % message)
            input = input.strip().lower()
            
            if input.isdigit():
                input = int(input)
                if input in valid:
                    validinput = True                    
                    return input
            elif len(input) == 1:
                c = ord(input)                
                f = self.keybingings.get(c, None)
                if f:
                    f(c)
                    validinput = True                    
                    return -1
            
        
    def get_favorites(self, c):
        self.state = 'favs'
        del self.favs[:]
        try:
            response = self.twitch.get_favorites_streams_status(config.get('settings', 'favorites'))
            receivedcount = len(response['streams'])
            
            for i in range(receivedcount):
                self.favs.append('%s playing: %s' % (response['streams'][i]['channel']['name'], response['streams'][i]['game']))
                
        except Exception as e:
            print 'Error getting favs streams!\n'
            print e.message
            return 0
        
    def get_games(self, c):        
        self.state = 'games'
        del self.games[:]
        try:
            response = self.twitch.get_game_list()
            receivedcount = len(response['top'])
            
            for i in range(receivedcount):
                self.games.append(response['top'][i]['game']['name'])
                
        except Exception as e:
            print 'Error getting games !\n'
            print e.message
            return 0
        
    def get_fav_games(self, c):
        self.state = 'favgames'
        del self.games[:]
        
        favgames = config.get('settings', 'favgames')
        if len(favgames) > 0:
            self.games.extend(favgames.split(', '))                        
        
    def get_channels(self, choice):
        self.state = 'channels'
        del self.channels[:]
        try:
            response = self.twitch.get_channel_for_game(transform_spaces(self.games[self.gchoice - 1]))
            receivedcount = len(response['streams'])
            
            for i in range(receivedcount):
                self.channels.append('%s (%s)' % (response['streams'][i]['channel']['name'], response['streams'][i]['viewers']))
                
        except Exception as e:
            print 'Error getting games !\n'
            print e.message
            return 0        
        
    def refresh(self, c):
        print 'tmp'
        
    def get_next(self, c):
        print 'tmp'
        
    def get_previous(self, c):
        print 'tmp'
        
# End of class Main

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def transform_spaces(s):
    return s.replace(' ', '%20')

def create_config(option, opt_str, value, parser):
    configfile = parser.values.configfile
    config.read(configfile)
    
    dir = os.path.dirname(configfile)
    if dir != "" and not os.path.isdir(dir):
        try:
            os.makedirs(dir)
        except OSError, msg:
            print msg
            exit(CONFIGFILE_ERROR)
    
    if not save_config(configfile, force=True):
        exit(CONFIGFILE_ERROR)
    print "Wrote config file: %s" % configfile
    exit(0)
    
def save_config(filepath, force=False):
    if force or os.path.isfile(filepath):
        try:
            config.write(open(filepath, 'w'))
            os.chmod(filepath, 0600)  # config may contain password
            return 1
        except IOError, msg:
            print >> sys.stderr, "Cannot write config file %s:\n%s" % (filepath, msg)
            return 0
    return -1

def html2text(str):
    str = re.sub(r'</h\d+>', "\n", str)
    str = re.sub(r'</p>', ' ', str)
    str = re.sub(r'<[^>]*?>', '', str)
    return str

def debug(data):
    if options.DEBUG:
        file = open("debug.log", 'a')
        if type(data) == type(str()):
            file.write(data)
        else:
            import pprint
            pp = pprint.PrettyPrinter(indent=4)
            file.write("\n====================\n" + pp.pformat(data) + "\n====================\n\n")
        file.close

def quit(msg='', exitcode=0):    
    # if this is a graceful exit and config file is present
    if not msg and not exitcode:
        save_config(cmd_args.configfile)
    else:
        print >> sys.stderr, msg,
    os._exit(exitcode)
    
def show_version(option, opt_str, value, parser):
    quit("twitch %s\n" % VERSION)


if __name__ == '__main__':
    default_config_path = os.path.expanduser('~') + '/.twitchrc'
    parser = OptionParser(usage="%prog [options]", description="%%prog %s" % VERSION)
    parser.add_option("-v", "--version", action="callback", callback=show_version,
                      help="Show version number")
    parser.add_option("-f", "--config", action="store", dest="configfile", default=default_config_path,
                      help="Path to configuration file.")
    parser.add_option("--create-config", action="callback", callback=create_config,
                      help="Create configuration file CONFIGFILE with default values.")
    parser.add_option("-d", "--debug", action="store_true", dest="DEBUG", default=False,
                      help="Everything passed to the debug() function will be added to the file debug.log.")
    (options, cmd_args) = parser.parse_args()
    debug(options)
    config.read(options.configfile)
    
    Main()
