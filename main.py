import sys
import os
import semver 
import survey
import aiohttp
import asyncio
import traceback
import json
import logging
import winreg
import aiofiles
import psutil
import xml.etree.ElementTree as ET
from datetime import datetime
from rich import print_json
from console.utils import set_title
from mitmproxy.tools.web.master import WebMaster
from mitmproxy import http
from mitmproxy.options import Options
from pypresence import AioPresence

appName = "RaidFN"
debug = False

backendTypeMap = {
  "CID": "AthenaCharacter",
  "Shoes": "AthenaShoes"
}

itemTypeMap = {
  "emote": "AthenaDance",
  "backpack": "AthenaBackpack",
  "outfit": "AthenaCharacter",
  "toy": "AthenaDance",
  "glider": "AthenaGlider",
  "emoji": "AthenaDance",
  "pet": "AthenaPetCarrier",
  "spray": "AthenaDance",
  "music": "AthenaMusicPack",
  "bannertoken": "HomebaseBannerIcon",
  "contrail": "AthenaSkyDiveContrail",
  "wrap": "AthenaItemWrap",
  "loadingscreen": "AthenaLoadingScreen",
  "pickaxe": "AthenaPickaxe",
  "vehicle_wheel": "VehicleCosmetics_Wheel",
  "vehicle_wheel": "VehicleCosmetics_Wheel",
  "vehicle_skin": "VehicleCosmetics_Skin",
  "vehicle_booster": "VehicleCosmetics_Booster",
  "vehicle_body": "VehicleCosmetics_Body",
  "vehicle_drifttrail": "VehicleCosmetics_DrifTrail",
  "vehicle_cosmeticvariant": "CosmeticVariantToken",
  "cosmeticvariant": "none",
  "bundle": "AthenaBundle",
  "battlebus": "AthenaBattleBus",
  "itemaccess": "none",
  "sparks_microphone": "SparksMicrophone",
  "sparks_keyboard": "SparksKeyboard",
  "sparks_bass": "SparksBass",
  "sparks_drum": "SparksDrums",
  "sparks_guitar": "SparksGuitar",
  "sparks_aura": "SparksAura",
  "sparks_song": "SparksSong",
  "building_set": "JunoBuildingSet",
  "building_prop": "JunoBuildingProp",
}

def read_fortnite_game_data():
    if not os.path.isfile('fortnite-game.json'):
        raise FileNotFoundError("Fortnite game data file not found")
    with open('fortnite-game.json', 'r', encoding='utf-8') as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            raise ValueError("Error decoding JSON from Fortnite game data file")

def cls():
  os.system("cls" if os.name == "nt" else "clear")

def readConfig():
  with open("userConfig.json") as f:
    config = json.loads(f.read())
    return config

async def aprint(text: str, delay: float):
  for character in text:
    sys.stdout.write(character)
    sys.stdout.flush()
    if character.isalpha():
      await asyncio.sleep(delay)
  sys.stdout.flush()
  return print()

def center(var: str, space: int | None = None):
  if not space:
    space = (
      os.get_terminal_size().columns
      - len(var.splitlines()[int(len(var.splitlines()) / 2)])
    ) // 2
  return "\n".join((" " * int(space)) + var for var in var.splitlines())

def processExists(name):
  for process in psutil.process_iter():
    try:
      if name.lower() in process.name().lower():
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
      pass
  return False

def proxy_toggle(enable: bool=True):
  INTERNET_SETTINGS = winreg.OpenKey(
    winreg.HKEY_CURRENT_USER,
    r"Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
    0,
    winreg.KEY_ALL_ACCESS,
  )

  def set_key(name: str, value: str | int):
    try:
      _, reg_type = winreg.QueryValueEx(INTERNET_SETTINGS, name)
      winreg.SetValueEx(INTERNET_SETTINGS, name, 0, reg_type, value)
    except FileNotFoundError:
      winreg.SetValueEx(INTERNET_SETTINGS, name, 0, winreg.REG_SZ, value)

  proxy_enable = winreg.QueryValueEx(INTERNET_SETTINGS, "ProxyEnable")[0]

  if proxy_enable == 0 and enable:
    set_key("ProxyServer", "127.0.0.1:1942")
    set_key("ProxyEnable", 1)
  elif proxy_enable == 1 and not enable:
    set_key("ProxyEnable", 0)
    set_key("ProxyServer", "")

