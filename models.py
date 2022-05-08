from sqlalchemy import Column, Integer, VARCHAR, SmallInteger, Float, ForeignKey, TIMESTAMP, text, BINARY, Boolean
from database import Base


class Abilities(Base):
    __tablename__ = "abilities"

    id = Column(Integer, nullable=False, primary_key=True)
    name = Column(VARCHAR)


class Ability_upgrades(Base):
    __tablename__ = "ability_upgrades"

    id = Column(Integer, nullable=False, primary_key=True)
    ability_id = Column(Integer, ForeignKey("abilities.id"))
    match_player_detail_id = Column(Integer, ForeignKey("matches_players_details.id"))
    level = Column(Integer)
    time = Column(Integer)


class Game_objectives(Base):
    __tablename__ = "game_objectives"

    id = Column(Integer, primary_key=True)
    match_player_detail_id_1 = Column(Integer, ForeignKey("matches_players_details.id"))
    match_player_detail_id_2 = Column(Integer, ForeignKey("matches_players_details.id"))
    key = Column(Integer)
    subtype = Column(VARCHAR)
    team = Column(Integer)
    time = Column(Integer)
    value = Column(Integer)
    slot = Column(Integer)


class Heroes(Base):
    __tablename__ = "heroes"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(VARCHAR)
    localized_name = Column(VARCHAR)


class Items(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(VARCHAR)


class Matches(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, nullable=False)
    cluster_region_id = Column(Integer, ForeignKey("cluster_regions.id"))
    start_time = Column(Integer)
    duration = Column(Integer)
    tower_status_radiant = Column(Integer)
    tower_status_dire = Column(Integer)
    barracks_status_radiant = Column(Integer)
    barracks_status_dire = Column(Integer)
    first_blood_time = Column(Integer)
    game_mode = Column(Integer)
    radiant_win = Column(Boolean)
    negative_votes = Column(Integer)
    positive_votes = Column(Integer)


class Matches_players_details(Base):
    __tablename__ = "matches_players_details"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    hero_id = Column(Integer, ForeignKey("heroes.id"))
    player_slot = Column(Integer)
    gold = Column(Integer)
    gold_spent = Column(Integer)
    gold_spent_per_min = Column(Integer)
    xp_per_min = Column(Integer)
    kills = Column(Integer)
    deaths = Column(Integer)
    assists = Column(Integer)
    denies = Column(Integer)
    last_hits = Column(Integer)
    stuns = Column(Integer)
    hero_damage = Column(Integer)
    hero_healing = Column(Integer)
    tower_damage = Column(Integer)
    item_id_1 = Column(Integer, ForeignKey("items.id"))
    item_id_2 = Column(Integer, ForeignKey("items.id"))
    item_id_3 = Column(Integer, ForeignKey("items.id"))
    item_id_4 = Column(Integer, ForeignKey("items.id"))
    item_id_5 = Column(Integer, ForeignKey("items.id"))
    item_id_6 = Column(Integer, ForeignKey("items.id"))
    level = Column(Integer)
    leaver_status = Column(Integer)
    xp_hero = Column(Integer)
    xp_creep = Column(Integer)
    xp_roshan = Column(Integer)
    xp_other = Column(Integer)
    gold_other = Column(Integer)
    gold_death = Column(Integer)
    gold_buyback = Column(Integer)
    gold_abandon = Column(Integer)
    gold_sell = Column(Integer)
    gold_destroying_structure = Column(Integer)
    gold_killing_heroes = Column(Integer)
    gold_killing_creeps = Column(Integer)
    gold_killing_roshan = Column(Integer)
    gold_killing_couriers = Column(Integer)


class Patches(Base):
    __tablename__ = "patches"

    id = Column(Integer, primary_key=True)
    name = Column(VARCHAR, nullable=False)
    release_date = Column(TIMESTAMP, nullable=False)


class Purchase_logs(Base):
    __tablename__ = "purchase_logs"

    id = Column(Integer, primary_key=True)
    match_player_detail_id = Column(Integer, ForeignKey("matches_players_details.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    time = Column(Integer)


class Players(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(VARCHAR)
    nick = Column(VARCHAR)

