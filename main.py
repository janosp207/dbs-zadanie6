import os

import psycopg2
from fastapi import FastAPI, Depends
from psycopg2.extras import RealDictCursor
from sqlalchemy import func, extract, and_, or_, not_, case, desc, cast, between
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import coalesce, count

from models import *

from database import connect_to_db

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/v4/patches")
async def getPatches(db_conn: Session = Depends(connect_to_db)):
    subquery1 = db_conn.query(Patches.name.label('patch_version'),
                              func.extract('epoch', Patches.release_date).label('patch_start_date'),
                              func.extract('epoch',
                                           func.lead(Patches.release_date).over(order_by=Patches.release_date)).label(
                                  'patch_end_date'),
                              ).select_from(Patches).order_by(Patches.release_date).subquery()

    res = db_conn.query(subquery1.c.patch_version,
                        subquery1.c.patch_start_date,
                        subquery1.c.patch_end_date,
                        func.round(Matches.duration / 60.0, 2).label('match_duration'),
                        Matches.start_time, Matches.id.label('match_id')). \
        join(Matches, and_(Matches.start_time <= subquery1.c.patch_end_date,
                           Matches.start_time >= subquery1.c.patch_start_date)). \
        group_by(subquery1.c.patch_version, subquery1.c.patch_start_date, subquery1.c.patch_end_date,
                 Matches.start_time, Matches.id). \
        order_by(subquery1.c.patch_version).all()

    patches = {
        "patches": []
    }
    tmpVersion = ""
    index = -1

    for patch in res:
        if tmpVersion == patch.patch_version:
            patches['patches'][index]['matches'].append({
                "duration": float(patch.match_duration),
                "match_id": patch.match_id,
            })
        else:
            tmpVersion = patch.patch_version
            index += 1
            patches['patches'].append({
                "patch_version": patch.patch_version,
                "patch_start_date": patch.patch_start_date,
                "patch_end_date": patch.patch_end_date,
                "matches": [{
                    "duration": float(patch.match_duration),
                    "match_id": patch.match_id,
                }]
            })
    return patches


@app.get("/v4/players/{player_id}/game_exp")
async def getGameExp(player_id: int, db_conn: Session = Depends(connect_to_db)):
    subquery1 = db_conn.query(
        Players.id.label('id'),
        func.coalesce(Players.nick, 'unknown').label('player_nick'),
        Heroes.localized_name.label('hero_localized_name'),
        func.round(Matches.duration / 60.0, 2).label('match_duration_minutes'),

        (func.coalesce(Matches_players_details.xp_hero, 0) +
         func.coalesce(Matches_players_details.xp_creep, 0) +
         func.coalesce(Matches_players_details.xp_other, 0) +
         func.coalesce(Matches_players_details.xp_roshan, 0)).label('experiences_gained'),

        Matches_players_details.level.label('level_gained'),
        (and_(Matches_players_details.player_slot >= 0, Matches_players_details.player_slot <= 4)).label('a'),
        Matches.radiant_win.label('b'),
        Matches_players_details.match_id.label('match_id')).select_from(Players). \
        join(Matches_players_details, Players.id == Matches_players_details.player_id). \
        join(Matches, Matches.id == Matches_players_details.match_id). \
        join(Heroes, Heroes.id == Matches_players_details.hero_id). \
        filter(Players.id == player_id). \
        order_by(Matches_players_details.match_id).subquery()

    res = db_conn.query(
        subquery1.c.id,
        subquery1.c.player_nick,
        subquery1.c.hero_localized_name,
        subquery1.c.match_duration_minutes,
        subquery1.c.experiences_gained,
        subquery1.c.level_gained,
        not_((or_(and_(subquery1.c.a, not_(subquery1.c.b)), and_(not_(subquery1.c.a), subquery1.c.b)))).label('winner'),
        subquery1.c.match_id).select_from(subquery1).all()

    player = {
        'id': res[0].id,
        'player_nick': res[0].player_nick,
        'matches': [],
    }

    for match in res:
        player['matches'].append({
            'experiences_gained': match.experiences_gained,
            'match_duration_minutes': match.match_duration_minutes,
            'hero_localized_name': match.hero_localized_name,
            'level_gained': match.level_gained,
            'match_id': match.match_id,
            'winner': match.winner,
        })

    return player