def gracefulExit():
  proxy_toggle(enable=False)
  while True:
    sys.exit()

class Addon:
  def __init__(self, server: "MitmproxyServer"):
    self.server = server

  def request(self, flow: http.HTTPFlow) -> None:
      url = flow.request.pretty_url

      if (
        "https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/game/v2/matchmakingservice/ticket/player"
        in flow.request.pretty_url
        and self.server.app.playlist
      ):
        playlistOld, playlistNew = list(self.server.app.playlistId.items())[0]
        flow.request.url = flow.request.url.replace(
          "%3A" + playlistOld, "%3A" + playlistNew
        )

      if self.server.app.name:
        nameOld, nameNew = list(self.server.app.nameId.items())[0]
        flow.request.url = flow.request.url.replace(nameOld, nameNew)

  def websocket_message(self, flow: http.HTTPFlow):
    assert flow.websocket is not None
    clientMsg = bool(flow.websocket.messages[-1].from_client)
    msg = flow.websocket.messages[-1]
    msg = str(msg).replace("\"WIN\"","\"PS5\"")
    msg = msg[1:-1]
    msg = msg
      
    if clientMsg:
        try:
          root = ET.fromstring(msg.replace("WIN","PS5"))
          status_element = root.find("status")
          json_data = json.loads(status_element.text)

          new_json_text = json.dumps(json_data)

          new_json_text.replace(":WIN:",":PS5:")
          
          status_element.text = new_json_text
          new_xml_data = ET.tostring(root)

          flow.websocket.messages[-1].content = new_xml_data
        except:
          pass


  def response(self, flow: http.HTTPFlow):
    try:
      url = flow.request.pretty_url

      if (
        ("setloadoutshuffleenabled" in url.lower())
        or 
        url
        == 
        "https://fortnitewaitingroom-public-service-prod.ol.epicgames.com/waitingroom/api/waitingroom"
        or 
        "socialban/api/public/v1"
        in 
        url.lower()
      ):
        flow.response = http.Response.make(
          204,
          b"", 
          {"Content-Type": "text/html"}
        )
      
      if "putmodularcosmetic" in url.lower():
        presetMap = {
          "CosmeticLoadout:LoadoutSchema_Character":"character",
          "CosmeticLoadout:LoadoutSchema_Emotes": "emotes",
          "CosmeticLoadout:LoadoutSchema_Platform": "lobby",
          "CosmeticLoadout:LoadoutSchema_Wraps": "wraps",
          "CosmeticLoadout:LoadoutSchema_Jam": "jam",
          "CosmeticLoadout:LoadoutSchema_Sparks": "instruments",
          "CosmeticLoadout:LoadoutSchema_Vehicle": "sports",
          "CosmeticLoadout:LoadoutSchema_Vehicle_SUV": "suv",
        }
          
                
        baseBody = flow.request.get_text()
        body = json.loads(baseBody)
        loadoutData = json.loads(body['loadoutData'])
        
        if body.get('presetId') != 0:
          presetId = body['presetId']
          
          slots = loadoutData['slots']
          presetType = body['loadoutType']
          
          configTemplate = {
            "presetType": presetType,
            "presetId": presetId,
            "slots":  slots
          }
          
          with open("userConfig.json") as f:
            data = json.load(f)
          
          key = presetMap.get(presetType)
          
          if data["saved"]['presets'][key].get(presetId):
            data["saved"]['presets'][key][presetId] = configTemplate
          else:
            data["saved"]['presets'][key].update({str(presetId):configTemplate})
          
          self.server.app.athena.update(
            {
              f"{presetType} {presetType}": {
                "attributes" : {
                  "display_name" : f"PRESET {presetId}",
                  "slots" : slots
                },
                "quantity" : 1,
                "templateId" : presetType
              },
            }
          )
          
          with open(
            "userConfig.json",
            "w"
          ) as f:
            json.dump(data, f,indent=2)
          
        try:
          accountId = url.split("/")[8]
        except:
          accountId = "cfd16ec54126497ca57485c1ee1987dc"
            
        response = {
          "profileRevision": 99999,
          "profileId": "athena",
          "profileChangesBaseRevision": 99999,
          "profileCommandRevision": 99999,
          "profileChanges": [
            {
              "changeType": "fullProfileUpdate",
              "profile": {
                "created": "",
                "updated": str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'),
                "rvn": 0,
                "wipeNumber": 1,
                "accountId": accountId,
                "profileId": "athena",
                "version": "no_version",
                "items": self.server.app.athena,
                "stats": {
                  "loadout_presets": {
                    "CosmeticLoadout:LoadoutSchema_Character": {},
                    "CosmeticLoadout:LoadoutSchema_Emotes": {},
                    "CosmeticLoadout:LoadoutSchema_Shoes": {},
                    "CosmeticLoadout:LoadoutSchema_Platform": {},
                    "CosmeticLoadout:LoadoutSchema_Wraps": {},
                    "CosmeticLoadout:LoadoutSchema_Jam": {},
                    "CosmeticLoadout:LoadoutSchema_Sparks": {},
                    "CosmeticLoadout:LoadoutSchema_Vehicle": {},
                    "CosmeticLoadout:LoadoutSchema_Vehicle_SUV": {}
                  }
                },
                "commandRevision": 99999,
                "profileCommandRevision": 99999,
                "profileChangesBaseRevision": 99999
              }
            }
          ]
        }
        
        if body.get('presetId') != 0:
          response['profileChanges'][0]['profile']['stats']['loadout_presets'][presetType].update(
            {
              presetId: f"{presetType} {presetId}"
            }
          )

        flow.response = http.Response.make(
          200,
          json.dumps(response),
          {"Content-Type": "application/json"}
        )

      if url == "https://fortnitecontent-website-prod07.ol.epicgames.com/content/api/pages/fortnite-game/":
          try:
              fortnitegame_response = read_fortnite_game_data()
          except (FileNotFoundError, ValueError) as e:
              fortnitegame_response = {"error": str(e)}
          
          flow.response = http.Response.make(
              200,
              json.dumps(fortnitegame_response),
              {"Content-Type": "application/json"}
          )

          
      if"/SetItemFavoriteStatusBatch" in url:
        text = flow.request.get_text()
        favData = json.loads(text)
        
        changeValue = favData['itemFavStatus'][0]
        itemIds = favData['itemIds']
        
        if changeValue:
          
          with open("userConfig.json") as f:
            data = json.load(f)
          
          for itemId in itemIds:
              if itemId not in data["saved"]["favorite"]:
                data["saved"]["favorite"].append(itemId)
              self.server.app.athena[itemId]["attributes"]['favorite'] = True
          
          with open("userConfig.json", "w") as f:
            json.dump(data, f,indent=2) 
        else:
          
          with open("userConfig.json") as f:
            data = json.load(f)
          
          for itemId in itemIds:
              if itemId in data["saved"]["favorite"]:
                data["saved"]["favorite"].remove(itemId)
              self.server.app.athena[itemId]["attributes"]['favorite'] = False
          
          with open(
            "userConfig.json",
            "w"
          ) as f:
            json.dump(data, f,indent=2)
        try:
          accountId = url.split("/")[8]
        except:
          accountId = "cfd16ec54126497ca57485c1ee1987dc"
        
        response = {
          "profileRevision": 99999,
          "profileId": "athena",
          "profileChangesBaseRevision": 99999,
          "profileCommandRevision": 99999,
          "profileChanges": [
            {
              "changeType": "fullProfileUpdate",
              "profile": {
                "created": "",
                "updated": str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'),
                "rvn": 0,
                "wipeNumber": 1,
                "accountId": accountId,
                "profileId": "athena",
                "version": "no_version",
                "items": self.server.app.athena,
                "commandRevision": 99999,
                "profileCommandRevision": 99999,
                "profileChangesBaseRevision": 99999
              }
            }
          ]
        }
        

        
        flow.response = http.Response.make(
          200,
          json.dumps(response),
          {"Content-Type": "application/json"}
        )
            
      if "/SetItemArchivedStatusBatch" in url:
        text = flow.request.get_text()
        archiveData = json.loads(text)
        
        changeValue = archiveData['archived']
        itemIds = archiveData['itemIds']
        
        if changeValue:
          
          data = readConfig()
            
          for itemId in itemIds:
              self.server.app.athena[itemId]["attributes"]['archived'] = True
              if itemId not in data['saved']['archived']:
                data["saved"]["archived"].append(itemId)
          
          with open(
            "userConfig.json",
            "w"
          ) as f:
            json.dump(data, f,indent=2)
        else:
          
          with open("userConfig.json") as f:
            data = json.load(f)
          
          for itemId in itemIds:
              self.server.app.athena[itemId]["attributes"]['archived'] = False
              if itemId not in data["saved"]["archived"]:
                data["saved"]["archived"].remove(itemId)
          
          with open(
            "userConfig.json",
            "w"
          ) as f:
            json.dump(data,f,indent=2)   
        
        try:
          accountId = url.split("/")[8]
        except:
          accountId = "cfd16ec54126497ca57485c1ee1987dc"
          
        response = {
          "profileRevision": 99999,
          "profileId": "athena",
          "profileChangesBaseRevision": 99999,
          "profileCommandRevision": 99999,
          "profileChanges": [
            {
              "changeType": "fullProfileUpdate",
              "profile": {
                "created": "",
                "updated": str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'),
                "rvn": 0,
                "wipeNumber": 1,
                "accountId": accountId,
                "profileId": "athena",
                "version": "no_version",
                "items": self.server.app.athena,
                "commandRevision": 99999,
                "profileCommandRevision": 99999,
                "profileChangesBaseRevision": 99999
              }
            }
          ]
        }
        
        flow.response = http.Response.make(
          200,
          json.dumps(response),
          {"Content-Type": "application/json"}
        )      
      if "#setcosmeticlockerslot" in url.lower():
        try:
          accountId = url.split("/")[8]
        except:
          accountId = "cfd16ec54126497ca57485c1ee1987dc"
        
        baseBody = flow.request.get_text()
        reqbody = json.loads(baseBody)
        
        response = {
          "profileRevision": 99999,
          "profileId": "athena",
          "profileChangesBaseRevision": 99999,
          "profileCommandRevision": 99999,
          "profileChanges": [
            {
              "changeType": "fullProfileUpdate",
              "profile": {
                "created": "",
                "updated": str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'),
                "rvn": 0,
                "wipeNumber": 1,
                "accountId": accountId,
                "profileId": "athena",
                "version": "no_version",
                "items": self.server.app.athena,
                "commandRevision": 99999,
                "profileCommandRevision": 99999,
                "profileChangesBaseRevision": 99999
              }
            }
          ]
        } 
        flow.response = http.Response.make(
          200,
          json.dumps(response),
          {"Content-Type": "application/json"}
        )   
        
      if url.lower().startswith("https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/matchmaking/session/") and "?sessionKey=" in url.lower():
        text = flow.response.get_text()
        matchData = json.loads(text)
        
        matchData['allowInvites'] = True
        matchData['allowJoinInProgress'] = True
        matchData['allowJoinViaPresence'] = True 
        
        matchData['allowJoinViaPresenceFriendsOnly'] = False
        matchData['attributes']['ALLOWBROADCASTING_b'] = False
        matchData['attributes']['ALLOWMIGRATION_s'] = "true"
        matchData['attributes']['ALLOWREADBYID_s'] = "true"
        matchData['attributes']['CHECKSANCTIONS_s'] = "false"
        matchData['attributes']['REJOINAFTERKICK_s'] = "OPEN"
        matchData['attributes']['allowMigration_s'] = True
        matchData['attributes']['allowReadById_s'] = True
        matchData['attributes']['checkSanctions_s'] = False
        matchData['attributes']['rejoinAfterKick_s'] = True
        
        matchData['shouldAdvertise'] = True
        matchData['usesPresence'] = True
        matchData['usesStats'] = False
        matchData['maxPrivatePlayers'] = 999
        matchData['maxPublicPlayers'] = 999
        matchData['openPrivatePlayers'] = 999
        matchData['openPublicPlayers'] = 999
        
        
        flow.response.text = json.dumps(matchData)
      

      if  "client/QueryProfile?profileId=athena" in url or "client/QueryProfile?profileId=common_core" in url or "client/ClientQuestLogin?profileId=athena" in url and self.server.app.config.get("EveryCosmetic"):
        text = flow.response.get_text()
        athenaFinal = json.loads(text)
        try:
          athenaFinal["profileChanges"][0]["profile"]["items"].update(self.server.app.athena)
          if self.server.app.level:
            athenaFinal["profileChanges"][0]["profile"]["stats"]["attributes"]["level"] = self.server.app.level
          if self.server.app.battleStars:
            athenaFinal["profileChanges"][0]["profile"]["stats"]["attributes"]["battlestars"] = self.server.app.battleStars
          try:
            if self.server.app.crowns:
              athenaFinal["profileChanges"][0]["profile"]["items"]["VictoryCrown_defaultvictorycrown"]['attributes']['victory_crown_account_data']["total_royal_royales_achieved_count"] = self.server.app.crowns
          except KeyError:
            pass
          flow.response.text = json.dumps(athenaFinal)
        except KeyError as e:
          if debug:
            print(e,traceback.format_exc())
            input(text)
          else:
            pass

      if (
        "https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/game/v2/matchmakingservice/ticket/player"
        in flow.request.pretty_url
        and self.server.app.playlist
      ):
        print_json(flow.response.text)

      if "/entitlement/api/account/" in url.lower():
        flow.response.text = flow.response.text.replace(
          "BANNED",
          "ACTIVE"
        )

      if url.startswith("https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/storeaccess/v1/request_access/"):
        accountId = url.split("/")[1:]
        flow.request.url = flow.request.url.replace(
          accountId,
          "cfd16ec54126497ca57485c1ee1987dc"
        )

      if "/fortnite/api/matchmaking/session/" in url.lower() and "/join" in url.lower():
        flow.response = http.Response.make(
          200,
          b"[]",
          {"Content-Type": "application/json"}
        )

      if "/fortnite/api/game/v2/br-inventory/account" in url.lower():
        currentStash = {
          "stash": {
            "globalcash": 5000
          }
        }
        flow.response.text = json.dumps(currentStash)

      if "/lightswitch/api/service/bulk/status" in url.lower():
        status = [
          {
            "serviceInstanceId": "fortnite",
            "status": "UP",
            "message": "fortnite is up.",
            "maintenanceUri": None,
            "overrideCatalogIds": ["a7f138b2e51945ffbfdacc1af0541053"],
            "allowedActions": [
              "PLAY",
              "DOWNLOAD"
            ],
            "banned": False,
            "launcherInfoDTO": {
              "appName": "Fortnite",
              "catalogItemId": "4fe75bbc5a674f4f9b356b5c90567da5",
              "namespace": "fn",
            },
          }
        ]
        dump = json.dumps(status)
        flow.response.text = dump

      if self.server.app.name:
        nameOld, nameNew = list(self.server.app.nameId.items())[0]
        if flow.response is not None and flow.response.text is not None:
          flow.response.text = flow.response.text.replace(
            nameOld,
            nameNew
          )

      if "/lfg/fortnite/tags" in url.lower() and self.server.app.InviteExploit:
        users = readConfig()
        users = users["InviteExploit"]["users"]
        flow.response.text = json.dumps({"users": users})

    except Exception as e:
      if debug:
        print(traceback.format_exc())
        input(e)


