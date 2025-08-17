import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog, Listbox
import random
import json
import os

# --- Core Game Classes ---

class Entity:
    """Base class for player and enemies."""
    def __init__(self, name, hp, stamina, attack, defense):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.max_stamina = stamina
        self.stamina = stamina
        self.attack = attack
        self.defense = defense
        self.is_defending = False

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, damage):
        if self.is_defending:
            damage = max(0, damage // 2) # Halve damage if defending
            self.is_defending = False # Defense only lasts for one turn
        
        actual_damage = max(0, damage - self.defense)
        self.hp -= actual_damage
        if self.hp < 0:
            self.hp = 0
        return actual_damage

class Player(Entity):
    """Player character class."""
    def __init__(self, name, hp, stamina, attack, defense):
        super().__init__(name, hp, stamina, attack, defense)
        self.xp = 0
        self.level = 1
        self.inventory = []
        self.weapon = None
        self.armor = None
        self.location = "town"
        self.quests = {}
        self.max_mana = 30
        self.mana = 30
        self.spells = []

    def add_item(self, item):
        self.inventory.append(item)

    def remove_item(self, item):
        self.inventory.remove(item)

    def equip_item(self, item):
        # Unequip previous item and remove its stats before equipping the new one
        if isinstance(item, Weapon):
            if self.weapon:
                self.attack -= self.weapon.attack_bonus
            self.weapon = item
            self.attack += item.attack_bonus
        elif isinstance(item, Armor):
            if self.armor:
                self.defense -= self.armor.defense_bonus
            self.armor = item
            self.defense += item.defense_bonus

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.level * 100:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.xp = 0
        self.max_hp += 20
        self.hp = self.max_hp
        self.max_stamina += 10
        self.stamina = self.max_stamina
        self.max_mana += 10
        self.mana = self.max_mana
        self.attack += 5
        self.defense += 2
        game.log(f"*** You leveled up to level {self.level}! ***")

    def to_dict(self):
        """Serialize player data for saving."""
        return {
            'name': self.name, 'hp': self.hp, 'max_hp': self.max_hp,
            'stamina': self.stamina, 'max_stamina': self.max_stamina,
            'mana': self.mana, 'max_mana': self.max_mana,
            'attack': self.attack, 'defense': self.defense, 'xp': self.xp,
            'level': self.level, 'location': self.location,
            'inventory': [item.name for item in self.inventory],
            'weapon': self.weapon.name if self.weapon else None,
            'armor': self.armor.name if self.armor else None,
            'quests': {k: v.to_dict() for k, v in self.quests.items()},
            'spells': [spell.name for spell in self.spells]
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialize player data for loading."""
        # Base stats are recalculated based on equipment, so we pass 0 for attack/defense initially
        player = cls(data['name'], data['max_hp'], data['max_stamina'], 0, 0)
        player.hp = data['hp']
        player.stamina = data['stamina']
        player.mana = data['mana']
        player.max_mana = data['max_mana']
        player.xp = data['xp']
        player.level = data['level']
        player.location = data['location']
        
        # Restore base stats from level
        player.attack = 10 + (player.level * 5)
        player.defense = 3 + (player.level * 2)

        # Re-create and equip items from data
        inventory_items = [create_item_from_name(item_name) for item_name in data['inventory']]
        player.inventory = [item for item in inventory_items if item]
        
        if data['weapon']:
            weapon_to_equip = next((item for item in player.inventory if item.name == data['weapon']), None)
            if weapon_to_equip:
                player.equip_item(weapon_to_equip)
        if data['armor']:
            armor_to_equip = next((item for item in player.inventory if item.name == data['armor']), None)
            if armor_to_equip:
                player.equip_item(armor_to_equip)

        for spell_name in data['spells']:
            player.spells.append(create_spell_from_name(spell_name))
        for quest_name, quest_data in data['quests'].items():
            player.quests[quest_name] = Quest.from_dict(quest_data)
            
        return player


class Enemy(Entity):
    """Enemy character class."""
    def __init__(self, name, hp, stamina, attack, defense, xp_reward):
        super().__init__(name, hp, stamina, attack, defense)
        self.xp_reward = xp_reward

# --- Item, Equipment, and Spell Classes ---

class Item:
    """Base class for items."""
    def __init__(self, name, description):
        self.name = name
        self.description = description

class Potion(Item):
    """Potion item class."""
    def __init__(self, name, description, effect, amount):
        super().__init__(name, description)
        self.effect = effect
        self.amount = amount

class Weapon(Item):
    """Weapon item class."""
    def __init__(self, name, description, attack_bonus):
        super().__init__(name, description)
        self.attack_bonus = attack_bonus

class Armor(Item):
    """Armor item class."""
    def __init__(self, name, description, defense_bonus):
        super().__init__(name, description)
        self.defense_bonus = defense_bonus
        
class Spell:
    """Spell class."""
    def __init__(self, name, description, mana_cost, damage):
        self.name = name
        self.description = description
        self.mana_cost = mana_cost
        self.damage = damage

# --- Quest Class ---

class Quest:
    """Quest class with stages."""
    def __init__(self, name, description, stages, reward):
        self.name = name
        self.description = description
        self.stages = stages
        self.current_stage = 0
        self.reward = reward
        self.completed = False

    def get_current_stage_info(self):
        return self.stages[self.current_stage]

    def advance_stage(self):
        if self.current_stage < len(self.stages) - 1:
            self.current_stage += 1
            return False # Not completed yet
        else:
            self.completed = True
            return True # Quest completed

    def to_dict(self):
        return {'name': self.name, 'description': self.description, 'stages': self.stages, 'current_stage': self.current_stage, 'reward': self.reward, 'completed': self.completed}

    @classmethod
    def from_dict(cls, data):
        quest = cls(data['name'], data['description'], data['stages'], data['reward'])
        quest.current_stage = data['current_stage']
        quest.completed = data['completed']
        return quest


# --- Game World ---

world = {
    "town": {
        "name": "Eldoria Town",
        "description": "A peaceful town, a sanctuary from the dangers of the world.",
        "exits": {"north": "forest", "west": "swamp"},
        "npc": "Old Man"
    },
    "forest": {
        "name": "Whispering Forest",
        "description": "A dark and eerie forest. You find a small, moss-covered shrine.",
        "exits": {"south": "town", "east": "cave"},
        "enemies": ["Goblin", "Wolf"],
        "secret": "Found an Amulet"
    },
    "swamp": {
        "name": "Haunted Swamp",
        "description": "A murky swamp filled with fog. The air is heavy and cold.",
        "exits": {"east": "town", "north": "mountain_pass"},
        "enemies": ["Banshee", "Giant Spider"],
        "npc": "Witch"
    },
    "cave": {
        "name": "Shadowy Cave",
        "description": "A damp and cold cave. Something dangerous lurks here.",
        "exits": {"west": "forest", "north": "boss_room"},
        "enemies": ["Troll", "Stone Golem"]
    },
    "mountain_pass": {
        "name": "Frozen Mountain Pass",
        "description": "A treacherous path through snowy mountains.",
        "exits": {"south": "swamp", "east": "castle_ruins"},
        "enemies": ["Wolf", "Stone Golem"]
    },
    "castle_ruins": {
        "name": "Ruins of Castle Varden",
        "description": "The crumbling remains of a once-mighty fortress.",
        "exits": {"west": "mountain_pass"},
        "enemies": ["Cursed Knight", "Troll"]
    },
    "boss_room": {
        "name": "Dragon's Lair",
        "description": "A massive cavern with a fearsome dragon.",
        "exits": {},
        "enemies": ["Dragon"]
    }
}

# --- Game Data ---

enemies = {
    "Goblin": {"hp": 30, "stamina": 20, "attack": 10, "defense": 5, "xp_reward": 25},
    "Wolf": {"hp": 40, "stamina": 30, "attack": 15, "defense": 3, "xp_reward": 35},
    "Banshee": {"hp": 50, "stamina": 60, "attack": 22, "defense": 6, "xp_reward": 70},
    "Troll": {"hp": 80, "stamina": 50, "attack": 25, "defense": 10, "xp_reward": 100},
    "Giant Spider": {"hp": 60, "stamina": 40, "attack": 20, "defense": 8, "xp_reward": 80},
    "Stone Golem": {"hp": 100, "stamina": 30, "attack": 20, "defense": 18, "xp_reward": 120},
    "Cursed Knight": {"hp": 90, "stamina": 70, "attack": 30, "defense": 15, "xp_reward": 150},
    "Dragon": {"hp": 250, "stamina": 100, "attack": 40, "defense": 20, "xp_reward": 500}
}

items = {
    "Health Potion": {"class": Potion, "args": {"description": "Restores 50 HP.", "effect": "heal", "amount": 50}},
    "Stamina Potion": {"class": Potion, "args": {"description": "Restores 40 Stamina.", "effect": "stamina", "amount": 40}},
    "Iron Sword": {"class": Weapon, "args": {"description": "A basic sword.", "attack_bonus": 10}},
    "Greatsword": {"class": Weapon, "args": {"description": "A heavy two-handed sword.", "attack_bonus": 18}},
    "Leather Armor": {"class": Armor, "args": {"description": "Simple leather armor.", "defense_bonus": 5}},
    "Steel Armor": {"class": Armor, "args": {"description": "Sturdy steel plate armor.", "defense_bonus": 12}},
    "Amulet of the Forest": {"class": Item, "args": {"description": "A quest item."}}
}

spells = {
    "Fireball": {"description": "Hurls a ball of fire.", "mana_cost": 15, "damage": 30},
    "Heal": {"description": "A minor healing spell.", "mana_cost": 20, "damage": -40} # Negative damage for healing
}

npcs = {
    "Old Man": {
        "dialogue": {
            0: "Welcome, traveler. The world is in peril. A fearsome dragon has appeared in the nearby cave. But first, I need you to find my lost amulet. I think I dropped it in the Whispering Forest.",
            1: "Thank you for finding my amulet! Now, please, defeat the dragon and bring peace back to our lands."
        },
        "quest": {
            "name": "Slay the Dragon",
            "description": "Help the Old Man and save the town.",
            "stages": [
                {"type": "find_item", "item": "Amulet of the Forest", "location": "forest", "target_description": "Find the Old Man's amulet."},
                {"type": "kill_enemy", "enemy": "Dragon", "location": "boss_room", "target_description": "Slay the Dragon."}
            ],
            "reward": "You saved the town! The Old Man gives you a Greatsword."
        }
    },
    "Witch": {
        "dialogue": {
            0: "What do you want, stranger? This swamp is no place for you... unless you can help me. A Cursed Knight in the castle ruins to the east stole my spellbook. Bring it back, and I shall reward you with knowledge.",
            1: "You have my spellbook! As promised, I will teach you a powerful spell."
        },
        "quest": {
            "name": "The Stolen Spellbook",
            "description": "Retrieve the Witch's spellbook.",
            "stages": [
                {"type": "kill_enemy", "enemy": "Cursed Knight", "location": "castle_ruins", "target_description": "Defeat the Cursed Knight to get the spellbook."}
            ],
            "reward": "The Witch teaches you the Fireball spell."
        }
    }
}

# --- Helper Functions ---
def create_item_from_name(name):
    if name in items:
        item_data = items[name]
        return item_data["class"](name, **item_data["args"])
    return None

def create_spell_from_name(name):
    if name in spells:
        return Spell(name, **spells[name])
    return None

# --- Main Game Application ---

class Game(tk.Tk):
    SAVE_FILE = "rpg_save.json"

    def __init__(self):
        super().__init__()
        self.title("Souls-Like RPG - Expanded Edition")
        self.geometry("800x600")

        self.player = None
        self.current_enemy = None

        self.create_widgets()
        self.show_start_menu()

    def create_widgets(self):
        self.text_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, state='disabled', bg='black', fg='lightgray', font=("Courier", 10))
        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.button_frame = tk.Frame(self, bg='black')
        self.button_frame.pack(padx=10, pady=10, fill=tk.X)

        self.stats_frame = tk.Frame(self, bg='black')
        self.stats_frame.pack(padx=10, pady=10, fill=tk.X)
        self.stats_label = tk.Label(self.stats_frame, text="", bg='black', fg='white', font=("Courier", 10))
        self.stats_label.pack()

    def log(self, message):
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, message + "\n")
        self.text_area.config(state='disabled')
        self.text_area.yview(tk.END)

    def update_stats(self):
        if not self.player: return
        stats = (f"HP: {self.player.hp}/{self.player.max_hp} | "
                 f"MP: {self.player.mana}/{self.player.max_mana} | "
                 f"Stamina: {self.player.stamina}/{self.player.max_stamina} | "
                 f"Level: {self.player.level} | XP: {self.player.xp}/{self.player.level*100}")
        self.stats_label.config(text=stats)
        
    def show_start_menu(self):
        self.clear_buttons()
        self.log("Welcome to the Souls-Like RPG!")
        tk.Button(self.button_frame, text="New Game", command=self.new_game).pack(side=tk.LEFT, padx=5)
        if os.path.exists(self.SAVE_FILE):
            tk.Button(self.button_frame, text="Load Game", command=self.load_game).pack(side=tk.LEFT, padx=5)

    def new_game(self):
        self.player = Player("Hero", 100, 50, 15, 5)
        self.player.add_item(create_item_from_name("Health Potion"))
        self.player.equip_item(create_item_from_name("Iron Sword"))
        self.player.equip_item(create_item_from_name("Leather Armor"))
        self.player.spells.append(create_spell_from_name("Heal"))
        self.log("\nA new journey begins...")
        self.show_location()

    def save_game(self):
        if not self.player: return
        with open(self.SAVE_FILE, 'w') as f:
            json.dump(self.player.to_dict(), f, indent=4)
        self.log("\nGame saved.")
        messagebox.showinfo("Save Game", "Your progress has been saved.")

    def load_game(self):
        if os.path.exists(self.SAVE_FILE):
            with open(self.SAVE_FILE, 'r') as f:
                player_data = json.load(f)
                self.player = Player.from_dict(player_data)
            self.log("\nGame loaded. Welcome back.")
            self.show_location()
        else:
            self.log("No save file found.")

    def show_location(self):
        self.update_stats()
        location_data = world[self.player.location]
        self.log(f"\n--- {location_data['name']} ---")
        self.log(location_data['description'])
        
        self.create_location_buttons()

        if "enemies" in location_data and random.random() < 0.6:
            self.start_combat(random.choice(location_data['enemies']))

    def create_location_buttons(self):
        self.clear_buttons()
        location_data = world[self.player.location]
        
        # Movement buttons
        for direction, destination in location_data['exits'].items():
            tk.Button(self.button_frame, text=f"Go {direction.capitalize()}", command=lambda d=destination: self.move_player(d)).pack(side=tk.LEFT, padx=5)
            
        # NPC button
        if "npc" in location_data:
            tk.Button(self.button_frame, text=f"Talk to {location_data['npc']}", command=lambda n=location_data['npc']: self.talk_to_npc(n)).pack(side=tk.LEFT, padx=5)
        
        # Secret/Search button
        if "secret" in location_data:
            tk.Button(self.button_frame, text="Search Area", command=self.search_area).pack(side=tk.LEFT, padx=5)
            
        # System buttons
        tk.Button(self.button_frame, text="Inventory", command=self.open_inventory_screen).pack(side=tk.RIGHT, padx=5)
        tk.Button(self.button_frame, text="Save Game", command=self.save_game).pack(side=tk.RIGHT, padx=5)

    def open_inventory_screen(self):
        inv_win = tk.Toplevel(self)
        inv_win.title("Inventory")
        inv_win.geometry("400x300")

        # Left side: List of items
        list_frame = tk.Frame(inv_win)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        inv_listbox = Listbox(list_frame)
        inv_listbox.pack(fill=tk.BOTH, expand=True)
        for item in self.player.inventory:
            # Add markers for equipped items
            marker = ""
            if self.player.weapon == item:
                marker = " (W)"
            elif self.player.armor == item:
                marker = " (A)"
            inv_listbox.insert(tk.END, item.name + marker)

        # Right side: Item details and actions
        details_frame = tk.Frame(inv_win)
        details_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        desc_label = tk.Label(details_frame, text="Select an item", wraplength=150, justify=tk.LEFT)
        desc_label.pack(pady=5)

        action_frame = tk.Frame(details_frame)
        action_frame.pack(pady=10)

        def on_item_select(event):
            selected_indices = inv_listbox.curselection()
            if not selected_indices:
                return

            # Clear previous buttons
            for widget in action_frame.winfo_children():
                widget.destroy()

            selected_item_name = inv_listbox.get(selected_indices[0]).split(" (")[0]
            selected_item = next((item for item in self.player.inventory if item.name == selected_item_name), None)

            if not selected_item:
                return

            desc_label.config(text=selected_item.description)

            # Define actions based on item type
            if isinstance(selected_item, (Weapon, Armor)):
                tk.Button(action_frame, text="Equip", command=lambda: equip_action(selected_item)).pack(fill=tk.X)
            if isinstance(selected_item, Potion):
                tk.Button(action_frame, text="Use", command=lambda: use_action(selected_item)).pack(fill=tk.X)
            tk.Button(action_frame, text="Drop", command=lambda: drop_action(selected_item)).pack(fill=tk.X)

        def equip_action(item):
            self.player.equip_item(item)
            self.log(f"You equipped the {item.name}.")
            self.update_stats()
            inv_win.destroy()

        def use_action(item):
            if item.effect == "heal":
                self.player.hp = min(self.player.max_hp, self.player.hp + item.amount)
                self.log(f"You used a {item.name} and healed for {item.amount} HP.")
            elif item.effect == "stamina":
                self.player.stamina = min(self.player.max_stamina, self.player.stamina + item.amount)
                self.log(f"You used a {item.name} and restored {item.amount} stamina.")
            self.player.remove_item(item)
            self.update_stats()
            inv_win.destroy()

        def drop_action(item):
            # Unequip if it's the currently equipped item
            if self.player.weapon == item:
                self.player.attack -= item.attack_bonus
                self.player.weapon = None
            if self.player.armor == item:
                self.player.defense -= item.defense_bonus
                self.player.armor = None
            
            self.player.remove_item(item)
            self.log(f"You dropped the {item.name}.")
            self.update_stats()
            inv_win.destroy()

        inv_listbox.bind('<<ListboxSelect>>', on_item_select)

    def move_player(self, destination):
        self.player.location = destination
        self.show_location()

    def search_area(self):
        location_data = world[self.player.location]
        secret = location_data.get("secret")
        if secret == "Found an Amulet":
            amulet = create_item_from_name("Amulet of the Forest")
            if not any(isinstance(item, Item) and item.name == amulet.name for item in self.player.inventory):
                self.player.add_item(amulet)
                self.log(f"You search the area and find the {amulet.name}!")
                self.check_quest_progress()
            else:
                self.log("You find nothing of interest.")

    def talk_to_npc(self, npc_name):
        npc_data = npcs[npc_name]
        quest_name = npc_data['quest']['name']

        # Assign quest if player doesn't have it
        if quest_name not in self.player.quests:
            quest_info = npc_data['quest']
            self.player.quests[quest_name] = Quest(quest_info['name'], quest_info['description'], quest_info['stages'], quest_info['reward'])
            self.log(f"\nNew quest: {quest_info['name']} - {quest_info['description']}")
        
        # Get current dialogue
        quest = self.player.quests[quest_name]
        dialogue = npc_data['dialogue'].get(quest.current_stage, "...")
        self.log(f"\n{npc_name}: {dialogue}")
        self.log(f"Current Objective: {quest.get_current_stage_info()['target_description']}")

    def start_combat(self, enemy_name):
        enemy_data = enemies[enemy_name]
        self.current_enemy = Enemy(enemy_name, **enemy_data)
        self.log(f"\nA wild {self.current_enemy.name} appears!")
        self.create_combat_buttons()

    def create_combat_buttons(self):
        self.clear_buttons()
        tk.Button(self.button_frame, text="Attack", command=lambda: self.perform_action("Attack")).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Defend", command=lambda: self.perform_action("Defend")).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Magic", command=lambda: self.perform_action("Magic")).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Use Item", command=lambda: self.perform_action("Use Item")).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Flee", command=lambda: self.perform_action("Flee")).pack(side=tk.LEFT, padx=5)

    def perform_action(self, action):
        if not self.current_enemy or not self.current_enemy.is_alive():
            return

        player_turn_ended = True
        if action == "Attack":
            self.player_attack()
        elif action == "Defend":
            self.player_defend()
        elif action == "Magic":
            player_turn_ended = self.show_spell_selection()
        elif action == "Use Item":
            player_turn_ended = self.show_item_selection()
        elif action == "Flee":
            self.flee()
            player_turn_ended = False # Fleeing ends combat immediately

        if player_turn_ended and self.current_enemy and self.current_enemy.is_alive():
            self.enemy_turn()

        self.update_stats()

    def player_attack(self):
        damage_done = self.current_enemy.take_damage(self.player.attack)
        self.log(f"You attack the {self.current_enemy.name} for {damage_done} damage.")
        if not self.current_enemy.is_alive():
            self.win_combat()

    def player_defend(self):
        self.player.is_defending = True
        self.log("You brace for the next attack, reducing incoming damage.")

    def show_spell_selection(self):
        spell_window = tk.Toplevel(self)
        spell_window.title("Cast a Spell")
        for spell in self.player.spells:
            btn = tk.Button(spell_window, text=f"{spell.name} ({spell.mana_cost} MP)", 
                            command=lambda s=spell: self.cast_spell(s, spell_window))
            btn.pack(pady=5, padx=10)
        return False # Turn doesn't end until a spell is cast or window is closed

    def cast_spell(self, spell, window):
        window.destroy()
        if self.player.mana >= spell.mana_cost:
            self.player.mana -= spell.mana_cost
            if spell.damage > 0: # Damage spell
                damage_done = self.current_enemy.take_damage(spell.damage)
                self.log(f"You cast {spell.name}, dealing {damage_done} damage!")
                if not self.current_enemy.is_alive():
                    self.win_combat()
            else: # Healing spell
                heal_amount = -spell.damage
                self.player.hp = min(self.player.max_hp, self.player.hp + heal_amount)
                self.log(f"You cast {spell.name}, healing for {heal_amount} HP.")
            
            if self.current_enemy and self.current_enemy.is_alive():
                self.enemy_turn()
            self.update_stats()
        else:
            self.log("Not enough mana!")

    def show_item_selection(self):
        potions = [item for item in self.player.inventory if isinstance(item, Potion)]
        if not potions:
            self.log("You have no potions to use.")
            return False
            
        item_window = tk.Toplevel(self)
        item_window.title("Use an Item")
        for item in potions:
            btn = tk.Button(item_window, text=f"{item.name}", 
                            command=lambda i=item: self.use_potion(i, item_window))
            btn.pack(pady=5, padx=10)
        return False # Turn doesn't end until item is used

    def use_potion(self, potion, window):
        window.destroy()
        if potion.effect == "heal":
            self.player.hp = min(self.player.max_hp, self.player.hp + potion.amount)
            self.log(f"You used a {potion.name} and healed for {potion.amount} HP.")
        elif potion.effect == "stamina":
            self.player.stamina = min(self.player.max_stamina, self.player.stamina + potion.amount)
            self.log(f"You used a {potion.name} and restored {potion.amount} stamina.")
        
        self.player.remove_item(potion)
        
        if self.current_enemy and self.current_enemy.is_alive():
            self.enemy_turn()
        self.update_stats()

    def flee(self):
        if random.random() < 0.5:
            self.log("You successfully fled the battle.")
            self.current_enemy = None
            self.show_location()
        else:
            self.log("You failed to flee!")
            self.enemy_turn()

    def enemy_turn(self):
        damage_done = self.player.take_damage(self.current_enemy.attack)
        self.log(f"The {self.current_enemy.name} attacks you for {damage_done} damage.")
        if not self.player.is_alive():
            self.game_over()

    def win_combat(self):
        self.log(f"You defeated the {self.current_enemy.name}!")
        self.player.gain_xp(self.current_enemy.xp_reward)
        self.check_quest_progress(defeated_enemy=self.current_enemy.name)
        self.current_enemy = None
        self.show_location()

    def check_quest_progress(self, defeated_enemy=None):
        for name, quest in self.player.quests.items():
            if quest.completed: continue
            
            stage = quest.get_current_stage_info()
            progress = False
            if stage['type'] == 'kill_enemy' and stage['enemy'] == defeated_enemy:
                progress = True
            elif stage['type'] == 'find_item' and any(item.name == stage['item'] for item in self.player.inventory):
                progress = True

            if progress:
                self.log(f"Quest Progress: '{quest.name}'")
                if quest.advance_stage():
                    self.complete_quest(quest)

    def complete_quest(self, quest):
        self.log(f"*** Quest Completed: {quest.name} ***")
        self.log(quest.reward)
        
        # Grant specific rewards
        if quest.name == "Slay the Dragon":
            self.player.add_item(create_item_from_name("Greatsword"))
        elif quest.name == "The Stolen Spellbook":
            self.player.spells.append(create_spell_from_name("Fireball"))

    def game_over(self):
        self.log("\nYou have been defeated. Game Over.")
        messagebox.showinfo("Game Over", "You have been defeated.")
        self.destroy()

    def clear_buttons(self):
        for widget in self.button_frame.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    game = Game()
    game.mainloop()