@app.get("/v4/players/{player_id}/game_objectives/")
async def getGameObjectives(player_id: int, db_conn: Session = Depends(connect_to_db)):
    res = db_conn.query(
        Players.id.label('id'),
        func.coalesce(Players.nick, 'unknown').label('player_nick'),
        Heroes.localized_name.label('hero_localized_name'),
        Matches_players_details.match_id.label('match_id'),
        func.coalesce(Game_objectives.subtype, 'NO_ACTION').label('hero_action'),
        case(
            (func.count(Game_objectives.subtype) == 0, 1),
            else_=func.count(Game_objectives.subtype)
        ).label('count'),
    ).select_from(Players). \
        join(Matches_players_details, Players.id == Matches_players_details.player_id). \
        join(Heroes, Heroes.id == Matches_players_details.hero_id). \
        join(Game_objectives, Game_objectives.match_player_detail_id_1 == Matches_players_details.id, full=True,
             isouter=True). \
        filter(Players.id == player_id). \
        group_by(func.coalesce(Game_objectives.subtype, 'NO_ACTION'), Matches_players_details.match_id, Players.id,
                 Heroes.localized_name). \
        order_by(Matches_players_details.match_id, func.coalesce(Game_objectives.subtype, 'NO_ACTION')).all()

    index = -1
    tempMatchId = -1

    player = {
        'id': res[0].id,
        'player_nick': res[0].player_nick,
        'matches': []
    }

    for match in res:
        if tempMatchId == match.match_id:
            player['matches'][index]['actions'].append({
                'hero_action': match.hero_action,
                'count': match.count,
            })
        else:
            tempMatchId = match.match_id
            index += 1
            player['matches'].append({
                'match_id': match.match_id,
                'hero_localized_name': match.hero_localized_name,
                'actions': [{
                    'hero_action': match.hero_action,
                    'count': match.count,
                }]
            })

    return player


@app.get("/v4/players/{player_id}/abilities/")
async def getAbilities(player_id: int, db_conn: Session = Depends(connect_to_db)):
    res = db_conn.query(
        Players.id.label('id'),
        func.coalesce(Players.nick, 'unknown').label('player_nick'),
        Heroes.localized_name.label('hero_localized_name'),
        Matches_players_details.match_id.label('match_id'),
        Abilities.name.label('ability_name'),
        func.count(Abilities.name).label('count'),
        func.max(Ability_upgrades.level).label('upgrade_level'),
    ).select_from(Matches_players_details). \
        join(Players, Players.id == Matches_players_details.player_id). \
        join(Heroes, Heroes.id == Matches_players_details.hero_id). \
        join(Ability_upgrades, Ability_upgrades.match_player_detail_id == Matches_players_details.id). \
        join(Abilities, Abilities.id == Ability_upgrades.ability_id). \
        filter(Players.id == player_id). \
        group_by(Abilities.name, Players.id, func.coalesce(Players.nick, 'unknown'), Heroes.localized_name,
                 Matches_players_details.match_id). \
        order_by(Matches_players_details.match_id, Abilities.name).all()

    index = -1
    tempMatchId = -1

    player = {
        'id': res[0].id,
        'player_nick': res[0].player_nick,
        'matches': []
    }

    for match in res:
        if tempMatchId == match.match_id:
            player['matches'][index]['abilities'].append({
                'ability_name': match.ability_name,
                'count': match.count,
                'upgrade_level': match.upgrade_level
            })
        else:
            tempMatchId = match.match_id
            index += 1
            player['matches'].append({
                'match_id': match.match_id,
                'hero_localized_name': match.hero_localized_name,
                'abilities': [{
                    'ability_name': match.ability_name,
                    'count': match.count,
                    'upgrade_level': match.upgrade_level
                }]
            })

    return player