class MitmproxyServer:
  def __init__(
    self,
    app: "RaidFN",
    loop: asyncio.AbstractEventLoop
  ):
    try:
      self.app = app
      self.loop = loop
      self.running = False
      self.task = None
      self.stopped = asyncio.Event()
      self.m = WebMaster(
        Options(),
        with_termlog=False
      )
      self.m.options.listen_host = "127.0.0.1"
      self.m.options.listen_port = 1942
      self.m.options.web_open_browser = False
      self.m.addons.add(Addon(self))
    except KeyboardInterrupt:
      pass

  def run_mitmproxy(self):
    self.running = True
    try:
      set_title(f"{appName}")
      closeFortnite = readConfig()['closeFortnite']
      if closeFortnite:
        startupTasks = [
          "taskkill /im FortniteLauncher.exe /F",
          "taskkill /im FortniteClient-Win64-Shipping_EAC_EOS.exe /F",
          "taskkill /im FortniteClient-Win64-Shipping.exe /F"
        ]
        for task in startupTasks:
          os.system(task+" > NUL 2>&1")
      self.task = self.loop.create_task(self.m.run())
    except KeyboardInterrupt:
      pass

  def start(self):
    self.running = True
    try:
      self.run_mitmproxy()
      proxy_toggle(True)
    except TypeError:
      if self.task:
        self.task.cancel()
      self.task = None
      self.stopped.set()
      return self.stop()

  def stop(self):
    self.running = False
    try:
      self.m.shutdown()
    except AssertionError:
      return "Unable to Close Proxy"

    proxy_toggle(enable=False)
    return True

