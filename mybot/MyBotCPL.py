#!/usr/bin/env python3
# Python 3.6

import math
import random
import logging
from enum import Enum

# Import the Halite SDK
import hlt
from hlt import constants
from hlt.positionals import Direction, Position

""" <<<Game Begin>>> """
game = hlt.Game()
game.ready("CPL")

logging.info(f"Successfully created bot! My Player ID is {game.my_id}.")

class BotClass(Enum):
    Normal = 1
    Blocker = 2

class BotState(Enum):
    SEARCH = 1
    MOVE_TO_TARGET = 2
    COLLECTING = 3
    BACK_TO_HOME = 4

""" <<<Game Loop>>> """
ship_stage = {}

# Utility Functions
def get_neighbors(position):
    """Returns valid neighboring positions."""
    directions = [Direction.North, Direction.South, Direction.East, Direction.West]
    neighbors = []
    for direction in directions:
        neighbors.append(position.directional_offset(direction))
    return neighbors

def heuristic(pos1, pos2):
    """Manhattan distance heuristic."""
    return abs(pos1.x - pos2.x) + abs(pos1.y - pos2.y)

def get_opponent_shipyards(game):
    """Find all opponent shipyards on the map."""
    opponent_shipyards = []
    for player_id, player in game.players.items():
        if player_id != game.my_id:  # Exclude my shipyard
            opponent_shipyards.append(player.shipyard.position)
    return opponent_shipyards

def a_star(game_map, source, target):
    """A* pathfinding to navigate from source to target."""
    open_set = [source]
    closed_set = set()
    came_from = {}

    gScore = {source: 0}
    fScore = {source: heuristic(source, target)}

    while open_set:
        current = min(open_set, key=lambda pos: fScore.get(pos, float('inf')))

        if current == target:
            # Reconstruct path
            path = []
            while current in came_from:
                path.insert(0, current)
                current = came_from[current]
            return path  # Return the path to follow

        open_set.remove(current)
        closed_set.add(current)

        for neighbor in get_neighbors(current):
            if neighbor in closed_set or game_map[neighbor].is_occupied:
                continue

            tentative_gScore = gScore[current] + game_map[neighbor].halite_amount / 10  # Example cost

            if neighbor not in open_set:
                open_set.append(neighbor)

            if tentative_gScore >= gScore.get(neighbor, float('inf')):
                continue

            came_from[neighbor] = current
            gScore[neighbor] = tentative_gScore
            fScore[neighbor] = gScore[neighbor] + heuristic(neighbor, target)

    return [] 

while True:
    game.update_frame()
    me = game.me
    game_map = game.game_map

    normal_count = 0
    blocker_count = 0
    blocker_limit = 4 
    minimum_normals = 5 

    opponent_shipyards = get_opponent_shipyards(game)
    logging.info(f"Opponent Shipyards: {opponent_shipyards}")


    command_queue = []

    for ship in me.get_ships():

        if ship.id not in ship_stage:
            if normal_count < minimum_normals:
                ship_stage[ship.id] = (BotState.MOVE_TO_TARGET, BotClass.Normal)
                normal_count += 1
            elif blocker_count < blocker_limit:
                ship_stage[ship.id] = (BotState.SEARCH, BotClass.Blocker)
                blocker_count += 1

        state, role = ship_stage[ship.id]

        if role == BotClass.Normal:
            if state == BotState.MOVE_TO_TARGET:
                halite_values = {}
                direction_values = {}
                for direction in [Direction.North, Direction.South, Direction.East, Direction.West]:
                    pos = ship.position.directional_offset(direction)
                    if not game_map[pos].is_occupied:
                        halite_values[pos] = game_map[pos].halite_amount
                        direction_values[pos] = direction

                if halite_values:
                    highest_halite_pos = max(halite_values, key=halite_values.get)
                    direction = direction_values[highest_halite_pos]
                    game_map[ship.position.directional_offset(direction)].mark_unsafe(ship)
                    command_queue.append(ship.move(direction))
                else:
                    command_queue.append(ship.stay_still())

                ship_stage[ship.id] = (BotState.COLLECTING, role)

            elif state == BotState.COLLECTING:
                command_queue.append(ship.stay_still())
                if ship.halite_amount >= constants.MAX_HALITE or game_map[ship.position].halite_amount < 20:
                    ship_stage[ship.id] = (BotState.BACK_TO_HOME if ship.halite_amount >= constants.MAX_HALITE else BotState.MOVE_TO_TARGET, role)

            elif state == BotState.BACK_TO_HOME:
                path = a_star(game_map, ship.position, me.shipyard.position)
                if path:
                    next_position = path[0]
                    direction = game_map.get_unsafe_moves(ship.position, next_position)[0]
                    game_map[ship.position.directional_offset(direction)].mark_unsafe(ship)
                    command_queue.append(ship.move(direction))
                else:
                    command_queue.append(ship.stay_still())

                if ship.position == me.shipyard.position:
                    ship_stage[ship.id] = (BotState.MOVE_TO_TARGET, role)

        elif role == BotClass.Blocker:

            if opponent_shipyards:
                target_shipyard = opponent_shipyards[0]  
                directions = [Direction.North, Direction.South, Direction.East, Direction.West]
                blocker_target = target_shipyard.directional_offset(directions[blocker_count % 4])

                path = a_star(game_map, ship.position, blocker_target)
                if path:
                    next_position = path[0]
                    direction = game_map.get_unsafe_moves(ship.position, next_position)[0]
                    game_map[ship.position.directional_offset(direction)].mark_unsafe(ship)
                    command_queue.append(ship.move(direction))
                else:
                    command_queue.append(ship.stay_still())
                    
    logging.info(f"Normal Bots: {normal_count}, Blocker Bots: {blocker_count}")


    # Spawn ships if appropriate
    if game.turn_number <= constants.MAX_TURNS - 50 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    game.end_turn(command_queue)