@app.get("/v4/matches/{match_id}/top_purchases/")
async def getTopPurchases(match_id: int, db_conn: Session = Depends(connect_to_db)):
    subquery1 = db_conn.query(
        Matches_players_details.id.label('madch_id')
    ).select_from(Matches_players_details). \
        join(Matches, Matches.id == Matches_players_details.match_id). \
        filter(
        and_(
            Matches.id == match_id,
            or_(
                and_(Matches.radiant_win == True,
                     and_(Matches_players_details.player_slot >= 0, Matches_players_details.player_slot <= 4)),
                and_(Matches.radiant_win == False,
                     and_(Matches_players_details.player_slot >= 128, Matches_players_details.player_slot <= 132)),
            )
        )
    )

    subquery2 = db_conn.query(
        Purchase_logs.match_player_detail_id.label('mpd_id'),
        Matches.id.label('match_id'),
        Heroes.id.label('hero_id'),
        Heroes.localized_name.label('localized_name'),
        Items.name.label('item_name'),
        Items.id.label('item_id'),
        func.count(Items.name).label('amount')
    ).select_from(Purchase_logs). \
        join(Items, Items.id == Purchase_logs.item_id). \
        join(Matches_players_details, Matches_players_details.id == Purchase_logs.match_player_detail_id). \
        join(Heroes, Matches_players_details.hero_id == Heroes.id). \
        join(Matches, Matches_players_details.match_id == Matches.id). \
        filter(Purchase_logs.match_player_detail_id.in_(subquery1)). \
        group_by(Items.name, Purchase_logs.match_player_detail_id, Heroes.localized_name, Heroes.id, Matches.id,
                 Items.id). \
        order_by(Heroes.id, func.count(Items.name).desc(), Items.name).subquery()

    subquery3 = db_conn.query(
        subquery2.c.mpd_id,
        subquery2.c.match_id,
        subquery2.c.hero_id,
        subquery2.c.localized_name,
        subquery2.c.item_name,
        subquery2.c.item_id,
        subquery2.c.amount,
        func.row_number().over(partition_by=subquery2.c.hero_id).label('row_number')). \
        select_from(subquery2).subquery()

    res = db_conn.query(
        subquery3.c.match_id,
        subquery3.c.hero_id,
        subquery3.c.localized_name,
        subquery3.c.item_id,
        subquery3.c.item_name,
        subquery3.c.amount,
        subquery3.c.row_number
    ).select_from(subquery3). \
        filter(subquery3.c.row_number <= 5).all()

    tempHeroId = 0

    match = {
        'id': int(match_id),
        'heroes': [],
    }

    for row in res:
        if tempHeroId != row.hero_id:
            match['heroes'].append({
                'id': row.hero_id,
                'name': row.localized_name,
                'top_purchases': [{
                    'id': row.item_id,
                    'name': row.item_name,
                    'count': int(row.amount)
                }]
            })
        else:
            match['heroes'][len(match['heroes']) - 1]['top_purchases'].append({
                'id': row.item_id,
                'name': row.item_name,
                'count': int(row.amount)
            })
        tempHeroId = row.hero_id

    return match