class RaidFN:
  def __init__(
    self,
    loop: asyncio.AbstractEventLoop | None=None,
    configFile: str = "userConfig.json",
    client_id=1228345213161050232
  ):
    self.loop = loop or asyncio.get_event_loop()
    self.ProxyEnabled = False
    self.configFile = configFile
    self.state = ""
    self.appVersion = semver.Version.parse("1.1.0")
    self.client_id = client_id
    self.mitmproxy_server = MitmproxyServer(
      app=self,
      loop=self.loop
    )
    self.running = False
    self.name = False
    self.nameId = {}
    self.athena = {}
    self.stats = {}
    self.playlist = False
    self.level = None
    self.battleStars = None
    self.crowns = None
    self.playlistId = {}

    self.config = {}

  async def __async_init__(self):
    try:
      async with aiofiles.open(self.configFile) as f:
        self.config = json.loads(await f.read())      
    except: 
      pass
    
    if self.config["InviteExploit"].get("enabled"):
      self.InviteExploit = True
    
    if self.config.get("EveryCosmetic"):
      self.athena = await self.buildAthena()


  async def needsUpdate(self):
    if not self.config.get("updateSkip"):
      return False

    return self.appVersion < self.appVersionServer
   
  async def buildAthena(self):
    apiKey = self.config.get("apiKey")
    if not apiKey or apiKey == "" or apiKey == "":
      input();sys.exit()

    base = {}

    config = readConfig()
    async with aiohttp.ClientSession() as session:
      async with session.get(
        "https://fortniteapi.io/v2/items/list?fields=id,name,styles,type",
        headers={"Authorization": apiKey},
      ) as request:
        FortniteItems = await request.json()
        GithubItems = await request.text()
        
    ThirdPartyItems = [item for item in GithubItems.split(";")]
    for Item in ThirdPartyItems:
      backendType = backendTypeMap.get(Item.split("_")[0])
      templateId = f"{backendType}:{Item}"

      variants = []

      itemTemplate = {
        templateId : {
          "templateId": templateId,
          "quantity": 1,
          "attributes": {
            "creation_time": None,
            "archived": True if templateId in config['saved']['archived'] else False,
            "favorite": True if templateId in config['saved']['favorite'] else False,
            "variants": variants,
            "item_seen": True,
            "giftFromAccountId": "cfd16ec54126497ca57485c1ee1987dc",
          },
        }
      }
      base.update(itemTemplate)

    for item in FortniteItems["items"]:

      variants = []
      
      if item.get("styles"):
        
        itemVariants = []
        variant = {}
        itemVariantChannels = {}
        
        for style in item['styles']:

          for styles in item["styles"]:
            styles['channel'] = styles['channel'].split(".")[-1]
            styles['tag'] = styles['tag'].split(".")[-1]
            
            channel = styles["channel"]
            channelName = styles["channelName"]
            
            if styles["channel"] not in variant:
              
              variant[channel] = {
                "channel": channel,
                "type": channelName,
                "options": []
              }
            
            
            variant[channel]["options"].append(
              {
                "tag": styles["tag"] ,
                "name": styles["name"],
              }
            )

          option = {
              "tag": styles["tag"],
              "name": styles["name"],
          }
          
          newStyle = list(variant.values())
          
          variantTemplate = {
            "channel": None,
            "active": None,
            "owned": []
          }
          variantFinal = newStyle[0]
          
          try:
            variantTemplate['channel'] = variantFinal['channel']
          except:
            continue
          
          variantTemplate['active'] = variantFinal['options'][0]['tag']
          
          for mat in variantFinal['options']:
            variantTemplate['owned'].append(mat['tag'])
            
          variants.append(variantTemplate)
      
      templateId = itemTypeMap.get(item["type"]["id"]) + ":" + item["id"]


      itemTemplate = {
          templateId : {
          "templateId": templateId,
          "quantity": 1,
          "attributes": {
            "creation_time": None,
            "archived": True if templateId in config['saved']['archived'] else False,
            "favorite": True if templateId in config['saved']['favorite'] else False,
            "variants": variants,
            "item_seen": True,
            "giftFromAccountId": "4735ce9132924caf8a5b17789b40f79c",
          },
        }
      }
      base.update(itemTemplate)
    
    extraTemplates = [
      {
        "VictoryCrown_defaultvictorycrown":
          {
            "templateId": "VictoryCrown:defaultvictorycrown",
            "attributes": {
              "victory_crown_account_data": {
                "has_victory_crown": True,
                "data_is_valid_for_mcp": True,
                "total_victory_crowns_bestowed_count": 500,
                "total_royal_royales_achieved_count": 1942
              },
              "max_level_bonus": 0,
              "level": 124,
              "item_seen": False,
              "xp": 0,
              "favorite": False
            },
            "quantity": 1
          }
      },
      {
        "Currency:MtxPurchased": {
          "templateId": "Currency:MtxPurchased",
          "attributes": {"platform": "EpicPC"},
          "quantity": 13500
        }
      }
    ]
    for template in extraTemplates:
      base.update(template)  

    config = readConfig()
    
    for presetType in config['saved']['presets'].values():
      for preset in presetType.values():
        base.update(
          {
            f"{preset['presetType']} {preset['presetId']}": {
              "attributes" : {
                "display_name" : f"PRESET {preset['presetId']}",
                "slots" : preset['slots']
              },
              "quantity" : 1,
              "templateId" : preset['presetType']
            },
          }
        )
    
    total = len(FortniteItems['items']) +len(ThirdPartyItems)
    self.athena = base
    
    return base

  def options(self):
    options = {}
    
    if self.ProxyEnabled:
      options.update({"Disable Proxy":"SET_PROXY_TASK"})
    else:
      options.update({"Enable Proxy":"SET_PROXY_TASK"})
      
    if self.name:
      options.update({"Remove Custom Display Name":"SET_NAME_TASK"})
    else:
      options.update({"Change Display Name":"SET_NAME_TASK"})
    
    if self.playlist:
      options.update({"Remove Custom Playlist":"SET_PLAYLIST_TASK"})
    else:
      options.update({"Set Playlist":"SET_PLAYLIST_TASK"})
      
    if self.playlist:
      options.update({"Remove Custom Playlist":"SET_PLAYLIST_TASK"})
    else:
      options.update({"Set Playlist":"SET_PLAYLIST_TASK"})
      
      
    
    options.update({f"Change Level": "SET_LEVEL_TASK"})
    options.update({f"Change Battle Stars": "SET_BATTLESTARS_TASK"})
    options.update({f"Change Crowns": "SET_CROWN_TASK"})
    
    options.update({f"Exit {appName}": "EXIT_TASK"})

    return options

  async def exec_command(self, option: str):
    options = self.options()
    match option:
      case "SET_PROXY_TASK":
        if self.running:
          self.mitmproxy_server.stop()

        else:
          try:
            self.mitmproxy_server.start()
            await self.mitmproxy_server.stopped.wait()
          except:
            self.running = False
            self.mitmproxy_server.stop()

      case "SET_NAME_TASK":
        self.name = not self.name
        if not self.name:
          self.nameId = {}
        else:
          old = input(f"[+] Current Name: ")
          new = input(f"[+] Enter New Display Name to Replace {old}: ")
          self.nameId[old] = new
        
      case "SET_LEVEL_TASK":
        level = input(f"[+] Set Level: ")
        self.level = int(level)
        
      case "SET_BATTLESTARS_TASK":
        battleStars = input(f"[+] Set Battle Stars: ")
        self.battleStars = int(battleStars)
        
      case "SET_CROWN_TASK":
        crowns = input(f"[+] Set Battle Stars: ")
        self.crowns = int(crowns)

      case "SET_PLAYLIST_TASK":
        self.playlist = not self.playlist
        if not self.playlist:
          self.playlistId = {}
          return
        new = input(
          f"[+] Enter New Playlist To Overide {self.config.get('Playlist')}: "
        )
        self.playlistId[self.config.get("Playlist", "")] = new
        
      case "EXIT_TASK":
        proxy_toggle(enable=False)
        cls()
        sys.exit(1)
      case _: pass

  async def checks(self):
    proxy_toggle(enable=False)
    needs_update = await self.needsUpdate()

    try:
      path = os.path.join(
        os.getenv('ProgramData'),
        "Epic",
        "UnrealEngineLauncher",
        "LauncherInstalled.dat"
      )
      with open(path) as file:
        Installed = json.load(file)

      for InstalledGame in Installed['InstallationList']:
        if InstalledGame['AppName'].upper() == "FORTNITE":
          self.path = InstalledGame['InstallLocation'].replace("/","\\")
          EasyAntiCheatLocation = self.path+"\\FortniteGame\\Binaries\\Win64\\EasyAntiCheat".replace("/","\\")
          EasyAntiCheatLocation = os.path.join(
            self.path,
            "FortniteGame",
            "Binaries",
            "Win64",
            "EasyAntiCheat",
          ).replace("/","\\")
          continue

      async with aiohttp.ClientSession() as session:
        eac_splash = "https://raw.githubusercontent.com/RaidFN-GH/External/refs/heads/main/SplashScreen.png"
        async with session.get(eac_splash) as request:
          content = await request.read()
      
      async with aiofiles.open(
        EasyAntiCheatLocation+"\\"+"SplashScreen.png", 
        'wb'
      ) as dest_file:
        await dest_file.write(content)
    except Exception as e:
      if debug:
        print(traceback.format_exc())
        input(e)
      
      for file in self.updateFiles:
        async with aiohttp.ClientSession() as session:
            data = await request.text()
            
        async with aiofiles.open(
          file=file,
          mode="w"
        ) as f:
          await f.write(data)

      return

    return

  async def intro(self):
    if self.running:
          self.mitmproxy_server.stop()

    else:
          try:
            self.mitmproxy_server.start()
            await self.mitmproxy_server.stopped.wait()
          except:
            self.running = False
            self.mitmproxy_server.stop()
  
  async def main(self):
    cls()
    proxy_toggle(enable=True)
    await self.checks()
    await self.intro()
    try:
      await self.menu()
    except KeyboardInterrupt:
      await self.menu()

  async def run(self):
    try:
      await self.main()
    except KeyboardInterrupt:
      exit()

  @staticmethod
  async def new():
    cls = RaidFN()
    await cls.__async_init__()
    return cls


if __name__ == "__main__":

  async def main():
    try:
      app = await RaidFN.new()
      await app.run()
    except:
      print(traceback.format_exc())

  asyncio.run(main())
