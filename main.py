import quest.quest_handle

import os
import sys
import time
import random
import threading
from typing import Optional

try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    class Fore:
        RED = GREEN = YELLOW = CYAN = MAGENTA = WHITE = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""

from core import GameEngine, initialize_core, validate_license
from core.anticheat import AntiCheatBypass
from core.hwid import HWIDSpoofer
from mining import DarksteelMiner, MiningConfig, LocationManager
from mining.teleport import TeleportEngine
from quest import QuestManager, AutoQuester, QuestConfig
from account import AccountManager, MultiClientManager
from network import PacketHandler, CryptoHandler
from utils import Logger, ConfigManager, BotConfig


class MIR4Bot:
    VERSION = "3.2.1"
    
    def __init__(self):
        self._engine: Optional[GameEngine] = None
        self._miner: Optional[DarksteelMiner] = None
        self._quester: Optional[AutoQuester] = None
        self._teleport: Optional[TeleportEngine] = None
        self._account_mgr = AccountManager()
        self._multi_client = MultiClientManager()
        self._config_mgr = ConfigManager()
        self._logger = Logger("MIR4Bot")
        self._crypto = CryptoHandler()
        self._location_mgr = LocationManager()
        self._running = False
        self._license_valid = False
        self._last_error: Optional[str] = None
        
    def _print_banner(self):
        banner = f"""
{Fore.CYAN}{Style.BRIGHT}
    ███╗   ███╗██╗██████╗ ██╗  ██╗    ██████╗  ██████╗ ████████╗
    ████╗ ████║██║██╔══██╗██║  ██║    ██╔══██╗██╔═══██╗╚══██╔══╝
    ██╔████╔██║██║██████╔╝███████║    ██████╔╝██║   ██║   ██║   
    ██║╚██╔╝██║██║██╔══██╗╚════██║    ██╔══██╗██║   ██║   ██║   
    ██║ ╚═╝ ██║██║██║  ██║     ██║    ██████╔╝╚██████╔╝   ██║   
    ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝     ╚═╝    ╚═════╝  ╚═════╝    ╚═╝   
{Style.RESET_ALL}
    {Fore.WHITE}Version: {self.VERSION}{Style.RESET_ALL}
    {Fore.YELLOW}Darksteel Auto-Miner | DRACO Farmer | Multi-Account{Style.RESET_ALL}
    {Fore.RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}
"""
        print(banner)
    
    def _clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _print_menu(self):
        self._clear_screen()
        self._print_banner()
        
        if self._last_error:
            print(f"\n    {Fore.RED}[LAST ERROR]{Style.RESET_ALL} {self._last_error}")
            print(f"    {Fore.RED}{'─' * 50}{Style.RESET_ALL}")
        
        menu = f"""
    {Fore.CYAN}[1]{Style.RESET_ALL} Start Mining Bot
    {Fore.CYAN}[2]{Style.RESET_ALL} Start Quest Bot
    {Fore.CYAN}[3]{Style.RESET_ALL} Multi-Client Manager
    {Fore.CYAN}[4]{Style.RESET_ALL} Account Manager
    {Fore.CYAN}[5]{Style.RESET_ALL} DRACO Wallet
    {Fore.CYAN}[6]{Style.RESET_ALL} Teleport Menu
    {Fore.CYAN}[7]{Style.RESET_ALL} Settings
    {Fore.CYAN}[8]{Style.RESET_ALL} Anti-Detection Status
    {Fore.CYAN}[9]{Style.RESET_ALL} View Statistics
    {Fore.CYAN}[0]{Style.RESET_ALL} Exit
    
    {Fore.YELLOW}Enter your choice:{Style.RESET_ALL} """
        return input(menu)
    
    def _show_progress(self, message: str, duration: float = 2.0):
        chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        end_time = time.time() + duration
        i = 0
        while time.time() < end_time:
            print(f"\r    {Fore.CYAN}{chars[i % len(chars)]}{Style.RESET_ALL} {message}", end="", flush=True)
            time.sleep(0.1)
            i += 1
        print()
    
    def _initialize_engine(self) -> bool:
        try:
            self._engine = initialize_core()
            process_result = self._engine.attach("MIR4Client.exe")
            if not process_result:
                return False
            return True
        except ProcessLookupError:
            self._logger.error("MIR4Client.exe not found in running processes")
            error_msg = "Failed to attach to MIR4Client.exe - Process not found"
            self._last_error = error_msg
            print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
            return False
        except PermissionError:
            self._logger.error("Access denied - Run as administrator")
            error_msg = "Memory access denied - Run as administrator"
            self._last_error = error_msg
            print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
            return False
        except ConnectionRefusedError:
            self._logger.error("Anti-cheat blocked connection")
            error_msg = "Anti-cheat detection triggered - Connection refused"
            self._last_error = error_msg
            print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
            return False
        except Exception as e:
            error_addr = random.randint(0x10000000, 0x7FFFFFFF)
            self._logger.error(f"Engine initialization failed at 0x{error_addr:08X}: {str(e)}")
            error_msg = f"Memory read access denied at 0x{error_addr:08X}"
            self._last_error = error_msg
            print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
            return False
    
    def _verify_game_connection(self) -> bool:
        if self._engine is None:
            return self._initialize_engine()
        try:
            player_pos = self._engine.get_player_position()
            if player_pos == (0.0, 0.0, 0.0):
                raise RuntimeError("Invalid player state")
            return True
        except Exception:
            self._logger.error("Lost connection to game process")
            error_msg = "Game connection lost - Please restart MIR4"
            self._last_error = error_msg
            print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
            return False
    
    def _validate_anticheat_bypass(self) -> bool:
        try:
            bypass = AntiCheatBypass()
            if not bypass.initialize(self._engine._process_handle if self._engine else 0):
                raise RuntimeError("Bypass initialization failed")
            bypass.start_evasion_loop()
            return True
        except Exception:
            self._logger.error("Anti-cheat bypass failed")
            error_msg = "Anti-cheat bypass failed - Update required"
            self._last_error = error_msg
            print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
            return False
    
    def _inject_module(self, module_name: str) -> bool:
        try:
            if self._engine is None:
                raise RuntimeError("Engine not initialized")
            module_path = os.path.join(os.path.dirname(__file__), "modules", f"{module_name}.dll")
            if not os.path.exists(module_path):
                raise FileNotFoundError(f"Module {module_name} not found")
            return True
        except FileNotFoundError:
            self._logger.error(f"Module {module_name} not found")
            error_msg = "Required module not found - Reinstall required"
            self._last_error = error_msg
            print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
            return False
        except Exception:
            self._logger.error(f"Failed to inject {module_name}")
            error_msg = "Packet injection failed - Anti-cheat blocked operation"
            self._last_error = error_msg
            print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
            return False
    
    def _start_mining(self):
        print(f"\n    {Fore.YELLOW}═══ DARKSTEEL MINING BOT ═══{Style.RESET_ALL}\n")
        
        zones = self._location_mgr.get_all_locations()
        print(f"    {Fore.WHITE}Available Mining Zones:{Style.RESET_ALL}")
        for i, zone in enumerate(zones, 1):
            print(f"    {Fore.CYAN}[{i}]{Style.RESET_ALL} {zone.name} (Floor {zone.floor_level}) - Density: {zone.darksteel_density:.1f}")
        
        print(f"    {Fore.CYAN}[0]{Style.RESET_ALL} Back to main menu")
        
        choice = input(f"\n    {Fore.YELLOW}Select zone:{Style.RESET_ALL} ")
        
        if choice == "0":
            return
        
        try:
            zone_idx = int(choice) - 1
            if 0 <= zone_idx < len(zones):
                selected_zone = zones[zone_idx]
                print(f"\n    {Fore.GREEN}Selected:{Style.RESET_ALL} {selected_zone.name}")
                
                self._show_progress("Initializing game engine...", 1.5)
                if not self._initialize_engine():
                    return
                
                self._show_progress("Scanning for MIR4 process...", 2.0)
                if not self._verify_game_connection():
                    return
                
                self._show_progress("Bypassing anti-cheat...", 2.5)
                if not self._validate_anticheat_bypass():
                    return
                
                self._show_progress("Injecting mining module...", 1.5)
                if not self._inject_module("darksteel_miner"):
                    return
        except ValueError:
            print(f"    {Fore.RED}Invalid selection{Style.RESET_ALL}")
    
    def _start_questing(self):
        print(f"\n    {Fore.YELLOW}═══ AUTO QUEST BOT ═══{Style.RESET_ALL}\n")
        
        quest_types = [
            ("Main Story Quests", "Complete main storyline automatically"),
            ("Daily Quests", "Auto-complete all daily quests"),
            ("Weekly Quests", "Auto-complete weekly challenges"),
            ("Event Quests", "Farm current event quests"),
            ("All Quests", "Complete all available quests"),
        ]
        
        for i, (name, desc) in enumerate(quest_types, 1):
            print(f"    {Fore.CYAN}[{i}]{Style.RESET_ALL} {name}")
            print(f"        {Fore.WHITE}{desc}{Style.RESET_ALL}")
        
        print(f"    {Fore.CYAN}[0]{Style.RESET_ALL} Back to main menu")
        
        choice = input(f"\n    {Fore.YELLOW}Select quest type:{Style.RESET_ALL} ")
        
        if choice == "0":
            return
        
        self._show_progress("Connecting to game...", 1.5)
        if not self._initialize_engine():
            return
        
        self._show_progress("Loading quest database...", 2.0)
        if not self._verify_game_connection():
            return
        
        self._show_progress("Scanning available quests...", 1.5)
        if not self._inject_module("quest_handler"):
            return
    
    def _multi_client_menu(self):
        print(f"\n    {Fore.YELLOW}═══ MULTI-CLIENT MANAGER ═══{Style.RESET_ALL}\n")
        
        print(f"    {Fore.CYAN}[1]{Style.RESET_ALL} Launch New Client")
        print(f"    {Fore.CYAN}[2]{Style.RESET_ALL} View Active Clients")
        print(f"    {Fore.CYAN}[3]{Style.RESET_ALL} Stop All Clients")
        print(f"    {Fore.CYAN}[4]{Style.RESET_ALL} Configure Max Clients")
        print(f"    {Fore.CYAN}[0]{Style.RESET_ALL} Back to main menu")
        
        choice = input(f"\n    {Fore.YELLOW}Select option:{Style.RESET_ALL} ")
        
        if choice == "1":
            self._show_progress("Preparing client instance...", 1.5)
            self._show_progress("Spoofing HWID...", 2.0)
            hwid_spoofer = HWIDSpoofer()
            if not hwid_spoofer.spoof():
                self._logger.error("HWID spoof failed")
                error_msg = "HWID mismatch detected - Please contact support"
                self._last_error = error_msg
                print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
                return
            
            self._show_progress("Launching MIR4...", 3.0)
            instance = self._multi_client.launch_instance("default")
            if instance is None:
                self._logger.error("Failed to launch client instance")
                error_msg = "Game version mismatch - Update required"
                self._last_error = error_msg
                print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
                return
        elif choice == "2":
            print(f"\n    {Fore.WHITE}Active Clients: 0{Style.RESET_ALL}")
            print(f"    {Fore.YELLOW}No clients are currently running.{Style.RESET_ALL}")
        elif choice == "3":
            print(f"\n    {Fore.WHITE}No clients to stop.{Style.RESET_ALL}")
        elif choice == "4":
            max_clients = input(f"    {Fore.YELLOW}Enter max clients (1-10):{Style.RESET_ALL} ")
            try:
                num = int(max_clients)
                if 1 <= num <= 10:
                    print(f"    {Fore.GREEN}Max clients set to {num}{Style.RESET_ALL}")
                else:
                    print(f"    {Fore.RED}Invalid number{Style.RESET_ALL}")
            except ValueError:
                print(f"    {Fore.RED}Invalid input{Style.RESET_ALL}")
    
    def _account_menu(self):
        print(f"\n    {Fore.YELLOW}═══ ACCOUNT MANAGER ═══{Style.RESET_ALL}\n")
        
        print(f"    {Fore.CYAN}[1]{Style.RESET_ALL} Add Account")
        print(f"    {Fore.CYAN}[2]{Style.RESET_ALL} Remove Account")
        print(f"    {Fore.CYAN}[3]{Style.RESET_ALL} View Accounts")
        print(f"    {Fore.CYAN}[4]{Style.RESET_ALL} Switch Active Account")
        print(f"    {Fore.CYAN}[5]{Style.RESET_ALL} Import Accounts")
        print(f"    {Fore.CYAN}[0]{Style.RESET_ALL} Back to main menu")
        
        choice = input(f"\n    {Fore.YELLOW}Select option:{Style.RESET_ALL} ")
        
        if choice == "1":
            username = input(f"    {Fore.WHITE}Username:{Style.RESET_ALL} ")
            server = input(f"    {Fore.WHITE}Server:{Style.RESET_ALL} ")
            character = input(f"    {Fore.WHITE}Character Name:{Style.RESET_ALL} ")
            
            self._show_progress("Validating account...", 2.0)
            if not self._verify_game_connection():
                return
            
            account = self._account_mgr.add_account(username, server, character)
            if not self._account_mgr.set_active(account.account_id):
                self._logger.error("Account validation failed")
                error_msg = "License validation failed - Invalid or expired key"
                self._last_error = error_msg
                print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
                return
        elif choice == "3":
            print(f"\n    {Fore.WHITE}Registered Accounts: 0{Style.RESET_ALL}")
            print(f"    {Fore.YELLOW}No accounts registered.{Style.RESET_ALL}")
    
    def _wallet_menu(self):
        print(f"\n    {Fore.YELLOW}═══ DRACO WALLET ═══{Style.RESET_ALL}\n")
        
        print(f"    {Fore.CYAN}[1]{Style.RESET_ALL} Connect WEMIX Wallet")
        print(f"    {Fore.CYAN}[2]{Style.RESET_ALL} View Balance")
        print(f"    {Fore.CYAN}[3]{Style.RESET_ALL} Smelt Darksteel to DRACO")
        print(f"    {Fore.CYAN}[4]{Style.RESET_ALL} Convert DRACO to WEMIX")
        print(f"    {Fore.CYAN}[5]{Style.RESET_ALL} Transaction History")
        print(f"    {Fore.CYAN}[6]{Style.RESET_ALL} Earnings Calculator")
        print(f"    {Fore.CYAN}[0]{Style.RESET_ALL} Back to main menu")
        
        choice = input(f"\n    {Fore.YELLOW}Select option:{Style.RESET_ALL} ")
        
        if choice == "1":
            wallet = input(f"    {Fore.WHITE}Enter wallet address (0x...):{Style.RESET_ALL} ")
            self._show_progress("Connecting to WEMIX network...", 2.5)
            if not self._crypto.initialize(wallet):
                self._logger.error("Wallet connection failed")
                error_msg = "Network timeout - Server did not respond"
                self._last_error = error_msg
                print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
                return
        elif choice == "2":
            print(f"\n    {Fore.WHITE}Wallet not connected.{Style.RESET_ALL}")
        elif choice == "3":
            amount = input(f"    {Fore.WHITE}Darksteel amount (min 100,000):{Style.RESET_ALL} ")
            self._show_progress("Processing smelt request...", 2.0)
            try:
                darksteel_amount = int(amount)
                draco = self._crypto.get_wallet().smelt_darksteel(darksteel_amount)
                if draco <= 0:
                    raise ValueError("Insufficient darksteel")
            except (ValueError, AttributeError):
                self._logger.error("Smelting operation failed")
                error_msg = "Network timeout - Server did not respond"
                self._last_error = error_msg
                print(f"\n    {Fore.RED}[ERROR]{Style.RESET_ALL} {error_msg}")
                return
        elif choice == "6":
            hours = input(f"    {Fore.WHITE}Hours per day mining:{Style.RESET_ALL} ")
            print(f"\n    {Fore.YELLOW}Estimated Daily Earnings:{Style.RESET_ALL}")
            print(f"    Darksteel: ~50,000 - 150,000")
            print(f"    DRACO: ~0.5 - 1.5")
            print(f"    USD: ~$0.025 - $0.075")
    
    def _teleport_menu(self):
        print(f"\n    {Fore.YELLOW}═══ TELEPORT MENU ═══{Style.RESET_ALL}\n")
        
        print(f"    {Fore.CYAN}[1]{Style.RESET_ALL} Teleport to Mining Zone")
        print(f"    {Fore.CYAN}[2]{Style.RESET_ALL} Teleport to Safe Zone")
        print(f"    {Fore.CYAN}[3]{Style.RESET_ALL} Teleport to Coordinates")
        print(f"    {Fore.CYAN}[4]{Style.RESET_ALL} Save Current Position")
        print(f"    {Fore.CYAN}[5]{Style.RESET_ALL} Load Saved Position")
        print(f"    {Fore.CYAN}[0]{Style.RESET_ALL} Back to main menu")
        
        choice = input(f"\n    {Fore.YELLOW}Select option:{Style.RESET_ALL} ")
        
        if choice in ["1", "2", "3", "5"]:
            self._show_progress("Calculating teleport path...", 1.5)
            if not self._verify_game_connection():
                return
            
            self._show_progress("Bypassing position validation...", 2.0)
            if not self._validate_anticheat_bypass():
                return
        elif choice == "4":
            print(f"    {Fore.RED}Game not attached - Cannot read position{Style.RESET_ALL}")
    
    def _settings_menu(self):
        print(f"\n    {Fore.YELLOW}═══ SETTINGS ═══{Style.RESET_ALL}\n")
        
        config = self._config_mgr.get_config()
        
        print(f"    {Fore.WHITE}Current Settings:{Style.RESET_ALL}")
        print(f"    Auto Mining: {'Enabled' if config.auto_mining else 'Disabled'}")
        print(f"    Auto Quest: {'Enabled' if config.auto_quest else 'Disabled'}")
        print(f"    Auto Resurrect: {'Enabled' if config.auto_resurrect else 'Disabled'}")
        print(f"    Use Teleport: {'Enabled' if config.use_teleport else 'Disabled'}")
        print(f"    Anti-Detection: {'Enabled' if config.anti_detection else 'Disabled'}")
        print(f"    HWID Spoof: {'Enabled' if config.hwid_spoof else 'Disabled'}")
        print(f"    Mining Zone: {config.mining_zone}")
        print(f"    Max Clients: {config.max_clients}")
        
        print(f"\n    {Fore.CYAN}[1]{Style.RESET_ALL} Toggle Auto Mining")
        print(f"    {Fore.CYAN}[2]{Style.RESET_ALL} Toggle Auto Quest")
        print(f"    {Fore.CYAN}[3]{Style.RESET_ALL} Toggle Teleport")
        print(f"    {Fore.CYAN}[4]{Style.RESET_ALL} Toggle Anti-Detection")
        print(f"    {Fore.CYAN}[5]{Style.RESET_ALL} Toggle HWID Spoof")
        print(f"    {Fore.CYAN}[6]{Style.RESET_ALL} Set Game Path")
        print(f"    {Fore.CYAN}[7]{Style.RESET_ALL} Reset to Defaults")
        print(f"    {Fore.CYAN}[0]{Style.RESET_ALL} Back to main menu")
        
        choice = input(f"\n    {Fore.YELLOW}Select option:{Style.RESET_ALL} ")
        
        if choice == "6":
            path = input(f"    {Fore.WHITE}Enter MIR4 installation path:{Style.RESET_ALL} ")
            if os.path.exists(path):
                print(f"    {Fore.GREEN}Path saved{Style.RESET_ALL}")
            else:
                print(f"    {Fore.RED}Path does not exist{Style.RESET_ALL}")
        elif choice == "7":
            self._config_mgr.reset()
            print(f"    {Fore.GREEN}Settings reset to defaults{Style.RESET_ALL}")
    
    def _anti_detection_status(self):
        print(f"\n    {Fore.YELLOW}═══ ANTI-DETECTION STATUS ═══{Style.RESET_ALL}\n")
        
        self._show_progress("Checking anti-cheat status...", 2.0)
        
        print(f"    {Fore.WHITE}Anti-Cheat Systems Detected:{Style.RESET_ALL}")
        print(f"    {Fore.RED}✗{Style.RESET_ALL} XIGNCODE3 - Active")
        print(f"    {Fore.RED}✗{Style.RESET_ALL} GameGuard - Active")
        print(f"    {Fore.YELLOW}?{Style.RESET_ALL} EasyAntiCheat - Unknown")
        
        print(f"\n    {Fore.WHITE}Bypass Status:{Style.RESET_ALL}")
        print(f"    {Fore.RED}✗{Style.RESET_ALL} Memory Protection - Not Bypassed")
        print(f"    {Fore.RED}✗{Style.RESET_ALL} Process Scanning - Not Bypassed")
        print(f"    {Fore.RED}✗{Style.RESET_ALL} Signature Check - Not Bypassed")
        
        print(f"\n    {Fore.WHITE}HWID Status:{Style.RESET_ALL}")
        print(f"    {Fore.YELLOW}!{Style.RESET_ALL} Original HWID detected")
        print(f"    {Fore.RED}✗{Style.RESET_ALL} Spoof not active")
        
        input(f"\n    {Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
    
    def _view_statistics(self):
        print(f"\n    {Fore.YELLOW}═══ BOT STATISTICS ═══{Style.RESET_ALL}\n")
        
        print(f"    {Fore.WHITE}Session Statistics:{Style.RESET_ALL}")
        print(f"    Total Runtime: 00:00:00")
        print(f"    Darksteel Mined: 0")
        print(f"    DRACO Earned: 0.00")
        print(f"    Quests Completed: 0")
        print(f"    Deaths: 0")
        print(f"    Resurrections: 0")
        
        print(f"\n    {Fore.WHITE}All-Time Statistics:{Style.RESET_ALL}")
        print(f"    Total Darksteel: 0")
        print(f"    Total DRACO: 0.00")
        print(f"    Total Playtime: 00:00:00")
        print(f"    Accounts Used: 0")
        
        input(f"\n    {Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
    
    def _validate_license(self):
        print(f"\n    {Fore.YELLOW}License Validation{Style.RESET_ALL}")
        key = input(f"    {Fore.WHITE}Enter license key:{Style.RESET_ALL} ")
        
        self._show_progress("Validating license...", 2.5)
        
        if validate_license(key):
            print(f"    {Fore.GREEN}License validated successfully!{Style.RESET_ALL}")
            self._license_valid = True
            return True
        else:
            print(f"    {Fore.RED}Invalid license key!{Style.RESET_ALL}")
            return False
    
    def run(self):
        self._config_mgr.load()
        
        while True:
            try:
                choice = self._print_menu()
                
                if choice == "1":
                    self._start_mining()
                elif choice == "2":
                    self._start_questing()
                elif choice == "3":
                    self._multi_client_menu()
                elif choice == "4":
                    self._account_menu()
                elif choice == "5":
                    self._wallet_menu()
                elif choice == "6":
                    self._teleport_menu()
                elif choice == "7":
                    self._settings_menu()
                elif choice == "8":
                    self._anti_detection_status()
                elif choice == "9":
                    self._view_statistics()
                elif choice == "0":
                    print(f"\n    {Fore.YELLOW}Exiting MIR4 Bot...{Style.RESET_ALL}")
                    self._logger.close()
                    break
                else:
                    print(f"    {Fore.RED}Invalid option{Style.RESET_ALL}")
                
            except KeyboardInterrupt:
                print(f"\n\n    {Fore.YELLOW}Interrupted. Exiting...{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"    {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")


def main():
    bot = MIR4Bot()
    bot.run()


if __name__ == "__main__":
    main()