@app.get("/v4/abilities/{ability_id}/usage/")
async def getAbilityUsage(ability_id: int, db_conn: Session = Depends(connect_to_db)):
    subquery1 = db_conn.query(
        Heroes.id.label('hero_id'),
        Heroes.localized_name.label('localized_name'),
        Abilities.id.label('ability_id'),
        Abilities.name.label('ability_name'),
        case([
            (Ability_upgrades.time * 1.0 / Matches.duration * 1.0 >= 1, '100-109'),
            (Ability_upgrades.time * 1.0 < Matches.duration * 0.1, '0-9'),
            (Ability_upgrades.time * 1.0 < Matches.duration * 0.2, '10-19'),
            (Ability_upgrades.time * 1.0 < Matches.duration * 0.3, '20-29'),
            (Ability_upgrades.time * 1.0 < Matches.duration * 0.4, '30-39'),
            (Ability_upgrades.time * 1.0 < Matches.duration * 0.5, '40-49'),
            (Ability_upgrades.time * 1.0 < Matches.duration * 0.6, '50-59'),
            (Ability_upgrades.time * 1.0 < Matches.duration * 0.7, '60-69'),
            (Ability_upgrades.time * 1.0 < Matches.duration * 0.8, '70-79'),
            (Ability_upgrades.time * 1.0 < Matches.duration * 0.9, '80-89'),
            (Ability_upgrades.time * 1.0 < Matches.duration * 1.0, '90-99'),
        ]).label('bucket'),
        case([
            (and_(Matches_players_details.player_slot <= 4, Matches.radiant_win == True), True),
            (and_(Matches_players_details.player_slot >= 128, Matches.radiant_win == False), True)
        ],
            else_=False).label("did_win")
    ).select_from(Matches_players_details). \
        join(Matches, Matches.id == Matches_players_details.match_id). \
        join(Ability_upgrades, Ability_upgrades.match_player_detail_id == Matches_players_details.id). \
        join(Heroes, Heroes.id == Matches_players_details.hero_id). \
        join(Abilities, Abilities.id == Ability_upgrades.ability_id). \
        filter(Abilities.id == ability_id).subquery()

    subquery2 = db_conn.query(
        subquery1.c.ability_id,
        subquery1.c.ability_name,
        subquery1.c.hero_id,
        subquery1.c.localized_name,
        subquery1.c.bucket,
        subquery1.c.did_win,
        func.count(subquery1.c.did_win).label('count')
    ).select_from(subquery1). \
        group_by(subquery1.c.ability_id, subquery1.c.ability_name, subquery1.c.hero_id, subquery1.c.localized_name,
                 subquery1.c.bucket, subquery1.c.did_win). \
        order_by(func.count(subquery1.c.did_win).desc()).subquery()

    subquery3 = db_conn.query(
        subquery2.c.ability_id,
        subquery2.c.ability_name,
        subquery2.c.hero_id,
        subquery2.c.localized_name,
        subquery2.c.bucket,
        subquery2.c.did_win,
        subquery2.c.count,
        func.row_number().over(partition_by=(subquery2.c.did_win, subquery2.c.hero_id), order_by=subquery2.c.count.desc()).label('row_number')
    ).select_from(subquery2).subquery()

    res = db_conn.query(
        subquery3.c.ability_id,
        subquery3.c.ability_name,
        subquery3.c.hero_id,
        subquery3.c.localized_name,
        subquery3.c.bucket,
        subquery3.c.did_win,
        subquery3.c.count
    ).select_from(subquery3).filter(subquery3.c.row_number == 1).all()

    ability = {
        'id': res[0].ability_id,
        'name': res[0].ability_name,
        'heroes': []
    }

    tempHeroId = 0

    for row in res:
        if(tempHeroId != row.hero_id):
            ability['heroes'].append({
                'id': row.hero_id,
                'name': row.localized_name,
            })
        if(row.did_win):
            ability['heroes'][-1]['usage_winners'] = {
                'bucket': row.bucket,
                'count': int(row.count)
            }
        else:
            ability['heroes'][-1]['usage_loosers'] = {
                'bucket': row.bucket,
                'count': int(row.count)
            }
        tempHeroId = row.hero_id

    return ability

@app.get("/v4/statistics/tower_kills/")
async def getTowerKills(db_conn: Session = Depends(connect_to_db)):
    subquery1 = db_conn.query(
        Matches_players_details.match_id.label('match_id'),
        Game_objectives.subtype.label('subtype'),
        Game_objectives.time.label('time'),
        Game_objectives.id.label('objective_id'),
        Heroes.id.label('hero_id'),
        Heroes.localized_name.label('localized_name'),
    ).select_from(Matches_players_details). \
        join(Game_objectives, Matches_players_details.id == Game_objectives.match_player_detail_id_1). \
        join(Heroes, Heroes.id == Matches_players_details.hero_id). \
        filter(Game_objectives.subtype == 'CHAT_MESSAGE_TOWER_KILL').\
        order_by(Matches_players_details.match_id, Game_objectives.time).subquery()

    subquery2 = db_conn.query(
        subquery1.c.match_id,
        subquery1.c.subtype,
        subquery1.c.time,
        subquery1.c.objective_id,
        subquery1.c.hero_id,
        subquery1.c.localized_name,
        (func.row_number().over(order_by=subquery1.c.objective_id) - func.row_number().over(partition_by=subquery1.c.localized_name, order_by=(subquery1.c.match_id, subquery1.c.time))). \
            label('grouped')).select_from(subquery1).subquery()

    subquery3 = db_conn.query(
        subquery2.c.hero_id,
        subquery2.c.localized_name,
        func.count().label('count')
    ).select_from(subquery2).group_by(subquery2.c.grouped, subquery2.c.match_id, subquery2.c.localized_name, subquery2.c.hero_id).subquery()

    res = db_conn.query(
        subquery3.c.hero_id,
        subquery3.c.localized_name,
        func.max(subquery3.c.count).label('tower_kills')
    ).select_from(subquery3).group_by(subquery3.c.hero_id, subquery3.c.localized_name).\
        order_by(func.max(subquery3.c.count).desc(), subquery3.c.localized_name).all()

    statistics = {
        'heroes': [],
    }

    for row in res:
        statistics['heroes'].append({
            'id': row.hero_id,
            'name': row.localized_name,
            'tower_kills': int(row.tower_kills)
        })

    return statistics
